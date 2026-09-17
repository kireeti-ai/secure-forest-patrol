"""Shared test fixtures: in-memory SQLite DB + FastAPI TestClient.

Restores the fixtures test_forest_crypto.py/test_forest_patrol.py expect
(``client``, ``db_session``, ``seeded_data``) -- this file was missing
entirely (pre-existing gap from the maritime->forest migration, unrelated
to the MQTT/WebSocket work this conftest was added to support).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.database import get_db
from app.main import app
from app.models import Base, Checkpoint, ForestNode, Gateway, PatrolOfficer


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)
    session = TestingSessionLocal()

    def _override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    try:
        yield session
    finally:
        session.close()
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_data(db_session: Session):
    db_session.add_all([
        ForestNode(node_id="FN-001", checkpoint_id="CP-001"),
        ForestNode(node_id="FN-002", checkpoint_id="CP-002"),
        Checkpoint(checkpoint_id="CP-001", name="North Ridge Gate", zone_id="ZONE-A"),
        Checkpoint(checkpoint_id="CP-002", name="River Crossing", zone_id="ZONE-B"),
        PatrolOfficer(officer_id="OFF-001", name="Test Officer"),
        Gateway(gateway_id="GW-01", name="Test Gateway"),
    ])
    db_session.commit()
    return {"nodes": ["FN-001", "FN-002"], "checkpoints": ["CP-001", "CP-002"]}
