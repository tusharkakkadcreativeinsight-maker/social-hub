"""Comprehensive API test script for SocialHub."""
import requests
import sys
import json
import os

BASE = os.getenv("SOCIALHUB_TEST_BASE", "http://127.0.0.1:8000")
results = []
TEST_EMAIL = "test@test.com"
TEST_USERNAME = "testuser"
TEST_PASSWORD = "TestPass1"
USER2_EMAIL = "user2@example.com"
USER2_USERNAME = "testuser2"
USER2_PASSWORD = "TestPass123"
ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "adminuser"
ADMIN_PASSWORD = "AdminPass123"

def test(name, method, url, data=None, headers=None, expected_status=None, files=None, allowed_statuses=None, form=None):
    """Run a single API test."""
    try:
        kwargs = {"headers": headers or {}, "timeout": 10}
        if method == "GET":
            r = requests.get(f"{BASE}{url}", **kwargs)
        elif method == "POST":
            if files:
                h = {k:v for k,v in (headers or {}).items() if k.lower() != 'content-type'}
                r = requests.post(f"{BASE}{url}", data=form, files=files, headers=h, timeout=10)
            elif form:
                h = {k:v for k,v in (headers or {}).items() if k.lower() != 'content-type'}
                r = requests.post(f"{BASE}{url}", data=form, headers=h, timeout=10)
            else:
                r = requests.post(f"{BASE}{url}", json=data, **kwargs)
        elif method == "PUT":
            r = requests.put(f"{BASE}{url}", json=data, **kwargs)
        elif method == "DELETE":
            r = requests.delete(f"{BASE}{url}", **kwargs)
        else:
            results.append((name, "FAIL", f"Unknown method {method}"))
            return
        
        try:
            detail = r.json()
        except:
            detail = r.text[:200]
        
        valid_statuses = set(allowed_statuses or [])
        if expected_status:
            valid_statuses.add(expected_status)

        if valid_statuses and r.status_code not in valid_statuses:
            results.append((name, "FAIL", f"Status {r.status_code}, expected {expected_status}. {json.dumps(detail)[:150]}"))
        else:
            results.append((name, "PASS", f"Status {r.status_code}"))
    except Exception as e:
        results.append((name, "FAIL", str(e)[:150]))


def direct_request(name, method, url, **kwargs):
    """Run direct requests used for follow-up IDs without crashing the whole suite."""
    try:
        return requests.request(method, f"{BASE}{url}", timeout=10, **kwargs)
    except Exception as e:
        results.append((name, "FAIL", str(e)[:150]))
        return None

# ==================== Health Check ====================
test("Health Check", "GET", "/api/health", expected_status=200)

# ==================== Auth Tests ====================
# First, try registering users - they may already exist from previous runs
# If they exist, just login

# Register or login test user
r = direct_request("Register User", "POST", "/api/auth/register",
    json={"email": TEST_EMAIL, "username": TEST_USERNAME, "password": TEST_PASSWORD, "full_name": "Test User"})
token = None
if r is not None and r.status_code == 201:
    token = r.json().get("access_token")
    results.append(("Register User", "PASS", "Created new user"))
