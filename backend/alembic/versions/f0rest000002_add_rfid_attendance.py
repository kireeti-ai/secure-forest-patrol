"""add RFID attendance tables and employee identity fields

Revision ID: f0rest000002
Revises: f0rest000001
"""
from alembic import op
import sqlalchemy as sa

revision = "f0rest000002"
down_revision = "f0rest000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("employee_id", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("rfid_uid", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_users_employee_id", "users", ["employee_id"])
    op.create_unique_constraint("uq_users_rfid_uid", "users", ["rfid_uid"])
    op.create_table("rfid_events", sa.Column("id", sa.String(length=36), primary_key=True),
                    sa.Column("rfid_uid", sa.String(length=32), nullable=False), sa.Column("employee_id", sa.String(length=64)),
                    sa.Column("node_id", sa.String(length=64), nullable=False), sa.Column("sequence", sa.Integer(), nullable=False),
                    sa.Column("event_type", sa.String(length=32), nullable=False), sa.Column("status", sa.String(length=16), nullable=False),
                    sa.Column("rssi", sa.Integer()), sa.Column("snr", sa.Float()), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
                    sa.UniqueConstraint("node_id", "sequence", name="uq_rfid_events_node_sequence"))
    op.create_index("ix_rfid_events_rfid_uid", "rfid_events", ["rfid_uid"])
    op.create_index("ix_rfid_events_employee_id", "rfid_events", ["employee_id"])
    op.create_table("attendance", sa.Column("id", sa.String(length=36), primary_key=True),
                    sa.Column("employee_id", sa.String(length=64), nullable=False), sa.Column("attendance_date", sa.Date(), nullable=False),
                    sa.Column("entry_at", sa.DateTime(timezone=True), nullable=False), sa.Column("exit_at", sa.DateTime(timezone=True)),
                    sa.UniqueConstraint("employee_id", "attendance_date", name="uq_attendance_employee_day"))
    op.create_index("ix_attendance_employee_id", "attendance", ["employee_id"])


def downgrade() -> None:
    op.drop_table("attendance")
    op.drop_table("rfid_events")
    op.drop_constraint("uq_users_rfid_uid", "users", type_="unique")
    op.drop_constraint("uq_users_employee_id", "users", type_="unique")
    op.drop_column("users", "rfid_uid")
    op.drop_column("users", "employee_id")
