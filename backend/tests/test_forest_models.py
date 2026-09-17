"""Forest domain model registration tests (no maritime tables)."""

from sqlalchemy import UniqueConstraint

from app.models import (
    AcousticEvent,
    Base,
    Checkpoint,
    Gateway,
    ForestNode,
    PatrolOfficer,
    PatrolEvent,
    SyncRecord,
)


def test_forest_tables_registered():
    tables = set(Base.metadata.tables)
    for expected in ["forest_nodes", "checkpoints", "patrol_officers",
                     "patrol_events", "acoustic_events", "gateways",
                     "sync_records", "users", "operator_checkpoint_access"]:
        assert expected in tables, f"missing {expected}"


def test_no_maritime_tables():
    tables = set(Base.metadata.tables)
    for gone in ["boats", "vessels", "telemetry", "alerts", "incidents",
                 "trips", "crew_messages", "boat_devices",
                 "device_associations", "historical_events"]:
        assert gone not in tables, f"maritime table leaked: {gone}"


def test_idempotency_constraints():
    patrol_uq = {c.name for c in PatrolEvent.__table__.constraints
                 if isinstance(c, UniqueConstraint)}
    assert "uq_patrol_events_node_sequence" in patrol_uq
    acoustic_uq = {c.name for c in AcousticEvent.__table__.constraints
                   if isinstance(c, UniqueConstraint)}
    assert "uq_acoustic_events_node_sequence" in acoustic_uq
    sync_uq = {c.name for c in SyncRecord.__table__.constraints
               if isinstance(c, UniqueConstraint)}
    assert "uq_sync_records_event_gateway" in sync_uq
    node_uq = {c.name for c in ForestNode.__table__.constraints
               if isinstance(c, UniqueConstraint)}
    assert "uq_forest_nodes_node_id" in node_uq
