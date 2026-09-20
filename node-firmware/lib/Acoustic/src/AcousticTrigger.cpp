#include "AcousticTrigger.h"

#include <algorithm>
#include <cmath>

namespace forest::acoustic {

float blockRms(const int16_t* samples, int count) {
    if (samples == nullptr || count <= 0) return 0.0f;
    double sum = 0.0;
    for (int i = 0; i < count; ++i) sum += samples[i];
    const double mean = sum / count;
    double acc = 0.0;
    for (int i = 0; i < count; ++i) {
        const double d = samples[i] - mean;
        acc += d * d;
    }
    return static_cast<float>(std::sqrt(acc / count));
}

float crestFactor(float peakAboveMean, float rms) {
    return rms > 0.0f ? peakAboveMean / rms : 0.0f;
}

float EnergyDetector::highThreshold() const {
    if (cfg_.relative) return noiseFloor_ * std::pow(10.0f, cfg_.highDb / 20.0f);
    if (!cfg_.adaptive || !floorInit_) return cfg_.high;
    return std::max(cfg_.high, noiseFloor_ * cfg_.noiseFactor + cfg_.noiseDelta);
}

float EnergyDetector::lowThreshold() const {
    if (cfg_.relative) return noiseFloor_ * std::pow(10.0f, cfg_.lowDb / 20.0f);
    if (!cfg_.adaptive || !floorInit_) return cfg_.low;
    // Keep the configured HIGH:LOW ratio so hysteresis scales with the floor.
    return std::max(cfg_.low, highThreshold() * (cfg_.low / cfg_.high));
}

EnergyDetector::Edge EnergyDetector::updateRelative(float rms) {
    const int warmTarget = std::min(cfg_.warmupBlocks, kMaxWarmupBlocks);
    if (warmBlocks_ < warmTarget) {   // collect RMS values; floor = median once complete; no triggering yet
        warm_[warmBlocks_++] = rms;
        floorInit_ = true;
        if (warmBlocks_ < warmTarget) {
            noiseFloor_ += (rms - noiseFloor_) / static_cast<float>(warmBlocks_);   // running mean, display only
        } else {
            float* mid = warm_ + warmTarget / 2;
            std::nth_element(warm_, mid, warm_ + warmTarget);
            noiseFloor_ = *mid;
            warmBlocks_ = cfg_.warmupBlocks;   // mark complete for warmedUp()
            if (cfg_.maxFloor > 0.0f && (noiseFloor_ > cfg_.maxFloor || noiseFloor_ < cfg_.minFloor)) fault_ = true;
        }
        return Edge::None;
    }
    if (fault_) return Edge::None;   // noisy/faulty sensor: never wake the ML
    const float floor = std::max(noiseFloor_, cfg_.minFloor);
    lastDeltaDb_ = 20.0f * std::log10(std::max(rms, 1e-6f) / floor);
    if (active_) {
        if (lastDeltaDb_ < cfg_.lowDb) {
            active_ = false;
            sustainCount_ = 0;
            return Edge::Falling;
        }
        return Edge::None;
    }
    if (lastDeltaDb_ >= cfg_.highDb) {
        active_ = true;
        return Edge::Rising;
    }
    if (lastDeltaDb_ >= cfg_.lowDb) {
        if (++sustainCount_ >= cfg_.sustainBlocks) {
            active_ = true;
            sustainCount_ = 0;
            return Edge::Rising;
        }
    } else {
        sustainCount_ = 0;
        noiseFloor_ += cfg_.floorAlpha * (rms - noiseFloor_);
    }
    return Edge::None;
}

EnergyDetector::Edge EnergyDetector::update(float rms) {
    if (cfg_.relative) return updateRelative(rms);
    Edge edge = Edge::None;
    if (!active_) {
        if (rms >= highThreshold()) {
            active_ = true;
            edge = Edge::Rising;
        } else if (cfg_.adaptive) {
            // Learn the background only while quiet, so an event cannot raise its own threshold.
            if (!floorInit_) {
                noiseFloor_ = rms;
                floorInit_ = true;
            } else {
                noiseFloor_ += cfg_.noiseAlpha * (rms - noiseFloor_);
            }
        }
    } else if (rms < lowThreshold()) {
        active_ = false;
        edge = Edge::Falling;
    }
    return edge;
}

}  // namespace forest::acoustic

