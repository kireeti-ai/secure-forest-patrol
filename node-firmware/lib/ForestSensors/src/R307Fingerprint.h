#pragma once

#include <HardwareSerial.h>
#include <cstdint>

namespace ForestSensors {

struct FingerprintMatch {
    std::uint16_t pageId = 0;
    std::uint16_t score = 0;
};

// NoFinger: nothing presented this poll. Matched: image matched an enrolled
// template (match populated). NotMatched: a finger was imaged but it does
// not match any enrolled template (match left untouched) -- distinct from
// NoFinger so callers can tell "wrong finger presented" from "no attempt".
enum class FingerprintScanResult : std::uint8_t { NoFinger, Matched, NotMatched };

class R307Fingerprint final {
public:
    R307Fingerprint(HardwareSerial& serial, int rxPin, int txPin,
                    std::uint32_t baud = 57600U,
                    std::uint32_t address = 0xFFFFFFFFUL,
                    std::uint32_t password = 0x00000000UL);
    bool begin();
    bool ready() const { return ready_; }
    FingerprintScanResult poll(FingerprintMatch& match);
    // Back-compat convenience for callers that only care about a confirmed match.
    bool pollMatch(FingerprintMatch& match) { return poll(match) == FingerprintScanResult::Matched; }
    // Forces the next poll() to attempt a fresh capture even if the previous finger was
    // never cleanly lifted (no intervening "no finger" reading) -- call this whenever a
    // new attempt should start regardless of whatever is currently resting on the sensor.
    void rearm() { armed_ = true; }

private:
    bool sendCommand_(const std::uint8_t* content, std::size_t contentLength,
                      std::uint8_t* response, std::size_t& responseLength,
                      std::uint32_t timeoutMs = 250U);
    bool readPacket_(std::uint8_t* packet, std::size_t& packetLength,
                     std::uint32_t timeoutMs);
    bool confirmation_(const std::uint8_t* response, std::size_t responseLength,
                       std::uint8_t& code) const;
    void flushInput_();

    HardwareSerial& serial_;
    int rxPin_;
    int txPin_;
    std::uint32_t baud_;
    std::uint32_t address_;
    std::uint32_t password_;
    bool ready_ = false;
    bool armed_ = true;
};

}  // namespace ForestSensors
