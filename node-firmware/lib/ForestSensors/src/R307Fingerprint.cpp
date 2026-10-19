#include "R307Fingerprint.h"

#include <Arduino.h>
#include <array>
#include <cstring>

namespace ForestSensors {
namespace {
constexpr std::uint16_t kHeader = 0xEF01U;
constexpr std::uint8_t kCommandPacket = 0x01U;
constexpr std::uint8_t kAckPacket = 0x07U;
constexpr std::uint8_t kVerifyPassword = 0x13U;
constexpr std::uint8_t kGenImage = 0x01U;
constexpr std::uint8_t kImageToTz = 0x02U;
constexpr std::uint8_t kSearch = 0x04U;
constexpr std::uint8_t kNoFinger = 0x02U;
constexpr std::size_t kMaxPacket = 32U;

void put32(std::uint8_t* p, std::uint32_t value) {
    p[0] = static_cast<std::uint8_t>(value >> 24U);
    p[1] = static_cast<std::uint8_t>(value >> 16U);
    p[2] = static_cast<std::uint8_t>(value >> 8U);
    p[3] = static_cast<std::uint8_t>(value);
}

std::uint16_t get16(const std::uint8_t* p) {
    return static_cast<std::uint16_t>((static_cast<std::uint16_t>(p[0]) << 8U) | p[1]);
}
}  // namespace

R307Fingerprint::R307Fingerprint(HardwareSerial& serial, int rxPin, int txPin,
                                 std::uint32_t baud, std::uint32_t address,
                                 std::uint32_t password)
    : serial_(serial), rxPin_(rxPin), txPin_(txPin), baud_(baud), address_(address), password_(password) {}

void R307Fingerprint::flushInput_() {
    while (serial_.available() > 0) static_cast<void>(serial_.read());
}

bool R307Fingerprint::begin() {
    serial_.begin(baud_, SERIAL_8N1, rxPin_, txPin_);
    flushInput_();
    const std::uint8_t content[] = {kVerifyPassword,
        static_cast<std::uint8_t>(password_ >> 24U), static_cast<std::uint8_t>(password_ >> 16U),
        static_cast<std::uint8_t>(password_ >> 8U), static_cast<std::uint8_t>(password_)};
    std::array<std::uint8_t, kMaxPacket> response{};
    std::size_t responseLength = response.size();
    if (!sendCommand_(content, sizeof(content), response.data(), responseLength)) return false;
    std::uint8_t code = 0xFFU;
    ready_ = confirmation_(response.data(), responseLength, code) && code == 0x00U;
    armed_ = true;
    return ready_;
}

bool R307Fingerprint::sendCommand_(const std::uint8_t* content, std::size_t contentLength,
                                   std::uint8_t* response, std::size_t& responseLength,
                                   std::uint32_t timeoutMs) {
    if (content == nullptr || contentLength == 0U || contentLength > 20U || response == nullptr) return false;
    const std::uint16_t packageLength = static_cast<std::uint16_t>(contentLength + 2U);
    std::array<std::uint8_t, kMaxPacket> packet{};
    const std::size_t total = 11U + contentLength;
    if (total > packet.size()) return false;
    packet[0] = static_cast<std::uint8_t>(kHeader >> 8U); packet[1] = static_cast<std::uint8_t>(kHeader);
    put32(packet.data() + 2U, address_);
    packet[6] = kCommandPacket;
    packet[7] = static_cast<std::uint8_t>(packageLength >> 8U); packet[8] = static_cast<std::uint8_t>(packageLength);
    std::memcpy(packet.data() + 9U, content, contentLength);
    std::uint16_t checksum = static_cast<std::uint16_t>(kCommandPacket + (packageLength >> 8U) + (packageLength & 0xFFU));
    for (std::size_t i = 0; i < contentLength; ++i) checksum = static_cast<std::uint16_t>(checksum + content[i]);
    packet[9U + contentLength] = static_cast<std::uint8_t>(checksum >> 8U);
    packet[10U + contentLength] = static_cast<std::uint8_t>(checksum);
    flushInput_();
    serial_.write(packet.data(), total);
    serial_.flush();
    return readPacket_(response, responseLength, timeoutMs);
}

bool R307Fingerprint::readPacket_(std::uint8_t* packet, std::size_t& packetLength,
                                  std::uint32_t timeoutMs) {
    const std::uint32_t start = millis();
    std::size_t count = 0U;
    while (millis() - start < timeoutMs) {
        while (serial_.available() > 0) {
            const int value = serial_.read();
            if (value < 0) continue;
            if (count == 0U && value != 0xEF) continue;
            if (count == 1U && value != 0x01) { count = 0U; continue; }
            if (count >= kMaxPacket) return false;
            packet[count++] = static_cast<std::uint8_t>(value);
            if (count >= 9U) {
                const std::size_t declared = (static_cast<std::size_t>(packet[7]) << 8U) | packet[8];
                const std::size_t expected = 9U + declared;
                if (declared < 3U || expected > packetLength || expected > kMaxPacket) return false;
                if (count == expected) { packetLength = count; return packet[6] == kAckPacket; }
            }
        }
        delay(1);
    }
    return false;
}

bool R307Fingerprint::confirmation_(const std::uint8_t* response, std::size_t responseLength,
                                    std::uint8_t& code) const {
    if (response == nullptr || responseLength < 12U || response[6] != kAckPacket) return false;
    const std::size_t declared = (static_cast<std::size_t>(response[7]) << 8U) | response[8];
    if (declared < 3U || 9U + declared != responseLength) return false;
    code = response[9];
    return true;
}

FingerprintScanResult R307Fingerprint::poll(FingerprintMatch& match) {
    if (!ready_) return FingerprintScanResult::NoFinger;
    std::array<std::uint8_t, kMaxPacket> response{};
    std::size_t responseLength = response.size();
    const std::uint8_t imageCommand[] = {kGenImage};
    // These timeouts are deliberately generous (not the ZFM/R307 datasheet's nominal figures):
    // this module measured ~80% comm timeouts at 150-250ms even for a plain "no finger"
    // check, and reliably succeeded once image2Tz/search were given 600-800ms.
    if (!sendCommand_(imageCommand, sizeof(imageCommand), response.data(), responseLength, 500U)) {
        return FingerprintScanResult::NoFinger;
    }
    std::uint8_t code = 0xFFU;
    if (!confirmation_(response.data(), responseLength, code)) return FingerprintScanResult::NoFinger;
    if (code == kNoFinger) { armed_ = true; return FingerprintScanResult::NoFinger; }
    if (code != 0x00U || !armed_) return FingerprintScanResult::NoFinger;
    const std::uint8_t charCommand[] = {kImageToTz, 0x01U};
    responseLength = response.size();
    if (!sendCommand_(charCommand, sizeof(charCommand), response.data(), responseLength, 600U)) {
        return FingerprintScanResult::NoFinger;
    }
    if (!confirmation_(response.data(), responseLength, code) || code != 0x00U) {
        // Image was captured but could not be turned into a template (poor
        // contact, smudge, etc.) -- a presented finger that is not a match.
        armed_ = false;
        return FingerprintScanResult::NotMatched;
    }
    const std::uint8_t searchCommand[] = {kSearch, 0x01U, 0x00U, 0x00U, 0x00U, 0xA3U};
    responseLength = response.size();
    if (!sendCommand_(searchCommand, sizeof(searchCommand), response.data(), responseLength, 800U)) {
        armed_ = false;
        return FingerprintScanResult::NotMatched;
    }
    if (!confirmation_(response.data(), responseLength, code) || code != 0x00U || responseLength < 16U) {
        // Search ran but found no enrolled template for this finger.
        armed_ = false;
        return FingerprintScanResult::NotMatched;
    }
    match.pageId = get16(response.data() + 10U);
    match.score = get16(response.data() + 12U);
    armed_ = false;
    return FingerprintScanResult::Matched;
}

}  // namespace ForestSensors
