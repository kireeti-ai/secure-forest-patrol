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
    // Relative-dB mode (EXPERIMENTAL, off by default). Thresholds are decibels above a measured
    // noise floor instead of absolute ADC counts, so they do not depend on trimmer gain or board:
    //   warm-up: median RMS of `warmupBlocks` blocks = initial floor (robust to a short burst); never triggers
    //   trigger: delta >= highDb (one block: transient/gunshot)
    //            or delta >= lowDb for `sustainBlocks` consecutive blocks (chainsaw)
    //   release: delta <  lowDb
    // The floor keeps adapting only while idle and delta < lowDb, so events cannot raise it.
    bool relative = false;
    float highDb = 10.0f;
    float lowDb = 6.0f;
    int sustainBlocks = 2;
    int warmupBlocks = 250;      // 4 s of 16 ms blocks (capped at kMaxWarmupBlocks)
    float floorAlpha = 0.005f;   // EMA weight after warm-up
    float minFloor = 1.0f;       // guards log10 against a dead-flat input
    // Sensor-health guard: if the warm-up floor exceeds this (RMS counts) the input is treated as
    // faulty/noisy, the detector never triggers (so ML never runs) until reboot. 0 disables.
    // A floor below minFloor (dead-flat / stuck-at-rail input) is a fault too.
    float maxFloor = 0.0f;
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
    // Relative mode diagnostics: dB above the noise floor for the last block, and whether the
    // warm-up has finished (no trigger is possible before that).
    float lastDeltaDb() const { return lastDeltaDb_; }
    bool sensorFault() const { return fault_; }
    bool warmedUp() const { return !cfg_.relative || warmBlocks_ >= cfg_.warmupBlocks; }

private:
    Edge updateRelative(float rms);
    EnergyDetectorConfig cfg_;
    bool active_ = false;
    bool floorInit_ = false;
    float noiseFloor_ = 0.0f;
    static constexpr int kMaxWarmupBlocks = 512;
    float warm_[kMaxWarmupBlocks];
    int warmBlocks_ = 0;
    int sustainCount_ = 0;
    bool fault_ = false;
    float lastDeltaDb_ = 0.0f;
};

// Peak/RMS of the AC component (crest factor): ~1.4 sine, ~3-4 noise, >6 impulsive. Diagnostic only.
float crestFactor(float peakAboveMean, float rms);

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
