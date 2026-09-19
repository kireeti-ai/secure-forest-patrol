"""Gateway -> backend forest ingestion schemas.

The gateway bridges LoRa to IP: it extracts field events from LoRa
frames and POSTs them here over Wi-Fi/HTTPS. The backend never sees raw
RF — only this HTTP contract.

Two ingestion kinds:
- patrol events  (RFID + fingerprint match result, RTC timestamp)
- acoustic events (TinyML classification + confidence, RTC timestamp)

Both carry the node's ECC signature + hash-chain links so the backend
can verify authenticity and history integrity offline-first.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class GatewayMeta(BaseModel):
    gateway_id: str = Field(min_length=1, max_length=64)
    received_at: datetime | None = None
    rssi: int | None = None
    snr: float | None = None


class ForestPatrolIngest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    sequence: int = Field(ge=0, le=4294967295)
    event_id: str | None = Field(default=None, max_length=64)
    event_type: str = Field(default="PATROL_EVENT", max_length=32)
    checkpoint_id: str | None = Field(default=None, max_length=64)
    officer_id: str | None = Field(default=None, max_length=64)
    rfid_result: str = Field(default="VALID", pattern="^(VALID|INVALID)$")
    fingerprint_result: str = Field(default="MATCH", pattern="^(MATCH|NO_MATCH)$")
    event_created_at: datetime
    previous_hash: str = Field(default="GENESIS", max_length=128)
    record_hash: str = Field(min_length=1, max_length=128)
    signature: str = Field(min_length=1, max_length=2048)
    gateway: GatewayMeta | None = None


class ForestAcousticIngest(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    sequence: int = Field(ge=0, le=4294967295)
    event_id: str | None = Field(default=None, max_length=64)
    checkpoint_id: str | None = Field(default=None, max_length=64)
    zone_id: str | None = Field(default=None, max_length=128)
    event_created_at: datetime
    classification: str = Field(min_length=1, max_length=32)
    confidence: float = Field(ge=0.0, le=1.0)
    model_version: str | None = Field(default=None, max_length=64)
    previous_hash: str = Field(default="GENESIS", max_length=128)
    record_hash: str = Field(min_length=1, max_length=128)
    signature: str = Field(min_length=1, max_length=2048)
    gateway: GatewayMeta | None = None


class GatewayStatusReport(BaseModel):
    gateway_id: str = Field(min_length=1, max_length=64)
    name: str | None = Field(default=None, max_length=200)
    lora_status: str | None = None
    wifi_status: str | None = None
    backend_status: str | None = None
    firmware_version: str | None = None
    records_received: int | None = Field(default=None, ge=0)
    records_forwarded: int | None = Field(default=None, ge=0)
    records_pending: int | None = Field(default=None, ge=0)


class IngestResult(BaseModel):
    outcome: str
    event_id: str | None = None
    duplicate: bool = False
    signature_status: str | None = None
    chain_status: str | None = None
    detail: str | None = None

class RfidScanIngest(BaseModel):
    type: str = Field(pattern="^RFID_SCAN$")
    node_id: str
    uid: str
    seq: int
    rssi: int
    snr: float
