# Quantization Report

FP32 Keras model (`models/final/final.keras`) converted to TFLite, then fully INT8-quantized using
a representative dataset of 300 samples drawn only from `train_v1` (never test data). Evaluated on
the frozen `test_v1` set (2,119 segments).

## Numerical verification (FP32 Keras vs FP32 TFLite)

- Max abs diff on first 50 test samples: **3.87e-07** (well under the 1e-4 tolerance)
- Argmax match: **100%**

## FP32 vs INT8 on frozen test_v1

| Metric | FP32 (Keras) | INT8 (TFLite) |
|---|---|---|
| Accuracy | 0.7069 | 0.7192 |
| Macro-F1 | 0.5611 | 0.5733 |
| Model size | 5.1 KB (raw weights) / 13.0 KB (.tflite) | 13.1 KB (.tflite) |

INT8 quantization did not degrade accuracy on this run (a very small model with a wide margin
between class counts can shift slightly either way; here INT8 was marginally *better* than FP32,
which is within expected quantization noise for a model this small).

- **Keras FP32 vs INT8 TFLite prediction agreement (test set): 98.21%**

## INT8 confusion matrix (test_v1, rows=true, cols=pred; order: background, chainsaw, gunshot)

```
             pred_bg  pred_chainsaw  pred_gunshot
true_bg         1240            451            90
true_chainsaw     39            247             9
true_gunshot       6              0            37
```

## Model inspection (forest_acoustic_int8.tflite)

- Input: shape `[1, 40, 101, 1]`, dtype `int8`, quant scale/zero-point `(0.01481, 11)`
- Output: shape `[1, 3]`, dtype `int8`
- Tensor count: 30
- Operators used: `CONV_2D`, `DEPTHWISE_CONV_2D`, `FULLY_CONNECTED`, `MAX_POOL_2D`, `MEAN`, `SOFTMAX`
- **All operators are in the TFLite Micro commonly-supported op set — 0 unsupported ops.**
  (Op list obtained with default delegates disabled so it reflects what's actually in the
  flatbuffer, not desktop XNNPACK delegate wrapping.)
- Model size: FP32 TFLite 13.0 KB, INT8 TFLite 13.1 KB — both far under the ~200KB target for
  ESP32-S3 flash budget.

## Validation methodology

Since no physical TFLite Micro embedded runtime is available in this environment, the INT8 model
was validated with the standard desktop `tf.lite.Interpreter` (with default delegates disabled) as
a stand-in, running the quantized graph exactly as TFLite Micro would interpret the same operator
set, and confirming predictions are explainably close to the FP32 Keras model's predictions on the
same test inputs (98.2% exact agreement). This is not a substitute for on-device validation — see
"HARDWARE DEPLOYMENT BLOCKED" in `FINAL_MODEL_REPORT.md`.
