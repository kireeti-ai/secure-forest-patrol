// Host tests for the MAX4466 trigger logic and the audio ring buffer.
#include <cmath>
#include <cstdio>
#include <random>
#include <vector>

#include "AcousticTrigger.h"
#include "AudioCapture.h"

using namespace forest::acoustic;
static int failures = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("FAIL: %s (line %d)\n", msg, __LINE__); ++failures; } } while (0)

static std::vector<int16_t> block(std::mt19937& g, float sigma, int dc, int n = 128) {
    std::normal_distribution<float> nd(0.0f, sigma);
    std::vector<int16_t> b(n);
    for (auto& v : b) v = static_cast<int16_t>(std::lround(dc + nd(g)));
    return b;
}

int main() {
    std::mt19937 g(1);

    // --- RMS: DC offset must not matter (MAX4466 idles near VCC/2 = ~2048 counts)
    {
        auto a = block(g, 10.0f, 2048), b = block(g, 10.0f, 500);
        const float ra = blockRms(a.data(), 128), rb = blockRms(b.data(), 128);
        CHECK(std::fabs(ra - 10.0f) < 3.0f, "rms ~ sigma");
        CHECK(std::fabs(ra - rb) < 3.0f, "rms independent of DC");
        int16_t flat[128]; for (auto& v : flat) v = 2000;
        CHECK(blockRms(flat, 128) < 1e-3f, "constant signal has zero AC rms");
        printf("rms sigma=10 dc=2048 -> %.2f ; dc=500 -> %.2f\n", ra, rb);
    }

    // --- Fixed thresholds + hysteresis
    {
        EnergyDetector d({120.0f, 60.0f, false, 0, 0, 0});
        int rising = 0, falling = 0;
        auto feed = [&](float rms) { auto e = d.update(rms); rising += e == EnergyDetector::Edge::Rising; falling += e == EnergyDetector::Edge::Falling; };
        for (int i = 0; i < 50; ++i) feed(20.0f);   CHECK(rising == 0, "quiet does not trigger");
        feed(119.0f);                               CHECK(rising == 0, "just below HIGH does not trigger");
        feed(125.0f);                               CHECK(rising == 1 && d.active(), "HIGH triggers");
        for (int i = 0; i < 20; ++i) feed(90.0f);   CHECK(d.active() && falling == 0, "between LOW and HIGH stays active (hysteresis)");
        for (int i = 0; i < 20; ++i) feed(70.0f + (i % 2) * 40.0f); CHECK(rising == 1, "no chatter around HIGH once active");
        feed(59.0f);                                CHECK(!d.active() && falling == 1, "below LOW releases");
        feed(100.0f);                               CHECK(rising == 1, "100 (< HIGH) does not re-trigger");
        feed(121.0f);                               CHECK(rising == 2, "re-arms after release");
    }

    // --- Adaptive: threshold follows the floor, and events do not raise their own threshold
    {
        EnergyDetector d({60.0f, 30.0f, true, 0.05f, 3.0f, 10.0f});
        for (int i = 0; i < 400; ++i) d.update(50.0f);          // noisy site: floor -> 50
        CHECK(d.noiseFloor() > 45.0f && d.noiseFloor() < 55.0f, "noise floor converges");
        CHECK(d.highThreshold() > 150.0f, "high threshold rises with the floor");
        CHECK(d.update(100.0f) == EnergyDetector::Edge::None, "moderate rise in a noisy site does not trigger");
        CHECK(d.update(400.0f) == EnergyDetector::Edge::Rising, "loud event triggers");
        const float floorBefore = d.noiseFloor();
        for (int i = 0; i < 100; ++i) d.update(400.0f);
        CHECK(std::fabs(d.noiseFloor() - floorBefore) < 1e-3f, "floor frozen while active");
        printf("adaptive: floor=%.1f high=%.1f low=%.1f\n", floorBefore, d.highThreshold(), d.lowThreshold());
    }

    // --- Ring buffer: pre-trigger history, wraparound, overwritten/not-yet-written rejection
    {
        std::vector<int16_t> storage(1000);
        SampleRing ring(storage.data(), storage.size());
        std::vector<int16_t> w(300), out(500);
        for (int round = 0; round < 7; ++round) {   // 2100 samples through a 1000-sample ring
            for (int i = 0; i < 300; ++i) w[i] = static_cast<int16_t>((round * 300 + i) & 0x7fff);
            ring.write(w.data(), w.size());
        }
        CHECK(ring.total() == 2100, "total counts every sample");
        CHECK(ring.copyWindow(1600, 500, out.data()), "recent window readable");
        bool ok = true; for (int i = 0; i < 500; ++i) ok &= out[i] == ((1600 + i) & 0x7fff);
        CHECK(ok, "window content correct across wraparound");
        CHECK(!ring.copyWindow(1000, 500, out.data()), "overwritten window rejected");
        CHECK(!ring.copyWindow(1800, 500, out.data()), "not-yet-written window rejected");
        auto st = computePcmStats(out.data(), 500);
        CHECK(st.count == 500 && st.max >= st.min, "stats sane");
    }

    printf(failures ? "\nTRIGGER/RING TESTS FAIL (%d)\n" : "\nTRIGGER/RING TESTS PASS\n", failures);
    return failures ? 1 : 0;
}
