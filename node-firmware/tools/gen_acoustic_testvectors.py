#!/usr/bin/env python3
"""Reference vectors for validating the ESP32 acoustic preprocessing + model.

Everything is computed with the *training* code path in ml/ (its feature
extractor, its normalisation, its real INT8 TFLite model) - never re-derived:

  vectors.bin       host parity test input  (test/data/, git-ignored)
  --emit-header     AcousticTestVectors.h    known int8 tensors + expected
                    model outputs for FOREST_ACOUSTIC_TEST_MODE=3 on device

Also prints how much the deliberate deployment deviation (per-window peak
normalisation instead of per-recording) changes predictions.

Run:  python3 tools/gen_acoustic_testvectors.py [--emit-header] [--sensitivity N]
"""
import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
ML = ROOT / "ml"
FW = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML / "preprocessing"))
from feature_extraction import get_feature_extractor  # noqa: E402

import tensorflow as tf  # noqa: E402

meta = json.load(open(ML / "models" / "final" / "final_metadata.json"))
MEAN, STD = meta["feature_mean"], meta["feature_std"]
CLASSES = ["background", "chainsaw", "gunshot"]
interp = tf.lite.Interpreter(model_path=str(ML / "models" / "final" / "forest_acoustic_int8.tflite"))
interp.allocate_tensors()
IN = interp.get_input_details()[0]
OUT = interp.get_output_details()[0]
IN_SCALE, IN_ZP = IN["quantization"]
extractor = get_feature_extractor()


def features_db(audio_f32):
    return extractor.extract_mel_spectrogram(audio_f32.astype(np.float32), 16000).astype(np.float32)  # (40, 101)


def to_tensor(db):
    x = ((db - MEAN) / STD)[..., np.newaxis].astype(np.float32)
    return np.round(x / IN_SCALE + IN_ZP).astype(np.int8)  # (40, 101, 1) -- same as convert_tflite.py


def run_model(tensor):
    interp.set_tensor(IN["index"], tensor[np.newaxis])
    interp.invoke()
    return interp.get_tensor(OUT["index"])[0].astype(np.int8)


def peak_norm(a, target=10 ** (-3 / 20)):
    p = float(np.max(np.abs(a)))
    return a * (target / p) if p > 0 else a


def load_test_windows():
    df = pd.read_csv(ML / "datasets" / "v1" / "test_v1.csv")
    return df[df["quality_status"] == "OK"]


def pick(df, cls, n, seed=7):
    rows = df[df["class"] == cls].sample(n=n, random_state=seed)
    return [(r["sample_id"], ML / r["processed_path"], cls) for _, r in rows.iterrows()]


def build_vectors():
    df = load_test_windows()
    items = pick(df, "chainsaw", 2) + pick(df, "gunshot", 2) + pick(df, "background", 2)
    vecs = []
    for name, path, cls in items:
        pcm, sr = sf.read(path, dtype="int16")
        assert sr == 16000 and len(pcm) == 16000, (path, sr, len(pcm))
        vecs.append((name, cls, pcm))
    rng = np.random.default_rng(0)
    t = np.arange(16000) / 16000
    vecs.append(("synthetic_tone_1k", "synthetic", (0.5 * np.sin(2 * np.pi * 1000 * t) * 32767).astype(np.int16)))
    imp = np.zeros(16000); imp[4000] = 0.9; imp[4001:4200] = 0.9 * np.exp(-np.arange(199) / 30)
    vecs.append(("synthetic_impulse", "synthetic", (imp * 32767).astype(np.int16)))
    vecs.append(("synthetic_noise", "synthetic", (rng.normal(0, 0.05, 16000) * 32767).clip(-32768, 32767).astype(np.int16)))
    return vecs


def write_bin(vecs, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"ACV1" + struct.pack("<I", len(vecs)))
        for name, cls, pcm in vecs:
            audio = pcm.astype(np.float32) / 32768.0       # exactly what sf.read(float32) gives
            db = features_db(audio)
            tensor = to_tensor(db)
            out = run_model(tensor)
            audio_pn = peak_norm(audio)                    # deviation path (device peak-normalises)
            tensor_pn = to_tensor(features_db(audio_pn))
            out_pn = run_model(tensor_pn)
            nm = name.encode()[:63].ljust(64, b"\0")
            f.write(nm)
            f.write(pcm.astype("<i2").tobytes())
            f.write(db.astype("<f4").tobytes())            # [mel][frame]
            f.write(tensor[..., 0].astype(np.int8).tobytes())
            f.write(out.tobytes())
            f.write(tensor_pn[..., 0].astype(np.int8).tobytes())
            f.write(out_pn.tobytes())
            print(f"{name:34s} ref-class={cls:10s} model={CLASSES[int(np.argmax(out))]:10s} "
                  f"model(peak-norm window)={CLASSES[int(np.argmax(out_pn))]}")
        # Reference for the optional 80 Hz high-pass: scipy causal sosfilt on the 1 kHz tone + a 40 Hz tone.
        import scipy.signal
        sos = scipy.signal.butter(2, 80, btype="highpass", fs=16000, output="sos")
        for name, cls, pcm in vecs:
            if name in ("synthetic_tone_1k", "synthetic_impulse"):
                f.write(scipy.signal.sosfilt(sos, pcm.astype(np.float32) / 32768.0).astype("<f4").tobytes())
    print("wrote", path, path.stat().st_size, "bytes")


