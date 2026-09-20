# Secure Offline Patrol Verification

Forest patrol attendance and acoustic threat detection: an ESP32-S3 checkpoint node reads RFID cards and listens for gunshots and chainsaws with an on-device TinyML model. Events travel over LoRa to a gateway, then MQTT to a FastAPI backend and a Next.js dashboard.

![ESP32-S3](https://img.shields.io/badge/ESP32--S3-E7352C?style=for-the-badge&logo=espressif&logoColor=white)
![C++](https://img.shields.io/badge/C%2B%2B-00599C?style=for-the-badge&logo=cplusplus&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![TensorFlow Lite](https://img.shields.io/badge/TensorFlow%20Lite%20Micro-FF6F00?style=for-the-badge&logo=tensorflow&logoColor=white)
![LoRa](https://img.shields.io/badge/LoRa-00AEEF?style=for-the-badge&logo=lora&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![MQTT](https://img.shields.io/badge/MQTT-660066?style=for-the-badge&logo=mqtt&logoColor=white)

## What is built

```
Node (ESP32-S3)                         Gateway (ESP32-S3)            Cloud
 RC522 RFID  ─┐                                                       
 MAX4466 ─ trigger ─ INMP441 ─ TinyML ─┤ LoRa 433 MHz ─▶ SX1278 ─ Wi-Fi ─ MQTT (EMQX) ─▶ FastAPI ─▶ PostgreSQL ─▶ Dashboard
 LittleFS event store  ◀── gateway ACK ┘   (SF7, 125 kHz)            webhook rules          (Vercel)    (Neon)
```

| Part | Folder | What it does |
|---|---|---|
| Node firmware | `node-firmware/` | RFID scans, acoustic detection, local event store, LoRa transmit with gateway-ACK sync |
| Sensor drivers | `node-firmware/lib/ForestSensors/` | Our own drivers: RC522 (SPI), DS3231 (I2C), MAX4466 (ADC/DMA), INMP441 (I2S). No third-party sensor libraries |
| Local event store | `node-firmware/lib/ForestStorage/` | Append-only, CRC-protected log on internal flash (LittleFS); events survive reset and power loss |
| Acoustic pipeline | `node-firmware/lib/Acoustic/` | MAX4466 relative-dB trigger, INMP441 capture, mel features, INT8 TFLite Micro classifier |
| Gateway | `gateway/` | LoRa receiver (continuous RX + watchdog), ACKs nodes, publishes to MQTT |
| Backend | `backend/` | FastAPI + PostgreSQL: RFID attendance, acoustic events, checkpoints, nodes |
| Dashboard | `dashboard/` | Overview, RFID scans, officers, acoustic events with analytics and review, gateway and node status |
| Model | `ml/` | Training data, features and the INT8 model (`Background / Chainsaw / Gunshot`) |

### How events flow
1. **RFID scan:** the card UID is read, written to the local store as `PENDING_SYNC`, sent over LoRa, and marked `SYNCED` only when the gateway's acknowledgement for that packet arrives. Unacknowledged events are retried.
2. **Acoustic event:** the MAX4466 wakes the pipeline, one second of INMP441 audio is classified on the chip, and only a 6-byte event (class, confidence, trigger level) is sent. No audio is transmitted.
3. **Backend:** the gateway publishes to MQTT; EMQX rules call the backend. RFID scans become attendance (check-in, check-out) and are validated against the officer's assigned checkpoint. Acoustic events are stored as `PENDING_REVIEW`.
4. **Dashboard:** operators see scans, attendance states (Present, Checked out, Yet to arrive, Absent) and acoustic detections, and review each detection as a real threat or a false alarm.

## Hardware and interfaces

| Component | Interface | Pins |
|---|---|---|
| RC522 RFID | SPI | SCK 35, MISO 37, MOSI 36, SS 4, RST 5 |
| SX1278 LoRa (node and gateway) | SPI | SCK 12, MISO 13, MOSI 11, CS 10, RST 9, DIO0 14 |
| MAX4466 microphone amplifier | ADC | OUT to GPIO 1 |
| INMP441 microphone | I2S | BCLK 6, WS 7, SD 8 |
| DS3231 RTC | I2C | SDA 21, SCL 20 (driver written, no RTC fitted) |
| RGB status LED | GPIO | 48 |

## Status

| Area | Status |
|---|---|
| RFID to dashboard, attendance, wrong-checkpoint detection | End-to-end verified |
| Local event store: write, reboot, re-flash, power cycle | Physically verified |
| Gateway ACK sync and retry | Physically verified |
| Custom RC522 driver | Physically verified |
| TinyML on the ESP32 (custom per-channel kernel, features) | Physically verified against the Python reference |
| Acoustic event over LoRa, MQTT and backend to the dashboard | Verified with live events |
| MAX4466 trigger and thresholds | Under validation: the sensor signal is unstable and thresholds are experimental |
| Real-audio classification accuracy | Not verified. The model has not been tested on this microphone; expect false alarms |
| DS3231 RTC driver | Implemented, no hardware |
| Fingerprint (R307), node-side signing, hash-chain ledger | Not implemented |
| Acoustic events | Unsigned; the backend stamps the time |

## Getting started

```bash
# Node firmware (RFID + acoustic + store), then watch the serial monitor
cd node-firmware && pio run -t upload && pio device monitor

# Gateway
cd gateway && pio run -t upload

# Backend tests
cd backend && python -m pytest -q tests

# Dashboard
cd dashboard && npm install && npm run dev
```

Serial commands on the node: `w` write a test event, `l` list stored events, `m` mark synced, `r` reboot, `x` erase, `t` driver check.

Set `NEXT_PUBLIC_API_BASE_URL` for the dashboard and `DATABASE_URL` for the backend. Attendance uses `FOREST_TIMEZONE` (default Asia/Kolkata) and `ATTENDANCE_ABSENT_AFTER` (default 10:00).

## Documentation

- [Custom sensor libraries](docs/CUSTOM_SENSOR_LIBRARIES.md)
- [Local event store](docs/LOCAL_DATABASE.md)
- [Acoustic node](docs/ACOUSTIC_NODE.md)
- [Gateway and backend contract](docs/GATEWAY_BACKEND_CONTRACT.md), [MQTT](docs/MQTT.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md), [docs index](docs/README.md)

## Known limits

- The backend has no authentication; it is intended for a closed operations network.
- The LoRa link has no encryption, and a node event is stamped with its arrival time because the node has no RTC.
- Audio cannot be reviewed on the dashboard: one second of audio is about 32 KB and a LoRa packet here carries at most 48 bytes.
