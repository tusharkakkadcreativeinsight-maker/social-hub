"""Add profile image, live, audit log, and soft-delete schema

Revision ID: 0004_profile_live_audit_soft_delete
Revises: 0003_reels_profile_music
Create Date: 2026-07-09

This revision is intentionally defensive because older local SQLite databases
may have been created from metadata while others were upgraded incrementally.
It only creates missing tables, columns, and indexes.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError


revision = '0004_profile_live_audit_soft_delete'
down_revision = '0003_reels_profile_music'
branch_labels = None
depends_on = None


IGNORED_DDL_ERRORS = (OperationalError, ProgrammingError)


def _inspector(conn):
    return sa.inspect(conn)


def _has_table(conn, table_name):
    return table_name in _inspector(conn).get_table_names()


def _has_column(conn, table_name, column_name):
    if not _has_table(conn, table_name):
        return False
    return column_name in {col['name'] for col in _inspector(conn).get_columns(table_name)}


def _has_index(conn, table_name, index_name):
    if not _has_table(conn, table_name):
        return False
    return index_name in {idx['name'] for idx in _inspector(conn).get_indexes(table_name)}


def safe_add_column(conn, table_name, column):
    if not _has_column(conn, table_name, column.name):
        op.add_column(table_name, column)


def safe_create_index(conn, index_name, table_name, columns, unique=False):
    if _has_table(conn, table_name) and not _has_index(conn, table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def safe_drop_index(conn, index_name, table_name):
    if _has_index(conn, table_name, index_name):
        try:
            op.drop_index(index_name, table_name=table_name)
        except IGNORED_DDL_ERRORS:
            pass


def safe_drop_column(conn, table_name, column_name):
    if _has_column(conn, table_name, column_name):
        try:
            op.drop_column(table_name, column_name)
        except IGNORED_DDL_ERRORS:
            pass


def upgrade():
    conn = op.get_bind()

    # Profile image fields live on the profiles table and power
    # /api/users/me/profile-image and /api/users/profile/picture.
    safe_add_column(conn, 'profiles', sa.Column('profile_picture', sa.String(length=500), nullable=True, server_default='default_profile.png'))
    safe_add_column(conn, 'profiles', sa.Column('cover_photo', sa.String(length=500), nullable=True, server_default='default_cover.jpg'))

    # Soft-delete fields used throughout content APIs.
    soft_delete_columns = {
        'posts': True,
        'comments': True,
        'stories': True,
        'reels': True,
        'messages': True,
        'live_streams': False,
        'marketplace_products': False,
        'demo_data_batches': False,
    }
    for table_name, include_deleted_at in soft_delete_columns.items():
        if _has_table(conn, table_name):
            safe_add_column(conn, table_name, sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
            if include_deleted_at:
                safe_add_column(conn, table_name, sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # Ensure live_streams has all fields expected by app/api/live.py and
    # app/websocket/live.py.
    if not _has_table(conn, 'live_streams'):
        op.create_table(
            'live_streams',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('host_id', sa.String(), nullable=False),
            sa.Column('title', sa.String(length=150), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
            sa.Column('camera_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('microphone_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('viewer_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('gifts_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=False),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['host_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
    else:
        live_columns = [
            sa.Column('title', sa.String(length=150), nullable=False, server_default='Live Stream'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
            sa.Column('camera_enabled', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('microphone_enabled', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('viewer_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('gifts_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.Column('started_at', sa.DateTime(), nullable=True),
            sa.Column('ended_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        ]
        for column in live_columns:
            safe_add_column(conn, 'live_streams', column)

    safe_create_index(conn, 'ix_live_streams_host_id', 'live_streams', ['host_id'])
    safe_create_index(conn, 'idx_live_status_created', 'live_streams', ['status', 'created_at'])
    safe_create_index(conn, 'idx_live_host_created', 'live_streams', ['host_id', 'created_at'])

    if not _has_table(conn, 'live_chat_messages'):
        op.create_table(
            'live_chat_messages',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('live_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['live_id'], ['live_streams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
    safe_create_index(conn, 'ix_live_chat_messages_live_id', 'live_chat_messages', ['live_id'])
    safe_create_index(conn, 'ix_live_chat_messages_user_id', 'live_chat_messages', ['user_id'])

    if not _has_table(conn, 'live_viewers'):
        op.create_table(
            'live_viewers',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('live_id', sa.String(), nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('joined_at', sa.DateTime(), nullable=False),
            sa.Column('left_at', sa.DateTime(), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
            sa.ForeignKeyConstraint(['live_id'], ['live_streams.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('live_id', 'user_id', name='unique_live_viewer'),
        )
    safe_create_index(conn, 'ix_live_viewers_live_id', 'live_viewers', ['live_id'])
    safe_create_index(conn, 'ix_live_viewers_user_id', 'live_viewers', ['user_id'])

    if not _has_table(conn, 'audit_logs'):
        op.create_table(
            'audit_logs',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('admin_id', sa.String(), nullable=True),
            sa.Column('action', sa.String(length=100), nullable=False),
            sa.Column('target_type', sa.String(length=50), nullable=True),
            sa.Column('target_id', sa.String(), nullable=True),
            sa.Column('reason', sa.Text(), nullable=True),
            sa.Column('details', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )


def downgrade():
    conn = op.get_bind()

    safe_drop_index(conn, 'ix_live_viewers_user_id', 'live_viewers')
    safe_drop_index(conn, 'ix_live_viewers_live_id', 'live_viewers')
    if _has_table(conn, 'live_viewers'):
        op.drop_table('live_viewers')

    safe_drop_index(conn, 'ix_live_chat_messages_user_id', 'live_chat_messages')
    safe_drop_index(conn, 'ix_live_chat_messages_live_id', 'live_chat_messages')
    if _has_table(conn, 'live_chat_messages'):
        op.drop_table('live_chat_messages')

    safe_drop_index(conn, 'idx_live_host_created', 'live_streams')
    safe_drop_index(conn, 'idx_live_status_created', 'live_streams')
    safe_drop_index(conn, 'ix_live_streams_host_id', 'live_streams')

    if _has_table(conn, 'audit_logs'):
        op.drop_table('audit_logs')

    # Keep profiles.profile_picture/cover_photo and common soft-delete columns on
    # downgrade because earlier migrations/model-created databases may already
    # depend on them. Only drop live-specific tables created by this revision.
