"""offset legacy unsigned acoustic_events.sequence into a disjoint range

Unsigned acoustic events (no node signing key/RTC yet) get a backend-assigned
per-node sequence starting at 1; signed acoustic events carry the node
firmware's own hardware sequence counter, also starting low. Both land in the
same `sequence` column under uq_acoustic_events_node_sequence, so an old
unsigned row can collide with a node's real signed sequence number and the
signed event silently gets treated as a duplicate of the unrelated old row
(see app/services/forest_acoustic.py::UNSIGNED_SEQUENCE_OFFSET, added in the
same change as this migration). This moves every existing unsigned row
(previous_hash = 'UNSIGNED') into that same offset range so historical test
data stops blocking new signed events.

Revision ID: f0rest000006
Revises: f0rest000005
"""
from alembic import op

revision = "f0rest000006"
down_revision = "f0rest000005"
branch_labels = None
depends_on = None

UNSIGNED_SEQUENCE_OFFSET = 900_000_000


def upgrade() -> None:
    op.execute(
        f"UPDATE acoustic_events SET sequence = sequence + {UNSIGNED_SEQUENCE_OFFSET} "
        f"WHERE previous_hash = 'UNSIGNED' AND sequence < {UNSIGNED_SEQUENCE_OFFSET}"
    )


def downgrade() -> None:
    op.execute(
        f"UPDATE acoustic_events SET sequence = sequence - {UNSIGNED_SEQUENCE_OFFSET} "
        f"WHERE previous_hash = 'UNSIGNED' AND sequence >= {UNSIGNED_SEQUENCE_OFFSET}"
    )
