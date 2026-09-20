#include "AcousticClassifier.h"

#include <Arduino.h>
#include <esp_heap_caps.h>

#include <TensorFlowLite_ESP32.h>
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include <cmath>

#include "AcousticKernels.h"
#include "AcousticModelData.h"
#include "AcousticTables.h"

namespace forest::acoustic {

struct AcousticClassifier::Impl {
    tflite::MicroErrorReporter errorReporter;
    tflite::MicroMutableOpResolver<6> resolver;
    const tflite::Model* model = nullptr;
    tflite::MicroInterpreter* interpreter = nullptr;
    TfLiteTensor* input = nullptr;
    TfLiteTensor* output = nullptr;
};

static bool nearlyEqual(float a, float b) { return std::fabs(a - b) <= 1e-7f * std::fmax(1.0f, std::fabs(b)); }

bool AcousticClassifier::begin(size_t arenaBytes) {
    if (ready_) return true;
    arenaBytes_ = arenaBytes;
    // Arena in internal RAM (fast); fall back to PSRAM if internal is short.
    arena_ = static_cast<uint8_t*>(heap_caps_aligned_alloc(16, arenaBytes, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
    if (arena_ == nullptr) arena_ = static_cast<uint8_t*>(heap_caps_aligned_alloc(16, arenaBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (arena_ == nullptr) { Serial.println("[ML] tensor arena allocation failed"); return false; }

    impl_ = new Impl();
    impl_->model = tflite::GetModel(kModelData);
    if (impl_->model->version() != TFLITE_SCHEMA_VERSION) {
        Serial.printf("[ML] model schema %lu != runtime %d\n", (unsigned long)impl_->model->version(), TFLITE_SCHEMA_VERSION);
        return false;
    }
    // Exactly the six builtin ops the model uses (ml/reports/QUANTIZATION_REPORT.json).
    impl_->resolver.AddConv2D();
    impl_->resolver.AddDepthwiseConv2D();
    // Custom per-channel kernel: the stock TFLM FULLY_CONNECTED ignores per-channel weight scales (see AcousticKernels.h).
    impl_->resolver.AddFullyConnected(RegisterFullyConnectedPerChannel());
    impl_->resolver.AddMaxPool2D();
    impl_->resolver.AddMean();
    impl_->resolver.AddSoftmax();

    static_assert(sizeof(tflite::MicroInterpreter) > 0, "");
    impl_->interpreter = new tflite::MicroInterpreter(impl_->model, impl_->resolver, arena_, arenaBytes, &impl_->errorReporter);
    if (impl_->interpreter->AllocateTensors() != kTfLiteOk) {
        Serial.printf("[ML] AllocateTensors failed (arena %u bytes too small or op missing)\n", (unsigned)arenaBytes);
        return false;
    }
    impl_->input = impl_->interpreter->input(0);
    impl_->output = impl_->interpreter->output(0);

    // Verify against what the preprocessing was generated for (tools/gen_acoustic_tables.py).
    const TfLiteTensor* in = impl_->input;
    const TfLiteTensor* out = impl_->output;
    bool ok = in->type == kTfLiteInt8 && in->dims->size == 4 && in->dims->data[0] == 1 &&
              in->dims->data[1] == tables::kNMels && in->dims->data[2] == tables::kNFrames && in->dims->data[3] == 1 &&
              nearlyEqual(in->params.scale, tables::kInputScale) && in->params.zero_point == tables::kInputZeroPoint;
    ok = ok && out->type == kTfLiteInt8 && out->dims->size == 2 && out->dims->data[0] == 1 && out->dims->data[1] == 3 &&
         nearlyEqual(out->params.scale, tables::kOutputScale) && out->params.zero_point == tables::kOutputZeroPoint;
    if (!ok) {
        Serial.printf("[ML] tensor mismatch: in type=%d scale=%.9g zp=%ld, out type=%d scale=%.9g zp=%ld\n",
                      (int)in->type, in->params.scale, (long)in->params.zero_point,
                      (int)out->type, out->params.scale, (long)out->params.zero_point);
        return false;
    }
    ready_ = true;
    Serial.printf("[ML] model loaded: %u bytes, arena used %u/%u bytes, input [1,%d,%d,1] int8 (scale %.6f zp %d)\n",
                  (unsigned)kModelDataLen, (unsigned)arenaUsedBytes(), (unsigned)arenaBytes_,
                  tables::kNMels, tables::kNFrames, in->params.scale, (int)in->params.zero_point);
    return true;
}

int8_t* AcousticClassifier::inputBuffer() const {
    return (impl_ && impl_->input) ? impl_->input->data.int8 : nullptr;
}

size_t AcousticClassifier::arenaUsedBytes() const {
    return impl_ && impl_->interpreter ? impl_->interpreter->arena_used_bytes() : 0;
}

bool AcousticClassifier::invoke(ClassifierResult& r) {
    if (!ready_) return false;
    const uint32_t t0 = micros();
    if (impl_->interpreter->Invoke() != kTfLiteOk) {
        Serial.println("[ML] Invoke failed");
        return false;
    }
    r.invokeUs = micros() - t0;
    const int8_t* q = impl_->output->data.int8;
    int best = 0;
    for (int i = 0; i < 3; ++i) {
        r.raw[i] = q[i];
        r.probs[i] = (static_cast<int>(q[i]) - tables::kOutputZeroPoint) * tables::kOutputScale;   // dequantise
        if (q[i] > q[best]) best = i;
    }
    r.classIndex = best;
    r.confidence = r.probs[best];
    return true;
}

}  // namespace forest::acoustic
