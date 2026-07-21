import io
import os
import sys
import uuid

from fastapi.testclient import TestClient
from PIL import Image

os.environ.setdefault("DEBUG", "true")
sys.path.insert(0, os.getcwd())

from main import app  # noqa: E402


client = TestClient(app)


def png_file(name: str):
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color="blue").save(buf, format="PNG")
    buf.seek(0)
    return (name, buf, "image/png")


def assert_clean_path(value: str, prefix: str):
    assert value.startswith(prefix), value
    assert not os.path.isabs(value), value
    assert "\\" not in value, value
    assert "//" not in value, value
    assert not value.startswith("uploads/"), value


routes = [
    "/api/health", "/", "/login", "/register", "/stories", "/reels", "/settings",
    "/data-studio", "/creator-dashboard", "/scheduled", "/marketplace", "/collabs",
    "/instagram-studio",
]
route_results = [(route, client.get(route).status_code) for route in routes]
bad_routes = [item for item in route_results if item[1] != 200]
assert not bad_routes, bad_routes

unique = uuid.uuid4().hex[:10]
user = {
    "email": f"smoke_{unique}@example.com",
    "username": f"smoke_{unique}",
    "password": "TestPass123",
    "full_name": "Smoke User",
}
registered = client.post("/api/auth/register", json=user)
assert registered.status_code == 201, registered.text
headers = {"Authorization": f"Bearer {registered.json()['access_token']}"}

upload_results = []

post = client.post(
    "/api/posts",
    headers=headers,
    data={"content": "smoke post"},
    files={"files": png_file("post.png")},
)
assert post.status_code in {200, 201}, post.text
post_path = post.json()["images"][0]["image_url"]
assert_clean_path(post_path, "posts/")
upload_results.append(("post", post_path))

story = client.post(
    "/api/stories",
    headers=headers,
    data={"caption": "smoke story"},
    files={"file": png_file("story.png")},
)
assert story.status_code == 201, story.text
story_path = story.json()["media_url"]
assert_clean_path(story_path, "stories/")
upload_results.append(("story", story_path))

reel = client.post(
    "/api/reels",
    headers=headers,
    data={"caption": "smoke reel"},
    files={"file": ("reel.mp4", io.BytesIO(b"0000"), "video/mp4")},
)
assert reel.status_code in {200, 201}, reel.text
reel_path = reel.json()["video_url"]
assert_clean_path(reel_path, "reels/")
upload_results.append(("reel", reel_path))

profile = client.post("/api/profile/photo", headers=headers, files={"file": png_file("profile.png")})
assert profile.status_code == 200, profile.text
profile_path = profile.json()["profile_picture"]
assert_clean_path(profile_path, "profiles/")
upload_results.append(("profile", profile_path))

cover = client.post("/api/users/profile/cover", headers=headers, files={"file": png_file("cover.png")})
assert cover.status_code == 200, cover.text
cover_path = cover.json()["cover_photo"]
assert_clean_path(cover_path, "covers/")
upload_results.append(("cover", cover_path))

product = client.post(
    "/api/marketplace/products",
    headers=headers,
    data={"title": "Item", "description": "Desc", "price": "1", "category": "General"},
    files={"image": png_file("product.png")},
)
assert product.status_code in {200, 201}, product.text
product_payload = product.json()
product_path = (product_payload.get("product") or product_payload).get("image_url")
assert_clean_path(product_path, "marketplace/")
upload_results.append(("marketplace", product_path))

original = client.post(
    "/api/data-studio/media/original/upload",
    headers=headers,
    data={"ownership_confirmed": "true"},
    files={"file": png_file("original.png")},
)
assert original.status_code in {200, 201}, original.text
original_payload = original.json()
original_path = (original_payload.get("asset") or original_payload).get("url") or original_payload.get("file_path")
assert_clean_path(original_path, "original_media/")
upload_results.append(("original", original_path))

print("SMOKE_ROUTES_OK", route_results)
print("SMOKE_UPLOADS_OK", upload_results)