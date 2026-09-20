#!/usr/bin/env python3
"""
Shared digital audio filter for SECURE FOREST PATROL (training AND ESP32 reference).

Causal 2nd-order Butterworth high-pass, one biquad section, fixed parameters.
Pipeline position: raw WAV -> resample 16 kHz -> mono -> FILTER -> 1 s windowing -> MFCC/Mel.
Only causal filtering (scipy.signal.sosfilt) is used: no filtfilt / zero-phase, since the
ESP32 processes a stream sample by sample. Filter state persists across the stream; in Python
the whole continuous recording is filtered BEFORE windowing so windows never restart the state.
"""
import numpy as np
from scipy.signal import butter, sosfilt


def design_filter(sr: int = 16000, cutoff_hz: float = 80.0, order: int = 2, kind: str = "highpass"):
    """Return second-order sections (n_sections x 6: b0 b1 b2 a0 a1 a2)."""
    return butter(order, cutoff_hz, btype=kind, fs=sr, output="sos")


def biquad_coefficients(sr: int = 16000, cutoff_hz: float = 80.0, order: int = 2, kind: str = "highpass"):
    """Coefficients normalised to a0 = 1 for the (single) biquad: b0, b1, b2, a1, a2."""
    sos = design_filter(sr, cutoff_hz, order, kind)
    b0, b1, b2, a0, a1, a2 = sos[0]
    return dict(b0=b0 / a0, b1=b1 / a0, b2=b2 / a0, a1=a1 / a0, a2=a2 / a0)


def apply_filter(audio: np.ndarray, sr: int, filter_cfg: dict = None) -> np.ndarray:
    """Causal filter of a continuous mono signal. No-op if filter_cfg is missing or disabled."""
    if not filter_cfg or not filter_cfg.get("enabled", False):
        return audio
    sos = design_filter(sr, filter_cfg.get("cutoff_hz", 80), filter_cfg.get("order", 2),
                        filter_cfg.get("type", "highpass"))
    return sosfilt(sos, audio.astype(np.float64)).astype(np.float32)


if __name__ == "__main__":
    print(biquad_coefficients())
