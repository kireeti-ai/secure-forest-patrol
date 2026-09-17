"""Gateway -> Backend MQTT consumer.

Transport only. Every handler below immediately hands off to the *same*
verification/persistence services the HTTP ingestion routes use
(``app/services/forest_patrol.py``, ``forest_acoustic.py``,
``forest_gateway_svc.py``) -- there is no duplicated business logic here,
per ``docs/MQTT.md``. WebSocket broadcasting is shared with the HTTP routes
too, via the helpers in ``app/services/ws_manager.py``, so a dashboard live
update fires the same way regardless of which transport an event arrived on.

Topics:
    forest/events/patrol       -> ForestPatrolIngest  -> ingest_patrol_event
    forest/events/acoustic     -> ForestAcousticIngest -> ingest_acoustic_event
    forest/events/node-status  -> GatewayStatusReport  -> report_gateway_status
    forest/events/sync         -> relayed live (SYNC_UPDATED) only; sync
                                   records themselves are still written as a
                                   side effect of patrol/acoustic ingestion,
                                   not from this topic (NOT IMPLEMENTED as a
                                   standalone write path -- see docs/MQTT.md)
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import get_mqtt_config
from app.core.database import SessionLocal, get_engine
from app.schemas.forest_ingest import ForestAcousticIngest, ForestPatrolIngest, GatewayStatusReport
from app.services.forest_acoustic import ingest_acoustic_event
from app.services.forest_gateway_svc import report_gateway_status
from app.services.forest_patrol import UnknownNodeError, ingest_patrol_event
from app.services.ws_manager import broadcast_acoustic_outcome, broadcast_gateway_status, broadcast_patrol_outcome, manager

logger = logging.getLogger("forest.mqtt")

TOPIC_PATROL = "forest/events/patrol"
TOPIC_ACOUSTIC = "forest/events/acoustic"
TOPIC_NODE_STATUS = "forest/events/node-status"
TOPIC_SYNC = "forest/events/sync"


class MqttConsumer:
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or (lambda: SessionLocal(bind=get_engine()))
        self._config = get_mqtt_config()
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="forest-backend", clean_session=True)
        if self._config.username:
            self._client.username_pw_set(self._config.username, self._config.password)
        if self._config.tls:
            self._client.tls_set()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        manager.bind_loop(loop)
        self._client.connect_async(self._config.host, self._config.port)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties=None) -> None:
        if reason_code != 0:
            logger.error("MQTT connect failed rc=%s", reason_code)
            return
        logger.info("MQTT connected to %s:%s", self._config.host, self._config.port)
        for topic in (TOPIC_PATROL, TOPIC_ACOUSTIC, TOPIC_NODE_STATUS, TOPIC_SYNC):
            client.subscribe(topic, qos=1)

    def _on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Malformed MQTT payload on %s", msg.topic)
            return

        try:
            if msg.topic == TOPIC_PATROL:
                self._handle_patrol(data)
            elif msg.topic == TOPIC_ACOUSTIC:
                self._handle_acoustic(data)
            elif msg.topic == TOPIC_NODE_STATUS:
                self._handle_node_status(data)
            elif msg.topic == TOPIC_SYNC:
                self._handle_sync(data)
        except Exception:
            logger.exception("Error handling MQTT message on %s", msg.topic)

    def _handle_patrol(self, data: dict) -> None:
        try:
            payload = ForestPatrolIngest.model_validate(data)
        except ValidationError:
            logger.warning("Malformed patrol payload: %s", data)
            return
        db = self._session_factory()
        try:
            try:
                body, _status = ingest_patrol_event(db, payload)
            except UnknownNodeError:
                manager.schedule_broadcast("PATROL_EVENT_REJECTED", {
                    "node_id": payload.node_id, "status": "UNKNOWN_NODE"})
                return
        finally:
            db.close()
        broadcast_patrol_outcome(body, payload.node_id, payload.checkpoint_id)

    def _handle_acoustic(self, data: dict) -> None:
        try:
            payload = ForestAcousticIngest.model_validate(data)
        except ValidationError:
            logger.warning("Malformed acoustic payload: %s", data)
            return
        db = self._session_factory()
        try:
            try:
                body, _status = ingest_acoustic_event(db, payload)
            except UnknownNodeError:
                return
        finally:
            db.close()
        broadcast_acoustic_outcome(body, payload.node_id, payload.checkpoint_id)

    def _handle_node_status(self, data: dict) -> None:
        try:
            payload = GatewayStatusReport.model_validate(data)
        except ValidationError:
            # Missing gateway_id entirely -- nothing to key a Gateway row on.
            logger.warning("Malformed node-status payload, dropped: %s", data)
            return
        # NOTE: today's real Gateway publishes a diagnostic envelope here
        # (gateway_id, node_id, sequence, rssi, snr, event_created_at,
        # temperature_c -- see docs/GATEWAY_BACKEND_CONTRACT.md), not an
        # actual GatewayStatusReport. Pydantic validates it anyway because
        # every GatewayStatusReport field except gateway_id is optional and
        # unknown fields are ignored by default -- it does NOT get rejected.
        # The per-node/per-packet fields (node_id, sequence, rssi, snr,
        # temperature) have no home in the Gateway table and are silently
        # discarded; only gateway_id + last_seen_at actually get persisted.
        # Logged here so that data loss is visible rather than silent.
        if "node_id" in data or "sequence" in data:
            logger.info("Diagnostic node-status payload from %s (node=%s seq=%s): "
                        "only gateway_id/last_seen_at persisted, rest discarded",
                        payload.gateway_id, data.get("node_id"), data.get("sequence"))
        db = self._session_factory()
        try:
            result = report_gateway_status(db, payload)
        finally:
            db.close()
        broadcast_gateway_status(result["gateway_id"])

    def _handle_sync(self, data: dict) -> None:
        # No standalone persistence path for this topic today -- sync
        # records are written as a side effect of patrol/acoustic ingestion.
        # This just relays the gateway's own sync diagnostics live.
        manager.schedule_broadcast("SYNC_UPDATED", {"raw": data})


consumer = MqttConsumer()
