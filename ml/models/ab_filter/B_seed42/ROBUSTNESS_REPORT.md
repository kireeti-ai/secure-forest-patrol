# Robustness Report

Synthetic Gaussian noise added to Mel-spectrogram features of the frozen `test_v1` set at evaluation time only (original test data on disk untouched). Evaluated with the final INT8 TFLite model.

| Condition | SNR (dB) | Accuracy | Macro-F1 | Background False-Alarm Rate |
|---|---|---|---|---|
| clean | N/A (clean) | 0.4271 | 0.3624 | 0.6564 |
| moderate | 15.0 | 0.4162 | 0.2836 | 0.5660 |
| strong | 5.0 | 0.0462 | 0.0336 | 0.9691 |
