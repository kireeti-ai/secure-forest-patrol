#include "BackendIngestionClient.h"

#include <ArduinoJson.h>
#include <cstring>

namespace forest::backend {

namespace {
constexpr const char* kTopicNodeStatus = "forest/events/node-status";
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
}

void BackendIngestionClient::logLine(const char* line) {
    if (logger_ != nullptr) {
        logger_->log(logging::LogLevel::info, line);
    }
}

void BackendIngestionClient::tick(std::uint32_t currentMs) {
    tickWifi(currentMs);
    tickMqtt(currentMs);
    if (wifiState_ == LinkState::Connected) {
        if (mqttState_ == LinkState::Connected) {
            mqttClient_.loop();
        }
        // RFID scans have a dedicated HTTP ingestion contract.  Do not make
        // attendance delivery depend on an unrelated MQTT broker connection.
        drainOutbox();
    }
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
    if (envelope.hasRfid) {
        return publishRfidHttp(envelope);
    }
    // Non-RFID telemetry follows the existing MQTT transport and remains in
    // the outbox until the broker reconnects.
    if (mqttState_ != LinkState::Connected) return false;

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

bool BackendIngestionClient::publishRfidHttp(const ForestEventEnvelope& envelope) {
    if (wifiState_ != LinkState::Connected) return false;

    HTTPClient http;
    char url[256];
    snprintf(url, sizeof(url), "%s/api/ingest/gateway/rfid-scan", config_.baseUrl);
    const bool useTls = std::strncmp(config_.baseUrl, "https://", 8U) == 0;
    if (useTls) {
        secureClient_.setInsecure();
        http.begin(secureClient_, url);
    } else {
        http.begin(url);
    }
    http.addHeader("Content-Type", "application/json");

    JsonDocument doc;
    doc["type"] = "RFID_SCAN";
    char nodeIdStr[16];
    snprintf(nodeIdStr, sizeof(nodeIdStr), "NODE_%02X", envelope.sourceId);
    doc["node_id"] = nodeIdStr;

    char uid[32]{};
    for (std::size_t index = 0U; index < envelope.rfidUidLength; ++index) {
        snprintf(uid + (index * 3U), sizeof(uid) - (index * 3U), "%02X%s", envelope.rfidUid[index], (index == envelope.rfidUidLength - 1) ? "" : ":");
    }
    doc["uid"] = uid;
    doc["seq"] = envelope.sequenceNumber;
    doc["rssi"] = envelope.rssiDbm;
    doc["snr"] = envelope.snrDb;

    char payload[512];
    serializeJson(doc, payload, sizeof(payload));

    int httpCode = http.POST(reinterpret_cast<uint8_t*>(payload), strlen(payload));
    if (httpCode > 0) {
        Serial.println("Backend upload: SUCCESS");
        Serial.printf("HTTP %d\n", httpCode);
    } else {
        Serial.println("[ERROR] Backend upload failed");
        Serial.printf("HTTP Error: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
    return httpCode >= 200 && httpCode < 300;
}

}  // namespace forest::backend
