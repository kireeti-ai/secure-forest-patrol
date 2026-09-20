# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.5979 | 0.4683 | 0.4329 |
| moderate | 15.0 | 0.4526 | 0.3393 | 0.6255 |
| strong | 5.0 | 0.6229 | 0.3669 | 0.3812 |
