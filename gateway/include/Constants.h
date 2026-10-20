#pragma once

#include <cstddef>

namespace forest::constants
{

    constexpr std::size_t kPacketHeaderSize = 8;
    constexpr std::size_t kPacketCrcSize = 2;
    // Must match node-firmware/include/Constants.h exactly (180: fits the signed patrol event
    // payload, type 'P' - see node-firmware's ForestCrypto/SignedPatrolPayload.h for the layout
    // this gateway's GatewayService.cpp decoder must match in lockstep).
    constexpr std::size_t kMaxPayloadSize = 180;
    constexpr std::size_t kMaxPacketSize = kPacketHeaderSize + kMaxPayloadSize + kPacketCrcSize;
    constexpr std::size_t kMaxRadioBufferSize = 255;
    constexpr std::size_t kPacketQueueCapacity = 8;
    constexpr std::size_t kEventBusMaxListeners = 8;
    constexpr std::size_t kDuplicatePacketCapacity = 32;
    constexpr std::size_t kPendingTransmissionCapacity = 8;
    constexpr std::uint32_t kDuplicateExpiryMs = 10000U;
    constexpr std::size_t kAcknowledgementPayloadSize = 2;
    // Extended ACK: the 2-byte acknowledged sequence number, plus the gateway's current UTC
    // unix epoch second (uint32 LE) - how a node with no RTC (see node-firmware's
    // ForestTime/SoftClock) learns real wall-clock time. Must match node-firmware/include/Constants.h.
    constexpr std::size_t kAcknowledgementPayloadSizeWithTime = 6;
    constexpr std::uint8_t kGatewayNodeId = 0xFEU;
    constexpr std::size_t kDtnQueueCapacity = 8U;
    constexpr std::uint32_t kDtnQueueLifetimeMs = 300000U;
    constexpr std::size_t kDtnProcessingBatchSize = 2U;

} // namespace forest::constants
