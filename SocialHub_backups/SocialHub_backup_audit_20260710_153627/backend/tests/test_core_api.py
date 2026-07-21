import io
import os
import sys
import uuid
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SEED_DEMO_ACCOUNTS", "false")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402


client = TestClient(app)


def _user(prefix="pytest"):
    unique = uuid.uuid4().hex[:10]
    return {
        "email": f"{prefix}_{unique}@example.com",
        "username": f"{prefix}_{unique}",
        "password": "TestPass123",
        "full_name": "Pytest User",
    }


def _auth_user(prefix="pytest"):
    payload = _user(prefix)
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    return payload, {"Authorization": f"Bearer {token}"}


def _png_file(name="image.png"):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buf, format="PNG")
    buf.seek(0)
    return (name, buf, "image/png")


def _mp4_file(name="reel.mp4"):
    # Minimal bytes are enough for endpoint/path validation; the API validates
    # MIME, extension, and size without decoding video frames.
    return (name, io.BytesIO(b"\x00\x00\x00\x18ftypmp42socialhub-test-video"), "video/mp4")


def _mp3_file(name="track.mp3"):
    # Minimal bytes are enough for endpoint/path validation; the API validates
    # MIME, extension, and size without decoding audio frames.
    return (name, io.BytesIO(b"ID3socialhub-test-audio"), "audio/mpeg")


def test_health_and_openapi_have_no_dirty_routes():
    assert client.get("/api/health").status_code == 200
    routes = [route.path for route in app.routes]
    assert not any("/../" in path for path in routes)


def test_auth_register_login_password_reset_and_2fa_setup():
    user, headers = _auth_user("auth")
    login = client.post("/api/auth/login", json={"email": user["email"], "password": user["password"]})
    assert login.status_code == 200
    assert login.json()["access_token"]

    forgot = client.post("/api/auth/forgot-password", json={"email": user["email"]})
    assert forgot.status_code == 200

    setup = client.post("/api/auth/setup-2fa", headers=headers)
    assert setup.status_code == 200
    assert setup.json()["secret"]
    assert setup.json()["qr_code_url"].startswith("otpauth://")


def test_posts_profile_uploads_search_notifications_and_admin_gate():
    _, headers = _auth_user("flow")
    post = client.post("/api/posts/", json={"content": "hello pytest #tests"}, headers=headers)
    assert post.status_code == 201, post.text
    post_id = post.json()["id"]
    assert client.get("/api/posts", headers=headers).status_code == 200
    assert client.get("/api/search?q=pytest", headers=headers).status_code == 200
    assert client.get("/api/notifications", headers=headers).status_code == 200
    assert client.get("/api/admin/dashboard", headers=headers).status_code in {200, 403}

    upload = client.post("/api/profile/photo", files={"file": _png_file()}, headers=headers)
    assert upload.status_code == 200, upload.text
    assert upload.json()["profile_picture"].startswith("profiles/")

    cover = client.post("/api/users/profile/cover", files={"file": _png_file("cover.png")}, headers=headers)
    assert cover.status_code == 200, cover.text
    assert cover.json()["cover_photo"].startswith("covers/")

    like = client.post(f"/api/likes/{post_id}", headers=headers)
    assert like.status_code in {200, 201, 400}


def test_reels_stories_chat_marketplace_collabs_and_data_studio_uploads():
    _, headers = _auth_user("media")

    story = client.post("/api/stories", data={"caption": "story"}, files={"file": _png_file("story.png")}, headers=headers)
    assert story.status_code == 201, story.text
    assert story.json()["media_url"].startswith("stories/")

    assert client.get("/api/reels", headers=headers).status_code == 200
    reel = client.post(
        "/api/reels/upload",
        data={"caption": "pytest reel", "title": "Pytest Audio", "hashtags": "pytest,reels"},
        files={"file": _mp4_file()},
        headers=headers,
    )
    assert reel.status_code == 201, reel.text
    reel_json = reel.json()
    assert reel_json["success"] is True
    assert reel_json["reel"]["video_url"].startswith("reels/")
    assert os.path.isabs(reel_json["reel"]["video_url"]) is False
    assert client.get(f"/uploads/{reel_json['reel']['video_url']}").status_code == 200

    assert client.get("/reels").status_code == 200
    chat = client.post("/api/chats", json={"participant_ids": []}, headers=headers)
    assert chat.status_code in {201, 400, 422}

    product = client.post(
        "/api/marketplace/products",
        data={"title": "Item", "description": "Desc", "price": "10", "category": "General"},
        files={"image": _png_file("product.png")},
        headers=headers,
    )
    assert product.status_code in {201, 200}, product.text

    collab = client.post("/api/collabs", json={"title": "Collab", "description": "Work", "budget": "Open", "category": "General"}, headers=headers)
    assert collab.status_code in {201, 200, 422}

    original = client.post(
        "/api/data-studio/media/original/upload",
        data={"ownership_confirmed": "true"},
        files={"file": _png_file("original.png")},
        headers=headers,
    )
    assert original.status_code in {200, 201}, original.text


