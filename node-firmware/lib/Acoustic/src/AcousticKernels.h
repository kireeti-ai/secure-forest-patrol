#pragma once
// Custom TFLite Micro kernel: INT8 FULLY_CONNECTED with PER-CHANNEL weight quantisation.
//
// Why this exists: the trained model (ml/models/final/forest_acoustic_int8.tflite) stores its two
// dense layers with one weight scale per output channel (TFLite's default). TFLite Micro's stock
// FULLY_CONNECTED kernel (both tanakamasayuki/TensorFlowLite_ESP32 1.0.0 and nickjgniklu/ESP_TF 2.1.1)
// applies only the FIRST channel's scale to every output, so the device computed different layer
// outputs than the trained model (e.g. [5,7,...] instead of [4,21,...]) and over-confident
// probabilities. This kernel reproduces TFLite's reference behaviour. The model is unchanged.
//
// Verified against Python TFLite by tools/verify_tflm_parity.py and on hardware in test mode 3.

#include "tensorflow/lite/c/common.h"

namespace forest::acoustic {
TfLiteRegistration RegisterFullyConnectedPerChannel();
}  // namespace forest::acoustic
