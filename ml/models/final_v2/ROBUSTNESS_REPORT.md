# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.8731 | 0.6794 | 0.0719 |
| moderate | 15.0 | 0.6966 | 0.3360 | 0.1937 |
| strong | 5.0 | 0.1109 | 0.0779 | 0.8911 |