#ifdef ARDUINO
#include <Arduino.h>
#include <driver/adc.h>
#include <esp_heap_caps.h>

namespace forest::acoustic {

bool Max4466Sampler::begin(int gpio, int sampleRateHz, int blockSize) {
    // GPIO1 = ADC1_CH0 on the ESP32-S3. Any ADC1 pin works; ADC2 is avoided (Wi-Fi/USB conflicts).
    int channel = -1;
    if (gpio >= 1 && gpio <= 10) channel = gpio - 1;   // ESP32-S3: GPIO1..10 = ADC1_CH0..9
    if (channel < 0) {
        Serial.printf("[ACOUSTIC] MAX4466 pin %d is not an ADC1 pin\n", gpio);
        return false;
    }
    blockSize_ = blockSize;
    block_ = static_cast<int16_t*>(heap_caps_malloc(sizeof(int16_t) * blockSize, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT));
    if (block_ == nullptr) return false;

    adc_digi_init_config_t init{};
    init.max_store_buf_size = 4 * blockSize * 8;   // 8 blocks of DMA backlog (4 bytes/sample)
    init.conv_num_each_intr = 4 * blockSize;       // one interrupt per block
    init.adc1_chan_mask = (1u << channel);
    init.adc2_chan_mask = 0;
    if (adc_digi_initialize(&init) != ESP_OK) {
        Serial.println("[ACOUSTIC] adc_digi_initialize failed");
        return false;
    }
    adc_digi_pattern_config_t pattern{};
    pattern.atten = ADC_ATTEN_DB_12;   // full ~0-3.1 V range: MAX4466 idles near VCC/2
    pattern.channel = static_cast<uint8_t>(channel);
    pattern.unit = 0;                  // ADC1
    pattern.bit_width = 12;
    adc_digi_configuration_t cfg{};
    cfg.conv_limit_en = false;
    cfg.conv_limit_num = 250;
    cfg.pattern_num = 1;
    cfg.adc_pattern = &pattern;
    cfg.sample_freq_hz = sampleRateHz;
    cfg.conv_mode = ADC_CONV_SINGLE_UNIT_1;
    cfg.format = ADC_DIGI_OUTPUT_FORMAT_TYPE2;
    if (adc_digi_controller_configure(&cfg) != ESP_OK || adc_digi_start() != ESP_OK) {
        Serial.println("[ACOUSTIC] ADC digital controller start failed");
        return false;
    }
    started_ = true;
    return true;
}

bool Max4466Sampler::readBlock(BlockStats& stats, uint32_t timeoutMs) {
    if (!started_) return false;
    while (filled_ < blockSize_) {
        uint32_t words[64];
        const int want = std::min<int>(64, blockSize_ - filled_);
        uint32_t got = 0;
        const esp_err_t err = adc_digi_read_bytes(reinterpret_cast<uint8_t*>(words), want * 4, &got, timeoutMs);
        if (err != ESP_OK || got == 0) return false;   // ESP_ERR_TIMEOUT: no data yet
        for (uint32_t i = 0; i < got / 4 && filled_ < blockSize_; ++i) {
            adc_digi_output_data_t d;
            d.val = words[i];
            if (d.type2.unit != 0) continue;
            block_[filled_++] = static_cast<int16_t>(d.type2.data);
        }
    }
    filled_ = 0;
    double sum = 0;
    int16_t mn = 32767, mx = -32768;
    for (int i = 0; i < blockSize_; ++i) {
        sum += block_[i];
        mn = std::min(mn, block_[i]);
        mx = std::max(mx, block_[i]);
    }
    stats.rms = blockRms(block_, blockSize_);
    stats.mean = static_cast<float>(sum / blockSize_);
    stats.min = mn;
    stats.max = mx;
    return true;
}

}  // namespace forest::acoustic
#endif  // ARDUINO
