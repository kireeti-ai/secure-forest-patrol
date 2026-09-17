# Gateway → Backend Contract

**Status:** MQTT transport IMPLEMENTED (backend + firmware), TESTED LOCALLY /
SIMULATED for the full signed-event path, NOT physically verified end-to-end.
HTTP ingestion routes remain a working fallback/management path.

## Architecture

```text
Field Node → LoRa → Gateway (parse/CRC/dedup) → local outbox
    → Wi-Fi → MQTT publish → Broker → Backend MQTT consumer
    → verification/persistence services (shared with the HTTP routes)
    → PostgreSQL → WebSocket → Dashboard
```

MQTT and HTTP both terminate in the *same* backend services
(`app/services/forest_patrol.py`, `forest_acoustic.py`, `forest_gateway_svc.py`)
— there is no duplicated verification/persistence logic between the two
transports. See `docs/MQTT.md` for topics, payload schemas, QoS, and
security requirements.

## Known gap: the physical Gateway cannot yet publish a full signed event

The node-firmware (field checkpoint nodes) does not yet implement
RFID/fingerprint sensing or on-device signing/hashing — the only real LoRa
payload the Gateway receives today is a 9-byte RTC+temperature diagnostic
packet (`GatewayService::handleReceivedPacket`, `gateway/src/Gateway/
GatewayService.cpp`). So:

- The **physical Gateway** publishes that diagnostic data to
  `forest/events/node-status` (see `docs/MQTT.md`). It does not carry
  `rfid_result`, `fingerprint_result`, `signature`, or hash-chain fields,
  because the firmware has none of that data to send. This diagnostic
  envelope actually *passes* `GatewayStatusReport` validation (every field
  but `gateway_id` is optional, extras are ignored) — it is not rejected.
  Only `gateway_id`/`last_seen_at` get persisted; the per-node/RSSI/
  temperature fields have no column to land in and are discarded (logged
  explicitly so this isn't silent — see `docs/MQTT.md`).
- The **full signed `PatrolEvent`/`AcousticEvent` MQTT path**
  (`forest/events/patrol`, `forest/events/acoustic`) is fully implemented
  and tested on the backend side, and exercised end-to-end with
  `backend/scripts/simulate_mqtt_gateway.py`, which publishes the same
  envelope shape a real signed Gateway event would use (see
  `backend/tests/forest_vectors.py` for the deterministic ECC vectors).
  This satisfies the "simulated gateway before physical integration"
  requirement, but is explicitly **SIMULATED**, not physically verified.
- Closing this gap requires node-firmware work (RFID reader, fingerprint
  sensor, on-device ECC signing, hash-chain state) that is out of scope for
  this transport phase.

## Gateway transport behavior (firmware)

`gateway/lib/Backend/BackendIngestionClient.{h,cpp}`:

- Wi-Fi and MQTT connection state are tracked **separately**
  (`LinkState wifiState()` / `mqttState()`) — never collapsed into one
  "ONLINE" flag.
- A fixed-size local outbox (`kOutboxCapacity = 32`) buffers events while
  either link is down; `tick()` drains it once both are connected.
- Reconnect attempts (Wi-Fi and MQTT) are retried on a 5 s interval
  (`kReconnectIntervalMs`). All failures here are treated as transient —
  the Gateway does not verify signatures itself, so there is no
  "permanent failure" case to distinguish at this layer.
- Outbox overflow drops the oldest queued event and logs it, rather than
  rejecting the newest one.

## Envelope published today (`forest/events/node-status`)

| Field | Type | Source |
|---|---|---|
| `gateway_id` | string | `BackendConfig::gatewayId`, formatted `GW-XX` |
| `node_id` | string | LoRa `sourceId`, formatted `0xXX` |
| `sequence` | integer | LoRa packet sequence number |
| `protocol_version` | integer | Wire protocol version (currently 4) |
| `rssi` / `snr` | number | From the LoRa receive |
| `gateway_received_at_ms` | integer | Gateway uptime (`millis()`), not wall-clock — the Gateway has no networked time source |
| `event_created_at` / `temperature_c` | string / number | Only present when the 9-byte RTC diagnostic payload was decoded |

## Canonical signed-event envelope (target, used by the simulator today)

See `ForestPatrolIngest` / `ForestAcousticIngest` in
`backend/app/schemas/forest_ingest.py` — `node_id`, `sequence`,
`event_created_at`, `rfid_result`/`fingerprint_result` or
`classification`/`confidence`, `previous_hash`, `record_hash`,
`signature`, optional `gateway` metadata block. This is the schema the
physical Gateway will publish to once node-firmware signing exists.

## Idempotency and verification

Unchanged from the HTTP path: duplicate detection on `(node_id, sequence)`,
ECC secp256r1 signature verification, and hash-chain linkage checks all
happen in the shared backend services — see `docs/MQTT.md` §"Reliability".
