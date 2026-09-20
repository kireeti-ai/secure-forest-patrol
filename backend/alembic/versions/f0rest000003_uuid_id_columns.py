"""convert VARCHAR(36) id columns created by f0rest000002 to native UUID

Revision ID: f0rest000003
Revises: f0rest000002
"""
from alembic import op
import sqlalchemy as sa

revision = "f0rest000003"
down_revision = "f0rest000002"
branch_labels = None
depends_on = None

# (table, column) pairs that must be UUID on PostgreSQL. Foreign keys are
# dropped and recreated around the type change.
_COLUMNS = [
    ("users", "id"),
    ("operator_checkpoint_access", "id"),
    ("operator_checkpoint_access", "user_id"),
    ("rfid_events", "id"),
    ("attendance", "id"),
]


def _is_varchar(inspector, table: str, column: str) -> bool:
    if table not in inspector.get_table_names():
        return False
    for col in inspector.get_columns(table):
        if col["name"] == column:
            return isinstance(col["type"], (sa.String, sa.CHAR)) and not isinstance(col["type"], sa.Text)
    return False


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite (tests) stores UUIDs as CHAR(36) already
    inspector = sa.inspect(bind)
    todo = [(t, c) for t, c in _COLUMNS if _is_varchar(inspector, t, c)]
    if not todo:
        return
    has_fk = "operator_checkpoint_access" in inspector.get_table_names()
    fk_names = [fk["name"] for fk in inspector.get_foreign_keys("operator_checkpoint_access")] if has_fk else []
    for name in fk_names:
        op.drop_constraint(name, "operator_checkpoint_access", type_="foreignkey")
    for table, column in todo:
        op.execute(sa.text(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE uuid USING {column}::uuid'))
    for name in fk_names:
        op.create_foreign_key(name, "operator_checkpoint_access", "users", ["user_id"], ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in _COLUMNS:
        op.execute(sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE varchar(36) USING {column}::text"))