def test_music_api_upload_list_search_update_and_delete():
    _, headers = _auth_user("music")

    upload = client.post(
        "/api/music/upload",
        data={"title": "Pytest Track", "artist": "Tester", "duration": "12.5", "category": "lofi"},
        files={"file": _mp3_file()},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    track = upload.json()
    assert track["audio_path"].startswith("music/")
    assert os.path.isabs(track["audio_path"]) is False
    music_id = track["id"]

    assert client.get("/api/music").status_code == 200
    assert client.get("/api/music/trending").status_code == 200
    assert client.get("/api/music/categories").status_code == 200
    assert client.get("/api/music/search?q=pytest").status_code == 200
    assert client.get("/api/music/me", headers=headers).status_code == 200

    detail = client.get(f"/api/music/{music_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["title"] == "Pytest Track"

    updated = client.patch(f"/api/music/{music_id}", json={"title": "Updated Track", "category": "beats"}, headers=headers)
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Updated Track"
    assert updated.json()["category"] == "beats"

    deleted = client.delete(f"/api/music/{music_id}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["success"] is True
    assert client.get(f"/api/music/{music_id}").status_code == 404


def test_dirty_compatibility_paths_are_not_available():
    _, headers = _auth_user("dirty")
    # ASGI test clients normalize ../ URL segments before routing, so the
    # authoritative check is that no registered FastAPI route contains them.
    routes = [route.path for route in app.routes]
    assert "/api/users/../profile/photo" not in routes
    assert "/api/posts/../feed" not in routes
    assert "/api/reels/../reels" not in routes
    assert "/api/follow/../unfollow/{user_id}" not in routes


def test_creator_ai_scheduler_explore_and_reel_metadata_features():
    _, headers = _auth_user("pro")

    ai = client.post("/api/ai/viral-hooks", json={"topic": "fitness tips", "audience": "creators"}, headers=headers)
    assert ai.status_code == 200, ai.text
    assert ai.json()["source"] in {"local_fallback", "openai"}
    assert ai.json()["hooks"]

    reel = client.post(
        "/api/reels/upload",
        data={
            "caption": "metadata reel",
            "hashtags": "pro,reels",
            "location": "Studio",
            "text_overlay": "Watch this",
            "filter_name": "cinematic",
            "trim_start": "0",
            "trim_end": "3",
        },
        files={"file": _mp4_file("metadata.mp4"), "thumbnail": _png_file("cover.png")},
        headers=headers,
    )
    assert reel.status_code == 201, reel.text
    body = reel.json()["reel"]
    assert body["video_url"].startswith("reels/")
    assert body["thumbnail_url"].startswith("covers/")

    due_time = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    sched = client.post("/api/schedule/post", json={"content": "due pytest post", "scheduled_at": due_time, "media_urls": [], "hashtags": ["pytest"], "content_type": "post"}, headers=headers)
    assert sched.status_code == 201, sched.text
    schedule_id = sched.json()["item"]["id"]
    # Non-admin users can create/list/cancel but cannot force publish due content.
    assert client.post("/api/schedule/publish-due", headers=headers).status_code in {403, 401}
    cancel = client.post(f"/api/schedule/{schedule_id}/cancel", headers=headers)
    assert cancel.status_code == 200, cancel.text

    explore = client.get("/api/explore/recommended", headers=headers)
    assert explore.status_code == 200, explore.text
    assert explore.json()["signals"]["uses_reel_views"] is True
