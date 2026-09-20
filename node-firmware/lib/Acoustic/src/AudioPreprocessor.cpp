#include "AudioPreprocessor.h"

#include <algorithm>
#include <cmath>

namespace forest::acoustic {

AudioPreprocessor::AudioPreprocessor() {
    constexpr int n = tables::kNFft;
    for (int i = 0; i < n / 2; ++i) {
        const double a = -2.0 * M_PI * i / n;
        cos_[i] = static_cast<float>(std::cos(a));
        sin_[i] = static_cast<float>(std::sin(a));
    }
    int bits = 0;
    while ((1 << bits) < n) ++bits;
    for (int i = 0; i < n; ++i) {
        int r = 0;
        for (int b = 0; b < bits; ++b) r |= ((i >> b) & 1) << (bits - 1 - b);
        bitrev_[i] = static_cast<uint16_t>(r);
    }
}

// In-place iterative radix-2 complex FFT on (re_, im_).
void AudioPreprocessor::fft512() {
    constexpr int n = tables::kNFft;
    for (int i = 0; i < n; ++i) {
        const int j = bitrev_[i];
        if (j > i) {
            std::swap(re_[i], re_[j]);
            std::swap(im_[i], im_[j]);
        }
    }
    for (int len = 2; len <= n; len <<= 1) {
        const int half = len >> 1;
        const int step = n / len;
        for (int base = 0; base < n; base += len) {
            for (int k = 0; k < half; ++k) {
                const float wr = cos_[k * step];
                const float wi = sin_[k * step];
                const int a = base + k;
                const int b = a + half;
                const float tr = re_[b] * wr - im_[b] * wi;
                const float ti = re_[b] * wi + im_[b] * wr;
                re_[b] = re_[a] - tr;
                im_[b] = im_[a] - ti;
                re_[a] += tr;
                im_[a] += ti;
            }
        }
    }
}

template <typename Sample>
void AudioPreprocessor::melDb(Sample sample, float* dbOut) {
    constexpr int n = tables::kNFft;
    constexpr int pad = n / 2;  // librosa centre=True, zero padding
    float maxPower = 0.0f;

    for (int t = 0; t < kFrames; ++t) {
        const int start = t * tables::kHop - pad;
        for (int i = 0; i < n; ++i) {
            const int idx = start + i;
            const float x = (idx >= 0 && idx < kSamples) ? sample(idx) : 0.0f;
            re_[i] = x * tables::kHann[i];
            im_[i] = 0.0f;
        }
        fft512();
        // Power spectrum, then sparse Slaney mel bank.
        for (int m = 0; m < kMels; ++m) {
            const int s = tables::kMelStart[m];
            const int len = tables::kMelLen[m];
            const float* w = &tables::kMelWeights[tables::kMelOffset[m]];
            float acc = 0.0f;
            for (int k = 0; k < len; ++k) {
                const float p = re_[s + k] * re_[s + k] + im_[s + k] * im_[s + k];
                acc += w[k] * p;
            }
            mel_[m * kFrames + t] = acc;
            if (acc > maxPower) maxPower = acc;
        }
    }

    // librosa.power_to_db(S, ref=np.max, amin=1e-10, top_db=80)
    constexpr float kAmin = 1e-10f;
    constexpr float kTopDb = 80.0f;
    const float refDb = 10.0f * log10f(std::max(kAmin, maxPower));
    float maxDb = -1e30f;
    for (int i = 0; i < kTensorSize; ++i) {
        const float db = 10.0f * log10f(std::max(kAmin, mel_[i])) - refDb;
        dbOut[i] = db;
        if (db > maxDb) maxDb = db;
    }
    const float floorDb = maxDb - kTopDb;
    for (int i = 0; i < kTensorSize; ++i) dbOut[i] = std::max(dbOut[i], floorDb);
}

void AudioPreprocessor::melDbFromFloat(const float* audio, float* dbOut) {
    melDb([audio](int i) { return audio[i]; }, dbOut);
}

void AudioPreprocessor::quantize(const float* db, int8_t* tensorOut) {
    for (int i = 0; i < kTensorSize; ++i) {
        const float x = (db[i] - tables::kFeatureMean) / tables::kFeatureStd;
        const float q = nearbyintf(x / tables::kInputScale + static_cast<float>(tables::kInputZeroPoint));
        tensorOut[i] = static_cast<int8_t>(std::min(127.0f, std::max(-128.0f, q)));
    }
}

bool AudioPreprocessor::process(const int16_t* pcm, int8_t* tensorOut, const PreprocessOptions& options,
                                float* filterScratch) {
    if (pcm == nullptr || tensorOut == nullptr) return false;
    if (options.highPass && filterScratch == nullptr) return false;

    // Sample source in "float PCM" units (x / 32768), optionally high-passed.
    constexpr float kInv = 1.0f / 32768.0f;
    float peak = 0.0f;
    if (options.highPass) {
        HighPassBiquad hp;
        for (int i = 0; i < kSamples; ++i) {
            const float y = hp.process(static_cast<float>(pcm[i]) * kInv);
            filterScratch[i] = y;
            peak = std::max(peak, std::fabs(y));
        }
    } else {
        int32_t peakInt = 0;
        for (int i = 0; i < kSamples; ++i) {
            const int32_t a = pcm[i] < 0 ? -static_cast<int32_t>(pcm[i]) : pcm[i];
            if (a > peakInt) peakInt = a;
        }
        peak = static_cast<float>(peakInt) * kInv;
    }
    const float gain = (options.peakNormalize && peak > 0.0f) ? options.peakTarget / peak : 1.0f;

    if (options.highPass) {
        melDb([&](int i) { return filterScratch[i] * gain; }, mel_);
    } else {
        melDb([&](int i) { return static_cast<float>(pcm[i]) * kInv * gain; }, mel_);
    }
    // melDb wrote dB into mel_ (dbOut aliases the working array only at the end
    // of the pass, after every power value has been consumed).
    quantize(mel_, tensorOut);
    return true;
}

}  // namespace forest::acoustic
