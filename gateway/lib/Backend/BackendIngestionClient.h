#pragma once

#include <cstdint>
#include <cstddef>

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

#include "LoRaTypes.h"
#include "Packet.h"
#include "ILogger.h"

namespace jalri::lora { class ILoRaDriver; }

namespace jalri::backend {

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

// A forest event as the gateway actually has it today: LoRa source/sequence
// plus whatever the 9-byte RTC+temperature diagnostic payload decoded to.
// No rfid/fingerprint/signature/hash fields are invented here -- the
// firmware doesn't produce that data yet (see docs/MQTT.md).
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
    void drainOutbox();
    bool publishEnvelope(const ForestEventEnvelope& envelope);
    void logLine(const char* line);

    BackendConfig config_;
    WiFiClient plainClient_;
    WiFiClientSecure secureClient_;
    PubSubClient mqttClient_;
    logging::ILogger* logger_{nullptr};

    LinkState wifiState_{LinkState::Disconnected};
    LinkState mqttState_{LinkState::Disconnected};
    std::uint32_t lastWifiAttemptMs_{0};
    std::uint32_t lastMqttAttemptMs_{0};
    static constexpr std::uint32_t kReconnectIntervalMs = 5000U;

    ForestEventEnvelope outbox_[kOutboxCapacity]{};
    std::size_t outboxHead_{0};
    std::size_t outboxCount_{0};
};

}  // namespace jalri::backend
