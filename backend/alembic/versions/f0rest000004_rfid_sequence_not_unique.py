"""allow repeated (node_id, sequence) on rfid_events

A node's sequence counter restarts at 0 whenever it reboots, so the unique
constraint made every post-reboot scan look like a duplicate and be dropped.

Revision ID: f0rest000004
Revises: f0rest000003
"""
from alembic import op

revision = "f0rest000004"
down_revision = "f0rest000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("rfid_events") as batch:
        batch.drop_constraint("uq_rfid_events_node_sequence", type_="unique")
    op.create_index("ix_rfid_events_node_sequence", "rfid_events", ["node_id", "sequence"])


def downgrade() -> None:
    op.drop_index("ix_rfid_events_node_sequence", table_name="rfid_events")
    with op.batch_alter_table("rfid_events") as batch:
        batch.create_unique_constraint("uq_rfid_events_node_sequence", ["node_id", "sequence"])
