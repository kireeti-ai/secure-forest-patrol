# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.7216 | 0.5760 | 0.3010 |
| moderate | 15.0 | 0.5295 | 0.3793 | 0.4526 |
| strong | 5.0 | 0.0203 | 0.0133 | 1.0000 |
