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
                   rng: np.random.RandomState, prob: float = 0.5, noise_snr_prob: float = 0.15) -> np.ndarray:
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

        # background noise mixing: convert dB-scale mel back to power, mix linearly (how sound
        # actually combines physically), then back to dB. Mixing the dB values directly (the old
        # approach) has no physical basis and under-represents real noisy conditions, which is a
        # likely contributor to the 5 dB-SNR accuracy collapse in ml/reports/ROBUSTNESS_REPORT.md.
        if rng.rand() < 0.3 and len(bg_pool_idx) > 0:
            noise = mel_batch[rng.choice(bg_pool_idx)]
            alpha = rng.uniform(0.05, 0.25)
            sig_power = np.power(10.0, out[i] / 10.0)
            noise_power = np.power(10.0, noise / 10.0)
            mixed_power = sig_power * (1 - alpha) + noise_power * alpha
            out[i] = 10.0 * np.log10(mixed_power + 1e-12)

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

        # Additive Gaussian noise at a random SNR (3-25 dB). The model was never trained
        # against this perturbation type even though ml/reports/ROBUSTNESS_REPORT.md evaluates
        # against exactly it (add_noise_snr in robustness_eval.py) - without this, training
        # only ever sees clean-ish audio and collapses under real additive noise at eval time.
        if rng.rand() < noise_snr_prob:
            snr_db = rng.uniform(3.0, 25.0)
            signal_power = np.mean(out[i] ** 2)
            noise_power = signal_power / (10 ** (snr_db / 10))
            out[i] = out[i] + rng.normal(0, np.sqrt(max(noise_power, 1e-6)), size=out[i].shape)

    return out
