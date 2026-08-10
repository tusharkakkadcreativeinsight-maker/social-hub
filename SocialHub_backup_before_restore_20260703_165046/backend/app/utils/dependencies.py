from fastapi import Depends, HTTPException, status, Header, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
from datetime import datetime
from io import BytesIO


from ..database import get_db
from ..models.models import User, UserRole
from .security import verify_token
from ..config import settings

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the currently authenticated user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    payload = verify_token(token, "access")

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User for token no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been banned",
        )

    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if the current user is an admin."""
    if current_user.role not in [UserRole.ADMIN.value, "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def get_moderator_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if the current user is an admin or moderator."""
    if current_user.role not in [UserRole.ADMIN.value, UserRole.MODERATOR.value, "admin", "moderator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or moderator access required",
        )
    return current_user


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None."""
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token, "access")
    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or user.is_banned:
        return None

    return user


def validate_image_file(file: UploadFile) -> bool:
    """Validate uploaded image file."""
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        return False

    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        return False

    # Enforce size limit
    try:
        if hasattr(file, 'size') and file.size is not None and file.size > settings.MAX_IMAGE_SIZE:
            return False
    except Exception:
        pass

    return True


async def validate_image_content(file: UploadFile) -> bool:
    """Verify image bytes with Pillow without consuming the upload permanently."""
    if not validate_image_file(file):
        return False
    try:
        from PIL import Image
        await file.seek(0)
        content = await file.read()
        await file.seek(0)
        with Image.open(BytesIO(content)) as img:
            img.verify()
        return True
    except Exception:
        try:
            await file.seek(0)
        except Exception:
            pass
        return False


def validate_video_file(file: UploadFile) -> bool:
    """Validate uploaded video file."""
    allowed_types = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"]
    if file.content_type not in allowed_types:
        return False

    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in [".mp4", ".mov", ".avi", ".webm"]:
        return False

    # Enforce size limit
    try:
        if hasattr(file, 'size') and file.size is not None and file.size > settings.MAX_VIDEO_SIZE:
            return False
    except Exception:
        pass

    return True


def validate_audio_file(file: UploadFile) -> bool:
    """Validate uploaded audio file for voice messages."""
    allowed_types = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/webm"]
    if file.content_type and file.content_type not in allowed_types:
        return False

    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in [".mp3", ".wav", ".ogg", ".m4a", ".webm"]:
        return False

    return True


def validate_upload_size(file: UploadFile, max_size: int) -> bool:
    """Validate UploadFile size when Starlette exposes it without consuming the stream."""
    try:
        return not (hasattr(file, "size") and file.size is not None and file.size > max_size)
    except Exception:
        return True


def safe_delete_upload_file(file_path: str) -> bool:
    """Delete a stored upload only if it resolves inside settings.UPLOAD_DIR."""
    if not file_path or file_path.startswith(("http://", "https://", "default")):
        return False
    base_dir = os.path.abspath(settings.UPLOAD_DIR)
    candidate = os.path.abspath(os.path.join(base_dir, file_path.replace("/", os.sep)))
    try:
        if os.path.commonpath([base_dir, candidate]) != base_dir:
            return False
        if os.path.isfile(candidate):
            os.remove(candidate)
            return True
    except Exception:
        return False
    return False


def _validate_upload_destination(upload_dir: str, subdir: str = "") -> str:
    base_upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    requested_dir = os.path.abspath(upload_dir or base_upload_dir)
    save_dir = os.path.abspath(os.path.join(requested_dir, subdir) if subdir else requested_dir)
    if os.path.commonpath([base_upload_dir, save_dir]) != base_upload_dir:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload destination")
    return save_dir


async def save_upload_file(upload_dir: str, file: UploadFile, subdir: str = "") -> str:
    """Save an uploaded file and return a clean relative uploads path.

    New code should call this with settings.UPLOAD_DIR and one of the shared
    subfolders (profiles, covers, posts, reels, stories, chat_files,
    marketplace, original_media/<user_id>). For backward compatibility, callers
    that pass an already nested upload directory are normalized back to a path
    relative to settings.UPLOAD_DIR, avoiding double folders in stored DB paths.
    """
    base_upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    save_dir = _validate_upload_destination(upload_dir, subdir)
    os.makedirs(save_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".jpg"
    if ext.lstrip(".").lower() not in settings.ALLOWED_EXTENSIONS and subdir != "chat_files":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File extension is not allowed")
    if ext.lower() == ".svg":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SVG uploads are not allowed")
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(save_dir, filename)

    content = await file.read()
    max_size = settings.MAX_VIDEO_SIZE if (file.content_type or "").startswith("video/") else settings.MAX_UPLOAD_SIZE
    if len(content) > max_size:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Uploaded file is too large")
    if (file.content_type or "").startswith("image/"):
        try:
            from PIL import Image
            with Image.open(BytesIO(content)) as img:
                img.verify()
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or corrupted image file")
    with open(filepath, "wb") as f:
        f.write(content)

    # Calculate relative path from base upload directory so frontend can access it.
    try:
        relative_path = os.path.relpath(save_dir, base_upload_dir)
        if relative_path == ".":
            return filename
        return os.path.join(relative_path, filename).replace("\\", "/")
    except ValueError:
        # Fallback when paths are on different drives
        if subdir:
            return os.path.join(subdir, filename).replace("\\", "/")
        # Extract the subfolder name from the upload_dir path
        folder_name = os.path.basename(upload_dir)
        return os.path.join(folder_name, filename).replace("\\", "/")


def create_pagination_metadata(total: int, page: int, page_size: int) -> dict:
    """Create pagination metadata."""
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


def get_pagination_params(page: int = 1, page_size: int = 10) -> tuple:
    """Get pagination offset and limit."""
    return (page - 1) * page_size, page_size