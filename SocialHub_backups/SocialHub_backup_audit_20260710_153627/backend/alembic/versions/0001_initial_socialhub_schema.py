"""initial socialhub schema

Revision ID: 0001_initial_socialhub_schema
Revises: 
Create Date: 2026-07-03

This baseline migration creates the current SQLAlchemy model metadata. It is
intentionally metadata-driven so PostgreSQL production migrations and SQLite
local fallback stay aligned with the application models.
"""

from typing import Sequence, Union

from alembic import op

from app.database import Base
from app.models import models  # noqa: F401 - registers all model tables


revision: str = "0001_initial_socialhub_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)