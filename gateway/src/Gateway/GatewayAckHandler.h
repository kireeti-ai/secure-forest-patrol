#pragma once

#include <cstdint>
#include <cstddef>
#include <array>
#include "ILoRaDriver.h"

namespace jalri::gateway {

struct GatewayStats {
    std::uint32_t packetsReceived = 0;
    std::uint32_t ackSent = 0;
    std::uint32_t duplicatePackets = 0;
    int rssi = 0;
    float snr = 0.0f;
    std::uint32_t lastSeenMs = 0;
    std::uint32_t ackTxFailures = 0;
};

struct DuplicateKey {
    std::uint8_t sourceId;
    std::uint8_t type;
    std::uint16_t sequenceNumber;

    bool operator<(const DuplicateKey& other) const {
        if (sourceId != other.sourceId) return sourceId < other.sourceId;
        if (type != other.type) return type < other.type;
        return sequenceNumber < other.sequenceNumber;
    }
};

class GatewayAckHandler {
public:
    GatewayAckHandler() = default;

    bool processDataPacket(std::uint8_t targetNodeId,
                          std::uint8_t destinationId,
                          std::uint16_t sequenceNumber,
                          int rssiDbm,
                          float snrDb,
                          std::uint32_t timestampMs,
                          lora::ILoRaDriver* radioDriver);

    const GatewayStats& stats() const { return stats_; }

private:
    bool sendDataAckPacket_(std::uint8_t targetNodeId,
                           std::uint16_t sequenceNumber,
                           lora::ILoRaDriver* radioDriver);

    static std::uint16_t computeCrc16_(const std::uint8_t* data, std::size_t length);

    struct DataDuplicateEntry { DuplicateKey key{}; std::uint32_t timestampMs = 0; bool active = false; };
    static constexpr std::size_t duplicateCapacity_ = 32U;
    static constexpr std::uint32_t duplicateExpiryMs_ = 10000U;
    std::array<DataDuplicateEntry, duplicateCapacity_> dataDuplicates_{};
    std::size_t nextDataDuplicate_ = 0;
    GatewayStats stats_{};
    std::uint16_t ackSeq_ = 1;
};

}  // namespace jalri::gateway