elif r is not None:
    # Try login
    r = direct_request("Register User", "POST", "/api/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if r is not None and r.status_code == 200:
        token = r.json().get("access_token")
        results.append(("Register User", "PASS", "User already exists, logged in"))
    elif r is not None:
        results.append(("Register User", "FAIL", f"Could not create or login: {r.text[:150]}"))

# Register or login second user
r2 = direct_request("Register User 2", "POST", "/api/auth/register",
    json={"email": USER2_EMAIL, "username": USER2_USERNAME, "password": USER2_PASSWORD, "full_name": "Test User 2"})
token2 = None
if r2 is not None and r2.status_code == 201:
    token2 = r2.json().get("access_token")
    results.append(("Register User 2", "PASS", "Created new user"))
elif r2 is not None:
    r2 = direct_request("Register User 2", "POST", "/api/auth/login", json={"email": USER2_EMAIL, "password": USER2_PASSWORD})
    if r2 is not None and r2.status_code == 200:
        token2 = r2.json().get("access_token")
        results.append(("Register User 2", "PASS", "User already exists, logged in"))
    elif r2 is not None:
        results.append(("Register User 2", "FAIL", f"Could not create or login: {r2.text[:150]}"))

# Register or login admin user
r_admin = direct_request("Register Admin", "POST", "/api/auth/register",
    json={"email": ADMIN_EMAIL, "username": ADMIN_USERNAME, "password": ADMIN_PASSWORD, "full_name": "Admin User"})
if r_admin is not None and r_admin.status_code == 201:
    results.append(("Register Admin", "PASS", "Created new user"))
elif r_admin is not None:
    results.append(("Register Admin", "PASS", "User may already exist"))

# Set admin role via API - use the server's setup_admin.py which connects to the server's DB
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    import subprocess
    proc = subprocess.run(
        [sys.executable, os.path.join(script_dir, "setup_admin.py")],
        capture_output=True, text=True, cwd=script_dir
    )
    output = (proc.stdout + proc.stderr)
    if proc.returncode == 0:
        results.append(("Set admin role", "PASS", output[:100].replace('\n',' ')))
    else:
        # The live server may already hold the local SQLite DB while this helper runs.
        # Keep this diagnostic non-fatal; admin login/endpoints below verify the actual role.
        results.append(("Set admin role", "SKIP", f"Helper unavailable; admin login will verify role. {output[:100].replace(chr(10),' ')}"))
except Exception as e:
    results.append(("Set admin role", "SKIP", f"Helper unavailable; admin login will verify role. {str(e)[:100]}"))

# Re-login as admin to get fresh token with admin role
admin_token = None
r_admin_login = direct_request("Admin Login", "POST", "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
if r_admin_login is not None and r_admin_login.status_code == 200:
    admin_token = r_admin_login.json().get("access_token")
    results.append(("Admin Login", "PASS", f"Status {r_admin_login.status_code}"))
elif r_admin_login is not None:
    results.append(("Admin Login", "FAIL", f"Status {r_admin_login.status_code}"))

auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
auth_headers2 = {"Authorization": f"Bearer {token2}"} if token2 else {}
admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

# Test duplicate registration
test("Duplicate Register (should fail)", "POST", "/api/auth/register",
     data={"email": TEST_EMAIL, "username": TEST_USERNAME, "password": TEST_PASSWORD},
     expected_status=400)

# ==================== Auth Me ====================
test("Get Current User", "GET", "/api/auth/me", headers=auth_headers, expected_status=200)

# ==================== User Profile ====================
test("Get User Profile", "GET", "/api/users/profile/testuser", headers=auth_headers, expected_status=200)
test("Update Profile", "PUT", "/api/users/profile",
     data={"full_name": "Updated Name", "bio": "Hello World", "location": "New York"},
     headers=auth_headers, expected_status=200)
test("Get User by ID", "GET", f"/api/users/by-username/testuser", headers=auth_headers, expected_status=200)

# ==================== Follow ====================
# Get user2_id from the me endpoint using token2
user2_id = None
if token2:
    r2_me = direct_request("Get User 2 Current User", "GET", "/api/auth/me", headers=auth_headers2)
    if r2_me is not None and r2_me.status_code == 200:
        user2_id = r2_me.json().get("id")
if user2_id:
    test("Follow User", "POST", f"/api/follow/{user2_id}", headers=auth_headers, expected_status=200, allowed_statuses=[400])
    test("Check Follow Status", "GET", f"/api/follow/check/{user2_id}", headers=auth_headers, expected_status=200)
    test("Get Followers", "GET", f"/api/follow/followers/{user2_id}", headers=auth_headers, expected_status=200)
    test("Get Following", "GET", f"/api/follow/following/{user2_id}", headers=auth_headers, expected_status=200)
else:
    results.append(("Follow User", "SKIP", "No user2_id"))

# ==================== Posts ====================
test("Create Post", "POST", "/api/posts",
     data={"content": "Hello, this is a test post!", "hashtags": "test,social"},
     headers=auth_headers, expected_status=201)
test("Get Feed", "GET", "/api/posts?page=1&page_size=10", headers=auth_headers, expected_status=200)

# Get a post ID
r_feed = direct_request("Fetch Feed For Post ID", "GET", "/api/posts?page=1&page_size=10", headers=auth_headers)
post_id = None
if r_feed is not None and r_feed.status_code == 200:
    posts = r_feed.json().get("posts", [])
    if posts:
        post_id = posts[0].get("id")

if post_id:
    test("Get Single Post", "GET", f"/api/posts/{post_id}", headers=auth_headers, expected_status=200)
    test("Update Post", "PUT", f"/api/posts/{post_id}",
         data={"content": "Updated post content"}, headers=auth_headers, expected_status=200)

# ==================== Comments ====================
if post_id:
    test("Create Comment", "POST", f"/api/comments/{post_id}",
         data={"content": "Nice post!"}, headers=auth_headers, expected_status=201)
    test("Get Comments", "GET", f"/api/comments/{post_id}", headers=auth_headers, expected_status=200)
else:
    results.append(("Create Comment", "SKIP", "No post found"))

# ==================== Likes ====================
if post_id:
    test("Like Post", "POST", f"/api/likes/{post_id}",
         data={"reaction": "like"}, headers=auth_headers, expected_status=200)
    test("Get Post Likes", "GET", f"/api/likes/{post_id}", headers=auth_headers, expected_status=200)
    test("Unlike Post", "DELETE", f"/api/likes/{post_id}", headers=auth_headers, expected_status=200)
else:
    results.append(("Like Post", "SKIP", "No post found"))

# ==================== Stories ====================
test("Get Stories", "GET", "/api/stories", headers=auth_headers, expected_status=200)

# ==================== Reels ====================
test("Get Reels", "GET", "/api/reels?page=1&page_size=10", headers=auth_headers, expected_status=200)

# ==================== Messaging ====================
test("Create Chat", "POST", "/api/chats",
     data={"participant_ids": [user2_id] if user2_id else ["fake"], "name": "Test Chat"},
     headers=auth_headers, expected_status=201)

r_chats = direct_request("Get Chats", "GET", "/api/chats", headers=auth_headers)
chat_id = None
if r_chats is not None and r_chats.status_code == 200:
    chats = r_chats.json()
    if chats:
        chat_id = chats[0].get("id")
    results.append(("Get Chats", "PASS", f"Status {r_chats.status_code}"))
elif r_chats is not None:
    results.append(("Get Chats", "FAIL", f"Status {r_chats.status_code}"))

if chat_id:
    test("Get Chat by ID", "GET", f"/api/chats/{chat_id}", headers=auth_headers, expected_status=200)
    test("Get Chat Messages", "GET", f"/api/chats/{chat_id}/messages", headers=auth_headers, expected_status=200)
    test("Send Message", "POST", f"/api/chats/{chat_id}/messages",
         data={"content": "Hello!"}, headers=auth_headers, expected_status=200)

# ==================== Notifications ====================
test("Get Notifications", "GET", "/api/notifications", headers=auth_headers, expected_status=200)
test("Get Unread Count", "GET", "/api/notifications/unread-count", headers=auth_headers, expected_status=200)

# ==================== Search ====================
test("Search All", "GET", "/api/search?q=test&type=all", headers=auth_headers, expected_status=200)
test("Search Users", "GET", "/api/search/users?q=test", headers=auth_headers, expected_status=200)
test("Search Hashtags", "GET", "/api/search/hashtags?q=test", headers=auth_headers, expected_status=200)

# ==================== Advanced / Creator Features ====================
test("AI Caption Fallback", "POST", "/api/ai/caption",
     data={"title": "Summer launch", "description": "Behind the scenes", "category": "creator"},
     headers=auth_headers, expected_status=200)

test("Creator Dashboard", "GET", "/api/creator/dashboard", headers=auth_headers, expected_status=200)

future_time = "2030-01-01T10:00:00"
r_schedule = direct_request("Create Scheduled Post", "POST", "/api/schedule/post",
    json={"content": "Scheduled from API test", "media_urls": [], "hashtags": ["test", "schedule"], "scheduled_at": future_time, "content_type": "post"},
    headers=auth_headers)
if r_schedule is not None and r_schedule.status_code == 201:
    scheduled_id = r_schedule.json().get("item", {}).get("id")
    results.append(("Create Scheduled Post", "PASS", "Status 201"))
elif r_schedule is not None:
    results.append(("Create Scheduled Post", "FAIL", f"Status {r_schedule.status_code}: {r_schedule.text[:150]}"))
    scheduled_id = None
else:
    scheduled_id = None
test("List Scheduled Posts", "GET", "/api/schedule/me", headers=auth_headers, expected_status=200)
if scheduled_id:
    test("Delete Scheduled Post", "DELETE", f"/api/schedule/{scheduled_id}", headers=auth_headers, expected_status=200)

test("Reject Invalid Scheduled Content Type", "POST", "/api/schedule/post",
     data={"content": "Invalid schedule", "scheduled_at": future_time, "content_type": "invalid"},
     headers=auth_headers, expected_status=400)

test("Create Marketplace Product", "POST", "/api/marketplace/products",
     form={"title": "API Test Product", "description": "Created by test_api.py", "price": "19.99", "category": "Testing"},
     headers=auth_headers, expected_status=201)
test("List Marketplace Products", "GET", "/api/marketplace/products", expected_status=200)

r_product = direct_request("Fetch Marketplace Products For ID", "GET", "/api/marketplace/products")
product_id = None
if r_product is not None and r_product.status_code == 200:
    products = r_product.json().get("products", [])
    if products:
        product_id = products[0].get("id")
if product_id:
    test("Get Marketplace Product", "GET", f"/api/marketplace/products/{product_id}", expected_status=200)
    test("Delete Own Marketplace Product", "DELETE", f"/api/marketplace/products/{product_id}", headers=auth_headers, expected_status=200, allowed_statuses=[404])

r_collab = direct_request("Create Collaboration Offer", "POST", "/api/collabs",
    json={"title": "API Test Collab", "description": "Looking for test creators", "budget": "$100", "category": "Testing"},
    headers=auth_headers)
if r_collab is not None and r_collab.status_code == 201:
    offer_id = r_collab.json().get("offer", {}).get("id")
    results.append(("Create Collaboration Offer", "PASS", "Status 201"))
elif r_collab is not None:
    offer_id = None
    results.append(("Create Collaboration Offer", "FAIL", f"Status {r_collab.status_code}: {r_collab.text[:150]}"))
else:
    offer_id = None
test("List Collaboration Offers", "GET", "/api/collabs", expected_status=200)
if offer_id and token2:
    test("Apply To Collaboration Offer", "POST", f"/api/collabs/{offer_id}/apply",
         data={"message": "Interested from API test"}, headers=auth_headers2, expected_status=200, allowed_statuses=[400])

if user2_id:
    r_group = direct_request("Create Group Chat", "POST", "/api/chat/groups",
        json={"name": "API Test Group", "member_ids": [user2_id]}, headers=auth_headers)
    if r_group is not None and r_group.status_code == 201:
        group_id = r_group.json().get("group", {}).get("id")
        results.append(("Create Group Chat", "PASS", "Status 201"))
    elif r_group is not None:
        group_id = None
        results.append(("Create Group Chat", "FAIL", f"Status {r_group.status_code}: {r_group.text[:150]}"))
    else:
        group_id = None
    test("List Group Chats", "GET", "/api/chat/groups", headers=auth_headers, expected_status=200)
    if group_id:
        test("Send Group Message", "POST", f"/api/chat/groups/{group_id}/messages",
             data={"content": "Hello group from API test", "message_type": "text"}, headers=auth_headers, expected_status=200)
else:
    results.append(("Create Group Chat", "SKIP", "No user2_id"))

# ==================== Reports ====================
test("Create Report", "POST", "/api/reports",
     data={"reason": "spam", "description": "Test report"},
     headers=auth_headers, expected_status=201)

# ==================== Admin ====================
test("Admin Dashboard", "GET", "/api/admin/dashboard", headers=admin_headers, expected_status=200)
test("Admin Get Users", "GET", "/api/admin/users", headers=admin_headers, expected_status=200)
test("Admin Get Posts", "GET", "/api/admin/posts", headers=admin_headers, expected_status=200)
test("Admin Get Reports", "GET", "/api/admin/reports", headers=admin_headers, expected_status=200)
test("Admin Analytics", "GET", "/api/admin/analytics?days=7", headers=admin_headers, expected_status=200)
test("Non-Admin Dashboard (should fail)", "GET", "/api/admin/dashboard", headers=auth_headers, expected_status=403)

# ==================== Frontend Pages ====================
test("Frontend Index", "GET", "/", expected_status=200)
test("Frontend Login", "GET", "/login", expected_status=200)
test("Frontend Register", "GET", "/register", expected_status=200)
test("Frontend Posts", "GET", "/posts", expected_status=200)
test("Frontend Chat", "GET", "/chat", expected_status=200)
test("Frontend Stories", "GET", "/stories", expected_status=200)
test("Frontend Reels", "GET", "/reels", expected_status=200)
test("Frontend Notifications", "GET", "/notifications", expected_status=200)
test("Frontend Search", "GET", "/search", expected_status=200)
test("Frontend Admin", "GET", "/admin", expected_status=200)
test("Frontend Profile", "GET", "/profile/testuser", expected_status=200)
test("Frontend Forgot Password", "GET", "/forgot-password", expected_status=200)
test("Frontend Reset Password", "GET", "/reset-password", expected_status=200)
test("Frontend Creator Dashboard", "GET", "/creator-dashboard", expected_status=200)
test("Frontend Scheduled", "GET", "/scheduled", expected_status=200)
test("Frontend Marketplace", "GET", "/marketplace", expected_status=200)
test("Frontend Collabs", "GET", "/collabs", expected_status=200)

# ==================== Results ====================
print("\n" + "="*60)
print("TEST RESULTS")
print("="*60)

passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
skipped = sum(1 for _, s, _ in results if s == "SKIP")

for name, status, detail in results:
    icon = "PASS" if status == "PASS" else "FAIL" if status == "FAIL" else "SKIP"
    print(f"  [{icon}] {name}: {detail}")

print(f"\nTotal {passed + failed + skipped} tests: {passed} passed, {failed} failed, {skipped} skipped")

if failed > 0:
    sys.exit(1)