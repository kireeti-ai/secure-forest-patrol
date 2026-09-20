#pragma once
// Audio -> model-input preprocessing that reproduces the training pipeline
// (ml/preprocessing/feature_extraction.py + ml/models/convert_tflite.py):
//
//   1 s PCM16 @16 kHz -> [80 Hz high-pass, OFF by default] -> peak normalise
//   -> 512-pt STFT (Hann, hop 160, zero-padded centre) -> power -> 40 Slaney
//   mel bands -> power_to_db(ref = max of this clip, top_db 80)
//   -> (dB - mean)/std -> int8 (input scale / zero point).
//
// Portable C++ (no Arduino headers) so it is unit-tested on a host against
// librosa. All buffers are owned by the object: construct it once (e.g. in
// PSRAM) and reuse it - process() performs no allocation.

#include <cstddef>
#include <cstdint>

#include "AcousticTables.h"

namespace forest::acoustic {

struct PreprocessOptions {
    bool highPass = false;       // 80 Hz Butterworth; model was trained WITHOUT it
    bool peakNormalize = true;   // per-window peak -> -3 dBFS (see AcousticConfig.h)
    float peakTarget = 0.70794578f;
};

// 2nd-order causal Butterworth high-pass, fc = 80 Hz @ 16 kHz, Direct Form II
// transposed; coefficients from ml/reports/FILTER_REPORT.md.
class HighPassBiquad {
public:
    void reset() { z1_ = z2_ = 0.0f; }
    float process(float x) {
        const float y = kB0 * x + z1_;
        z1_ = kB1 * x - kA1 * y + z2_;
        z2_ = kB2 * x - kA2 * y;
        return y;
    }
private:
    static constexpr float kB0 = 0.9780304792065597f;
    static constexpr float kB1 = -1.9560609584131194f;
    static constexpr float kB2 = 0.9780304792065597f;
    static constexpr float kA1 = -1.9555782403150352f;
    static constexpr float kA2 = 0.9565436765112031f;
    float z1_ = 0.0f, z2_ = 0.0f;
};

class AudioPreprocessor {
public:
    static constexpr int kSamples = tables::kWindowSamples;  // 16000
    static constexpr int kMels = tables::kNMels;             // 40
    static constexpr int kFrames = tables::kNFrames;         // 101
    static constexpr int kTensorSize = kMels * kFrames;      // 4040

    AudioPreprocessor();

    // PCM16 window (kSamples) -> int8 model input tensor (kTensorSize, [mel][frame]).
    // `filterScratch` must point to kSamples floats when options.highPass is set
    // (otherwise it may be null). Returns false on bad arguments.
    bool process(const int16_t* pcm, int8_t* tensorOut, const PreprocessOptions& options,
                 float* filterScratch = nullptr);

    // Float audio in [-1, 1] (no normalisation applied) -> dB features [mel][frame].
    // Used by tests to compare against librosa bit-for-bit-ish.
    void melDbFromFloat(const float* audio, float* dbOut);

    // dB features -> int8 tensor.
    static void quantize(const float* db, int8_t* tensorOut);

private:
    template <typename Sample>
    void melDb(Sample sample, float* dbOut);
    void fft512();

    float re_[tables::kNFft];
    float im_[tables::kNFft];
    float cos_[tables::kNFft / 2];
    float sin_[tables::kNFft / 2];
    uint16_t bitrev_[tables::kNFft];
    float mel_[kTensorSize];  // mel power, then reused for dB
};

}  // namespace forest::acoustic
