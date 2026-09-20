#!/usr/bin/env python3
"""
Simple training-only augmentation for Mel-spectrogram features, following
ml/configs/augmentation.yaml (kept intentionally simple):
  - gain variation: random dB offset added to the (already dB-scale) mel spec
  - time shift: circular roll along the time axis
  - background noise mixing: mix in a small amount of a random background-class
    spectrogram from the same batch (mel-domain approximation of waveform mixing)
  - spec masking (SpecAugment): random time and frequency band masking
"""
import numpy as np


def augment_batch(mel_batch: np.ndarray, y_batch: np.ndarray, background_idx: int,
                   rng: np.random.RandomState, prob: float = 0.5) -> np.ndarray:
    """mel_batch: (N, n_mels, T) dB-scale mel spectrograms. Returns augmented copy."""
    out = mel_batch.copy()
    n, n_mels, T = out.shape
    bg_pool_idx = np.where(y_batch == background_idx)[0]

    for i in range(n):
        if rng.rand() > prob:
            continue

        # gain variation
        if rng.rand() < 0.4:
            gain_db = rng.uniform(-6, 6)
            out[i] += gain_db

        # time shift
        if rng.rand() < 0.3:
            max_shift = max(1, int(0.1 * T))
            shift = rng.randint(-max_shift, max_shift + 1)
            out[i] = np.roll(out[i], shift, axis=1)

        # background noise mixing (mel-domain mix-in of a random background sample)
        if rng.rand() < 0.3 and len(bg_pool_idx) > 0:
            noise = mel_batch[rng.choice(bg_pool_idx)]
            alpha = rng.uniform(0.05, 0.25)
            out[i] = np.log(np.exp(out[i]) * (1 - alpha) + np.exp(noise) * alpha + 1e-8) \
                if False else out[i] * (1 - alpha) + noise * alpha  # linear mix in dB domain (simple approximation)

        # SpecAugment time mask
        if rng.rand() < 0.3:
            for _ in range(2):
                mask_w = rng.randint(1, max(2, int(0.2 * T)))
                start = rng.randint(0, max(1, T - mask_w))
                out[i][:, start:start + mask_w] = out[i].mean()

        # SpecAugment frequency mask
        if rng.rand() < 0.3:
            for _ in range(2):
                mask_h = rng.randint(1, max(2, int(0.2 * n_mels)))
                start = rng.randint(0, max(1, n_mels - mask_h))
                out[i][start:start + mask_h, :] = out[i].mean()

    return out
