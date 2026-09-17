#pragma once

#include <cstdint>

#if __has_include("Secrets.h")
#include "Secrets.h"
#endif

#ifndef FOREST_GATEWAY_INGESTION_KEY
#define FOREST_GATEWAY_INGESTION_KEY ""
#endif

// Wi-Fi credentials are a real secret and must come from Secrets.h
// (gitignored), never a committed default -- see Secrets.example.h.
#ifndef FOREST_WIFI_SSID
#define FOREST_WIFI_SSID ""
#endif

#ifndef FOREST_WIFI_PASSWORD
#define FOREST_WIFI_PASSWORD ""
#endif

#ifndef FOREST_PRODUCTION_BACKEND
#define FOREST_PRODUCTION_BACKEND 1
#endif

#ifndef FOREST_MQTT_BROKER_HOST
#define FOREST_MQTT_BROKER_HOST "10.38.112.147"
#endif

#ifndef FOREST_MQTT_BROKER_PORT
#define FOREST_MQTT_BROKER_PORT 1883
#endif

#ifndef FOREST_MQTT_TLS
#define FOREST_MQTT_TLS 0
#endif

// MQTT broker credentials are a real secret and must come from Secrets.h
// (gitignored) in any build that sets FOREST_MQTT_TLS=1 -- never committed.
#ifndef FOREST_MQTT_USERNAME
#define FOREST_MQTT_USERNAME ""
#endif

#ifndef FOREST_MQTT_PASSWORD
#define FOREST_MQTT_PASSWORD ""
#endif

namespace forest {

struct BackendBuildConfig {
    // Development remains the default; production is selected explicitly at build time.
    static constexpr const char* wifiSsid = FOREST_WIFI_SSID;
    static constexpr const char* wifiPassword = FOREST_WIFI_PASSWORD;
    static constexpr const char* developmentBaseUrl = "http://10.38.112.147:8000";
    static constexpr const char* productionBaseUrl = "https://forest-frontend-dashboard.onrender.com";
    static constexpr const char* baseUrl =
        FOREST_PRODUCTION_BACKEND ? productionBaseUrl : developmentBaseUrl;
    static constexpr const char* ingestionKey = FOREST_GATEWAY_INGESTION_KEY;
    static constexpr std::uint8_t gatewayId = 0xFE;
    // MQTT is the primary Gateway -> Backend event transport (see
    // docs/MQTT.md); the HTTP baseUrl above remains a fallback/management
    // path. Local dev points at the docker-compose Mosquitto broker;
    // production MUST configure TLS + auth (FOREST_MQTT_BROKER_HOST is a
    // build flag, not a committed production secret).
    static constexpr const char* mqttBrokerHost = FOREST_MQTT_BROKER_HOST;
    static constexpr std::uint16_t mqttBrokerPort = FOREST_MQTT_BROKER_PORT;
    static constexpr bool mqttTls = static_cast<bool>(FOREST_MQTT_TLS);
    static constexpr const char* mqttUsername = FOREST_MQTT_USERNAME;
    static constexpr const char* mqttPassword = FOREST_MQTT_PASSWORD;
};

struct BuildConfig {
    static constexpr const char* firmwareName = "forest-gateway-firmware";
    static constexpr const char* firmwareVersion = "0.1.0";
    static constexpr const char* targetBoard = "esp32-s3-devkitc-1-n16r8";
    static constexpr bool simulationMode = false;
};

}  // namespace forest
