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

    bad = client.put("/api/employees/OFF900/checkpoints", json={"checkpoint_ids": ["CP-99"]})
    assert bad.status_code == 404

    presence = client.get("/api/officer-presence").json()
    assert next(row for row in presence if row["employee_id"] == "OFF900")["checkpoints"] == ["CP-01", "CP-02"]
