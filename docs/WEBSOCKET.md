# WebSocket: Backend → Dashboard Live Updates

**Status:** IMPLEMENTED, TESTED LOCALLY (`backend/tests/test_forest_ws.py`,
`test_mqtt_consumer.py::test_broadcast_fires_on_valid_patrol`). Manual
browser verification (dashboard live-updating on a simulated event) is
UNDER VALIDATION — see the plan's verification section for the exact
steps; not yet confirmed by a human in a browser at the time of writing.

## Endpoint

`WS /ws` on the backend (`app/api/routes/forest_ws.py`). No authentication,
consistent with the rest of this backend (`app/main.py` documents the
no-auth stance explicitly). The dashboard does not send any commands over
this socket — it is receive-only from the dashboard's perspective.

## Relationship to REST — WebSocket is NOT the source of truth

PostgreSQL, via the `/api/forest/*` REST routes, remains authoritative.
This socket only *notifies* that something changed; it never carries
enough information to reconstruct dashboard state on its own. The
dashboard client (`dashboard/lib/ws.ts`) enforces this:

- On **every** successful connection — the first one and every
  reconnect — it calls back into the page's existing REST fetch function
  before processing any further messages.
  Reconnect uses exponential backoff (1s → 15s cap).
- Missing a message (a dropped connection, a backend restart) does not
  corrupt state, because the next reconnect triggers a full REST refetch.

## Event types

Emitted after a successful ingest is persisted, via the shared helpers in
`app/services/ws_manager.py` (`broadcast_patrol_outcome`,
`broadcast_acoustic_outcome`, `broadcast_gateway_status`) — called from
both `app/services/mqtt_consumer.py` and the HTTP routes in
`app/api/routes/forest_ingest.py`, so the event type and payload shape
never depend on which transport an event arrived over:

| Type | Fired when | Payload fields (beyond `type`/`timestamp`) |
|---|---|---|
| `PATROL_EVENT_VERIFIED` | A patrol event is accepted | `event_id`, `node_id`, `checkpoint_id`, `status` |
| `PATROL_EVENT_REJECTED` | A patrol event is rejected (invalid signature, broken chain, unknown node) | `event_id`?, `node_id`, `checkpoint_id`?, `status` |
| `ACOUSTIC_EVENT_RECEIVED` | An acoustic detection is recorded (always `PENDING_REVIEW` — never auto-confirmed) | `event_id`, `node_id`, `checkpoint_id`, `status` |
| `LEDGER_VERIFICATION_RESULT` | Alongside a patrol event, reports its chain/signature status | `event_id`, `node_id`, `chain_status`, `signature_status` |
| `GATEWAY_STATUS_CHANGED` | A Gateway status report is processed | `gateway_id`, `status` |
| `SYNC_UPDATED` | A `forest/events/sync` MQTT message is relayed (not persisted — see `docs/MQTT.md`) | `raw` |

`NODE_STATUS_CHANGED` is reserved in the dashboard's event-type union
(`dashboard/lib/ws.ts`) for a future per-node status write path; nothing
publishes it yet (today's Gateway diagnostic data lands on
`GATEWAY_STATUS_CHANGED` territory instead — see `docs/MQTT.md`).

Every message is JSON: `{"type": "...", "timestamp": "<ISO 8601 UTC>", ...}`.

## Dashboard client

`dashboard/lib/ws.ts` exports `useForestWebSocket(eventTypes, onEvent,
onReconnect)`, wired into the Overview, Patrols, Acoustic Events, Gateway,
Nodes, and Sync History pages — each subscribes only to the event types
relevant to its own view and re-triggers its existing `lib/api.ts` fetch
function. No new data-fetching pattern was introduced; the existing
polling intervals stay in place as a fallback if the socket is down.
