"""Quick API smoke test."""
import urllib.request, json, sys

BASE = "http://localhost:8000"

def api(method, path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": json.loads(e.read()).get("detail", str(e))}

# 1. Register
print("1. Register...", end=" ")
r = api("POST", "/api/auth/register", {"email":"test2@test.com","username":"test2","password":"TestPass1","full_name":"Test2"})
if "access_token" in r:
    print("OK")
    token = r["access_token"]
else:
    print(f"FAILED: {r.get('detail','')}")
    # Try login instead
    r = api("POST", "/api/auth/login", {"email":"test@test.com","password":"TestPass1"})
    token = r.get("access_token","")
    print(f"Login result: {'OK' if token else 'FAILED'}")

# 2. Login
print("2. Login...", end=" ")
r = api("POST", "/api/auth/login", {"email":"test@test.com","password":"TestPass1"})
if "access_token" in r:
    token = r["access_token"]
    print("OK")
else:
    print(f"FAILED: {r.get('detail','')}")

if not token:
    print("Cannot continue without token!")
    sys.exit(1)

# 3. Auth me
print("3. Auth me...", end=" ")
r = api("GET", "/api/auth/me", token=token)
if "username" in r:
    print(f"OK: {r['username']} ({r['email']})")
else:
    print(f"FAILED: {r}")

# 4. Health
print("4. Health check...", end=" ")
r = api("GET", "/api/health")
if r.get("status") == "healthy":
    print("OK")
else:
    print(f"FAILED: {r}")

# 5. Get feed
print("5. Get feed...", end=" ")
r = api("GET", "/api/posts", token=token)
if "posts" in r:
    print(f"OK: {r['total']} posts")
else:
    print(f"FAILED: {r}")

# 6. Profile
print("6. Get profile...", end=" ")
r = api("GET", "/api/users/profile/testuser", token=token)
if "username" in r:
    print(f"OK: {r['username']}")
else:
    print(f"FAILED: {r}")

# 7. Search
print("7. Search...", end=" ")
r = api("GET", "/api/search?q=test", token=token)
if "users" in r:
    print(f"OK: {len(r['users'])} users, {len(r.get('posts',[]))} posts")
else:
    print(f"FAILED: {r}")

# 8. Notifications
print("8. Notifications...", end=" ")
r = api("GET", "/api/notifications", token=token)
if isinstance(r, list):
    print(f"OK: {len(r)} notifications")
else:
    print(f"FAILED: {r}")

# 9. Chats
print("9. Chats...", end=" ")
r = api("GET", "/api/chats", token=token)
if isinstance(r, list):
    print(f"OK: {len(r)} chats")
else:
    print(f"FAILED: {r}")

# 10. Trending
print("10. Trending hashtags...", end=" ")
r = api("GET", "/api/trending/hashtags")
if isinstance(r, list):
    print(f"OK: {len(r)} hashtags")
else:
    print(f"FAILED: {r}")

# 11. Trending posts
print("11. Trending posts...", end=" ")
r = api("GET", "/api/trending/posts", token=token)
if "posts" in r:
    print(f"OK: {r['total']} posts")
else:
    print(f"FAILED: {r}")

# 12. Homepage
print("12. Homepage HTML...", end=" ")
req = urllib.request.Request("http://localhost:8000/")
resp = urllib.request.urlopen(req)
html = resp.read().decode()
if "SocialHub" in html:
    print(f"OK: {len(html)} bytes loaded")
else:
    print("FAILED")

# 13. Login page
print("13. Login page...", end=" ")
req = urllib.request.Request("http://localhost:8000/login")
resp = urllib.request.urlopen(req)
if "Login" in resp.read().decode():
    print("OK")
else:
    print("FAILED")

print()
print("=" * 50)
print("ALL 13 API TESTS COMPLETED")
print("=" * 50)