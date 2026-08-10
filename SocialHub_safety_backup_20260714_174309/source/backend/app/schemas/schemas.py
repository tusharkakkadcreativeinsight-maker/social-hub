from pydantic import BaseModel as PydanticBaseModel, EmailStr, Field, field_validator, field_serializer, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime
import re
from app.utils.time import isoformat_utc_z, to_utc_naive, utcnow_naive


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(json_encoders={datetime: isoformat_utc_z})

    @field_serializer('*', when_used='json', check_fields=False)
    def serialize_datetime_fields(self, value):
        if isinstance(value, datetime):
            return isoformat_utc_z(value)
        return value


# ==================== AUTH SCHEMAS ====================
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    full_name: Optional[str] = Field(None, max_length=100)

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must contain only letters, numbers, and underscores')
        return v.lower()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class TwoFactorSetup(BaseModel):
    secret: str
    qr_code_url: str


class TwoFactorVerifyRequest(BaseModel):
    code: str
    temp_token: Optional[str] = None


# ==================== USER SCHEMAS ====================
class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    is_active: bool
    is_verified: bool
    is_email_verified: bool
    account_type: str
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    badge: Optional[str] = None
    profile_picture: Optional[str] = None
    cover_photo: Optional[str] = None

    @field_validator('profile_picture', 'cover_photo', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v == 'undefined' or v == 'null':
            return None
        return v

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    email: str
    bio: Optional[str] = None
    profile_picture: Optional[str] = None
    cover_photo: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    account_type: str
    is_verified: bool
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    reels_count: int = 0
    created_at: datetime
    badge: Optional[str] = None
    social_links: List['SocialLinkResponse'] = []

    model_config = ConfigDict(from_attributes=True)


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = None
    location: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = Field(None, max_length=20)
    account_type: Optional[str] = None


class UserSearchResult(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_verified: bool
    followers_count: int = 0
    badge: Optional[str] = None

    @field_validator('profile_picture', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        if v == '' or v == 'undefined' or v == 'null':
            return None
        return v

    model_config = ConfigDict(from_attributes=True)


class SocialLinkCreate(BaseModel):
    platform: str = Field(..., max_length=50)
    url: str = Field(..., max_length=500)


class SocialLinkResponse(BaseModel):
    id: str
    platform: str
    url: str

    model_config = ConfigDict(from_attributes=True)


# ==================== POST SCHEMAS ====================
class PostImageResponse(BaseModel):
    id: str
    image_url: str
    is_video: bool
    video_url: Optional[str] = None
    order: int

    model_config = ConfigDict(from_attributes=True)


class PostCreate(BaseModel):
    content: Optional[str] = Field(None, max_length=5000)
    hashtags: Optional[List[str]] = None
    tagged_user_ids: Optional[List[str]] = None
    scheduled_time: Optional[datetime] = None


class PostUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=5000)
    hashtags: Optional[List[str]] = None
    tagged_user_ids: Optional[List[str]] = None


class PollCreate(BaseModel):
    question: str = Field(..., max_length=500)
    options: List[str] = Field(..., min_length=2, max_length=6)
    expires_hours: Optional[int] = Field(None, ge=1, le=168)


class PollResponse(BaseModel):
    id: str
    question: str
    expires_at: Optional[datetime] = None
    options: List['PollOptionResponse'] = []
    total_votes: int = 0
    user_vote: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PollOptionResponse(BaseModel):
    id: str
    text: str
    votes_count: int
    percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class PollVoteRequest(BaseModel):
    option_id: str


class PostResponse(BaseModel):
    id: str
    user_id: str
    content: Optional[str] = None
    is_scheduled: bool
    scheduled_time: Optional[datetime] = None
    is_published: bool
    hashtags: Optional[List[str]] = None
    post_type: str = 'normal'
    repost_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    images: List[PostImageResponse] = []
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    author: Optional[UserSearchResult] = None
    is_liked: bool = False
    is_saved: bool = False
    poll: Optional[PollResponse] = None
    repost: Optional['PostResponse'] = None

    model_config = ConfigDict(from_attributes=True)


class PostFeedResponse(BaseModel):
    posts: List[PostResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


# ==================== BOOKMARK SCHEMAS ====================
class BookmarkResponse(BaseModel):
    id: str
    post_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== SHARE SCHEMAS ====================
class ShareResponse(BaseModel):
    id: str
    post_id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepostRequest(BaseModel):
    content: Optional[str] = Field(None, max_length=5000)


# ==================== LIKE SCHEMAS ====================
class LikeRequest(BaseModel):
    reaction: str = "like"


class LikeResponse(BaseModel):
    id: str
    user_id: str
    post_id: str
    reaction: str
    created_at: datetime
    user: Optional[UserSearchResult] = None

    model_config = ConfigDict(from_attributes=True)


# ==================== COMMENT SCHEMAS ====================
class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[str] = None


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentReactionRequest(BaseModel):
    reaction: str = "like"


class CommentResponse(BaseModel):
    id: str
    post_id: str
    user_id: str
    parent_id: Optional[str] = None
    content: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    author: Optional[UserSearchResult] = None
    replies: List['CommentResponse'] = []
    reactions_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# ==================== FOLLOWER SCHEMAS ====================
class FollowResponse(BaseModel):
    id: str
    follower_id: str
    following_id: str
    is_pending: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FollowListResponse(BaseModel):
    users: List[UserSearchResult]
    total: int


# ==================== STORY SCHEMAS ====================
class StoryResponse(BaseModel):
    id: str
    user_id: str
    media_url: str
    media_type: str
    caption: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    user: Optional[UserSearchResult] = None
    is_expired: bool = False
    viewers_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class StoryReactionRequest(BaseModel):
    reaction: str = "like"


class StoryHighlightCreate(BaseModel):
    story_id: str
    title: str = Field(..., max_length=100)
    cover_url: Optional[str] = None


class StoryHighlightResponse(BaseModel):
    id: str
    user_id: str
    story_id: str
    title: str
    cover_url: Optional[str] = None
    created_at: datetime
    story: Optional[StoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class StoryViewerResponse(BaseModel):
    user: UserSearchResult
    viewed_at: datetime


# ==================== REEL SCHEMAS ====================
class ReelCreate(BaseModel):
    caption: Optional[str] = Field(None, max_length=2000)
    hashtags: Optional[List[str]] = None


class ReelResponse(BaseModel):
    id: str
    user_id: str
    video_url: str
    thumbnail_url: Optional[str] = None
    cover_image: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    location: Optional[str] = None
    music_id: Optional[str] = None
    music_name: Optional[str] = None
    music_artist: Optional[str] = None
    visibility: str = "public"
    views_count: int
    shares_count: int = 0
    created_at: datetime
    likes_count: int = 0
    comments_count: int = 0
    user: Optional[UserSearchResult] = None
    is_liked: bool = False
    is_saved: bool = False

    model_config = ConfigDict(from_attributes=True)


class ReelCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class MusicResponse(BaseModel):
    id: str
    title: str
    artist: Optional[str] = None
    audio_path: str
    duration: Optional[float] = None
    category: Optional[str] = None
    is_trending: bool = False
    use_count: int = 0
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReelMusicUpdate(BaseModel):
    music_id: str


# ==================== MESSAGE SCHEMAS ====================
class MessageResponse(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    receiver_id: Optional[str] = None
    content: Optional[str] = None
    message_text: Optional[str] = None
    message_type: str
    file_url: Optional[str] = None
    is_read: bool
    is_deleted: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    sender: Optional[UserSearchResult] = None
    reactions: List['MessageReactionResponse'] = []

    model_config = ConfigDict(from_attributes=True)


class MessageReactionResponse(BaseModel):
    id: str
    user_id: str
    reaction: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageReactionRequest(BaseModel):
    reaction: str = "like"


class ChatResponse(BaseModel):
    id: str
    name: Optional[str] = None
    is_group: bool
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message: Optional[MessageResponse] = None
    participants: List[UserSearchResult] = []
    unread_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    content: Optional[str] = None
    message_text: Optional[str] = None
    receiver_id: Optional[str] = None
    message_type: str = "text"


class CreateChatRequest(BaseModel):
    participant_ids: List[str] = Field(..., min_length=1)
    name: Optional[str] = None
    is_group: bool = False


class DeleteMessageRequest(BaseModel):
    delete_for_all: bool = False


# ==================== NOTIFICATION SCHEMAS ====================
class NotificationResponse(BaseModel):
    id: str
    user_id: str
    actor_id: Optional[str] = None
    type: str
    message: str
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None
    is_read: bool
    created_at: datetime
    actor: Optional[UserSearchResult] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingResponse(BaseModel):
    likes: bool
    comments: bool
    follows: bool
    messages: bool
    mentions: bool
    story_reactions: bool
    email_notifications: bool
    push_notifications: bool

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingUpdate(BaseModel):
    likes: Optional[bool] = None
    comments: Optional[bool] = None
    follows: Optional[bool] = None
    messages: Optional[bool] = None
    mentions: Optional[bool] = None
    story_reactions: Optional[bool] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None


# ==================== REPORT SCHEMAS ====================
class CreateReportRequest(BaseModel):
    reported_user_id: Optional[str] = None
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    reason: str
    description: Optional[str] = Field(None, max_length=1000)


class ReportResponse(BaseModel):
    id: str
    reported_by: str
    reported_user_id: Optional[str] = None
    post_id: Optional[str] = None
    comment_id: Optional[str] = None
    reel_id: Optional[str] = None
    story_id: Optional[str] = None
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    reporter: Optional[UserSearchResult] = None
    reported_user: Optional[UserSearchResult] = None

    model_config = ConfigDict(from_attributes=True)


class UpdateReportStatus(BaseModel):
    status: str


# ==================== ADMIN SCHEMAS ====================
class AdminDashboard(BaseModel):
    total_users: int
    total_posts: int
    total_reports: int
    active_users_today: int
    new_users_today: int
    total_stories: int
    total_reels: int


class BanUserRequest(BaseModel):
    is_banned: bool
    reason: Optional[str] = None


class WarningCreateRequest(BaseModel):
    user_id: str
    warning_type: str
    reason: str


class WarningResponse(BaseModel):
    id: str
    user_id: str
    issued_by: Optional[str] = None
    warning_type: str
    reason: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    id: str
    admin_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AnalyticsResponse(BaseModel):
    date: str
    users_count: int
    posts_count: int
    likes_count: int
    comments_count: int


# ==================== SEARCH SCHEMAS ====================
class SearchResponse(BaseModel):
    users: List[UserSearchResult] = []
    posts: List[PostResponse] = []
    reels: List[ReelResponse] = []
    hashtags: List[str] = []


# ==================== TRENDING SCHEMAS ====================
class TrendingHashtagResponse(BaseModel):
    hashtag: str
    count: int

    model_config = ConfigDict(from_attributes=True)


# ==================== LOGIN HISTORY SCHEMAS ====================
class LoginHistoryResponse(BaseModel):
    id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_at: datetime
    is_successful: bool

    model_config = ConfigDict(from_attributes=True)


class ActiveSessionResponse(BaseModel):
    id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    last_activity: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==================== PAGINATION ====================
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


# ==================== INSTAGRAM GROWTH STUDIO SCHEMAS ====================
class InstagramStatusResponse(BaseModel):
    connected: bool
    username: Optional[str] = None
    account_id: Optional[str] = None
    account_type: Optional[str] = None
    media_count: Optional[int] = None
    message: str = ""


class InstagramMetric(BaseModel):
    label: str
    value: Any = 0
    icon: str = "chart-line"
    change: Optional[str] = None
    color: str = "var(--primary)"


class InstagramDashboardResponse(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    metrics: List[InstagramMetric] = []
    recent_posts: List[Dict[str, Any]] = []
    total_posts_imported: int = 0
    total_syncs: int = 0
    last_sync: Optional[str] = None
    local_posts_count: int = 0
    total_likes_received: int = 0
    total_comments_received: int = 0


class CaptionAssistantRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200)
    tone: str = "professional"
    keywords: Optional[str] = None
    emoji: bool = True


class CaptionSuggestion(BaseModel):
    text: str
    tone: str


class CaptionAssistantResponse(BaseModel):
    suggestions: List[CaptionSuggestion] = []


class ScheduledPostCreate(BaseModel):
    content: str = Field(..., max_length=5000)
    scheduled_at: datetime
    hashtags: Optional[List[str]] = None
    media_urls: Optional[List[str]] = None
    platform: str = "socialhub"

    @field_validator('scheduled_at')
    @classmethod
    def validate_scheduled_at(cls, v):
        scheduled_at = to_utc_naive(v)
        if scheduled_at <= utcnow_naive():
            raise ValueError('scheduled_at must be in the future')
        return scheduled_at


class ScheduledPostResponse(BaseModel):
    id: str
    user_id: str
    content: Optional[str] = None
    media_urls: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    scheduled_at: datetime
    status: str
    platform: str
    created_at: datetime
    published_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SyncLogResponse(BaseModel):
    id: str
    sync_type: str
    status: str
    posts_imported: int
    posts_updated: int
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
