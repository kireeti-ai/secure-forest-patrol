#pragma once

// Copy this file to Secrets.h (gitignored) and fill in real values. Never commit Secrets.h.

#define FOREST_GATEWAY_INGESTION_KEY "replace-with-a-real-ingestion-key"
#define FOREST_WIFI_SSID "your-wifi-ssid"
#define FOREST_WIFI_PASSWORD "your-wifi-password"
#define FOREST_MQTT_USERNAME "your-mqtt-username"
#define FOREST_MQTT_PASSWORD "your-mqtt-password"
// AES-128-GCM pre-shared key for the LoRa uplink (Phase 4, docs/TAMPER_EVIDENCE_SECURITY_PLAN.md).
// Generate 16 random bytes (e.g. `python3 -c "import os; print(','.join(f'0x{b:02X}U' for b in os.urandom(16)))"`)
// and use the SAME 16 bytes here and in node-firmware/include/Config.h's FOREST_LORA_AES_KEY.
#define FOREST_LORA_AES_KEY {0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U,0x00U}
