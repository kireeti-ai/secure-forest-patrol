#include "SensorMath.h"

#include <cmath>

namespace ForestSensors {

float blockRms(const int16_t* samples, size_t count, float* meanOut) {
    if (samples == nullptr || count == 0) {
        if (meanOut) *meanOut = 0.0f;
        return 0.0f;
    }
    double sum = 0.0;
    for (size_t i = 0; i < count; ++i) sum += samples[i];
    const double mean = sum / static_cast<double>(count);
    double acc = 0.0;
    for (size_t i = 0; i < count; ++i) {
        const double d = samples[i] - mean;
        acc += d * d;
    }
    if (meanOut) *meanOut = static_cast<float>(mean);
    return static_cast<float>(std::sqrt(acc / static_cast<double>(count)));
}

}  // namespace ForestSensors
