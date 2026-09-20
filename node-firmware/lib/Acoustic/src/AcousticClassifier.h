#pragma once
// TFLite Micro wrapper around the existing INT8 model (ml/models/final/forest_acoustic_int8.tflite,
// embedded by tools/embed_model.py). No model is trained or converted here.
//
// Memory: the tensor arena is allocated once in begin(); classify() performs no allocation.

#include <cstddef>
#include <cstdint>

#include "AudioPreprocessor.h"

namespace forest::acoustic {

struct ClassifierResult {
    int classIndex = -1;         // 0=background 1=chainsaw 2=gunshot (tables::kClassNames)
    float confidence = 0.0f;     // softmax probability of classIndex
    float probs[3] = {0, 0, 0};
    int8_t raw[3] = {0, 0, 0};   // raw INT8 output tensor
    uint32_t invokeUs = 0;       // TFLite Micro Invoke() time
};

class AcousticClassifier {
public:
    // Loads the model, allocates the arena and VERIFIES that the model's tensor shapes,
    // types and quantisation match the constants the preprocessing was generated for.
    // Returns false (and logs why) on any mismatch - never runs on a model it cannot verify.
    bool begin(size_t arenaBytes);
    bool ready() const { return ready_; }

    // Input tensor to be filled by AudioPreprocessor (kTensorSize int8 values).
    int8_t* inputBuffer() const;
    bool invoke(ClassifierResult& result);

    size_t arenaUsedBytes() const;
    size_t arenaSizeBytes() const { return arenaBytes_; }

private:
    bool ready_ = false;
    size_t arenaBytes_ = 0;
    uint8_t* arena_ = nullptr;
    struct Impl;
    Impl* impl_ = nullptr;
};

}  // namespace forest::acoustic
