"""Forest-patrol domain enumerations.

These are plain ``str`` enums used for validation and API contracts.
They are intentionally stored as ``String`` columns (not PostgreSQL ENUM
types) so the schema stays portable between PostgreSQL and SQLite/test
databases and so future values never require a database enum migration.

There is intentionally NO role enum: this backend has no authentication
layer and therefore no RBAC (see ``docs/BACKEND.md``).
"""

from enum import Enum


class ForestNodeType(str, Enum):
    CHECKPOINT_NODE = "CHECKPOINT_NODE"
    ACOUSTIC_NODE = "ACOUSTIC_NODE"


class ForestNodeStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


class OfficerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class RfidResult(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"


class FingerprintResult(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"


class SignatureStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    PENDING = "PENDING"


class ChainStatus(str, Enum):
    VALID = "VALID"
    BROKEN = "BROKEN"
    PENDING = "PENDING"


class EventSyncStatus(str, Enum):
    SYNCED = "SYNCED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class AcousticClassification(str, Enum):
    GUNSHOT = "Gunshot"
    CHAINSAW = "Chainsaw"
    NON_THREAT = "Non-threat"


class AcousticReviewStatus(str, Enum):
    DETECTED = "DETECTED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
    CONFIRMED = "CONFIRMED"


class SyncState(str, Enum):
    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    FORWARDED = "FORWARDED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class IngestOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    ALREADY_PROCESSED = "ALREADY_PROCESSED"
    DUPLICATE = "DUPLICATE"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    BROKEN_CHAIN = "BROKEN_CHAIN"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNKNOWN_NODE = "UNKNOWN_NODE"


class SystemStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"
