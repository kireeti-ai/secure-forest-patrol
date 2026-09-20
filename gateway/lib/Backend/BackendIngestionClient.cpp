#include "BackendIngestionClient.h"

#include <ArduinoJson.h>
#include <cstring>

namespace forest::backend {

namespace {
constexpr const char* kTopicNodeStatus = "forest/events/node-status";
constexpr const char* kTopicRfid = "forest/events/rfid";
constexpr const char* kTopicGatewayStatus = "forest/events/gateway-status";
constexpr int kProtocolVersion = 4;  // matches forest::protocol wire format

const char* wifiStatusName(wl_status_t status) {
    switch (status) {
        case WL_CONNECTED: return "CONNECTED";
        case WL_NO_SSID_AVAIL: return "NO_SSID_AVAILABLE";
        case WL_CONNECT_FAILED: return "CONNECT_FAILED";
        case WL_CONNECTION_LOST: return "CONNECTION_LOST";
        case WL_DISCONNECTED: return "DISCONNECTED";
        case WL_IDLE_STATUS: return "IDLE";
        default: return "UNKNOWN";
    }
}
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
    // PubSubClient's default 256-byte packet limit is too small for the
    // gateway-status JSON plus its topic; oversized publishes fail silently.
    mqttClient_.setBufferSize(512);
    // Bound every blocking socket operation so a dead broker/DNS cannot hold the
    // network task for long either.
    mqttClient_.setSocketTimeout(4);
    plainClient_.setTimeout(4);
    secureClient_.setTimeout(4);
    outboxMutex_ = xSemaphoreCreateMutex();
}

void BackendIngestionClient::begin() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.persistent(false);
    WiFi.begin(config_.wifiSsid, config_.wifiPassword);
    wifiState_ = LinkState::Connecting;
    Serial.printf("[WIFI] CONNECTING | SSID=%s | status=%s(%d)\n",
                  config_.wifiSsid != nullptr ? config_.wifiSsid : "<unset>",
                  wifiStatusName(WiFi.status()), static_cast<int>(WiFi.status()));
    if (networkTask_ == nullptr) {
        // 16 KB stack: the TLS handshake needs far more than the default.
        xTaskCreatePinnedToCore(&BackendIngestionClient::networkTask, "backend-net", 16384, this, 1, &networkTask_, 0);
    }
}

void BackendIngestionClient::networkTask(void* self) {
    auto* client = static_cast<BackendIngestionClient*>(self);
    for (;;) {
        client->tick(millis());
        vTaskDelay(pdMS_TO_TICKS(10));
    }
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
        // Every gateway -> backend message (RFID scans, node telemetry and
        // the gateway heartbeat) goes over MQTT; see docs/MQTT.md.
        drainOutbox();
        tickGatewayStatus(currentMs);
    }
}

void BackendIngestionClient::tickGatewayStatus(std::uint32_t currentMs) {
    if ((currentMs - lastStatusReportMs_) < kStatusReportIntervalMs) return;
    lastStatusReportMs_ = currentMs;

    JsonDocument doc;
    char gatewayIdStr[8];
    snprintf(gatewayIdStr, sizeof(gatewayIdStr), "GW-%02X", config_.gatewayId);
    doc["gateway_id"] = gatewayIdStr;
    doc["name"] = gatewayIdStr;
    doc["lora_status"] = "ACTIVE";
    doc["wifi_status"] = WiFi.status() == WL_CONNECTED ? "CONNECTED" : "DISCONNECTED";
    // Reaching this line means the MQTT link to the broker is up.
    doc["backend_status"] = "REACHABLE";
    doc["firmware_version"] = "0.1.0";
    char payload[384];
    const size_t len = serializeJson(doc, payload, sizeof(payload));
    const bool ok = mqttClient_.publish(kTopicGatewayStatus, reinterpret_cast<const uint8_t*>(payload), len, false);
    Serial.printf("[GATEWAY STATUS] MQTT %s\n", ok ? "published" : "FAILED");
}

