#pragma once

#include <cstddef>
#include <cstdint>
#include <array>

namespace forest::config
{

#ifndef FOREST_NODE_ID
#define FOREST_NODE_ID 1U
#endif
#ifndef FOREST_TEST_MODE
#define FOREST_TEST_MODE 0
#endif
#ifndef FOREST_RFID_SS_PIN
#define FOREST_RFID_SS_PIN 4
#endif
#ifndef FOREST_RFID_RST_PIN
#define FOREST_RFID_RST_PIN 5
#endif
// Transmitted as part of every signed patrol event (Phase 2, docs/TAMPER_EVIDENCE_SECURITY_PLAN.md)
// and covered by the signature - must match whatever this node is registered under in the
// backend's checkpoint records, and is a build-time constant since officer identity (the RFID
// scan) is per-event but which physical checkpoint this node sits at is not.
#ifndef FOREST_CHECKPOINT_ID
#define FOREST_CHECKPOINT_ID "CP-01"
#endif
// Phase 4 (docs/TAMPER_EVIDENCE_SECURITY_PLAN.md): AES-128-GCM confidentiality key for the LoRa
// uplink, wrapped around the already-signed application payload (ForestCrypto/src/LoRaCipher.h).
// Must be byte-identical to gateway/include/Config.h's copy - this is a pre-shared symmetric key
// for the node<->gateway link, not derived from or related to the node's ECDSA signing identity.
// Demo/single-deployment scope: one key shared network-wide, not rotated or per-node; a real
// fleet deployment should provision this per-node (e.g. alongside the node's NVS-stored ECDSA
// key) rather than compiling it into every node's firmware image identically.
#ifndef FOREST_LORA_AES_KEY
#define FOREST_LORA_AES_KEY {0x2AU,0x2EU,0x9CU,0xBEU,0xF7U,0xEEU,0x59U,0xD6U,0x2BU,0x5BU,0xE1U,0xB0U,0x08U,0x89U,0x66U,0x72U}
#endif

    struct RadioConfig
    {
        long frequencyHz;
        int sckPin;
        int misoPin;
        int mosiPin;
        int chipSelectPin;
        int resetPin;
        int dio0Pin;
    };

    struct NodeConfig
    {
        std::uint8_t nodeId;
    };

    struct ProtocolConfig
    {
        std::uint8_t preamble;
        std::uint8_t version;
        std::size_t maxPayloadSize;
        std::size_t maxRadioPacketSize;
    };

    struct PowerConfig
    {
        std::uint32_t heartbeatIntervalMs;
        std::uint32_t telemetryIntervalMs;
    };

    struct SensorConfig
    {
        int i2cSdaPin;
        int i2cSclPin;
        int rfidSsPin;
        int rfidResetPin;
    };

    struct ReliabilityConfig
    {
        std::uint32_t acknowledgementTimeoutMs;
        std::uint8_t maxRetries;
    };

    struct NetworkConfig
    {
        struct StaticRoute
        {
            constexpr StaticRoute(std::uint8_t destination = 0U, std::uint8_t nextHop = 0U)
                : destinationId(destination), nextHopId(nextHop) {}
            std::uint8_t destinationId = 0;
            std::uint8_t nextHopId = 0;
        };
        static constexpr std::size_t kStaticRouteCapacity = 8U;
        constexpr NetworkConfig(std::uint8_t ttl = 0U, std::uint8_t maxHops = 0U,
                                 std::uint32_t neighborTimeout = 0U, std::size_t metricWindow = 0U,
                                 std::uint8_t routeDestination = 0U, std::uint8_t routeNextHop = 0U)
            : defaultTtl(ttl), maximumHopCount(maxHops), neighborTimeoutMs(neighborTimeout),
              linkMetricWindowSize(metricWindow),
              staticRoutes{StaticRoute(routeDestination, routeNextHop)},
              staticRouteCount((routeDestination != 0U && routeNextHop != 0U) ? 1U : 0U) {}
        std::uint8_t defaultTtl;
        std::uint8_t maximumHopCount;
        std::uint32_t neighborTimeoutMs;
        std::size_t linkMetricWindowSize;
        std::array<StaticRoute, kStaticRouteCapacity> staticRoutes{};
        std::size_t staticRouteCount = 0;
    };

    struct FirmwareConfig
    {
        const RadioConfig radio;
        const NodeConfig node;
        const ProtocolConfig protocol;
        const PowerConfig power;
        const SensorConfig sensors;
        const ReliabilityConfig reliability;
        const NetworkConfig network;
    };

    constexpr NetworkConfig kDefaultNetworkConfig(8U, 16U, 30000U, 8U, 0xFEU, 0x02U);

    constexpr FirmwareConfig kDefaultFirmwareConfig{
        {433000000L, 12, 13, 11, 10, 9, 14},
        {static_cast<std::uint8_t>(FOREST_NODE_ID)},
        {0xA5U, 4U, 48U, 255U},
        {10000U, 15000U},
        {21, 20, FOREST_RFID_SS_PIN, FOREST_RFID_RST_PIN},
        {2500U, 3U},
        kDefaultNetworkConfig,
    };

} // namespace forest::config
