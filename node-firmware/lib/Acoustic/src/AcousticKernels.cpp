#include "AcousticKernels.h"

#include "tensorflow/lite/c/builtin_op_data.h"
#include "tensorflow/lite/kernels/internal/common.h"
#include "tensorflow/lite/kernels/internal/quantization_util.h"
#include "tensorflow/lite/kernels/kernel_util.h"
#include "tensorflow/lite/micro/kernels/kernel_util.h"
#include "tensorflow/lite/micro/micro_context.h"

namespace forest::acoustic {
namespace {

struct OpData {
    int32_t inputZeroPoint;
    int32_t outputZeroPoint;
    int32_t activationMin;
    int32_t activationMax;
    int32_t outputChannels;
    int32_t* multiplier;   // per output channel, allocated in the persistent arena
    int32_t* shift;
};

void* Init(TfLiteContext* context, const char*, size_t) {
    return context->AllocatePersistentBuffer(context, sizeof(OpData));
}

TfLiteStatus Prepare(TfLiteContext* context, TfLiteNode* node) {
    auto* data = static_cast<OpData*>(node->user_data);
    const auto* params = static_cast<const TfLiteFullyConnectedParams*>(node->builtin_data);
    tflite::MicroContext* micro = tflite::GetMicroContext(context);

    TfLiteTensor* input = micro->AllocateTempInputTensor(node, 0);
    TfLiteTensor* filter = micro->AllocateTempInputTensor(node, 1);
    TfLiteTensor* output = micro->AllocateTempOutputTensor(node, 0);
    TF_LITE_ENSURE(context, input != nullptr && filter != nullptr && output != nullptr);
    TF_LITE_ENSURE_EQ(context, input->type, kTfLiteInt8);
    TF_LITE_ENSURE_EQ(context, filter->type, kTfLiteInt8);
    TF_LITE_ENSURE_EQ(context, output->type, kTfLiteInt8);
    TF_LITE_ENSURE_EQ(context, filter->dims->size, 2);
    TF_LITE_ENSURE_EQ(context, filter->quantization.type, kTfLiteAffineQuantization);

    const auto* q = static_cast<const TfLiteAffineQuantization*>(filter->quantization.params);
    const int32_t outputs = filter->dims->data[0];
    const bool perChannel = q->scale->size == outputs;
    TF_LITE_ENSURE(context, perChannel || q->scale->size == 1);
    for (int i = 0; i < q->zero_point->size; ++i) TF_LITE_ENSURE_EQ(context, q->zero_point->data[i], 0);  // symmetric int8 weights

    data->outputChannels = outputs;
    data->multiplier = static_cast<int32_t*>(context->AllocatePersistentBuffer(context, sizeof(int32_t) * outputs));
    data->shift = static_cast<int32_t*>(context->AllocatePersistentBuffer(context, sizeof(int32_t) * outputs));
    TF_LITE_ENSURE(context, data->multiplier != nullptr && data->shift != nullptr);
    for (int c = 0; c < outputs; ++c) {
        const double weightScale = q->scale->data[perChannel ? c : 0];
        const double real = static_cast<double>(input->params.scale) * weightScale / static_cast<double>(output->params.scale);
        tflite::QuantizeMultiplier(real, &data->multiplier[c], &data->shift[c]);
    }
    data->inputZeroPoint = input->params.zero_point;
    data->outputZeroPoint = output->params.zero_point;
    TF_LITE_ENSURE_OK(context, tflite::CalculateActivationRangeQuantized(context, params->activation, output,
                                                                        &data->activationMin, &data->activationMax));
    micro->DeallocateTempTfLiteTensor(input);
    micro->DeallocateTempTfLiteTensor(filter);
    micro->DeallocateTempTfLiteTensor(output);
    return kTfLiteOk;
}

TfLiteStatus Eval(TfLiteContext* context, TfLiteNode* node) {
    const auto* data = static_cast<const OpData*>(node->user_data);
    const TfLiteEvalTensor* input = tflite::micro::GetEvalInput(context, node, 0);
    const TfLiteEvalTensor* filter = tflite::micro::GetEvalInput(context, node, 1);
    const TfLiteEvalTensor* bias = tflite::micro::GetEvalInput(context, node, 2);   // int32, may be null
    TfLiteEvalTensor* output = tflite::micro::GetEvalOutput(context, node, 0);

    const int32_t outputs = data->outputChannels;
    const int32_t inputs = filter->dims->data[1];
    const int32_t inputElems = tflite::micro::GetTensorShape(input).FlatSize();
    const int32_t batches = inputElems / inputs;
    const int8_t* in = tflite::micro::GetTensorData<int8_t>(input);
    const int8_t* w = tflite::micro::GetTensorData<int8_t>(filter);
    const int32_t* b = bias ? tflite::micro::GetTensorData<int32_t>(bias) : nullptr;
    int8_t* out = tflite::micro::GetTensorData<int8_t>(output);

    for (int32_t n = 0; n < batches; ++n) {
        for (int32_t c = 0; c < outputs; ++c) {
            int32_t acc = 0;
            for (int32_t i = 0; i < inputs; ++i) {
                acc += (static_cast<int32_t>(in[n * inputs + i]) - data->inputZeroPoint) * static_cast<int32_t>(w[c * inputs + i]);
            }
            if (b) acc += b[c];
            acc = tflite::MultiplyByQuantizedMultiplier(acc, data->multiplier[c], data->shift[c]);
            acc += data->outputZeroPoint;
            acc = acc < data->activationMin ? data->activationMin : acc;
            acc = acc > data->activationMax ? data->activationMax : acc;
            out[n * outputs + c] = static_cast<int8_t>(acc);
        }
    }
    return kTfLiteOk;
}

}  // namespace

TfLiteRegistration RegisterFullyConnectedPerChannel() {
    return tflite::micro::RegisterOp(Init, Prepare, Eval);
}

}  // namespace forest::acoustic
