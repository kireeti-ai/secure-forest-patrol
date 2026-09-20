#pragma once
// MAX4466 wake-up trigger: cheap acoustic energy detection that decides whether the
// (much more expensive) MFCC/TinyML inference should run at all.
//
//   ADC samples -> mean (DC) removal -> RMS -> hysteresis (HIGH/LOW) -> trigger
//
// EnergyDetector / blockRms are portable C++ (host-tested). Max4466Sampler is the
// ESP32-S3 DMA ADC front end (Arduino builds only).

#include <cstdint>

namespace forest::acoustic {

// RMS of the AC component of a block: subtract the block mean, then sqrt(mean(x^2)).
// A raw ADC value is NOT compared with a threshold: the MAX4466 output rides on a
// ~VCC/2 bias, so the DC offset must be removed first.
float blockRms(const int16_t* samples, int count);

struct EnergyDetectorConfig {
    float high;            // enter TRIGGERED when rms >= high
    float low;             // leave TRIGGERED when rms <  low   (must be < high)
    bool adaptive;         // optional: follow a slowly-tracked noise floor
    float noiseAlpha;      // EMA weight while quiet
    float noiseFactor;     // adaptive: high = max(cfg.high, floor*factor + delta)
    float noiseDelta;
};

class EnergyDetector {
public:
    enum class Edge { None, Rising, Falling };

    explicit EnergyDetector(const EnergyDetectorConfig& config) : cfg_(config) {}

    // Feed one block RMS. Returns the edge (if any) this block caused.
    Edge update(float rms);

    bool active() const { return active_; }
    float noiseFloor() const { return noiseFloor_; }
    float highThreshold() const;
    float lowThreshold() const;

private:
    EnergyDetectorConfig cfg_;
    bool active_ = false;
    bool floorInit_ = false;
    float noiseFloor_ = 0.0f;
};

#ifdef ARDUINO
struct BlockStats {
    float rms = 0.0f;
    float mean = 0.0f;   // DC level in ADC counts
    int16_t min = 0;
    int16_t max = 0;
};

// Continuous ADC1 sampling of the MAX4466 through the ESP32-S3 digital-controller DMA:
// no per-sample CPU work, the task only wakes once per block.
class Max4466Sampler {
public:
    bool begin(int gpio, int sampleRateHz, int blockSize);
    // Waits up to timeoutMs for a full block; false on timeout/driver error.
    bool readBlock(BlockStats& stats, uint32_t timeoutMs);
    int blockSize() const { return blockSize_; }
private:
    int blockSize_ = 0;
    int filled_ = 0;
    int16_t* block_ = nullptr;   // allocated once in begin()
    bool started_ = false;
};
#endif

}  // namespace forest::acoustic
