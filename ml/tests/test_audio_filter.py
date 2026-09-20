"""Tests for the shared digital audio filter (preprocessing/audio_filter.py)."""
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import sosfilt

ML_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ML_ROOT / "preprocessing"))
from audio_filter import apply_filter, biquad_coefficients, design_filter  # noqa: E402
from feature_extraction import get_feature_extractor  # noqa: E402

SR = 16000
CFG = {"enabled": True, "type": "highpass", "order": 2, "cutoff_hz": 80}


def _signal(n=SR * 3, seed=0):
    rng = np.random.RandomState(seed)
    t = np.arange(n) / SR
    return (0.3 * np.sin(2 * np.pi * 1000 * t) + 0.05 * rng.randn(n) + 0.2).astype(np.float32)  # +0.2 DC


def test_disabled_is_identity():
    x = _signal()
    assert np.array_equal(apply_filter(x, SR, {"enabled": False}), x)
    assert np.array_equal(apply_filter(x, SR, None), x)


def test_filtered_valid_and_length_preserved():
    x = _signal()
    y = apply_filter(x, SR, CFG)
    assert y.shape == x.shape and y.dtype == np.float32
    assert np.all(np.isfinite(y))


def test_removes_dc_keeps_passband():
    x = _signal()
    y = apply_filter(x, SR, CFG)
    assert abs(y[SR:].mean()) < 0.01 < abs(x.mean())
    # 1 kHz tone amplitude preserved (+-2 %)
    assert abs(np.abs(np.fft.rfft(y[SR:2 * SR]))[1000] / np.abs(np.fft.rfft(x[SR:2 * SR]))[1000] - 1) < 0.02


def test_matches_manual_df2t_biquad():
    """Direct Form II Transposed reference (what the ESP32 runs) must equal sosfilt."""
    c = biquad_coefficients(SR, 80, 2, "highpass")
    x = _signal(4000)
    z1 = z2 = 0.0
    out = []
    for s in x.astype(np.float64):
        yv = c["b0"] * s + z1
        z1 = c["b1"] * s - c["a1"] * yv + z2
        z2 = c["b2"] * s - c["a2"] * yv
        out.append(yv)
    assert np.allclose(out, sosfilt(design_filter(), x.astype(np.float64)), atol=1e-9)


def test_streaming_chunks_equal_whole():
    """Carrying state across chunk boundaries == filtering the continuous stream."""
    x = _signal(SR).astype(np.float64)
    sos = design_filter()
    whole = sosfilt(sos, x)
    zi = np.zeros((sos.shape[0], 2))
    parts = []
    for i in range(0, len(x), 512):
        y, zi = sosfilt(sos, x[i:i + 512], zi=zi)
        parts.append(y)
    assert np.allclose(np.concatenate(parts), whole, atol=1e-12)


def test_feature_shapes_unchanged():
    ext = get_feature_extractor()
    x = _signal(SR)
    y = apply_filter(x, SR, CFG)
    assert ext.extract_mfcc(y, SR).shape == ext.extract_mfcc(x, SR).shape == (13, 101)
    mel = ext.extract_mel_spectrogram(y, SR)
    assert mel.shape == ext.extract_mel_spectrogram(x, SR).shape == (40, 101)
    assert np.all(np.isfinite(mel))


def test_int8_model_inference_on_filtered_audio():
    tf = pytest.importorskip("tensorflow")
    path = ML_ROOT / "models" / "final" / "forest_acoustic_int8.tflite"
    if not path.exists():
        pytest.skip("model not present")
    interp = tf.lite.Interpreter(model_path=str(path))
    interp.allocate_tensors()
    i, o = interp.get_input_details()[0], interp.get_output_details()[0]
    mel = get_feature_extractor().extract_mel_spectrogram(apply_filter(_signal(SR), SR, CFG), SR)
    x = np.round((mel[None, ..., None] - mel.mean()) / (mel.std() + 1e-8) / i["quantization"][0]
                 + i["quantization"][1]).clip(-128, 127).astype(np.int8)
    interp.set_tensor(i["index"], x)
    interp.invoke()
    assert interp.get_tensor(o["index"]).shape == (1, 3)
