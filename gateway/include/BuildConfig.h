#pragma once

#include <cstdint>

#if __has_include("Secrets.h")
#include "Secrets.h"
#endif

#ifndef JALRI_GATEWAY_INGESTION_KEY
#define JALRI_GATEWAY_INGESTION_KEY ""
#endif

// Wi-Fi credentials are a real secret and must come from Secrets.h
// (gitignored), never a committed default -- see Secrets.example.h.
#ifndef JALRI_WIFI_SSID
#define JALRI_WIFI_SSID ""
#endif

#ifndef JALRI_WIFI_PASSWORD
#define JALRI_WIFI_PASSWORD ""
#endif

#ifndef JALRI_PRODUCTION_BACKEND
#define JALRI_PRODUCTION_BACKEND 1
#endif

#ifndef JALRI_MQTT_BROKER_HOST
#define JALRI_MQTT_BROKER_HOST "10.38.112.147"
#endif

#ifndef JALRI_MQTT_BROKER_PORT
#define JALRI_MQTT_BROKER_PORT 1883
#endif

namespace jalri {

struct BackendBuildConfig {
    // Development remains the default; production is selected explicitly at build time.
    static constexpr const char* wifiSsid = JALRI_WIFI_SSID;
    static constexpr const char* wifiPassword = JALRI_WIFI_PASSWORD;
    static constexpr const char* developmentBaseUrl = "http://10.38.112.147:8000";
    static constexpr const char* productionBaseUrl = "https://jalari-frontend-dashboard.onrender.com";
    static constexpr const char* baseUrl =
        JALRI_PRODUCTION_BACKEND ? productionBaseUrl : developmentBaseUrl;
    static constexpr const char* ingestionKey = JALRI_GATEWAY_INGESTION_KEY;
    static constexpr std::uint8_t gatewayId = 0xFE;
    // MQTT is the primary Gateway -> Backend event transport (see
    // docs/MQTT.md); the HTTP baseUrl above remains a fallback/management
    // path. Local dev points at the docker-compose Mosquitto broker;
    // production MUST configure TLS + auth (JALRI_MQTT_BROKER_HOST is a
    // build flag, not a committed production secret).
    static constexpr const char* mqttBrokerHost = JALRI_MQTT_BROKER_HOST;
    static constexpr std::uint16_t mqttBrokerPort = JALRI_MQTT_BROKER_PORT;
};

struct BuildConfig {
    static constexpr const char* firmwareName = "jalri-gateway-firmware";
    static constexpr const char* firmwareVersion = "0.1.0";
    static constexpr const char* targetBoard = "esp32-s3-devkitc-1-n16r8";
    static constexpr bool simulationMode = false;
};

}  // namespace jalri
