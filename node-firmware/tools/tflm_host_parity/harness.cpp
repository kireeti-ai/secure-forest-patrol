// Host harness: runs the INT8 model through the REAL TFLite Micro kernels of the firmware's TFLM
// library (compiled for the host by run.sh). argv[1]=model, argv[2]="stock"|"fixed":
//   stock = library FULLY_CONNECTED (ignores per-channel weight scales - the bug),
//   fixed = lib/Acoustic/src/AcousticKernels.cpp (per-channel), as used on the device.
// stdin: one line of 4040 int8 values per window; stdout: three int8 outputs per window.
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <vector>
#include "AcousticKernels.h"
#include "tensorflow/lite/micro/micro_error_reporter.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
extern "C" void DebugLog(const char* s) { fputs(s, stderr); }
int main(int argc, char** argv) {
    FILE* f = fopen(argv[1], "rb"); std::vector<unsigned char> model; fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    model.resize(n); fread(model.data(), 1, n, f); fclose(f);
    const bool fixed = argc > 2 && !strcmp(argv[2], "fixed");
    tflite::MicroErrorReporter er;
    tflite::MicroMutableOpResolver<6> r;
    r.AddConv2D(); r.AddDepthwiseConv2D();
    if (fixed) r.AddFullyConnected(forest::acoustic::RegisterFullyConnectedPerChannel()); else r.AddFullyConnected();
    r.AddMaxPool2D(); r.AddMean(); r.AddSoftmax();
    static uint8_t arena[100000] __attribute__((aligned(16)));
    tflite::MicroInterpreter it(tflite::GetModel(model.data()), r, arena, sizeof(arena), &er);
    if (it.AllocateTensors() != kTfLiteOk) return 1;
    std::vector<int> tmp(4040);
    for (;;) {
        for (int i = 0; i < 4040; ++i) if (scanf("%d", &tmp[i]) != 1) return 0;
        for (int i = 0; i < 4040; ++i) it.input(0)->data.int8[i] = (int8_t)tmp[i];
        it.Invoke();
        const int8_t* o = it.output(0)->data.int8;
        printf("%d %d %d\n", o[0], o[1], o[2]);
    }
}
