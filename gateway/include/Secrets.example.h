#pragma once

// Copy this file to Secrets.h and replace the values locally.
// Secrets.h is ignored and must never be committed.
#define JALRI_GATEWAY_INGESTION_KEY "replace-with-the-same-key-configured-on-render"
#define JALRI_WIFI_SSID "replace-with-the-gateway-wifi-ssid"
#define JALRI_WIFI_PASSWORD "replace-with-the-gateway-wifi-password"
// Only needed for the [env:production] build (JALRI_MQTT_TLS=1) -- create
// these in the HiveMQ Cloud console under Access Management.
#define JALRI_MQTT_USERNAME "replace-with-the-hivemq-cloud-username"
#define JALRI_MQTT_PASSWORD "replace-with-the-hivemq-cloud-password"
