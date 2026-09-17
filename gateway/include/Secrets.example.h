#pragma once

// Copy this file to Secrets.h and replace the values locally.
// Secrets.h is ignored and must never be committed.
#define FOREST_GATEWAY_INGESTION_KEY "replace-with-the-same-key-configured-on-render"
#define FOREST_WIFI_SSID "replace-with-the-gateway-wifi-ssid"
#define FOREST_WIFI_PASSWORD "replace-with-the-gateway-wifi-password"
// Only needed for the [env:production] build (FOREST_MQTT_TLS=1) -- create
// these in the HiveMQ Cloud console under Access Management.
#define FOREST_MQTT_USERNAME "replace-with-the-hivemq-cloud-username"
#define FOREST_MQTT_PASSWORD "replace-with-the-hivemq-cloud-password"
