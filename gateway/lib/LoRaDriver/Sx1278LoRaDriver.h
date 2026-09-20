#pragma once

#include <array>
#include <cstdint>

#include "ILoRaDriver.h"

namespace forest::lora {

class Sx1278LoRaDriver final : public ILoRaDriver {
public:
    bool begin() override;
    bool receive(RawRadioPacket& packet) override;
    bool send(const std::uint8_t* data, std::size_t length) override;

    uint32_t packetsReceivedCounter() const { return packetsReceivedCounter_; }
    uint32_t watchdogRearms() const { return watchdogRearms_; }
    uint32_t watchdogReinits() const { return watchdogReinits_; }
    uint32_t acksSentCounter() const { return acksSentCounter_; }

private:
    // Receiver watchdog: the SX1278 has been seen to stop hearing nodes after long uptime while the
    // firmware kept running. Every second the operating mode is read back; if the chip is not in LoRa
    // continuous-RX it is re-armed, and after a long silence it is fully re-initialised.
    void watchdog_();
    bool configureRadio_();

    static constexpr long frequencyHz = 433000000L;
    static constexpr int spreadingFactor = 7;
    static constexpr long signalBandwidthHz = 125000L;
    static constexpr int codingRateDenominator = 5;
    static constexpr std::uint32_t reinitAfterSilenceMs = 600000U;   // 10 minutes
    static constexpr int syncWord = 0x12;

    std::array<std::uint8_t, 255> rxBuffer_{};

    uint32_t packetsReceivedCounter_{0};
    uint32_t acksSentCounter_{0};
    uint32_t watchdogRearms_{0};
    uint32_t watchdogReinits_{0};
    uint32_t lastWatchdogMs_{0};
    uint32_t lastActivityMs_{0};
};

}  // namespace forest::lora
