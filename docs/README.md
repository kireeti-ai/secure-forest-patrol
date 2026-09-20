# SECURE OFFLINE PATROL VERIFICATION — Project README

> **Secure Offline Patrol Verification** — A tamper-evident, offline-first forest patrol verification system using LoRa mesh, biometric identity verification, TinyML acoustic threat detection, and a cryptographic hash chain ledger.

---

## Overview

This project, Secure Offline Patrol Verification, implements a complete forest patrol system for deployment in remote, connectivity-limited environments. It consists of:

1. **Field Nodes** (ESP32 + SX1278 LoRa) — Checkpoint and acoustic patrol nodes deployed in the forest.
2. **LoRa Gateway** (ESP32-S3) — Receives field events over 433 MHz LoRa, verifies integrity, and forwards to backend over Wi-Fi.
3. **Forest Backend** (FastAPI + PostgreSQL) — Validates records, stores hash chain, verifies RSA signatures.
4. **Forest Dashboard** (Next.js) — Operations dashboard for patrol monitoring, acoustic event review, ledger inspection, and gateway health.

---

## Architecture Summary

```
Field Nodes
    │   (RFID scan + fingerprint verification + RTC timestamp + acoustic event)
    │   RSA-sign + SHA-256 hash + local queue
    ▼
LoRa Link (433 MHz SX1278) ─── offline-first DTN store-and-forward
    ▼
ESP32-S3 Gateway
    │   (receive, decode, verify RSA signature, check hash chain, deduplicate)
    ▼
Wi-Fi/GSM Backhaul IP Link ─── separated from LoRa field link
    ▼
FastAPI Forest Backend
    │   (PostgreSQL persistence, hash chain verification, audit trail)
    ▼
Forest Dashboard (Next.js)
    │   (patrol verification queue, acoustic review, ledger inspector, node health)
```

### Key Network Separation

| Link | Protocol | Description |
|:-----|:---------|:------------|
| Node → Gateway | LoRa 433 MHz | Field events over SX1278 — works offline |
| Gateway → Backend | Wi-Fi (IP) / GSM | IP backhaul — queued if offline |

These two links are **completely independent**. The LoRa field link works without Wi-Fi.

---

## Project Structure

```
SECURE-FOREST-PATROL/
├── node-firmware/          # PlatformIO — Field Node (ESP32 + SX1278 + RFID + Fingerprint)
├── gateway/                # PlatformIO — LoRa Gateway (ESP32-S3)
├── dashboard/              # Next.js — Operations Dashboard
└── docs/                   # Project documentation (this directory)
```

---

## Quick Start

### Node Firmware
```bash
cd node-firmware
pio run --target upload
```

### Gateway
```bash
cd gateway
pio run --target upload
```

### Dashboard (Development)
```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

---

## Documentation Index

| Document | Description |
|:---------|:------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Full system architecture, data flow, and component design |
| [DATA_MODEL.md](./DATA_MODEL.md) | Forest patrol data types and API schemas |
| [EVENT_MODEL.md](./EVENT_MODEL.md) | Field event packet format and encoding |
| [LEDGER.md](./LEDGER.md) | Tamper-evident hash chain and RSA signature design |
| [GATEWAY_INTEGRATION.md](./GATEWAY_INTEGRATION.md) | Gateway dual-link architecture and integration guide |
| [SYNC_PROTOCOL.md](./SYNC_PROTOCOL.md) | Offline-first DTN synchronization protocol |
| [DASHBOARD.md](./DASHBOARD.md) | Dashboard routes, components, and usage guide |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | Current implementation status and next steps |

---

## Implementation Status

See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for current status.

**Phase 9 — Dashboard Migration** is complete. The dashboard displays demo/mock data labeled `DEMO / MOCK / NOT CONNECTED` until the backend API is connected.

---

## Node firmware documents

- [`docs/CUSTOM_SENSOR_LIBRARIES.md`](CUSTOM_SENSOR_LIBRARIES.md): the `ForestSensors` driver library (RC522 SPI, DS3231 I2C, MAX4466 ADC, INMP441 I2S), written without third-party sensor libraries.
- [`docs/LOCAL_DATABASE.md`](LOCAL_DATABASE.md): the on-node persistent event store (LittleFS on internal flash), persistence demo and test evidence.
- [`docs/ACOUSTIC_NODE.md`](ACOUSTIC_NODE.md): the MAX4466 + INMP441 + TinyML acoustic pipeline.
