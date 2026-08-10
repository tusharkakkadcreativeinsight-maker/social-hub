"""Add music library metadata and reel music columns

Revision ID: 0005_music_library_reels
Revises: 0004_profile_live_audit_soft_delete
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError


revision = '0005_music_library_reels'
down_revision = '0004_profile_live_audit_soft_delete'
branch_labels = None
depends_on = None

IGNORED = (OperationalError, ProgrammingError)


def _has_table(conn, table):
    return table in sa.inspect(conn).get_table_names()


def _has_column(conn, table, column):
    return _has_table(conn, table) and column in {c['name'] for c in sa.inspect(conn).get_columns(table)}


def _has_index(conn, table, index):
    return _has_table(conn, table) and index in {i['name'] for i in sa.inspect(conn).get_indexes(table)}


def _add_column(conn, table, column):
    if not _has_column(conn, table, column.name):
        op.add_column(table, column)


def _create_index(conn, name, table, cols):
    if _has_table(conn, table) and not _has_index(conn, table, name):
        op.create_index(name, table, cols)


def upgrade():
    conn = op.get_bind()
    if not _has_table(conn, 'music'):
        op.create_table(
            'music',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('title', sa.String(length=150), nullable=False),
            sa.Column('artist', sa.String(length=150), nullable=True),
            sa.Column('audio_path', sa.String(length=500), nullable=False),
            sa.Column('duration', sa.Float(), nullable=True),
            sa.Column('category', sa.String(length=80), nullable=True),
            sa.Column('is_trending', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('user_id', sa.String(), nullable=True),
            sa.Column('created_by', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
    else:
        _add_column(conn, 'music', sa.Column('created_by', sa.String(), nullable=True))
        _add_column(conn, 'music', sa.Column('use_count', sa.Integer(), nullable=False, server_default='0'))
        _add_column(conn, 'music', sa.Column('updated_at', sa.DateTime(), nullable=True))

    for name, cols in {
        'ix_music_created_by': ['created_by'],
        'ix_music_use_count': ['use_count'],
        'ix_music_title': ['title'],
        'ix_music_artist': ['artist'],
        'ix_music_category': ['category'],
        'ix_music_is_trending': ['is_trending'],
    }.items():
        _create_index(conn, name, 'music', cols)

    _add_column(conn, 'reels', sa.Column('music_id', sa.String(), nullable=True))
    _add_column(conn, 'reels', sa.Column('music_name', sa.String(length=150), nullable=True))
    _create_index(conn, 'ix_reels_music_id', 'reels', ['music_id'])


def downgrade():
    conn = op.get_bind()
    for idx in ['ix_music_created_by', 'ix_music_use_count']:
        if _has_index(conn, 'music', idx):
            try:
                op.drop_index(idx, table_name='music')
            except IGNORED:
                pass
    for col in ['updated_at', 'use_count', 'created_by']:
        if _has_column(conn, 'music', col):
            try:
                op.drop_column('music', col)
            except IGNORED:
                pass