#pragma once

#include <cstdint>
#include <cstddef>

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <freertos/FreeRTOS.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include "LoRaTypes.h"
#include "Packet.h"
#include "ILogger.h"

namespace forest::lora { class ILoRaDriver; }

namespace forest::backend {

struct BackendConfig {
    const char* wifiSsid;
    const char* wifiPassword;
    const char* baseUrl;
    const char* ingestionKey;
    std::uint8_t gatewayId;
    const char* mqttBrokerHost;
    std::uint16_t mqttBrokerPort;
    // Production brokers (e.g. HiveMQ Cloud) require TLS + auth; local dev
    // Mosquitto does not. See docs/MQTT.md.
    bool mqttTls;
    const char* mqttUsername;
    const char* mqttPassword;
};

struct ForestEventEnvelope {
    std::uint8_t sourceId{0};
    std::uint16_t sequenceNumber{0};
    int rssiDbm{0};
    float snrDb{0.0f};
    std::uint32_t gatewayReceivedAtMs{0};
    bool hasRtc{false};
    std::uint16_t rtcYear{0};
    std::uint8_t rtcMonth{0};
    std::uint8_t rtcDay{0};
    std::uint8_t rtcHour{0};
    std::uint8_t rtcMinute{0};
    std::uint8_t rtcSecond{0};
    float temperatureC{0.0f};
    // Acoustic detection from a node (MAX4466 trigger + TinyML). Payload 'A' v1:
    // [0x41, 0x01, class(1=chainsaw,2=gunshot), confidence u8 (p*255), trigger RMS u16 LE].
    bool hasAcoustic{false};
    std::uint8_t acousticClass{0};
    std::uint8_t acousticConfidenceU8{0};
    std::uint16_t acousticTriggerRms{0};
    // Shared cap on raw UID bytes for both rfidUid and verifyUid below, enforced by
    // GatewayService when it parses the LoRa payload. The formatted-hex scratch buffers
    // in BackendIngestionClient.cpp (`char uid[32]`) are sized off this constant via a
    // static_assert -- bump both together if the UID format ever grows.
    static constexpr std::size_t kMaxUidLength = 10U;

    bool hasRfid{false};
    std::uint8_t rfidUid[kMaxUidLength]{};
    std::uint8_t rfidUidLength{0};
    // Two-factor verification result ('V' payload): card claimed an officer, then a
    // fingerprint was (or wasn't) presented within the node's verification window.
    // verifyStatus: 1=MATCH, 2=MISMATCH (wrong/no finger -- possible proxy), 3=TIMEOUT.
    bool hasVerification{false};
    std::uint8_t verifyStatus{0};
    std::uint8_t verifyUid[kMaxUidLength]{};
    std::uint8_t verifyUidLength{0};
    std::uint16_t verifyClaimedPageId{0};
    std::uint16_t verifyActualPageId{0};
    std::uint16_t verifyScore{0};

    // Signed patrol event (Phase 2, docs/TAMPER_EVIDENCE_SECURITY_PLAN.md). Payload 'P' v1 - see
    // node-firmware/lib/ForestCrypto/src/SignedPatrolPayload.h for the exact wire layout this
    // must stay in lockstep with.
    static constexpr std::size_t kMaxCheckpointIdLen = 16U;
    static constexpr std::size_t kPatrolHashBytes = 32U;
    static constexpr std::size_t kMaxSignatureBytes = 72U;

    bool hasPatrol{false};
    std::uint32_t patrolSequence{0};
    std::uint32_t patrolEpoch{0};
    std::uint8_t patrolRfidResult{0};          // 1=VALID, 2=INVALID
    std::uint8_t patrolFingerprintResult{0};   // 1=MATCH, 2=NO_MATCH
    char patrolCheckpointId[kMaxCheckpointIdLen + 1]{};
    std::uint8_t patrolOfficerUid[kMaxUidLength]{};
    std::uint8_t patrolOfficerUidLength{0};
    std::uint8_t patrolPreviousHash[kPatrolHashBytes]{};
    std::uint8_t patrolRecordHash[kPatrolHashBytes]{};
    std::uint8_t patrolSignature[kMaxSignatureBytes]{};
    std::uint8_t patrolSignatureLength{0};
};

enum class LinkState { Disconnected, Connecting, Connected };

// Wi-Fi -> MQTT publish path for events the gateway pulls off LoRa.
//
// Wi-Fi and MQTT connection state are tracked separately (never collapsed
// into one "ONLINE" flag, per docs/GATEWAY_BACKEND_CONTRACT.md). Events are
// queued into a fixed-size local outbox so nothing is lost while either
// link is down; tick() drains the outbox once both links are up. This
// class only retries transient transport failures -- there is no
// "permanent failure" case here because the gateway does not verify
// signatures itself (that stays a backend responsibility).
class BackendIngestionClient final {
public:
    static constexpr std::size_t kOutboxCapacity = 32;

    explicit BackendIngestionClient(const BackendConfig& config);

    // Starts Wi-Fi and a dedicated network task (core 0) that runs tick(). All
    // Wi-Fi/DNS/MQTT work stays off the main loop, so an unreachable broker can
    // never stall LoRa reception there.
    void begin();
    void tick(std::uint32_t currentMs);
    void dispatchMessages(lora::ILoRaDriver& radioDriver);

    // Called by GatewayService when a non-duplicate forest event is parsed
    // off LoRa. Non-blocking: just enqueues into the local outbox.
    void enqueue(const ForestEventEnvelope& envelope);

    void setLogger(logging::ILogger* logger) { logger_ = logger; }

    LinkState wifiState() const { return wifiState_; }
    LinkState mqttState() const { return mqttState_; }

private:
    void tickWifi(std::uint32_t currentMs);
    void tickMqtt(std::uint32_t currentMs);
    void tickGatewayStatus(std::uint32_t currentMs);
    void drainOutbox();
    bool publishEnvelope(const ForestEventEnvelope& envelope);
    bool publishRfid(const ForestEventEnvelope& envelope);
    bool publishAcoustic(const ForestEventEnvelope& envelope);
    bool publishVerification(const ForestEventEnvelope& envelope);
    bool publishPatrol(const ForestEventEnvelope& envelope);
    void logLine(const char* line);
    static void networkTask(void* self);

    BackendConfig config_;
    WiFiClient plainClient_;
    WiFiClientSecure secureClient_;
    PubSubClient mqttClient_;
    logging::ILogger* logger_{nullptr};

    LinkState wifiState_{LinkState::Disconnected};
    LinkState mqttState_{LinkState::Disconnected};
    std::uint32_t lastWifiAttemptMs_{0};
    std::uint32_t lastMqttAttemptMs_{0};
    std::uint32_t lastStatusReportMs_{0};
    static constexpr std::uint32_t kReconnectIntervalMs = 5000U;
    static constexpr std::uint32_t kMaxMqttBackoffMs = 30000U;
    std::uint32_t mqttBackoffMs_{kReconnectIntervalMs};
    static constexpr std::uint32_t kStatusReportIntervalMs = 30000U;

    ForestEventEnvelope outbox_[kOutboxCapacity]{};
    std::size_t outboxHead_{0};
    std::size_t outboxCount_{0};
    std::uint32_t outboxHeadSerial_{0};  // bumps whenever the head advances (pop or drop-oldest)
    SemaphoreHandle_t outboxMutex_{nullptr};  // outbox is shared: main loop enqueues, network task drains
    TaskHandle_t networkTask_{nullptr};
};

}  // namespace forest::backend
