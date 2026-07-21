"""Add new features: verification, collections, analytics, wallet, highlights, hashtags, chat, search, reports

Revision ID: 0002_add_new_features
Revises: 0001_initial_socialhub_schema
Create Date: 2026-07-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text
from sqlalchemy.exc import OperationalError

revision = '0002_add_new_features'
down_revision = '0001_initial_socialhub_schema'
branch_labels = None
depends_on = None


def safe_add_column(table, column):
    """Add column only if it doesn't exist (handles SQLite duplicate column errors)."""
    try:
        op.add_column(table, column)
    except OperationalError as e:
        if 'duplicate column name' not in str(e).lower():
            raise


def safe_create_table(table_name, *args, **kwargs):
    """Create table only if it doesn't exist."""
    try:
        op.create_table(table_name, *args, **kwargs)
    except OperationalError as e:
        if 'already exists' not in str(e).lower():
            raise


def upgrade():
    # Enable UUID extension if using PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS uuid-ossp"))
    
    # ========== USERS TABLE UPDATES ==========
    safe_add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='0'))
    safe_add_column('users', sa.Column('account_type', sa.String(20), nullable=False, server_default='public'))
    safe_add_column('users', sa.Column('badge', sa.String(50), nullable=True))
    safe_add_column('users', sa.Column('two_factor_secret', sa.String(255), nullable=True))
    safe_add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='0'))
    
    # ========== MESSAGES TABLE UPDATES ==========
    safe_add_column('messages', sa.Column('receiver_id', sa.String(), nullable=True))
    safe_add_column('messages', sa.Column('message_text', sa.Text(), nullable=True))
    safe_add_column('messages', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    safe_add_column('messages', sa.Column('deleted_for_all', sa.Boolean(), nullable=False, server_default='0'))
    safe_add_column('messages', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # ========== REELS TABLE UPDATES ==========
    safe_add_column('reels', sa.Column('edit_metadata', sa.Text(), nullable=True))
    safe_add_column('reels', sa.Column('trim_start', sa.Float(), nullable=True))
    safe_add_column('reels', sa.Column('trim_end', sa.Float(), nullable=True))
    safe_add_column('reels', sa.Column('text_overlay', sa.String(255), nullable=True))
    safe_add_column('reels', sa.Column('filter_name', sa.String(100), nullable=True))
    safe_add_column('reels', sa.Column('music_name', sa.String(150), nullable=True))
    safe_add_column('reels', sa.Column('audio_name', sa.String(150), nullable=True))
    safe_add_column('reels', sa.Column('location', sa.String(255), nullable=True))
    safe_add_column('reels', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='0'))
    
    # ========== STORIES TABLE UPDATES ==========
    safe_add_column('stories', sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='0'))
    
    # ========== REEL_COMMENTS TABLE UPDATES ==========
    safe_add_column('reel_comments', sa.Column('parent_id', sa.String(), nullable=True))
    safe_add_column('reel_comments', sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'))
    
    # ========== SCHEDULED_POSTS TABLE UPDATES ==========
    safe_add_column('scheduled_posts', sa.Column('content_type', sa.String(20), nullable=False, server_default='post'))
    safe_add_column('scheduled_posts', sa.Column('platform', sa.String(20), nullable=False, server_default='socialhub'))
    safe_add_column('scheduled_posts', sa.Column('published_at', sa.DateTime(), nullable=True))
    
    # ========== MARKETPLACE_PRODUCTS TABLE UPDATES ==========
    safe_add_column('marketplace_products', sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='0'))
    safe_add_column('marketplace_products', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # ========== COLLABORATION_OFFERS TABLE UPDATES ==========
    safe_add_column('collaboration_offers', sa.Column('status', sa.String(20), nullable=False, server_default='open'))
    safe_add_column('collaboration_offers', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # ========== NEW TABLES ==========
    
    # Verification Requests
    safe_create_table('verification_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('document_url', sa.String(500), nullable=True),
        sa.Column('category', sa.String(50), nullable=False, server_default='creator'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='unique_verification_request_user')
    )
    op.create_index('idx_verification_status', 'verification_requests', ['status'], unique=False)
    
    # Saved Collections
    safe_create_table('saved_collections',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('cover_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='unique_collection_name')
    )
    op.create_index('idx_saved_collection_user', 'saved_collections', ['user_id'], unique=False)
    
    # Collection Items
    safe_create_table('collection_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('collection_id', sa.String(), nullable=False),
        sa.Column('post_id', sa.String(), nullable=True),
        sa.Column('reel_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['saved_collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reel_id'], ['reels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_id', 'post_id', name='unique_collection_post'),
        sa.UniqueConstraint('collection_id', 'reel_id', name='unique_collection_reel')
    )
    op.create_index('idx_collection_item_collection', 'collection_items', ['collection_id'], unique=False)
    
    # Profile Visits
    safe_create_table('profile_visits',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('visited_user_id', sa.String(), nullable=False),
        sa.Column('visitor_id', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('country', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['visited_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['visitor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_profile_visit_visited', 'profile_visits', ['visited_user_id', 'created_at'], unique=False)
    op.create_index('idx_profile_visit_visitor', 'profile_visits', ['visitor_id', 'created_at'], unique=False)
    
    # Creator Wallet
    safe_create_table('creator_wallets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('balance', sa.Float(), nullable=False, server_default='0'),
        sa.Column('total_earned', sa.Float(), nullable=False, server_default='0'),
        sa.Column('total_withdrawn', sa.Float(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='unique_creator_wallet_user')
    )
    op.create_index('idx_creator_wallet_user', 'creator_wallets', ['user_id'], unique=True)
    
    # Earning Records
    safe_create_table('earning_records',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('source_id', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_earning_user', 'earning_records', ['user_id', 'created_at'], unique=False)
    
    # Payout Requests
    safe_create_table('payout_requests',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('payment_method', sa.String(50), nullable=False, server_default='bank_transfer'),
        sa.Column('account_details', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('processed_by', sa.String(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('admin_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_payout_user', 'payout_requests', ['user_id', 'created_at'], unique=False)
    
    # Recent Searches
    safe_create_table('recent_searches',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('search_type', sa.String(20), nullable=False),
        sa.Column('query', sa.String(255), nullable=False),
        sa.Column('target_user_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_recent_search_user', 'recent_searches', ['user_id', 'created_at'], unique=False)
    
    # Hashtag Trends
    safe_create_table('hashtag_trends',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('hashtag', sa.String(100), nullable=False),
        sa.Column('trend_score', sa.Float(), nullable=False, server_default='0'),
        sa.Column('post_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_likes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_comments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_shares', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_calculated', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('hashtag', name='unique_hashtag_trend')
    )
    op.create_index('idx_hashtag_trend_score', 'hashtag_trends', ['hashtag', 'trend_score'], unique=False)
    
    # User Online Status
    safe_create_table('user_online_status',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('is_online', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('last_seen', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='unique_user_online_status')
    )
    op.create_index('idx_user_online_status_user', 'user_online_status', ['user_id'], unique=True)
    
    # Deleted Messages
    safe_create_table('deleted_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'message_id', name='unique_deleted_message')
    )
    op.create_index('idx_deleted_message_user', 'deleted_messages', ['user_id'], unique=False)


def downgrade():
    # Drop new tables in reverse order
    op.drop_table('deleted_messages')
    op.drop_table('user_online_status')
    op.drop_table('hashtag_trends')
    op.drop_table('recent_searches')
    op.drop_table('payout_requests')
    op.drop_table('earning_records')
    op.drop_table('creator_wallets')
    op.drop_table('profile_visits')
    op.drop_table('collection_items')
    op.drop_table('saved_collections')
    op.drop_table('verification_requests')
    
    # Remove columns from existing tables
    with op.batch_alter_table('users') as batch:
        batch.drop_column('badge')
        batch.drop_column('account_type')
        batch.drop_column('is_verified')
        batch.drop_column('two_factor_enabled')
        batch.drop_column('two_factor_secret')
    
    with op.batch_alter_table('messages') as batch:
        batch.drop_column('updated_at')
        batch.drop_column('deleted_for_all')
        batch.drop_column('is_deleted')
        batch.drop_column('message_text')
        batch.drop_column('receiver_id')
    
    with op.batch_alter_table('reels') as batch:
        batch.drop_column('location')
        batch.drop_column('audio_name')
        batch.drop_column('music_name')
        batch.drop_column('filter_name')
        batch.drop_column('text_overlay')
        batch.drop_column('trim_end')
        batch.drop_column('trim_start')
        batch.drop_column('edit_metadata')
        batch.drop_column('is_demo')
    
    with op.batch_alter_table('stories') as batch:
        batch.drop_column('is_archived')
    
    with op.batch_alter_table('reel_comments') as batch:
        batch.drop_column('likes_count')
        batch.drop_column('parent_id')
    
    with op.batch_alter_table('scheduled_posts') as batch:
        batch.drop_column('published_at')
        batch.drop_column('platform')
        batch.drop_column('content_type')
    
    with op.batch_alter_table('marketplace_products') as batch:
        batch.drop_column('updated_at')
        batch.drop_column('is_deleted')
    
    with op.batch_alter_table('collaboration_offers') as batch:
        batch.drop_column('updated_at')
        batch.drop_column('status')