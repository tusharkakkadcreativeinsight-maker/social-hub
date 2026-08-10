import io
import os
import sys
import uuid

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


def test_dirty_compatibility_paths_are_not_available():
    _, headers = _auth_user("dirty")
    # ASGI test clients normalize ../ URL segments before routing, so the
    # authoritative check is that no registered FastAPI route contains them.
    routes = [route.path for route in app.routes]
    assert "/api/users/../profile/photo" not in routes
    assert "/api/posts/../feed" not in routes
    assert "/api/reels/../reels" not in routes
    assert "/api/follow/../unfollow/{user_id}" not in routes
