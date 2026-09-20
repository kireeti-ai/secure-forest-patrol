from app.core.security import hash_password
from app.models.user import User


def test_rfid_scan_authorizes_and_marks_entry_then_exit(client, db_session, seeded_data):
    employee = User(email="employee@forest.local", full_name="RFID Employee", employee_id="EMP001",
                    rfid_uid="A3:B7:91:2F", password_hash=hash_password("EmployeePassword123!"), role="EMPLOYEE")
    db_session.add(employee)
    db_session.commit()

    first = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "a3:b7:91:2f", "seq": 15, "rssi": -67, "snr": 8.5})
    assert first.status_code == 202
    assert first.json()["status"] == "AUTHORIZED"
    assert first.json()["attendance_action"] == "ENTRY"

    duplicate = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "A3:B7:91:2F", "seq": 15, "rssi": -67, "snr": 8.5})
    assert duplicate.status_code == 200
    assert duplicate.json()["outcome"] == "DUPLICATE"

    second = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "A3:B7:91:2F", "seq": 16, "rssi": -67, "snr": 8.5})
    assert second.status_code == 202
    assert second.json()["attendance_action"] == "EXIT"


def test_unknown_rfid_is_recorded_without_attendance(client, db_session, seeded_data):
    response = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "73:21:AC:09", "seq": 17, "rssi": -70, "snr": 7.0})
    assert response.status_code == 202
    assert response.json()["status"] == "UNKNOWN"
    assert response.json()["attendance_action"] is None


def test_rfid_assignment_is_normalized(client, db_session, seeded_data):
    employee = User(email="manage@forest.local", full_name="Managed Employee", employee_id="EMP002",
                    password_hash=hash_password("ManagedPassword123!"), role="EMPLOYEE")
    db_session.add(employee)
    db_session.commit()

    assigned = client.put("/api/employees/EMP002/rfid", json={"rfid_uid": "aa-bb-cc-dd"})
    assert assigned.status_code == 200
    assert assigned.json()["rfid_uid"] == "AA:BB:CC:DD"


def test_mqtt_rfid_and_gateway_status_topics(client, db_session, seeded_data):
    import json
    from types import SimpleNamespace

    from app.services.mqtt_consumer import TOPIC_GATEWAY_STATUS, TOPIC_RFID, MqttConsumer

    consumer = MqttConsumer(session_factory=lambda: db_session)
    db_session.close = lambda: None  # the consumer closes its session; keep the test one open

    def send(topic, body):
        consumer._on_message(None, None, SimpleNamespace(topic=topic, payload=json.dumps(body).encode()))

    send(TOPIC_RFID, {"type": "RFID_SCAN", "node_id": "NODE_01", "uid": "30:BD:57:58", "seq": 40, "rssi": -60, "snr": 9.0})
    send(TOPIC_GATEWAY_STATUS, {"gateway_id": "GW-FE", "wifi_status": "CONNECTED", "backend_status": "REACHABLE"})

    from sqlalchemy import select
    from app.models.forest_gateway import Gateway
    from app.models.rfid import RfidEvent
    assert db_session.scalar(select(RfidEvent).where(RfidEvent.sequence == 40)).status == "UNKNOWN"
    assert db_session.scalar(select(Gateway).where(Gateway.gateway_id == "GW-FE")).wifi_status == "CONNECTED"


def test_assign_employee_to_checkpoints(client, db_session, seeded_data):
    employee = User(email="cp@forest.local", full_name="CP Officer", employee_id="OFF900",
                    password_hash=hash_password("CheckpointPass123!"), role="OFFICER")
    db_session.add(employee)
    db_session.commit()
    for cid in ("CP-01", "CP-02"):
        client.post("/api/forest/checkpoints", json={"checkpoint_id": cid, "name": cid})

    ok = client.put("/api/employees/OFF900/checkpoints", json={"checkpoint_ids": ["CP-02", "CP-01", "CP-01"]})
    assert ok.status_code == 200
    assert ok.json()["checkpoints"] == ["CP-01", "CP-02"]

    narrowed = client.put("/api/employees/OFF900/checkpoints", json={"checkpoint_ids": ["CP-01"]})
    assert narrowed.status_code == 200 and narrowed.json()["checkpoints"] == ["CP-01"]

    bad = client.put("/api/employees/OFF900/checkpoints", json={"checkpoint_ids": ["CP-99"]})
    assert bad.status_code == 404

    presence = client.get("/api/officer-presence").json()
    assert next(row for row in presence if row["employee_id"] == "OFF900")["checkpoints"] == ["CP-01"]


