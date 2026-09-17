# MQTT: Gateway → Backend Transport

**Status:** IMPLEMENTED (backend consumer + firmware publisher). TESTED
LOCALLY (backend unit tests, in-process) and PHYSICALLY VERIFIED for the
Wi-Fi + MQTT transport link itself (a real Gateway connected to a local
broker over its own Wi-Fi and published; confirmed via serial logs and
broker logs). SIMULATED end-to-end for the full signed-event path (via
`backend/scripts/simulate_mqtt_gateway.py`) — a physical Gateway → broker →
backend run with a *real signed* event is still NOT IMPLEMENTED, because
node-firmware doesn't produce signed events yet. See
`docs/GATEWAY_BACKEND_CONTRACT.md`.

MQTT is the primary Gateway → Backend event transport. The HTTP routes
under `/api/ingest/gateway/*` remain a working fallback/management path —
both call the exact same verification/persistence services
(`app/services/forest_patrol.py`, `forest_acoustic.py`,
`forest_gateway_svc.py`), so there is no divergence in what gets accepted,
rejected, or persisted between the two transports.

## Broker

**Local development**: a self-hosted Mosquitto broker via the repo-root
`docker-compose.yml` (`docker compose up mosquitto`), configured by
`mosquitto/mosquitto.conf`. No TLS, no authentication — this is fine for a
broker bound to `localhost` during development, but **must not** be used
as-is in production.

**Production**: a managed cloud broker (HiveMQ Cloud, serverless tier) —
TLS on port 8883, authenticated. Both sides are already wired for this:

- **Backend**: set `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT=8883`,
  `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_TLS=true` as environment
  variables on the deployment host (see the production env var list in the
  repo root README / deployment notes). `app/services/mqtt_consumer.py`
  calls `tls_set()` and `username_pw_set()` when these are set.
- **Gateway**: build with `pio run -e production` (`gateway/platformio.ini`)
  — this sets `FOREST_MQTT_BROKER_HOST`/`PORT`/`FOREST_MQTT_TLS=1` as build
  flags. `FOREST_MQTT_USERNAME`/`FOREST_MQTT_PASSWORD` (the credentials
  created in the HiveMQ Cloud console) must be added to `Secrets.h`
  (gitignored, never a build flag) — see `Secrets.example.h`.
  `BackendIngestionClient` uses `WiFiClientSecure` with `setInsecure()`
  (encrypts the link but does not pin/validate the broker's certificate —
  a deliberate tradeoff to avoid a CA bundle that would eventually expire
  and brick the device; event authenticity is still guaranteed at the
  application layer by the ECC signature + hash chain regardless of
  transport, so this does not weaken the system's core tamper-evidence
  guarantee — it only means an active MITM impersonating the broker isn't
  detected at the TLS layer).

Never commit broker credentials, tokens, or TLS private keys to the repo.

## Topics

| Topic | Publisher | Payload schema | Backend handler |
|---|---|---|---|
| `forest/events/patrol` | Gateway (once node-firmware signs events) / simulator | `ForestPatrolIngest` | `ingest_patrol_event` |
| `forest/events/acoustic` | Gateway (once node-firmware signs events) / simulator | `ForestAcousticIngest` | `ingest_acoustic_event` |
| `forest/events/node-status` | Gateway (today: diagnostic RTC/temp data) | `GatewayStatusReport` (loosely -- see note below) | `report_gateway_status` |
| `forest/events/sync` | Gateway (future) | free-form | relayed live as `SYNC_UPDATED`; **not persisted** — sync records are written today as a side effect of patrol/acoustic ingestion, not from this topic |

**Note on `forest/events/node-status` today:** the physical Gateway
publishes a diagnostic envelope (`gateway_id`, `node_id`, `sequence`,
`rssi`, `snr`, `event_created_at`, `temperature_c`) that is *not* really a
`GatewayStatusReport`. It still validates, because every field on that
schema except `gateway_id` is optional and Pydantic ignores unknown fields
by default — it is not rejected. The practical effect: `report_gateway_status`
updates `gateway_id`/`last_seen_at` and silently discards the rest, since
the `Gateway` table has no columns for per-node diagnostic data. The
backend logs this explicitly (`app/services/mqtt_consumer.py`) so the data
loss is visible rather than silent. This is a known placeholder, not a bug
to "fix" by rejecting the payload — see `docs/GATEWAY_BACKEND_CONTRACT.md`.

Payload schemas are the same Pydantic models the HTTP ingestion routes use
— see `backend/app/schemas/forest_ingest.py`. There is no separate MQTT
schema to keep in sync.

## QoS

QoS 1 (at-least-once) on both subscribe and publish. Application-level
idempotency (below) makes at-least-once safe — QoS does not have to
guarantee exactly-once.

## Reliability / idempotency

MQTT QoS does not replace application-level deduplication. Every event is
deduplicated in the backend on `(node_id, sequence)`:

- First delivery → `ACCEPTED` (schema valid, signature valid, chain valid)
  → one row in `patrol_events`/`acoustic_events`.
- Repeated delivery of the same event → `DUPLICATE`/`ALREADY_PROCESSED`,
  no second row.
- Invalid signature → `INVALID_SIGNATURE`, row persisted with that status
  for audit (not silently dropped).
- Broken hash-chain linkage → `BROKEN_CHAIN`, same treatment.
- Unknown node → rejected, nothing persisted.
- Malformed JSON / schema mismatch → logged and dropped.

This is exactly the same outcome vocabulary the HTTP routes return in
`IngestResult` (`app/schemas/forest_ingest.py`).

## Offline behavior

If Wi-Fi or the broker is unreachable, the Gateway's local outbox
(`gateway/lib/Backend/BackendIngestionClient.h`, `kOutboxCapacity = 32`)
holds events and retries on a 5-second interval — see
`docs/GATEWAY_BACKEND_CONTRACT.md`. This is separate from, and does not
replace, the field-node DTN store-and-forward service
(`node-firmware/lib/Services/src/DtnStoreForwardService`), which protects
events for the LoRa hop before they ever reach the Gateway.

## Backend consumer implementation

`backend/app/services/mqtt_consumer.py` — connects and subscribes on
FastAPI startup (`app/main.py` lifespan), routes each topic to the matching
ingestion service, and broadcasts a WebSocket notification
(`docs/WEBSOCKET.md`) after each successful ingest. Transport parsing and
domain verification are kept in separate functions — the MQTT callback
never contains business logic itself.

## Testing this locally

```bash
docker compose up mosquitto
# in another terminal, from backend/
uvicorn app.main:app --reload
# in a third terminal
python scripts/simulate_mqtt_gateway.py
```

The simulator publishes: a valid patrol event, a duplicate of it, an
invalid-signature variant, a broken-hash-chain variant, an unknown-node
event, and a malformed payload — check `/api/forest/patrols` or the
dashboard to see the results, and `backend/tests/test_mqtt_consumer.py`
for the equivalent in-process assertions.
