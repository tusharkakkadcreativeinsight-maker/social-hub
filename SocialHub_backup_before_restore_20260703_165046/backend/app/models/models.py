import uuid
import json
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Text, ForeignKey,
    Enum as SAEnum, Float, BigInteger, Table, UniqueConstraint, Index
)
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship, backref
import enum
from ..database import Base


def generate_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.utcnow()


# ---------- CUSTOM JSON ARRAY TYPE ----------
class JSONArray(TypeDecorator):
    """Stores a Python list as a JSON string in the database."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return []


# ---------- ENUMS ----------
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"


class AccountType(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class ReactionType(str, enum.Enum):
    LIKE = "like"
    LOVE = "love"
    HAHA = "haha"
    WOW = "wow"
    SAD = "sad"
    ANGRY = "angry"
    FIRE = "fire"
    CLAP = "clap"


class NotificationType(str, enum.Enum):
    FOLLOW = "follow"
    LIKE = "like"
    COMMENT = "comment"
    MESSAGE = "message"
    FOLLOW_REQUEST = "follow_request"
    ACCEPT_FOLLOW = "accept_follow"
    TAG = "tag"
    STORY = "story"
    REEL = "reel"
    MENTION = "mention"
    SHARE = "share"


class ReportReason(str, enum.Enum):
    SPAM = "spam"
    HARASSMENT = "harassment"
    NUDITY = "nudity"
    HATE_SPEECH = "hate_speech"
    VIOLENCE = "violence"
    MISINFORMATION = "misinformation"
    OTHER = "other"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    REVIEWING = "reviewing"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    SYSTEM = "system"


class WarningType(str, enum.Enum):
    CONTENT_VIOLATION = "content_violation"
    SPAM = "spam"
    HARASSMENT = "harassment"
    FAKE_ACCOUNT = "fake_account"
    OTHER = "other"


# ---------- ASSOCIATION TABLES ----------
post_tags = Table(
    'post_tags', Base.metadata,
    Column('post_id', String, ForeignKey('posts.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
)

chat_participants = Table(
    'chat_participants', Base.metadata,
    Column('chat_id', String, ForeignKey('chats.id', ondelete='CASCADE'), primary_key=True),
    Column('user_id', String, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('joined_at', DateTime, default=utcnow)
)


# ---------- USER MODEL ----------
class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_banned = Column(Boolean, default=False, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    account_type = Column(String(20), default=AccountType.PUBLIC.value, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    verification_token = Column(String(255), nullable=True)
    two_factor_secret = Column(String(255), nullable=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    badge = Column(String(50), nullable=True)  # 'verified', 'popular', 'new', etc.

    # Relationships
    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    reels = relationship("Reel", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", foreign_keys="[Notification.user_id]", back_populates="user", cascade="all, delete-orphan")
    sent_notifications = relationship("Notification", foreign_keys="[Notification.actor_id]", back_populates="actor", cascade="all, delete-orphan")
    sent_messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="user", cascade="all, delete-orphan")
    post_shares = relationship("PostShare", back_populates="user", cascade="all, delete-orphan")

    # Follow relationships
    followers_rel = relationship(
        "Follower", foreign_keys="[Follower.following_id]",
        back_populates="following", cascade="all, delete-orphan"
    )
    following_rel = relationship(
        "Follower", foreign_keys="[Follower.follower_id]",
        back_populates="follower", cascade="all, delete-orphan"
    )

    # Reports
    reports_made = relationship("Report", foreign_keys="[Report.reported_by]", back_populates="reporter", cascade="all, delete-orphan")
    reports_received = relationship("Report", foreign_keys="[Report.reported_user_id]", back_populates="reported_user", cascade="all, delete-orphan")

    # Social links
    social_links = relationship("SocialLink", back_populates="user", cascade="all, delete-orphan")

    # Notifications settings
    notification_settings = relationship("NotificationSetting", uselist=False, back_populates="user", cascade="all, delete-orphan")

    # Login history
    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")

    # Active sessions
    active_sessions = relationship("ActiveSession", back_populates="user", cascade="all, delete-orphan")
    instagram_accounts = relationship("InstagramAccount", back_populates="user", cascade="all, delete-orphan")
    instagram_media = relationship("InstagramMedia", back_populates="user", cascade="all, delete-orphan")

    # Warnings
    warnings_received = relationship("Warning", foreign_keys="[Warning.user_id]", back_populates="user", cascade="all, delete-orphan")
    warnings_issued = relationship("Warning", foreign_keys="[Warning.issued_by]", back_populates="issuer", cascade="all, delete-orphan")

    @property
    def followers_count(self):
        return len(self.followers_rel) if self.followers_rel else 0

    @property
    def following_count(self):
        return len(self.following_rel) if self.following_rel else 0

    @property
    def posts_count(self):
        return len(self.posts) if self.posts else 0

    @property
    def profile_picture(self):
        return self.profile.profile_picture if self.profile else None

    @property
    def cover_photo(self):
        return self.profile.cover_photo if self.profile else None


# ---------- PROFILE MODEL ----------
class Profile(Base):
    __tablename__ = 'profiles'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    bio = Column(Text, nullable=True)
    profile_picture = Column(String(500), nullable=True, default='default_profile.png')
    cover_photo = Column(String(500), nullable=True, default='default_cover.jpg')
    website = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    gender = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="profile")


# ---------- SOCIAL LINK MODEL ----------
class SocialLink(Base):
    __tablename__ = 'social_links'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    platform = Column(String(50), nullable=False)  # 'twitter', 'instagram', 'linkedin', 'youtube', 'tiktok'
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="social_links")


# ---------- POST MODEL ----------
class Post(Base):
    __tablename__ = 'posts'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = Column(Text, nullable=True)
    is_scheduled = Column(Boolean, default=False, nullable=False)
    scheduled_time = Column(DateTime, nullable=True)
    is_published = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    hashtags = Column(JSONArray, nullable=True)
    post_type = Column(String(20), default='normal', nullable=False)  # 'normal', 'poll', 'repost'
    repost_id = Column(String, ForeignKey('posts.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    author = relationship("User", back_populates="posts")
    images = relationship("PostImage", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="post", cascade="all, delete-orphan")
    shares = relationship("PostShare", foreign_keys="[PostShare.post_id]", back_populates="post", cascade="all, delete-orphan")
    tagged_users = relationship("User", secondary=post_tags, lazy='dynamic')
    poll = relationship("Poll", uselist=False, back_populates="post", cascade="all, delete-orphan")
    repost = relationship("Post", remote_side=[id], backref="reposts")

    __table_args__ = (
        Index('idx_post_user_created', 'user_id', 'created_at'),
        Index('idx_post_published', 'is_published', 'is_deleted'),
    )

    @property
    def likes_count(self):
        return len(self.likes) if self.likes else 0

    @property
    def comments_count(self):
        return len(self.comments) if self.comments else 0

    @property
    def shares_count(self):
        return len(self.shares) if self.shares else 0


# ---------- POST IMAGE MODEL ----------
class PostImage(Base):
    __tablename__ = 'post_images'

    id = Column(String, primary_key=True, default=generate_uuid)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(String(500), nullable=False)
    is_video = Column(Boolean, default=False, nullable=False)
    video_url = Column(String(500), nullable=True)
    order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    post = relationship("Post", back_populates="images")


# ---------- BOOKMARK MODEL ----------
class Bookmark(Base):
    __tablename__ = 'bookmarks'
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='unique_user_bookmark'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="bookmarks")
    post = relationship("Post", back_populates="bookmarks")


# ---------- POST SHARE MODEL ----------
class PostShare(Base):
    __tablename__ = 'post_shares'
    __table_args__ = (
        Index('idx_share_post', 'post_id'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="post_shares")
    post = relationship("Post", foreign_keys=[post_id], back_populates="shares")


# ---------- POLL MODEL ----------
class Poll(Base):
    __tablename__ = 'polls'

    id = Column(String, primary_key=True, default=generate_uuid)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), unique=True, nullable=False)
    question = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    post = relationship("Post", back_populates="poll")
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")


# ---------- POLL OPTION MODEL ----------
class PollOption(Base):
    __tablename__ = 'poll_options'

    id = Column(String, primary_key=True, default=generate_uuid)
    poll_id = Column(String, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False)
    text = Column(String(255), nullable=False)
    votes_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    poll = relationship("Poll", back_populates="options")
    voters = relationship("PollVote", back_populates="option", cascade="all, delete-orphan")


# ---------- POLL VOTE MODEL ----------
class PollVote(Base):
    __tablename__ = 'poll_votes'
    __table_args__ = (
        UniqueConstraint('user_id', 'poll_id', name='unique_poll_vote'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    poll_id = Column(String, ForeignKey('polls.id', ondelete='CASCADE'), nullable=False)
    option_id = Column(String, ForeignKey('poll_options.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    option = relationship("PollOption", back_populates="voters")


# ---------- LIKE MODEL ----------
class Like(Base):
    __tablename__ = 'likes'
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    reaction = Column(String(20), default=ReactionType.LIKE.value, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")


# ---------- COMMENT MODEL ----------
class Comment(Base):
    __tablename__ = 'comments'

    id = Column(String, primary_key=True, default=generate_uuid)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(String, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    replies = relationship("Comment", backref=backref("parent", remote_side="Comment.id"), cascade="all, delete-orphan")
    reactions = relationship("CommentReaction", back_populates="comment", cascade="all, delete-orphan")


# ---------- COMMENT REACTION MODEL ----------
class CommentReaction(Base):
    __tablename__ = 'comment_reactions'
    __table_args__ = (
        UniqueConstraint('user_id', 'comment_id', name='unique_comment_reaction'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    comment_id = Column(String, ForeignKey('comments.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reaction = Column(String(20), default=ReactionType.LIKE.value, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    comment = relationship("Comment", back_populates="reactions")


# ---------- FOLLOWER MODEL ----------
class Follower(Base):
    __tablename__ = 'followers'
    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='unique_follow'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    follower_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    following_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    is_pending = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    follower = relationship("User", foreign_keys=[follower_id], back_populates="following_rel")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers_rel")


# ---------- STORY MODEL ----------
class Story(Base):
    __tablename__ = 'stories'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    media_url = Column(String(500), nullable=False)
    media_type = Column(String(20), nullable=False)
    caption = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="stories")
    reactions = relationship("StoryReaction", back_populates="story", cascade="all, delete-orphan")
    viewers = relationship("StoryView", back_populates="story", cascade="all, delete-orphan")
    highlight = relationship("StoryHighlight", back_populates="story", uselist=False)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ---------- STORY VIEW MODEL ----------
class StoryView(Base):
    __tablename__ = 'story_views'
    __table_args__ = (
        UniqueConstraint('user_id', 'story_id', name='unique_story_view'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    story_id = Column(String, ForeignKey('stories.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    viewed_at = Column(DateTime, default=utcnow)

    story = relationship("Story", back_populates="viewers")


# ---------- STORY HIGHLIGHT MODEL ----------
class StoryHighlight(Base):
    __tablename__ = 'story_highlights'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    story_id = Column(String, ForeignKey('stories.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(100), nullable=False)
    cover_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    story = relationship("Story", back_populates="highlight")


# ---------- STORY REACTION MODEL ----------
class StoryReaction(Base):
    __tablename__ = 'story_reactions'
    __table_args__ = (
        UniqueConstraint('user_id', 'story_id', name='unique_story_reaction'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    story_id = Column(String, ForeignKey('stories.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reaction = Column(String(20), default=ReactionType.LIKE.value, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    story = relationship("Story", back_populates="reactions")


# ---------- REEL MODEL ----------
class Reel(Base):
    __tablename__ = 'reels'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(JSONArray, nullable=True)
    views_count = Column(Integer, default=0, nullable=False)
    shares_count = Column(Integer, default=0, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)
    edit_metadata = Column(JSONArray, nullable=True)
    trim_start = Column(Float, nullable=True)
    trim_end = Column(Float, nullable=True)
    text_overlay = Column(String(255), nullable=True)
    filter_name = Column(String(100), nullable=True)
    music_name = Column(String(150), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="reels")
    likes = relationship("ReelLike", back_populates="reel", cascade="all, delete-orphan")
    comments = relationship("ReelComment", back_populates="reel", cascade="all, delete-orphan")
    saves = relationship("ReelSave", back_populates="reel", cascade="all, delete-orphan")

    @property
    def likes_count(self):
        return len(self.likes) if self.likes else 0

    @property
    def comments_count(self):
        return len(self.comments) if self.comments else 0


# ---------- REEL LIKE MODEL ----------
class ReelLike(Base):
    __tablename__ = 'reel_likes'
    __table_args__ = (
        UniqueConstraint('user_id', 'reel_id', name='unique_reel_like'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    reel_id = Column(String, ForeignKey('reels.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    reel = relationship("Reel", back_populates="likes")


# ---------- REEL SAVE MODEL ----------
class ReelSave(Base):
    __tablename__ = 'reel_saves'
    __table_args__ = (
        UniqueConstraint('user_id', 'reel_id', name='unique_reel_save'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    reel_id = Column(String, ForeignKey('reels.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    reel = relationship("Reel", back_populates="saves")


# ---------- REEL COMMENT MODEL ----------
class ReelComment(Base):
    __tablename__ = 'reel_comments'

    id = Column(String, primary_key=True, default=generate_uuid)
    reel_id = Column(String, ForeignKey('reels.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    reel = relationship("Reel", back_populates="comments")


# ---------- CHAT MODEL ----------
class Chat(Base):
    __tablename__ = 'chats'

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=True)
    is_group = Column(Boolean, default=False, nullable=False)
    created_by = Column(String, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan", order_by="Message.created_at")
    participants = relationship("User", secondary=chat_participants, lazy='dynamic')


# ---------- MESSAGE MODEL ----------
class Message(Base):
    __tablename__ = 'messages'

    id = Column(String, primary_key=True, default=generate_uuid)
    chat_id = Column(String, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=True)
    message_type = Column(String(20), default=MessageType.TEXT.value, nullable=False)
    file_url = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_for_all = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages")
    reactions = relationship("MessageReaction", back_populates="message", cascade="all, delete-orphan")


# ---------- MESSAGE REACTION MODEL ----------
class MessageReaction(Base):
    __tablename__ = 'message_reactions'
    __table_args__ = (
        UniqueConstraint('user_id', 'message_id', name='unique_message_reaction'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reaction = Column(String(20), default=ReactionType.LIKE.value, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    message = relationship("Message", back_populates="reactions")


# ---------- NOTIFICATION MODEL ----------
class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    actor_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    type = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    reference_id = Column(String, nullable=True)
    reference_type = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor = relationship("User", foreign_keys=[actor_id], back_populates="sent_notifications")


# ---------- NOTIFICATION SETTING MODEL ----------
class NotificationSetting(Base):
    __tablename__ = 'notification_settings'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    likes = Column(Boolean, default=True, nullable=False)
    comments = Column(Boolean, default=True, nullable=False)
    follows = Column(Boolean, default=True, nullable=False)
    messages = Column(Boolean, default=True, nullable=False)
    mentions = Column(Boolean, default=True, nullable=False)
    story_reactions = Column(Boolean, default=True, nullable=False)
    email_notifications = Column(Boolean, default=False, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="notification_settings")


# ---------- REPORT MODEL ----------
class Report(Base):
    __tablename__ = 'reports'

    id = Column(String, primary_key=True, default=generate_uuid)
    reported_by = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    reported_user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=True)
    comment_id = Column(String, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True)
    reason = Column(String(30), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=ReportStatus.PENDING.value, nullable=False)
    resolved_by = Column(String, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    reporter = relationship("User", foreign_keys=[reported_by], back_populates="reports_made")
    reported_user = relationship("User", foreign_keys=[reported_user_id], back_populates="reports_received")


# ---------- WARNING MODEL ----------
class Warning(Base):
    __tablename__ = 'warnings'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    issued_by = Column(String, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    warning_type = Column(String(30), nullable=False)
    reason = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", foreign_keys=[user_id], back_populates="warnings_received")
    issuer = relationship("User", foreign_keys=[issued_by], back_populates="warnings_issued")


# ---------- LOGIN HISTORY MODEL ----------
class LoginHistory(Base):
    __tablename__ = 'login_history'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    login_at = Column(DateTime, default=utcnow)
    is_successful = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="login_history")


# ---------- ACTIVE SESSION MODEL ----------
class ActiveSession(Base):
    __tablename__ = 'active_sessions'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_jti = Column(String(255), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(String(255), nullable=True)
    last_activity = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", back_populates="active_sessions")


# ---------- AUDIT LOG MODEL ----------
class AuditLog(Base):
    __tablename__ = 'audit_logs'

    id = Column(String, primary_key=True, default=generate_uuid)
    admin_id = Column(String, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)  # 'user', 'post', 'report'
    target_id = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)


# ---------- TRENDING HASHTAG MODEL ----------
class TrendingHashtag(Base):
    __tablename__ = 'trending_hashtags'

    id = Column(String, primary_key=True, default=generate_uuid)
    hashtag = Column(String(100), nullable=False, unique=True, index=True)
    count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, default=utcnow)


# ---------- ROLE MODEL ----------
class Role(Base):
    __tablename__ = 'roles'

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSONArray, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


# ---------- BLOCKED USER MODEL ----------
class BlockedUser(Base):
    __tablename__ = 'blocked_users'
    __table_args__ = (
        UniqueConstraint('blocker_id', 'blocked_id', name='unique_block'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    blocker_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    blocked_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)

    blocker = relationship("User", foreign_keys=[blocker_id])
    blocked = relationship("User", foreign_keys=[blocked_id])


# ---------- HASHTAG MODEL ----------
class Hashtag(Base):
    __tablename__ = 'hashtags'

    id = Column(String, primary_key=True, default=generate_uuid)
    tag = Column(String(100), nullable=False, unique=True, index=True)
    post_count = Column(Integer, default=0, nullable=False)
    last_used = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)


# ---------- MENTION MODEL ----------
class Mention(Base):
    __tablename__ = 'mentions'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    post_id = Column(String, ForeignKey('posts.id', ondelete='CASCADE'), nullable=True, index=True)
    comment_id = Column(String, ForeignKey('comments.id', ondelete='CASCADE'), nullable=True, index=True)
    mentioned_by = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    user = relationship("User", foreign_keys=[user_id])
    mentioner = relationship("User", foreign_keys=[mentioned_by])
    post = relationship("Post", foreign_keys=[post_id])
    comment = relationship("Comment", foreign_keys=[comment_id])


# ---------- OFFICIAL INSTAGRAM GRAPH API MODELS ----------
class InstagramAccount(Base):
    __tablename__ = 'instagram_accounts'
    __table_args__ = (
        UniqueConstraint('user_id', 'instagram_user_id', name='unique_user_instagram_account'),
        Index('idx_instagram_account_user', 'user_id'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_user_id = Column(String(100), nullable=False)
    username = Column(String(150), nullable=False)
    profile_picture_url = Column(String(1000), nullable=True)
    account_type = Column(String(50), nullable=True)
    access_token_encrypted = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=True)
    connected_at = Column(DateTime, default=utcnow, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="instagram_accounts")
    media = relationship("InstagramMedia", back_populates="account", cascade="all, delete-orphan")
    import_logs = relationship("InstagramImportLog", back_populates="account", cascade="all, delete-orphan")


class InstagramMedia(Base):
    __tablename__ = 'instagram_media'
    __table_args__ = (
        UniqueConstraint('user_id', 'instagram_media_id', name='unique_user_instagram_media_real'),
        Index('idx_instagram_media_user_created', 'user_id', 'created_at'),
        Index('idx_instagram_media_account', 'instagram_account_id'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_account_id = Column(String, ForeignKey('instagram_accounts.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_media_id = Column(String(150), nullable=False)
    media_type = Column(String(30), nullable=False)
    media_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    caption = Column(Text, nullable=True)
    permalink = Column(String(1000), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    imported_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User", back_populates="instagram_media")
    account = relationship("InstagramAccount", back_populates="media")


class InstagramReel(Base):
    __tablename__ = 'instagram_reels'
    __table_args__ = (UniqueConstraint('user_id', 'instagram_media_id', name='unique_user_instagram_reel'),)

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_account_id = Column(String, ForeignKey('instagram_accounts.id', ondelete='CASCADE'), nullable=False)
    instagram_media_id = Column(String(150), nullable=False)
    media_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    caption = Column(Text, nullable=True)
    permalink = Column(String(1000), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    imported_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class InstagramImportLog(Base):
    __tablename__ = 'instagram_import_logs'
    __table_args__ = (Index('idx_instagram_import_log_user', 'user_id', 'created_at'),)

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_account_id = Column(String, ForeignKey('instagram_accounts.id', ondelete='SET NULL'), nullable=True)
    status = Column(String(20), default='started', nullable=False)
    action = Column(String(50), nullable=False)
    requested_count = Column(Integer, default=0, nullable=False)
    imported_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    account = relationship("InstagramAccount", back_populates="import_logs")


# ---------- INSTAGRAM SYNC LOG MODEL ----------
class InstagramSyncLog(Base):
    __tablename__ = 'instagram_sync_logs'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    sync_type = Column(String(50), nullable=False)  # 'profile', 'posts', 'media', 'full'
    status = Column(String(20), default='completed', nullable=False)  # 'in_progress', 'completed', 'failed'
    posts_imported = Column(Integer, default=0)
    posts_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utcnow)
    completed_at = Column(DateTime, nullable=True)


# ---------- INSTAGRAM IMPORTER MODELS ----------
class InstagramImport(Base):
    __tablename__ = 'instagram_imports'
    __table_args__ = (
        Index('idx_instagram_import_user', 'user_id', 'imported_at'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_username = Column(String(100), nullable=True)
    source_type = Column(String(20), nullable=False)  # 'api', 'json', 'demo'
    imported_at = Column(DateTime, default=utcnow, nullable=False)
    total_posts = Column(Integer, default=0, nullable=False)
    total_reels = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default='completed', nullable=False)

    user = relationship("User")


class ImportedInstagramMedia(Base):
    __tablename__ = 'imported_instagram_media'
    __table_args__ = (
        UniqueConstraint('user_id', 'instagram_media_id', name='unique_user_instagram_media'),
        Index('idx_imported_instagram_user_created', 'user_id', 'created_at'),
        Index('idx_imported_instagram_type', 'media_type'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    instagram_media_id = Column(String(150), nullable=False)
    media_type = Column(String(30), nullable=False)  # IMAGE / VIDEO / CAROUSEL_ALBUM / REEL
    caption = Column(Text, nullable=True)
    media_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    permalink = Column(String(1000), nullable=True)
    timestamp = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    local_file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User")


# ---------- SCHEDULED POST MODEL ----------
class ScheduledPost(Base):
    __tablename__ = 'scheduled_posts'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    content = Column(Text, nullable=True)
    media_urls = Column(JSONArray, nullable=True)
    hashtags = Column(JSONArray, nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'published', 'failed'
    content_type = Column(String(20), default='post', nullable=False)  # 'post', 'reel', 'story'
    platform = Column(String(20), default='socialhub', nullable=False)  # 'socialhub', 'instagram'
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    published_at = Column(DateTime, nullable=True)


# ---------- STORY INTERACTION MODEL ----------
class StoryPoll(Base):
    __tablename__ = 'story_polls'

    id = Column(String, primary_key=True, default=generate_uuid)
    story_id = Column(String, ForeignKey('stories.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    poll_type = Column(String(20), default='poll', nullable=False)  # poll, quiz, question
    question = Column(Text, nullable=False)
    options = Column(JSONArray, nullable=True)
    correct_option = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow)

    story = relationship("Story")
    user = relationship("User")
    votes = relationship("StoryPollVote", back_populates="poll", cascade="all, delete-orphan")


class StoryPollVote(Base):
    __tablename__ = 'story_poll_votes'
    __table_args__ = (
        UniqueConstraint('poll_id', 'user_id', name='unique_story_poll_vote'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    poll_id = Column(String, ForeignKey('story_polls.id', ondelete='CASCADE'), nullable=False, index=True)
    story_id = Column(String, ForeignKey('stories.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    poll = relationship("StoryPoll", back_populates="votes")
    user = relationship("User")


# ---------- MARKETPLACE MODEL ----------
class MarketplaceProduct(Base):
    __tablename__ = 'marketplace_products'

    id = Column(String, primary_key=True, default=generate_uuid)
    seller_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, default=0, nullable=False)
    category = Column(String(80), nullable=True)
    image_url = Column(String(500), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    seller = relationship("User")


# ---------- COLLABORATION MODEL ----------
class CollaborationOffer(Base):
    __tablename__ = 'collaboration_offers'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    budget = Column(String(80), nullable=True)
    category = Column(String(80), nullable=True)
    status = Column(String(20), default='open', nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User")
    applications = relationship("CollaborationApplication", back_populates="offer", cascade="all, delete-orphan")


class CollaborationApplication(Base):
    __tablename__ = 'collaboration_applications'
    __table_args__ = (
        UniqueConstraint('offer_id', 'user_id', name='unique_collab_application'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    offer_id = Column(String, ForeignKey('collaboration_offers.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    message = Column(Text, nullable=True)
    status = Column(String(20), default='pending', nullable=False)
    created_at = Column(DateTime, default=utcnow)

    offer = relationship("CollaborationOffer", back_populates="applications")
    user = relationship("User")


# ---------- DEVICE TOKEN MODEL (Push Notifications) ----------
class DeviceToken(Base):
    __tablename__ = 'device_tokens'

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(500), nullable=False)
    platform = Column(String(20), nullable=False)  # 'ios', 'android', 'web'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User")


# ---------- DEMO DATA BATCH MODEL ----------
class DemoDataBatch(Base):
    __tablename__ = 'demo_data_batches'
    __table_args__ = (
        Index('idx_demo_batch_created', 'created_at'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    batch_name = Column(String(100), nullable=False)
    users_count = Column(Integer, nullable=False)
    posts_count = Column(Integer, nullable=False)
    reels_count = Column(Integer, nullable=False)
    follow_edges_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)


# ---------- ORIGINAL MEDIA ASSET MODEL ----------
class OriginalMediaAsset(Base):
    __tablename__ = 'original_media_assets'
    __table_args__ = (
        Index('idx_original_media_user', 'user_id', 'created_at'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=False)
    media_type = Column(String(20), nullable=False)  # 'image', 'video'
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds for video
    is_used_in_post = Column(Boolean, default=False, nullable=False)
    is_used_in_reel = Column(Boolean, default=False, nullable=False)
    ownership_confirmed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User")


# ---------- MEDIA IMPORT LOG MODEL ----------
class MediaImportLog(Base):
    __tablename__ = 'media_import_logs'
    __table_args__ = (
        Index('idx_media_import_user', 'user_id', 'created_at'),
    )

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    asset_id = Column(String, ForeignKey('original_media_assets.id', ondelete='SET NULL'), nullable=True)
    action = Column(String(50), nullable=False)  # 'upload', 'create_post', 'create_reel'
    source = Column(String(50), nullable=False)  # 'upload', 'instagram_api', 'demo'
    status = Column(String(20), nullable=False)  # 'success', 'failed'
    error_message = Column(Text, nullable=True)
    extra_metadata = Column('metadata', JSONArray, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    user = relationship("User")
    asset = relationship("OriginalMediaAsset")


# ---------- INDEXES FOR PERFORMANCE ----------
# Additional indexes are defined in __table_args__ above for each model.


# ---------- INIT EXPORT ----------
# The __init__.py in this package imports these models.
