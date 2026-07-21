"""security admin report compatibility

Revision ID: 0006_security_admin_report_compat
Revises: 0005_music_library_reels
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError


revision = "0006_security_admin_report_compat"
down_revision = "0005_music_library_reels"
branch_labels = None
depends_on = None


IGNORED = (OperationalError, ProgrammingError)


def _has_table(conn, table_name: str) -> bool:
    try:
        return sa.inspect(conn).has_table(table_name)
    except Exception:
        return False


def _has_column(conn, table_name: str, column_name: str) -> bool:
    try:
        return any(col["name"] == column_name for col in sa.inspect(conn).get_columns(table_name))
    except Exception:
        return False


def _safe_add_column(conn, table_name: str, column: sa.Column) -> None:
    if not _has_table(conn, table_name) or _has_column(conn, table_name, column.name):
        return
    try:
        op.add_column(table_name, column)
    except IGNORED:
        pass


def upgrade() -> None:
    conn = op.get_bind()
    _safe_add_column(conn, "reports", sa.Column("reel_id", sa.String(), nullable=True))
    _safe_add_column(conn, "reports", sa.Column("story_id", sa.String(), nullable=True))
    _safe_add_column(conn, "reports", sa.Column("resolved_by", sa.String(), nullable=True))
    _safe_add_column(conn, "reports", sa.Column("resolved_at", sa.DateTime(), nullable=True))
    _safe_add_column(conn, "audit_logs", sa.Column("reason", sa.Text(), nullable=True))


def downgrade() -> None:
    # Keep downgrade conservative for SQLite compatibility and production safety.
    conn = op.get_bind()
    for table_name, column_name in [
        ("audit_logs", "reason"),
        ("reports", "resolved_at"),
        ("reports", "resolved_by"),
        ("reports", "story_id"),
        ("reports", "reel_id"),
    ]:
        if not _has_table(conn, table_name) or not _has_column(conn, table_name, column_name):
            continue
        try:
            op.drop_column(table_name, column_name)
        except IGNORED:
            pass