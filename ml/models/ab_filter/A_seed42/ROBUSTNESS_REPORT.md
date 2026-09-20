# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.6177 | 0.4733 | 0.4301 |
| moderate | 15.0 | 0.6187 | 0.2910 | 0.2813 |
| strong | 5.0 | 0.8405 | 0.3044 | 0.0000 |
