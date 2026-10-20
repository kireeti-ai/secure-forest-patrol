# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.8117 | 0.6459 | 0.1920 |
| moderate | 15.0 | 0.8395 | 0.6117 | 0.0949 |
| strong | 5.0 | 0.7353 | 0.3874 | 0.1567 |