void BackendIngestionClient::tickWifi(std::uint32_t currentMs) {
    const bool up = WiFi.status() == WL_CONNECTED;
    if (up && wifiState_ != LinkState::Connected) {
        wifiState_ = LinkState::Connected;
        Serial.printf("[WIFI] CONNECTED | SSID=%s IP=%s GW=%s DNS=%s RSSI=%d dBm MAC=%s\n",
                      WiFi.SSID().c_str(), WiFi.localIP().toString().c_str(),
                      WiFi.gatewayIP().toString().c_str(),
                      WiFi.dnsIP().toString().c_str(),
                      WiFi.RSSI(),
                      WiFi.macAddress().c_str());
        Serial.flush();
    } else if (!up && wifiState_ == LinkState::Connected) {
        wifiState_ = LinkState::Disconnected;
        Serial.printf("[WIFI] DISCONNECTED | status=%s(%d)\n",
                      wifiStatusName(WiFi.status()), static_cast<int>(WiFi.status()));
        Serial.flush();
    }
    if (!up && (currentMs - lastWifiAttemptMs_) >= kReconnectIntervalMs) {
        lastWifiAttemptMs_ = currentMs;
        Serial.printf("[WIFI] DISCONNECTED | status=%s(%d)\n",
                      wifiStatusName(WiFi.status()), static_cast<int>(WiFi.status()));
        wifiState_ = LinkState::Connecting;
        WiFi.disconnect();
        WiFi.begin(config_.wifiSsid, config_.wifiPassword);
        Serial.printf("[WIFI] RECONNECTING | SSID=%s\n", config_.wifiSsid != nullptr ? config_.wifiSsid : "<unset>");
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
    if ((currentMs - lastMqttAttemptMs_) >= mqttBackoffMs_) {
        lastMqttAttemptMs_ = currentMs;
        mqttState_ = LinkState::Connecting;
        char clientId[24];
        snprintf(clientId, sizeof(clientId), "gw-%02X", config_.gatewayId);
        const bool connected = (config_.mqttUsername != nullptr && config_.mqttUsername[0] != '\0')
            ? mqttClient_.connect(clientId, config_.mqttUsername, config_.mqttPassword)
            : mqttClient_.connect(clientId);
        if (connected) {
            mqttState_ = LinkState::Connected;
            mqttBackoffMs_ = kReconnectIntervalMs;
            logLine("[MQTT] CONNECTED");
        } else {
            mqttState_ = LinkState::Disconnected;
            // Back off (5 s -> 30 s) while the broker/DNS is unreachable.
            mqttBackoffMs_ = (mqttBackoffMs_ * 2U > kMaxMqttBackoffMs) ? kMaxMqttBackoffMs : mqttBackoffMs_ * 2U;
        }
    }
}

void BackendIngestionClient::enqueue(const ForestEventEnvelope& envelope) {
    if (xSemaphoreTake(outboxMutex_, pdMS_TO_TICKS(200)) != pdTRUE) {
        logLine("[MQTT] OUTBOX BUSY, EVENT DROPPED");
        return;
    }
    if (outboxCount_ >= kOutboxCapacity) {
        // Outbox full: drop the oldest queued event rather than the new
        // one, so the freshest field data always has a chance to publish.
        outboxHead_ = (outboxHead_ + 1) % kOutboxCapacity;
        outboxCount_--;
        outboxHeadSerial_++;
        logLine("[MQTT] OUTBOX FULL, DROPPED OLDEST");
    }
    const std::size_t tail = (outboxHead_ + outboxCount_) % kOutboxCapacity;
    outbox_[tail] = envelope;
    outboxCount_++;
    xSemaphoreGive(outboxMutex_);
}

void BackendIngestionClient::drainOutbox() {
    for (;;) {
        // Copy the head out and release the lock before publishing, so a slow
        // publish can never make the main loop's enqueue() time out and drop scans.
        ForestEventEnvelope envelope;
        std::uint32_t serial = 0;
        if (xSemaphoreTake(outboxMutex_, pdMS_TO_TICKS(50)) != pdTRUE) return;
        if (outboxCount_ == 0) {
            xSemaphoreGive(outboxMutex_);
            return;
        }
        envelope = outbox_[outboxHead_];
        serial = outboxHeadSerial_;
        xSemaphoreGive(outboxMutex_);

        if (!publishEnvelope(envelope)) return;  // leave it queued, retry next tick

        if (xSemaphoreTake(outboxMutex_, pdMS_TO_TICKS(50)) != pdTRUE) return;
        // If enqueue() dropped this event as "oldest" meanwhile, it is already gone.
        if (serial == outboxHeadSerial_ && outboxCount_ > 0) {
            outboxHead_ = (outboxHead_ + 1) % kOutboxCapacity;
            outboxCount_--;
            outboxHeadSerial_++;
        }
        xSemaphoreGive(outboxMutex_);
    }
}

bool BackendIngestionClient::publishEnvelope(const ForestEventEnvelope& envelope) {
    // Everything stays in the outbox until the broker connection is up.
    if (mqttState_ != LinkState::Connected) return false;
    if (envelope.hasRfid) {
        return publishRfid(envelope);
    }

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

bool BackendIngestionClient::publishRfid(const ForestEventEnvelope& envelope) {
    JsonDocument doc;
    doc["type"] = "RFID_SCAN";
    char nodeIdStr[16];
    snprintf(nodeIdStr, sizeof(nodeIdStr), "NODE_%02X", envelope.sourceId);
    doc["node_id"] = nodeIdStr;

    char uid[32]{};
    for (std::size_t index = 0U; index < envelope.rfidUidLength; ++index) {
        snprintf(uid + (index * 3U), sizeof(uid) - (index * 3U), "%02X%s", envelope.rfidUid[index],
                 (index == envelope.rfidUidLength - 1) ? "" : ":");
    }
    doc["uid"] = uid;
    doc["seq"] = envelope.sequenceNumber;
    doc["rssi"] = envelope.rssiDbm;
    doc["snr"] = envelope.snrDb;

    char payload[256];
    const size_t len = serializeJson(doc, payload, sizeof(payload));
    const bool ok = mqttClient_.publish(kTopicRfid, reinterpret_cast<const uint8_t*>(payload), len, false);
    Serial.printf("[MQTT PUBLISH] topic=%s node=%s uid=%s seq=%u -> %s\n", kTopicRfid, nodeIdStr, uid,
                  static_cast<unsigned>(envelope.sequenceNumber), ok ? "PUBLISHED" : "FAILED");
    return ok;
}

}  // namespace forest::backend