def emit_header(vecs, path):
    chosen = {}
    for name, cls, pcm in vecs:
        if cls in CLASSES and cls not in chosen:
            chosen[cls] = (name, pcm)
    lines = ["// GENERATED by tools/gen_acoustic_testvectors.py - do not edit.",
             "// Known int8 model inputs (from ml/ feature pipeline on real test-set windows) and the",
             "// outputs the real INT8 TFLite model produces for them in Python. FOREST_ACOUSTIC_TEST_MODE=3",
             "// feeds these to TFLite Micro on the device and compares.",
             "#pragma once", "#include <cstdint>", "", "namespace forest::acoustic {",
             "struct KnownVector { const char* name; int8_t expectedOutput[3]; int expectedClass; const int8_t* tensor; };"]
    entries = []
    for cls in CLASSES:
        name, pcm = chosen[cls]
        tensor = to_tensor(features_db(pcm.astype(np.float32) / 32768.0))
        out = run_model(tensor)
        sym = f"kVec_{cls}"
        flat = tensor[..., 0].reshape(-1)
        rows = [", ".join(str(int(v)) for v in flat[i:i + 24]) for i in range(0, len(flat), 24)]
        lines.append(f"inline constexpr int8_t {sym}[{len(flat)}] = {{\n    " + ",\n    ".join(rows) + "};")
        entries.append(f'    {{"{cls}:{name[:40]}", {{{", ".join(str(int(v)) for v in out)}}}, {int(np.argmax(out))}, {sym}}}')
    lines.append("inline constexpr KnownVector kKnownVectors[3] = {\n" + ",\n".join(entries) + "};")
    # One real 1 s window as PCM16, so the device can run the WHOLE chain (preprocess + model)
    # on real audio without a microphone and be compared with the ml/ tensor kVec_gunshot.
    name, pcm = chosen["gunshot"]
    rows = [", ".join(str(int(v)) for v in pcm[i:i + 24]) for i in range(0, len(pcm), 24)]
    lines.append(f"// PCM16 source window of kVec_gunshot ({name}).")
    lines.append(f"inline constexpr int16_t kKnownPcmGunshot[{len(pcm)}] = {{\n    " + ",\n    ".join(rows) + "};")
    lines += ["}  // namespace forest::acoustic", ""]
    path.write_text("\n".join(lines))
    print("wrote", path, path.stat().st_size, "bytes")


def sensitivity(n):
    """How much does per-window peak normalisation change predictions vs the training path?"""
    df = load_test_windows()
    parts = [df[df["class"] == c].sample(n=min(n, (df["class"] == c).sum()), random_state=1) for c in CLASSES]
    sub = pd.concat(parts)
    same = total = 0
    flips = {}
    for _, r in sub.iterrows():
        audio, _ = sf.read(ML / r["processed_path"], dtype="float32")
        a = int(np.argmax(run_model(to_tensor(features_db(audio)))))
        b = int(np.argmax(run_model(to_tensor(features_db(peak_norm(audio))))))
        total += 1; same += int(a == b)
        if a != b:
            flips[(CLASSES[a], CLASSES[b])] = flips.get((CLASSES[a], CLASSES[b]), 0) + 1
    print(f"peak-normalisation sensitivity: {same}/{total} predictions unchanged ({100*same/total:.1f}%); changed: {flips}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-header", action="store_true")
    ap.add_argument("--sensitivity", type=int, default=0)
    a = ap.parse_args()
    v = build_vectors()
    write_bin(v, FW / "test" / "data" / "vectors.bin")
    if a.emit_header:
        emit_header(v, FW / "lib" / "Acoustic" / "src" / "AcousticTestVectors.h")
    if a.sensitivity:
        sensitivity(a.sensitivity)
