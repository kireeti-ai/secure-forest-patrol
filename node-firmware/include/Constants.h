#pragma once

#include <cstddef>

namespace forest::constants
{

    constexpr std::size_t kPacketHeaderSize = 8;
    constexpr std::size_t kPacketCrcSize = 2;
    // 180: large enough for a signed patrol event (type 'P', see ForestCrypto/SignedPatrolPayload.h:
    // up to 13 + 10-byte officer UID + 2*32-byte hashes + 1 + up to 72-byte DER signature = 160
    // bytes), with headroom. Was 48 before Phase 2 (docs/TAMPER_EVIDENCE_SECURITY_PLAN.md) added
    // signed events; legacy 'R'/'A'/'V' payloads are far smaller and unaffected.
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
    // unix epoch second (uint32 LE) - how a node with no RTC (see ForestTime/SoftClock) learns
    // real wall-clock time. Older gateways/nodes that only know the 2-byte form still
    // interoperate: Validator accepts either exact size.
    constexpr std::size_t kAcknowledgementPayloadSizeWithTime = 6;
    constexpr std::uint8_t kGatewayNodeId = 0xFEU;
    constexpr std::size_t kDtnQueueCapacity = 8U;
    constexpr std::uint32_t kDtnQueueLifetimeMs = 300000U;
    constexpr std::size_t kDtnProcessingBatchSize = 2U;

} // namespace forest::constants
