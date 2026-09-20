# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.4412 | 0.3664 | 0.6412 |
| moderate | 15.0 | 0.1430 | 0.0848 | 0.9955 |
| strong | 5.0 | 0.1392 | 0.0815 | 1.0000 |
