// Host test: the device preprocessing (lib/Acoustic/src/AudioPreprocessor) must reproduce
// the training pipeline (librosa + ml/ normalisation). Reference data comes from
// tools/gen_acoustic_testvectors.py (real test-set windows + synthetic signals).
//
// Pass criteria (measured, not assumed):
//   * dB features vs librosa:   max |diff| <= 0.05 dB
//   * int8 tensor vs ml/ path:  every element within +/-1 LSB, and >= 99.9% exactly equal
//   * high-pass biquad vs scipy sosfilt: max |diff| <= 1e-4
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "AudioPreprocessor.h"

using namespace forest::acoustic;

static bool readAll(FILE* f, void* dst, size_t n) { return fread(dst, 1, n, f) == n; }

int main(int argc, char** argv) {
    const char* path = argc > 1 ? argv[1] : "test/data/vectors.bin";
    FILE* f = fopen(path, "rb");
    if (!f) { printf("FAIL: cannot open %s (run tools/gen_acoustic_testvectors.py)\n", path); return 2; }
    char magic[4]; uint32_t count = 0;
    if (!readAll(f, magic, 4) || memcmp(magic, "ACV1", 4) != 0 || !readAll(f, &count, 4)) { printf("FAIL: bad file\n"); return 2; }

    constexpr int N = AudioPreprocessor::kSamples, T = AudioPreprocessor::kTensorSize;
    static AudioPreprocessor pre;
    std::vector<int16_t> pcm(N);
    std::vector<float> refDb(T), db(T);
    std::vector<int8_t> refQ(T), refQpn(T), q(T), qpn(T);
    std::vector<std::vector<int16_t>> allPcm;
    std::vector<std::string> names;
    int failures = 0;

    printf("%-34s %10s %10s %10s %12s\n", "vector", "dB max", "dB mean", "q !=", "q peaknorm !=");
    for (uint32_t v = 0; v < count; ++v) {
        char name[65] = {0}; int8_t out[3], outPn[3];
        if (!readAll(f, name, 64) || !readAll(f, pcm.data(), N * 2) || !readAll(f, refDb.data(), T * 4) ||
            !readAll(f, refQ.data(), T) || !readAll(f, out, 3) || !readAll(f, refQpn.data(), T) || !readAll(f, outPn, 3)) {
            printf("FAIL: truncated file\n"); return 2;
        }
        allPcm.push_back(pcm); names.push_back(name);

        // 1) exact chain (no peak normalisation) vs librosa dB + int8
        std::vector<float> audio(N);
        for (int i = 0; i < N; ++i) audio[i] = static_cast<float>(pcm[i]) / 32768.0f;
        pre.melDbFromFloat(audio.data(), db.data());
        double maxd = 0, sum = 0;
        for (int i = 0; i < T; ++i) { double d = std::fabs(db[i] - refDb[i]); maxd = std::max(maxd, d); sum += d; }
        AudioPreprocessor::quantize(db.data(), q.data());
        int diff1 = 0, big1 = 0;
        for (int i = 0; i < T; ++i) { int d = std::abs(int(q[i]) - int(refQ[i])); diff1 += d != 0; big1 += d > 1; }

        // 2) production path: process() with per-window peak normalisation
        PreprocessOptions opt; opt.highPass = false; opt.peakNormalize = true;
        pre.process(pcm.data(), qpn.data(), opt);
        int diff2 = 0, big2 = 0;
        for (int i = 0; i < T; ++i) { int d = std::abs(int(qpn[i]) - int(refQpn[i])); diff2 += d != 0; big2 += d > 1; }

        printf("%-34s %10.4f %10.5f %5d(>1:%d) %7d(>1:%d)\n", name, maxd, sum / T, diff1, big1, diff2, big2);
        const bool silentReference = (std::string(name).find("noise") != std::string::npos);
        (void)silentReference;
        if (maxd > 0.05 || big1 > 0 || diff1 > T / 1000 || big2 > 0 || diff2 > T / 500) ++failures;
    }

    // 3) optional high-pass vs scipy sosfilt
    for (const char* want : {"synthetic_tone_1k", "synthetic_impulse"}) {
        std::vector<float> ref(N);
        if (!readAll(f, ref.data(), N * 4)) { printf("FAIL: missing HPF reference\n"); return 2; }
        size_t idx = 0; for (; idx < names.size(); ++idx) if (names[idx] == want) break;
        HighPassBiquad hp; double maxd = 0;
        for (int i = 0; i < N; ++i) maxd = std::max(maxd, double(std::fabs(hp.process(allPcm[idx][i] / 32768.0f) - ref[i])));
        printf("high-pass vs scipy sosfilt [%s]: max |diff| = %.3g\n", want, maxd);
        if (maxd > 1e-4) ++failures;
    }
    fclose(f);
    printf(failures ? "\nPARITY FAIL (%d)\n" : "\nPARITY PASS\n", failures);
    return failures ? 1 : 0;
}
