"""add fingerprint_page_id to users and verification_events table

Two-factor checkpoint verification (card + fingerprint): the officer's enrolled
R307S template slot alongside their RFID UID, and the audit trail of resolved
card+fingerprint attempts (MATCH/MISMATCH/TIMEOUT) that now drives attendance
instead of a bare card tap. See app/services/verification.py.

Revision ID: f0rest000005
Revises: f0rest000004
"""
from alembic import op
import sqlalchemy as sa

from app.models.guid import GUID

revision = "f0rest000005"
down_revision = "f0rest000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("fingerprint_page_id", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_users_fingerprint_page_id", "users", ["fingerprint_page_id"])

    op.create_table(
        "verification_events",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("claimed_uid", sa.String(length=32), nullable=False),
        sa.Column("claimed_employee_id", sa.String(length=64)),
        sa.Column("claimed_page_id", sa.Integer(), nullable=False),
        sa.Column("actual_page_id", sa.Integer(), nullable=False),
        sa.Column("actual_employee_id", sa.String(length=64)),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("node_id", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("rssi", sa.Integer()),
        sa.Column("snr", sa.Float()),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_verification_events_node_sequence", "verification_events", ["node_id", "sequence"])
    op.create_index("ix_verification_events_claimed_uid", "verification_events", ["claimed_uid"])
    op.create_index("ix_verification_events_claimed_employee_id", "verification_events", ["claimed_employee_id"])
    op.create_index("ix_verification_events_actual_employee_id", "verification_events", ["actual_employee_id"])


def downgrade() -> None:
    op.drop_table("verification_events")
    op.drop_constraint("uq_users_fingerprint_page_id", "users", type_="unique")
    op.drop_column("users", "fingerprint_page_id")
