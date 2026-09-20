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
