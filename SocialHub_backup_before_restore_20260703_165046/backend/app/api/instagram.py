from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models.models import InstagramAccount, InstagramImportLog, InstagramMedia, InstagramReel, Post, PostImage, Reel, User
from ..utils.dependencies import get_current_user
from ..utils.security import decrypt_secret, encrypt_secret

router = APIRouter(prefix="/api/instagram", tags=["Official Instagram Integration"])
GRAPH_BASE = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}"
OAUTH_DIALOG = f"https://www.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}/dialog/oauth"
SCOPES = "instagram_basic,pages_show_list,pages_read_engagement,business_management"


def require_config():
    if not settings.INSTAGRAM_CLIENT_ID or not settings.INSTAGRAM_CLIENT_SECRET:
        raise HTTPException(500, "Set INSTAGRAM_CLIENT_ID and INSTAGRAM_CLIENT_SECRET in .env")


def make_state(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "purpose": "instagram_oauth", "exp": datetime.utcnow() + timedelta(minutes=15)}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def read_state(state: str) -> str:
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(400, "Invalid or expired OAuth state")
    if payload.get("purpose") != "instagram_oauth" or not payload.get("sub"):
        raise HTTPException(400, "Invalid OAuth state")
    return payload["sub"]


def graph_get(path_or_url: str, token: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = path_or_url if path_or_url.startswith("http") else f"{GRAPH_BASE}/{path_or_url.lstrip('/')}"
    params = dict(params or {}, access_token=token)
    try:
        res = requests.get(url, params=params, timeout=30)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Instagram API request failed: {exc}")
    data = res.json() if res.content else {}
    if not res.ok:
        raise HTTPException(res.status_code, data.get("error", {}).get("message") or res.text or "Instagram API failed")
    return data


def exchange_code(code: str) -> Dict[str, Any]:
    require_config()
    short = requests.get(f"{GRAPH_BASE}/oauth/access_token", params={"client_id": settings.INSTAGRAM_CLIENT_ID, "client_secret": settings.INSTAGRAM_CLIENT_SECRET, "redirect_uri": settings.INSTAGRAM_REDIRECT_URI, "code": code}, timeout=30).json()
    if "access_token" not in short:
        raise HTTPException(400, short.get("error", {}).get("message") or "Could not get token")
    long_res = requests.get(f"{GRAPH_BASE}/oauth/access_token", params={"grant_type": "fb_exchange_token", "client_id": settings.INSTAGRAM_CLIENT_ID, "client_secret": settings.INSTAGRAM_CLIENT_SECRET, "fb_exchange_token": short["access_token"]}, timeout=30)
    long = long_res.json()
    if not long_res.ok or "access_token" not in long:
        raise HTTPException(400, long.get("error", {}).get("message") or "Could not exchange token")
    return long


def find_ig_account(token: str) -> Dict[str, Any]:
    pages = graph_get("me/accounts", token, {"fields": "id,name,instagram_business_account{id,username,profile_picture_url}"})
    for page in pages.get("data", []) or []:
        ig = page.get("instagram_business_account")
        if ig and ig.get("id"):
            return ig
    raise HTTPException(400, "No authorized Instagram Business/Creator account found")


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def account_dict(a: InstagramAccount):
    return {"id": a.id, "instagram_user_id": a.instagram_user_id, "username": a.username, "profile_picture_url": a.profile_picture_url, "account_type": a.account_type, "token_expires_at": a.token_expires_at.isoformat() if a.token_expires_at else None, "connected_at": a.connected_at.isoformat() if a.connected_at else None}


def media_dict(m: InstagramMedia):
    return {"id": m.id, "instagram_media_id": m.instagram_media_id, "media_type": m.media_type, "media_url": m.media_url, "thumbnail_url": m.thumbnail_url, "caption": m.caption, "permalink": m.permalink, "timestamp": m.timestamp.isoformat() if m.timestamp else None, "like_count": m.like_count, "comments_count": m.comments_count, "imported_at": m.imported_at.isoformat() if m.imported_at else None}


def current_account(db: Session, user_id: str) -> InstagramAccount:
    account = db.query(InstagramAccount).filter(InstagramAccount.user_id == user_id).order_by(InstagramAccount.connected_at.desc()).first()
    if not account:
        raise HTTPException(404, "No Instagram account connected")
    return account


def fetch_media(account: InstagramAccount, limit: int):
    token = decrypt_secret(account.access_token_encrypted)
    if not token:
        raise HTTPException(401, "Instagram token cannot be decrypted; reconnect Instagram")
    data = graph_get(f"{account.instagram_user_id}/media", token, {"fields": "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp,like_count,comments_count", "limit": min(limit, 100)})
    return data.get("data", []) or []


def upsert_media(db: Session, account: InstagramAccount, raw: Dict[str, Any], imported=False):
    media = db.query(InstagramMedia).filter(InstagramMedia.user_id == account.user_id, InstagramMedia.instagram_media_id == str(raw.get("id"))).first()
    if not media:
        media = InstagramMedia(user_id=account.user_id, instagram_account_id=account.id, instagram_media_id=str(raw.get("id")))
    media.media_type = raw.get("media_type") or "UNKNOWN"
    media.media_url = raw.get("media_url")
    media.thumbnail_url = raw.get("thumbnail_url")
    media.caption = raw.get("caption") or ""
    media.permalink = raw.get("permalink")
    media.timestamp = parse_time(raw.get("timestamp"))
    media.like_count = int(raw.get("like_count") or 0)
    media.comments_count = int(raw.get("comments_count") or 0)
    if imported:
        media.imported_at = datetime.utcnow()
    db.add(media)
    return media


@router.get("/connect")
def connect_instagram(current_user: User = Depends(get_current_user)):
    require_config()
    url = OAUTH_DIALOG + "?" + urlencode({"client_id": settings.INSTAGRAM_CLIENT_ID, "redirect_uri": settings.INSTAGRAM_REDIRECT_URI, "scope": SCOPES, "response_type": "code", "state": make_state(current_user.id)})
    return {"auth_url": url}


@router.get("/callback")
def instagram_callback(code: str = Query(None), state: str = Query(None), db: Session = Depends(get_db)):
    if not code or not state:
        raise HTTPException(400, "Missing code/state")
    user_id = read_state(state)
    token_data = exchange_code(code)
    token = token_data["access_token"]
    ig = find_ig_account(token)
    profile = graph_get(ig["id"], token, {"fields": "id,username,profile_picture_url,account_type"})
    account = db.query(InstagramAccount).filter(InstagramAccount.user_id == user_id, InstagramAccount.instagram_user_id == profile["id"]).first()
    if not account:
        account = InstagramAccount(user_id=user_id, instagram_user_id=profile["id"])
    account.username = profile.get("username") or ig.get("username") or "instagram"
    account.profile_picture_url = profile.get("profile_picture_url") or ig.get("profile_picture_url")
    account.account_type = profile.get("account_type")
    account.access_token_encrypted = encrypt_secret(token)
    account.token_expires_at = datetime.utcnow() + timedelta(seconds=int(token_data.get("expires_in") or 5184000))
    account.connected_at = datetime.utcnow()
    db.add(account)
    db.commit()
    return RedirectResponse(f"/connect-instagram?connected=1&username={account.username}")


@router.get("/account")
def get_account(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = db.query(InstagramAccount).filter(InstagramAccount.user_id == current_user.id).order_by(InstagramAccount.connected_at.desc()).first()
    return {"connected": bool(account), "account": account_dict(account) if account else None}


@router.delete("/disconnect")
def disconnect(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.delete(current_account(db, current_user.id))
    db.commit()
    return {"message": "Instagram account disconnected"}


@router.get("/media")
def get_media(refresh: bool = False, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = current_account(db, current_user.id)
    if refresh or db.query(InstagramMedia).filter(InstagramMedia.instagram_account_id == account.id).count() == 0:
        for raw in fetch_media(account, limit):
            upsert_media(db, account, raw)
        db.commit()
    records = db.query(InstagramMedia).filter(InstagramMedia.instagram_account_id == account.id).order_by(InstagramMedia.timestamp.desc().nullslast()).limit(limit).all()
    return {"account": account_dict(account), "media": [media_dict(x) for x in records]}


@router.post("/import")
def import_media(media_ids: List[str], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = current_account(db, current_user.id)
    imported = []
    for mid in media_ids:
        m = db.query(InstagramMedia).filter(InstagramMedia.id == mid, InstagramMedia.user_id == current_user.id).first()
        if m:
            m.imported_at = datetime.utcnow()
            imported.append(m)
    db.add(InstagramImportLog(user_id=current_user.id, instagram_account_id=account.id, action="import_selected", requested_count=len(media_ids), imported_count=len(imported), status="success", completed_at=datetime.utcnow()))
    db.commit()
    return {"message": f"Imported {len(imported)} Instagram media records", "media": [media_dict(x) for x in imported]}


@router.post("/import/{media_id}")
def import_one(media_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    account = current_account(db, current_user.id)
    m = db.query(InstagramMedia).filter(InstagramMedia.id == media_id, InstagramMedia.user_id == current_user.id).first()
    if not m:
        raise HTTPException(404, "Instagram media not found or not owned by you")
    m.imported_at = datetime.utcnow()
    if m.media_type == "VIDEO" and m.permalink and "/reel/" in m.permalink:
        db.add(InstagramReel(user_id=current_user.id, instagram_account_id=account.id, instagram_media_id=m.instagram_media_id, media_url=m.media_url, thumbnail_url=m.thumbnail_url, caption=m.caption, permalink=m.permalink, timestamp=m.timestamp, imported_at=datetime.utcnow()))
    db.add(InstagramImportLog(user_id=current_user.id, instagram_account_id=account.id, action="import_one", requested_count=1, imported_count=1, status="success", completed_at=datetime.utcnow()))
    db.commit()
    return {"message": "Instagram media imported", "media": media_dict(m)}


@router.post("/import/{media_id}/post")
def create_post_from_instagram(media_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(InstagramMedia).filter(InstagramMedia.id == media_id, InstagramMedia.user_id == current_user.id).first()
    if not m:
        raise HTTPException(404, "Instagram media not found or not owned by you")
    post = Post(user_id=current_user.id, content=m.caption, hashtags=[], is_published=True, post_type="normal")
    db.add(post)
    db.flush()
    if m.media_url:
        db.add(PostImage(post_id=post.id, image_url=m.thumbnail_url or m.media_url, is_video=m.media_type == "VIDEO", video_url=m.media_url if m.media_type == "VIDEO" else None, order=0))
    m.imported_at = datetime.utcnow()
    db.commit()
    return {"message": "Created SocialHub post from authorized Instagram media", "post_id": post.id}


@router.post("/import/{media_id}/reel")
def create_reel_from_instagram(media_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(InstagramMedia).filter(InstagramMedia.id == media_id, InstagramMedia.user_id == current_user.id).first()
    if not m:
        raise HTTPException(404, "Instagram media not found or not owned by you")
    if not m.media_url or m.media_type != "VIDEO":
        raise HTTPException(400, "Only authorized Instagram videos/reels can become SocialHub reels")
    reel = Reel(user_id=current_user.id, video_url=m.media_url, thumbnail_url=m.thumbnail_url, caption=m.caption, hashtags=[])
    m.imported_at = datetime.utcnow()
    db.add(reel)
    db.commit()
    return {"message": "Created SocialHub reel from authorized Instagram media", "reel_id": reel.id}
