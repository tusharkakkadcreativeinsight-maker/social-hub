# SocialHub

FastAPI + SQLAlchemy backend with SQLite-by-default, PostgreSQL-ready configuration, JWT auth, WebSocket chat, and a vanilla HTML/CSS/JavaScript frontend.

## Windows PowerShell Quick Start (Recommended)

This is the fastest way to get up and running on Windows:

```powershell
# 1. Open PowerShell and navigate to the project
cd SocialHub

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 3. Install all dependencies (one-time setup)
pip install -r requirements.txt

# 4. Verify backend works
python -m compileall backend
python backend/test_import.py
# Output: ✅ All imports successful!

# 5. Create/check database tables
python backend/test_db.py
# Output: ✅ Tables are ready.

# 6. Run all tests independently (no manual setup needed!)
pytest -q
# Output: ✅ 5 passed

# 7. Start the backend server
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 8. In a DIFFERENT PowerShell window, verify it's working:
Invoke-WebRequest http://127.0.0.1:8000/api/health | ConvertFrom-Json
# Output: {"status": "healthy", "app": "SocialHub", "version": "1.0.0"}

# 9. Open your browser
start http://127.0.0.1:8000
# Login with: test@test.com / TestPass1
```

That's it. SQLite is the default local database, and local/debug startup creates or checks tables automatically. Production should use Alembic migrations instead of relying on auto-create.

## Local SQLite Configuration

- **Default location:** `SocialHub/socialhub.db`
- **Auto-created:** YES (when server starts)
- **Demo account:** `test@test.com` / `TestPass1` (auto-seeded)
- **Use case:** Perfect for local development and testing

To reset the database:

```powershell
cd SocialHub
Remove-Item socialhub.db, socialhub.db-shm, socialhub.db-wal -Force -ErrorAction SilentlyContinue
# Restart the server and tables will be recreated
```

## Production and Sharing Safety

- Do **not** commit or ZIP: `.env`, `socialhub.db`, `__pycache__`, `.pyc`, `.pytest_cache`, logs, or uploaded media
- Keep only `.env.example` as the template (never `.env`)
- Before sharing: rotate `SECRET_KEY`, `APP_SECRET_KEY`, SMTP credentials, and OAuth secrets
- For production: set `DEBUG=false`, strong `SECRET_KEY`, explicit `CORS_ORIGINS`, and use PostgreSQL

## Seed demo data

Demo accounts are not seeded in production. Enable only for local/demo use:

```powershell
cd SocialHub\backend
python seed_data.py
python setup_admin.py
```

Or set in `.env`:

```env
DEBUG=true
SEED_DEMO_ACCOUNTS=true
```

## Run tests and checks

```powershell
cd SocialHub
python -m compileall backend
python backend/test_import.py
python backend/test_db.py
python backend/check_upload_paths.py
pytest -q
node --check frontend/static/js/app.js
node --check frontend/static/js/animations.js
```

Optional API smoke test while the server is running:

```powershell
cd SocialHub\backend
python test_api.py
```

Pytest uses FastAPI `TestClient` and does not require a live server:

```powershell
cd SocialHub
pytest -q
```

Frontend syntax checks:

```powershell
node --check frontend/static/js/app.js
node --check frontend/static/js/animations.js
```

## Reset local database and uploads

```powershell
cd SocialHub
Remove-Item socialhub.db,socialhub.db-shm,socialhub.db-wal -Force -ErrorAction SilentlyContinue
Get-ChildItem frontend\uploads -Recurse -File | Where-Object { $_.Name -ne '.gitkeep' } | Remove-Item -Force
```

Restart the server to recreate local SQLite tables.

## PostgreSQL setup

1. Install PostgreSQL.
2. Create a database and user.
3. Configure `.env`:

```env
DEBUG=false
DATABASE_URL=postgresql://socialhub_user:replace_password@localhost:5432/socialhub
CORS_ORIGINS=https://yourdomain.com
SECRET_KEY=replace-with-strong-random-secret
AUTO_CREATE_TABLES=false
SEED_DEMO_ACCOUNTS=false
```

4. Run migrations:

```powershell
cd SocialHub\backend
python -m alembic upgrade head
```

See `POSTGRESQL_SETUP.md` for more details.

## Key API areas

- Auth: `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`, `/api/auth/forgot-password`, `/api/auth/reset-password`, `/api/auth/setup-2fa`, `/api/auth/verify-2fa`
- Profile/uploads: `/api/users/profile`, `/api/users/profile/picture`, `/api/users/profile/cover`, `/api/profile/photo`
- Posts/feed: `/api/posts`, `/api/feed`, `/api/posts/upload`
- Reels/stories: `/api/reels`, `/api/reels/upload`, `/api/stories`
- Chat: `/api/chats`, `/ws/chat?token=...`
- Search/notifications/admin: `/api/search`, `/api/notifications`, `/api/admin/dashboard`
- Data Studio/marketplace/collabs: `/api/data-studio/*`, `/api/marketplace/products`, `/api/collabs`

Compatibility aliases live only in `backend/app/api/aliases.py`. Dirty `/../` routes are intentionally removed.

## Final acceptance commands

```powershell
cd SocialHub
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

python -m compileall backend

cd backend
python test_import.py
python test_db.py
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

In another terminal:

```powershell
cd SocialHub
pytest -q
node --check frontend/static/js/app.js
node --check frontend/static/js/animations.js
```

## Clean final ZIP command

Before sharing a ZIP, remove local secrets/runtime files and keep only `.gitkeep` files inside upload folders:

```powershell
cd SocialHub
Get-ChildItem -Recurse -Directory -Include __pycache__,.pytest_cache | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Recurse -Include *.pyc,*.pyo,*.log,*.db,*.db-shm,*.db-wal,.env | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem frontend\uploads -Recurse -File | Where-Object { $_.Name -ne '.gitkeep' } | Remove-Item -Force
Compress-Archive -Path * -DestinationPath ..\SocialHub-clean.zip -Force
```