def test_wrong_checkpoint_scan_is_flagged_and_not_attendance(client, db_session, seeded_data):
    from datetime import datetime, timezone
    from app.models.forest_node import ForestNode

    for cid, node in (("CP-01", "NODE_01"), ("CP-02", None)):
        client.post("/api/forest/checkpoints", json={"checkpoint_id": cid, "name": cid, "node_id": node})
    client.post("/api/forest/nodes", json={"node_id": "NODE_01", "checkpoint_id": "CP-01"})
    for emp, uid, cp in (("OFFA", "AA:00:00:01", "CP-01"), ("OFFB", "AA:00:00:02", "CP-02")):
        db_session.add(User(email=f"{emp}@forest.local", full_name=emp, employee_id=emp, rfid_uid=uid,
                            password_hash=hash_password("SomePassword123!"), role="OFFICER"))
        db_session.commit()
        client.put(f"/api/employees/{emp}/checkpoints", json={"checkpoint_ids": [cp]})

    ok = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "AA:00:00:01", "seq": 50, "rssi": -60, "snr": 9.0})
    assert ok.json()["status"] == "AUTHORIZED" and ok.json()["attendance_action"] == "ENTRY"

    wrong = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "AA:00:00:02", "seq": 51, "rssi": -60, "snr": 9.0})
    assert wrong.json()["status"] == "INVALID" and wrong.json()["attendance_action"] is None
    assert "invalid checkpoint CP-01" in wrong.json()["reason"] and "CP-02" in wrong.json()["reason"]

    states = {c["checkpointId"]: c["state"] for c in client.get("/api/forest/checkpoints").json()}
    assert (states["CP-01"], states["CP-02"]) == ("ONLINE", "OFFLINE")   # only the one with a live node
    node = next(n for n in client.get("/api/forest/nodes").json() if n["nodeId"] == "NODE_01")
    assert node["lastSeenAt"] is not None
    events = client.get("/api/rfid-events").json()
    assert {e["checkpoint_id"] for e in events if e["node_id"] == "NODE_01"} == {"CP-01"}
    bad = next(e for e in events if e["status"] == "INVALID")
    assert bad["employee_id"] == "OFFB" and "invalid checkpoint CP-01" in bad["reason"]


def test_sequence_reuse_after_node_reboot_is_a_new_scan(client, db_session, seeded_data):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.rfid import RfidEvent

    scan = {"type": "RFID_SCAN", "node_id": "NODE_01", "uid": "73:21:AC:09", "seq": 0, "rssi": -60, "snr": 9.0}
    assert client.post("/api/ingest/gateway/rfid-scan", json=scan).json()["outcome"] == "ACCEPTED"
    # an immediate redelivery is still a duplicate
    assert client.post("/api/ingest/gateway/rfid-scan", json=scan).json()["outcome"] == "DUPLICATE"

    # node reboots later and restarts its counter at 0: must be recorded, not dropped
    event = db_session.scalar(select(RfidEvent).where(RfidEvent.rfid_uid == "73:21:AC:09"))
    event.timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()
    assert client.post("/api/ingest/gateway/rfid-scan", json=scan).json()["outcome"] == "ACCEPTED"
    assert len(list(db_session.scalars(select(RfidEvent).where(RfidEvent.rfid_uid == "73:21:AC:09")))) == 2


def test_gateway_goes_offline_when_it_stops_reporting(client, db_session, seeded_data):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.models.forest_gateway import Gateway

    client.post("/api/ingest/gateway/status", json={
        "gateway_id": "GW-T", "lora_status": "ACTIVE", "wifi_status": "CONNECTED", "backend_status": "REACHABLE"})
    live = next(g for g in client.get("/api/forest/gateways").json() if g["gatewayId"] == "GW-T")
    assert live["online"] is True and live["wifiStatus"] == "CONNECTED"

    row = db_session.scalar(select(Gateway).where(Gateway.gateway_id == "GW-T"))
    row.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db_session.commit()
    stale = next(g for g in client.get("/api/forest/gateways").json() if g["gatewayId"] == "GW-T")
    assert stale["online"] is False
    assert (stale["wifiStatus"], stale["backendStatus"], stale["loraStatus"]) == ("DISCONNECTED", "UNREACHABLE", "NO_TRAFFIC")
    status = client.get("/api/forest/system-status").json()
    assert "GW-T" not in status["gateway"]["details"] and status["wifiBackhaul"]["details"].startswith("0/")
