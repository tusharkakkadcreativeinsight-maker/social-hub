import requests
import json
import os

BASE = "http://localhost:8000"

def main():
    email = os.getenv("SOCIALHUB_SMOKE_EMAIL", "test@test.com")
    password = os.getenv("SOCIALHUB_SMOKE_PASSWORD", "TestPass1")
    username = os.getenv("SOCIALHUB_SMOKE_USERNAME", "testuser")

    print(f"=== Logging in as {username} ===")
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    print(f"Login status: {r.status_code}")
    if r.status_code != 200:
        print(f"Error: {r.json()}")
        return 1
    token = r.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    print("\n=== Getting profile ===")
    r = requests.get(f"{BASE}/api/users/profile/{username}", headers=headers)
    print(f"Profile status: {r.status_code}")
    print(f"Profile: {json.dumps(r.json(), indent=2)}")

    print("\n=== Creating a post ===")
    r = requests.post(f"{BASE}/api/posts/", json={"content": "Local smoke test post"}, headers=headers)
    print(f"Post status: {r.status_code}")
    print(f"Post: {json.dumps(r.json(), indent=2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())