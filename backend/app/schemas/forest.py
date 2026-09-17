"""Forest dashboard / operations schemas (all values come from the DB).

Response models serialize as camelCase (the dashboard's contract) via
``alias_generator``; ``populate_by_name=True`` means internal code keeps
constructing them with the original snake_case field names. Fields with no
real backend data source yet are explicit, documented, nullable additions
-- never a fabricated non-null value. See docs/IMPLEMENTATION_STATUS.md for
which fields these are and why.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ForestModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class CamelModel(BaseModel):
    """For response schemas that aren't ORM-backed (e.g. LedgerResponse)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class NodeCreate(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    node_type: str = Field(default="CHECKPOINT_NODE", pattern="^(CHECKPOINT_NODE|ACOUSTIC_NODE)$")
    checkpoint_id: str | None = Field(default=None, max_length=64)
    zone_id: str | None = Field(default=None, max_length=128)
    firmware_version: str | None = Field(default=None, max_length=64)
    public_key: str | None = Field(default=None, max_length=1024)


class NodeUpdate(BaseModel):
    node_type: str | None = Field(default=None, pattern="^(CHECKPOINT_NODE|ACOUSTIC_NODE)$")
    checkpoint_id: str | None = None
    zone_id: str | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE|MAINTENANCE)$")
    firmware_version: str | None = None
    public_key: str | None = Field(default=None, max_length=1024)


class NodeResponse(ForestModel):
    id: str
    node_id: str
    node_type: str
    checkpoint_id: str | None
    zone_id: str | None
    status: str
    firmware_version: str | None
    has_public_key: bool = False
    installed_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime
    # last_event_time mirrors last_seen_at (real: set on every ingest, see
    # app/services/forest_patrol.py) under the name the dashboard expects.
    last_event_time: datetime | None = None
    # NOT YET IMPLEMENTED: node-firmware has no battery/RTC-health/LoRa-
    # activity/queue-depth telemetry reporting today, and sync history is
    # not aggregated per-node (see docs/GATEWAY_BACKEND_CONTRACT.md) --
    # always null until that exists, never a fabricated reading.
    last_sync_time: datetime | None = None
    lora_activity: str | None = None
    local_queue_state: int | None = None
    rtc_state: str | None = None
    battery_level: int | None = None
    health: str | None = None


class CheckpointCreate(BaseModel):
    checkpoint_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    zone_id: str | None = Field(default=None, max_length=128)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    node_id: str | None = Field(default=None, max_length=64)
    active: bool = True


class CheckpointUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    zone_id: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    node_id: str | None = None
    active: bool | None = None


class CheckpointResponse(ForestModel):
    id: str
    checkpoint_id: str
    name: str
    zone_id: str | None
    latitude: float | None
    longitude: float | None
    node_id: str | None
    active: bool
    created_at: datetime
    updated_at: datetime


class OfficerCreate(BaseModel):
    officer_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    badge_number: str | None = Field(default=None, max_length=64)


class OfficerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    badge_number: str | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|INACTIVE)$")


class OfficerResponse(ForestModel):
    id: str
    officer_id: str
    name: str
    badge_number: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    # last_verified_patrol/patrol_count/mismatch_count are real aggregates
    # over patrol_events (see list_officers in forest_checkpoints.py).
    last_verified_patrol: datetime | None = None
    patrol_count: int = 0
    mismatch_count: int = 0
    # NOT YET IMPLEMENTED: officers have no checkpoint assignment column --
    # null, not a fabricated assignment.
    assigned_checkpoint: str | None = None


class PatrolResponse(ForestModel):
    id: str
    event_id: str
    node_id: str
    checkpoint_id: str | None
    officer_id: str | None
    sequence: int
    event_type: str
    rfid_result: str | None
    fingerprint_result: str | None
    event_created_at: datetime
    gateway_received_at: datetime | None
    backend_received_at: datetime
    previous_hash: str
    record_hash: str
    signature_status: str
    chain_status: str
    sync_status: str
    created_at: datetime
    verified_at: datetime | None
    # officer_name is a real join against patrol_officers (see patrol_out
    # in forest_patrol_api.py); null if the officer_id has no match.
    officer_name: str | None = None
    # record_status is derived from signature_status/chain_status, not a
    # separately stored value -- see patrol_out.
    record_status: str | None = None
    # NOT YET IMPLEMENTED: no physical RFID tag value is stored, only the
    # VALID/INVALID result -- null, not a fabricated tag ID.
    rfid: str | None = None


class AcousticReviewUpdate(BaseModel):
    review_status: str = Field(pattern="^(DETECTED|PENDING_REVIEW|REVIEWED|DISMISSED|CONFIRMED)$")
    reviewed_by: str | None = Field(default=None, max_length=200)


class AcousticResponse(ForestModel):
    id: str
    event_id: str
    node_id: str
    checkpoint_id: str | None
    zone_id: str | None
    sequence: int
    event_created_at: datetime
    classification: str
    confidence: float
    model_version: str | None
    previous_hash: str
    record_hash: str
    signature_status: str
    chain_status: str
    sync_status: str
    review_status: str
    gateway_received_at: datetime | None
    backend_received_at: datetime
    created_at: datetime
    reviewed_at: datetime | None
    # No audio-clip storage exists anywhere in this system -- always False,
    # a real (if unexciting) answer, not a placeholder.
    clip_available: bool = False


class LedgerResponse(CamelModel):
    event_kind: str
    event_id: str
    node_id: str
    sequence: int
    event_created_at: datetime
    previous_hash: str
    record_hash: str
    signature_status: str
    chain_status: str
    sync_status: str
    # signature is real (stored on every patrol/acoustic event) -- included
    # so the dashboard can display/verify it, not previously exposed here.
    signature: str | None = None
    # duplicate_status is always "UNIQUE" by construction: a duplicate
    # event never gets its own patrol_events/acoustic_events row in the
    # first place (see ingest_patrol_event/ingest_acoustic_event) -- only
    # unique events ever appear in the ledger, so this is a real invariant,
    # not an unverified default.
    duplicate_status: str = "UNIQUE"


class GatewayResponse(ForestModel):
    id: str
    gateway_id: str
    name: str | None
    status: str
    lora_status: str | None
    wifi_status: str | None
    backend_status: str | None
    firmware_version: str | None
    records_received: int
    records_forwarded: int
    records_pending: int
    last_seen_at: datetime | None
    last_successful_sync_at: datetime | None
    # pending_sync_queue mirrors records_pending under the dashboard's name
    # (same real counter). duplicate_packets/verification_failures/wifi_ip
    # are NOT YET IMPLEMENTED (gateway status reports don't carry them --
    # see docs/GATEWAY_BACKEND_CONTRACT.md) -- null, not fabricated.
    pending_sync_queue: int | None = None
    duplicate_packets: int | None = None
    verification_failures: int | None = None
    wifi_ip: str | None = None


class SyncRecordResponse(ForestModel):
    id: str
    sync_id: str
    event_id: str
    node_id: str
    gateway_id: str
    received_at: datetime | None
    forwarded_at: datetime | None
    attempt_count: int
    sync_status: str
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    # event_timestamp mirrors received_at (real; no separate original-event
    # timestamp is stored on SyncRecord itself). duplicate_state/
    # verification_result are real, derived in forest_ledger.py from
    # sync_status/failure_reason -- not fabricated, just not stored
    # under these names on the model.
    event_timestamp: datetime | None = None
    duplicate_state: str = "UNIQUE"
    verification_result: str | None = None
