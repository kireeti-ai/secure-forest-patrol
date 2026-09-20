# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.5781 | 0.4636 | 0.4767 |
| moderate | 15.0 | 0.5970 | 0.2868 | 0.3077 |
| strong | 5.0 | 0.8018 | 0.2974 | 0.0460 |
