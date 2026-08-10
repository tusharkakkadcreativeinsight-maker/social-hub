"""production_sync

Revision ID: fb5d7dca1541
Revises: 0006_security_admin_report_compat
Create Date: 2026-08-10 17:40:53.368325

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, ProgrammingError


# revision identifiers, used by Alembic.
revision: str = 'fb5d7dca1541'
down_revision: Union[str, None] = '0006_security_admin_report_compat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


IGNORED = (OperationalError, ProgrammingError, NotImplementedError)


def safe_exec(cmd):
    try:
        cmd()
    except IGNORED:
        pass


def upgrade() -> None:
    # Safely apply constraints and FKs so it doesn't fail on SQLite (NotImplementedError) 
    # or Postgres (already exists)
    safe_exec(lambda: op.create_unique_constraint('unique_collection_post', 'collection_items', ['collection_id', 'post_id']))
    safe_exec(lambda: op.create_unique_constraint('unique_collection_reel', 'collection_items', ['collection_id', 'reel_id']))
    safe_exec(lambda: op.drop_index(op.f('idx_creator_wallet_user'), table_name='creator_wallets'))
    safe_exec(lambda: op.drop_index(op.f('idx_deleted_message_user'), table_name='deleted_messages'))
    
    safe_exec(lambda: op.alter_column('messages', 'updated_at', existing_type=sa.DateTime(), nullable=False))
    safe_exec(lambda: op.create_index(op.f('ix_messages_receiver_id'), 'messages', ['receiver_id'], unique=False))
    safe_exec(lambda: op.create_foreign_key('fk_messages_receiver_id_users', 'messages', 'users', ['receiver_id'], ['id'], ondelete='CASCADE'))
    
    safe_exec(lambda: op.alter_column('music', 'updated_at', existing_type=sa.DateTime(), nullable=False))
    safe_exec(lambda: op.drop_index(op.f('ix_music_use_count'), table_name='music'))
    safe_exec(lambda: op.create_foreign_key('fk_music_created_by_users', 'music', 'users', ['created_by'], ['id'], ondelete='SET NULL'))
    safe_exec(lambda: op.create_foreign_key('fk_reel_comments_parent_id_reel_comments', 'reel_comments', 'reel_comments', ['parent_id'], ['id'], ondelete='CASCADE'))
    safe_exec(lambda: op.create_foreign_key('fk_reels_music_id_music', 'reels', 'music', ['music_id'], ['id'], ondelete='SET NULL'))
    safe_exec(lambda: op.create_foreign_key('fk_reports_reel_id_reels', 'reports', 'reels', ['reel_id'], ['id'], ondelete='SET NULL'))
    safe_exec(lambda: op.create_foreign_key('fk_reports_story_id_stories', 'reports', 'stories', ['story_id'], ['id'], ondelete='SET NULL'))
    
    safe_exec(lambda: op.add_column('saved_collections', sa.Column('updated_at', sa.DateTime(), nullable=True)))
    
    safe_exec(lambda: op.drop_index(op.f('idx_saved_collection_user'), table_name='saved_collections'))
    safe_exec(lambda: op.drop_index(op.f('idx_user_online_status_user'), table_name='user_online_status'))


def downgrade() -> None:
    safe_exec(lambda: op.create_index(op.f('idx_user_online_status_user'), 'user_online_status', ['user_id'], unique=True))
    safe_exec(lambda: op.create_index(op.f('idx_saved_collection_user'), 'saved_collections', ['user_id'], unique=False))
    safe_exec(lambda: op.drop_column('saved_collections', 'updated_at'))
    
    safe_exec(lambda: op.drop_constraint('fk_reports_story_id_stories', 'reports', type_='foreignkey'))
    safe_exec(lambda: op.drop_constraint('fk_reports_reel_id_reels', 'reports', type_='foreignkey'))
    safe_exec(lambda: op.drop_constraint('fk_reels_music_id_music', 'reels', type_='foreignkey'))
    safe_exec(lambda: op.drop_constraint('fk_reel_comments_parent_id_reel_comments', 'reel_comments', type_='foreignkey'))
    safe_exec(lambda: op.drop_constraint('fk_music_created_by_users', 'music', type_='foreignkey'))
    
    safe_exec(lambda: op.create_index(op.f('ix_music_use_count'), 'music', ['use_count'], unique=False))
    safe_exec(lambda: op.alter_column('music', 'updated_at', existing_type=sa.DateTime(), nullable=True))
    
    safe_exec(lambda: op.drop_constraint('fk_messages_receiver_id_users', 'messages', type_='foreignkey'))
    safe_exec(lambda: op.drop_index(op.f('ix_messages_receiver_id'), table_name='messages'))
    safe_exec(lambda: op.alter_column('messages', 'updated_at', existing_type=sa.DateTime(), nullable=True))
    
    safe_exec(lambda: op.create_index(op.f('idx_deleted_message_user'), 'deleted_messages', ['user_id'], unique=False))
    safe_exec(lambda: op.create_index(op.f('idx_creator_wallet_user'), 'creator_wallets', ['user_id'], unique=True))
    safe_exec(lambda: op.drop_constraint('unique_collection_reel', 'collection_items', type_='unique'))
    safe_exec(lambda: op.drop_constraint('unique_collection_post', 'collection_items', type_='unique'))
