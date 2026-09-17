"""Simulated Gateway: publishes realistic signed events over MQTT.

This is the "simulated gateway" integration test called for before physical
hardware integration (docs/MQTT.md, docs/IMPLEMENTATION_STATUS.md). It does
NOT talk to real hardware -- it publishes the same JSON envelope a real
Gateway would, using the same deterministic signing vectors the backend's
own test suite uses, so the whole verification pipeline (signature, hash
chain, duplicate detection) can be exercised locally against a running
backend + Postgres + Mosquitto broker.

Usage (with the backend and a broker running):

    python scripts/simulate_mqtt_gateway.py --host localhost --port 1883

Requires a ForestNode "FN-001" already registered in the database with the
public key from tests/forest_vectors.public_pem() -- see docs/MQTT.md for
how to seed one.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paho.mqtt.client as mqtt

from tests.forest_vectors import patrol_payload

TOPIC_PATROL = "forest/events/patrol"


def _publish(client: mqtt.Client, topic: str, body: dict, label: str) -> None:
    client.publish(topic, json.dumps(body), qos=1)
    print(f"[PUBLISH] {label}: node={body.get('node_id')} seq={body.get('sequence')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    args = parser.parse_args()

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.port)
    client.loop_start()
    time.sleep(0.5)

    valid_body, _, valid_hash = patrol_payload(sequence=1)
    _publish(client, TOPIC_PATROL, valid_body, "valid patrol event")
    time.sleep(0.3)

    _publish(client, TOPIC_PATROL, valid_body, "duplicate of the same event")
    time.sleep(0.3)

    tampered = dict(valid_body)
    tampered["sequence"] = 2
    tampered["signature"] = tampered["signature"][::-1]
    _publish(client, TOPIC_PATROL, tampered, "invalid signature")
    time.sleep(0.3)

    broken_chain, _, _ = patrol_payload(sequence=3, previous_hash="WRONG-HASH")
    _publish(client, TOPIC_PATROL, broken_chain, "broken hash chain")
    time.sleep(0.3)

    unknown_node, _, _ = patrol_payload(node_id="FN-UNKNOWN", sequence=1)
    _publish(client, TOPIC_PATROL, unknown_node, "unknown node")
    time.sleep(0.3)

    client.publish(TOPIC_PATROL, "{not valid json", qos=1)
    print("[PUBLISH] malformed payload")
    time.sleep(0.3)

    client.loop_stop()
    client.disconnect()
    print("Done. Check backend logs / /api/forest/patrols / the dashboard for results.")


if __name__ == "__main__":
    main()
