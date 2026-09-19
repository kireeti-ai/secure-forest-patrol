from app.core.security import create_access_token, hash_password
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

    token = create_access_token({"sub": str(employee.id), "role": "EMPLOYEE"})
    mine = client.get("/api/my-attendance", headers={"Authorization": f"Bearer {token}"})
    assert mine.status_code == 200
    assert len(mine.json()["records"]) == 1
    assert mine.json()["records"][0]["exit_at"] is not None


def test_unknown_rfid_is_recorded_without_attendance(client, db_session, seeded_data):
    response = client.post("/api/ingest/gateway/rfid-scan", json={
        "type": "RFID_SCAN", "node_id": "NODE_01", "uid": "73:21:AC:09", "seq": 17, "rssi": -70, "snr": 7.0})
    assert response.status_code == 202
    assert response.json()["status"] == "UNKNOWN"
    assert response.json()["attendance_action"] is None


def test_only_officer_can_manage_rfid_assignments(client, db_session, seeded_data):
    employee = User(email="manage@forest.local", full_name="Managed Employee", employee_id="EMP002",
                    password_hash=hash_password("ManagedPassword123!"), role="EMPLOYEE")
    db_session.add(employee)
    db_session.commit()

    employee_token = create_access_token({"sub": str(employee.id), "role": "EMPLOYEE"})
    denied = client.put("/api/employees/EMP002/rfid", json={"rfid_uid": "AA:BB:CC:DD"},
                        headers={"Authorization": f"Bearer {employee_token}"})
    assert denied.status_code == 403

    officer = User(email="officer@forest.local", full_name="RFID Officer", employee_id="OFF001",
                   password_hash=hash_password("OfficerPassword123!"), role="OFFICER")
    db_session.add(officer)
    db_session.commit()
    officer_token = create_access_token({"sub": str(officer.id), "role": "OFFICER"})
    assigned = client.put("/api/employees/EMP002/rfid", json={"rfid_uid": "aa-bb-cc-dd"},
                          headers={"Authorization": f"Bearer {officer_token}"})
    assert assigned.status_code == 200
    assert assigned.json()["rfid_uid"] == "AA:BB:CC:DD"
