"""Add Instagram-like reels, profile image, and music features

Revision ID: 0003_reels_profile_music
Revises: 0002_add_new_features
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError

revision = '0003_reels_profile_music'
down_revision = '0002_add_new_features'
branch_labels = None
depends_on = None


def _has_table(conn, table_name):
    inspector = sa.inspect(conn)
    return table_name in inspector.get_table_names()


def _has_column(conn, table_name, column_name):
    if not _has_table(conn, table_name):
        return False
    inspector = sa.inspect(conn)
    return column_name in {col['name'] for col in inspector.get_columns(table_name)}


def safe_add_column(conn, table, column):
    if not _has_column(conn, table, column.name):
        op.add_column(table, column)


def safe_create_index(conn, name, table, columns):
    if not _has_table(conn, table):
        return
    indexes = {idx['name'] for idx in sa.inspect(conn).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns)


def upgrade():
    conn = op.get_bind()

    if not _has_table(conn, 'music'):
        op.create_table(
            'music',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('title', sa.String(length=150), nullable=False),
            sa.Column('artist', sa.String(length=150), nullable=True),
            sa.Column('audio_path', sa.String(length=500), nullable=False),
            sa.Column('duration', sa.Float(), nullable=True),
            sa.Column('category', sa.String(length=80), nullable=True),
            sa.Column('is_trending', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )

    safe_create_index(conn, 'ix_music_user_id', 'music', ['user_id'])
    safe_create_index(conn, 'ix_music_title', 'music', ['title'])
    safe_create_index(conn, 'ix_music_artist', 'music', ['artist'])
    safe_create_index(conn, 'ix_music_category', 'music', ['category'])
    safe_create_index(conn, 'ix_music_is_trending', 'music', ['is_trending'])

    safe_add_column(conn, 'reels', sa.Column('cover_image', sa.String(length=500), nullable=True))
    safe_add_column(conn, 'reels', sa.Column('visibility', sa.String(length=20), nullable=False, server_default='public'))
    safe_add_column(conn, 'reels', sa.Column('music_id', sa.String(), nullable=True))
    safe_create_index(conn, 'ix_reels_music_id', 'reels', ['music_id'])

    # Existing profile pictures live in profiles.profile_picture. No users column
    # is required; this migration is intentionally compatible with both SQLite
    # and PostgreSQL while keeping the existing schema boundary.


def downgrade():
    conn = op.get_bind()
    for idx in ['ix_reels_music_id']:
        try:
            op.drop_index(idx, table_name='reels')
        except (OperationalError, ProgrammingError):
            pass
    for column in ['music_id', 'visibility', 'cover_image']:
        if _has_column(conn, 'reels', column):
            try:
                op.drop_column('reels', column)
            except (OperationalError, ProgrammingError):
                pass
    if _has_table(conn, 'music'):
        op.drop_table('music')