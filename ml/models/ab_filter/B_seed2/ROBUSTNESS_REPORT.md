# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.6503 | 0.4945 | 0.3885 |
| moderate | 15.0 | 0.6177 | 0.3638 | 0.3880 |
| strong | 5.0 | 0.1454 | 0.0871 | 0.9916 |
