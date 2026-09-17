#include "BackendIngestionClient.h"

#include <ArduinoJson.h>

namespace forest::backend {

namespace {
constexpr const char* kTopicNodeStatus = "forest/events/node-status";
constexpr int kProtocolVersion = 4;  // matches forest::protocol wire format
}  // namespace

BackendIngestionClient::BackendIngestionClient(const BackendConfig& config)
    : config_(config) {
    if (config_.mqttTls) {
        // Certificate validation is intentionally skipped (setInsecure())
        // rather than pinning a CA bundle that will eventually expire and
        // brick the device. This still gets an encrypted link (protects
        // MQTT_USERNAME/MQTT_PASSWORD from passive sniffing); it does not
        // protect against an active MITM impersonating the broker. That
        // gap is acceptable here because event authenticity is guaranteed
        // at the application layer regardless of transport (ECC signature
        // + hash chain, verified by the backend) -- see docs/MQTT.md.
        secureClient_.setInsecure();
        mqttClient_.setClient(secureClient_);
    } else {
        mqttClient_.setClient(plainClient_);
    }
    mqttClient_.setServer(config_.mqttBrokerHost, config_.mqttBrokerPort);
}

void BackendIngestionClient::begin() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(config_.wifiSsid, config_.wifiPassword);
    wifiState_ = LinkState::Connecting;
    logLine("[WIFI] CONNECTING");
}

void BackendIngestionClient::logLine(const char* line) {
    if (logger_ != nullptr) {
        logger_->log(logging::LogLevel::info, line);
    }
}

void BackendIngestionClient::tick(std::uint32_t currentMs) {
    tickWifi(currentMs);
    tickMqtt(currentMs);
    if (wifiState_ == LinkState::Connected && mqttState_ == LinkState::Connected) {
        mqttClient_.loop();
        drainOutbox();
    }
}

void BackendIngestionClient::tickWifi(std::uint32_t currentMs) {
    const bool up = WiFi.status() == WL_CONNECTED;
    if (up && wifiState_ != LinkState::Connected) {
        wifiState_ = LinkState::Connected;
        logLine("[WIFI] CONNECTED");
    } else if (!up && wifiState_ == LinkState::Connected) {
        wifiState_ = LinkState::Disconnected;
        logLine("[WIFI] DISCONNECTED");
    }
    if (!up && (currentMs - lastWifiAttemptMs_) >= kReconnectIntervalMs) {
        lastWifiAttemptMs_ = currentMs;
        wifiState_ = LinkState::Connecting;
        WiFi.disconnect();
        WiFi.begin(config_.wifiSsid, config_.wifiPassword);
    }
}

void BackendIngestionClient::tickMqtt(std::uint32_t currentMs) {
    if (wifiState_ != LinkState::Connected) {
        if (mqttState_ != LinkState::Disconnected) {
            mqttState_ = LinkState::Disconnected;
        }
        return;
    }
    if (mqttClient_.connected()) {
        if (mqttState_ != LinkState::Connected) {
            mqttState_ = LinkState::Connected;
            logLine("[MQTT] CONNECTED");
        }
        return;
    }
    if (mqttState_ == LinkState::Connected) {
        mqttState_ = LinkState::Disconnected;
        logLine("[MQTT] DISCONNECTED");
    }
    // Transient failure (broker/Wi-Fi hiccup): retry on an interval rather
    // than blocking the tick loop. Never treated as permanent -- there is
    // no "invalid credentials" style failure the gateway can distinguish
    // here, so it always keeps retrying.
    if ((currentMs - lastMqttAttemptMs_) >= kReconnectIntervalMs) {
        lastMqttAttemptMs_ = currentMs;
        mqttState_ = LinkState::Connecting;
        char clientId[24];
        snprintf(clientId, sizeof(clientId), "gw-%02X", config_.gatewayId);
        const bool connected = (config_.mqttUsername != nullptr && config_.mqttUsername[0] != '\0')
            ? mqttClient_.connect(clientId, config_.mqttUsername, config_.mqttPassword)
            : mqttClient_.connect(clientId);
        if (connected) {
            mqttState_ = LinkState::Connected;
            logLine("[MQTT] CONNECTED");
        }
    }
}

void BackendIngestionClient::enqueue(const ForestEventEnvelope& envelope) {
    if (outboxCount_ >= kOutboxCapacity) {
        // Outbox full: drop the oldest queued event rather than the new
        // one, so the freshest field data always has a chance to publish.
        outboxHead_ = (outboxHead_ + 1) % kOutboxCapacity;
        outboxCount_--;
        logLine("[MQTT] OUTBOX FULL, DROPPED OLDEST");
    }
    const std::size_t tail = (outboxHead_ + outboxCount_) % kOutboxCapacity;
    outbox_[tail] = envelope;
    outboxCount_++;
}

void BackendIngestionClient::drainOutbox() {
    while (outboxCount_ > 0) {
        const ForestEventEnvelope& envelope = outbox_[outboxHead_];
        if (!publishEnvelope(envelope)) {
            break;  // leave it queued, retry next tick
        }
        outboxHead_ = (outboxHead_ + 1) % kOutboxCapacity;
        outboxCount_--;
    }
}

bool BackendIngestionClient::publishEnvelope(const ForestEventEnvelope& envelope) {
    JsonDocument doc;
    char gatewayIdStr[8];
    snprintf(gatewayIdStr, sizeof(gatewayIdStr), "GW-%02X", config_.gatewayId);
    doc["gateway_id"] = gatewayIdStr;
    char nodeIdStr[8];
    snprintf(nodeIdStr, sizeof(nodeIdStr), "0x%02X", envelope.sourceId);
    doc["node_id"] = nodeIdStr;
    doc["sequence"] = envelope.sequenceNumber;
    doc["protocol_version"] = kProtocolVersion;
    doc["rssi"] = envelope.rssiDbm;
    doc["snr"] = envelope.snrDb;
    doc["gateway_received_at_ms"] = envelope.gatewayReceivedAtMs;
    if (envelope.hasRtc) {
        char rtcIso[24];
        snprintf(rtcIso, sizeof(rtcIso), "20%02u-%02u-%02uT%02u:%02u:%02uZ",
                  envelope.rtcYear - 2000, envelope.rtcMonth, envelope.rtcDay,
                  envelope.rtcHour, envelope.rtcMinute, envelope.rtcSecond);
        doc["event_created_at"] = rtcIso;
        doc["temperature_c"] = envelope.temperatureC;
    }

    char buffer[256];
    const size_t len = serializeJson(doc, buffer, sizeof(buffer));
    Serial.printf("[MQTT PUBLISH] topic=%s node=%s seq=%u\n", kTopicNodeStatus, nodeIdStr,
                  static_cast<unsigned>(envelope.sequenceNumber));
    const bool ok = mqttClient_.publish(kTopicNodeStatus, reinterpret_cast<const uint8_t*>(buffer), len, false);
    Serial.println(ok ? "[MQTT RESULT] PUBLISHED" : "[MQTT RESULT] FAILED");
    return ok;
}

void BackendIngestionClient::dispatchMessages(lora::ILoRaDriver& /*radioDriver*/) {
    // Reserved for a future downlink (backend/broker -> node) acknowledgement
    // path. Nothing to do today: the outbox is drained from tick() above.
}

}  // namespace forest::backend
