# PostgreSQL 17 setup for SocialHub on Windows

SocialHub is configured to use PostgreSQL through SQLAlchemy using:

- `psycopg2-binary` for synchronous API/database sessions
- `asyncpg` for async database sessions

This guide uses:

- Host: `localhost`
- Port: `5432`
- Database: `socialhub`
- Username: `socialhub_user`
- Password: `socialhub123`

## 1. Install dependencies in VS Code PowerShell

Open VS Code terminal and run:

```powershell
cd "D:\social media\SocialHub"
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Install/start PostgreSQL 17

Install PostgreSQL 17 for Windows if it is not installed.

After installing, make sure the PostgreSQL service is running.

Make sure the Windows service is running:

```powershell
Get-Service postgresql*
```

If it is stopped, start it from `services.msc` or run PowerShell as Administrator:

```powershell
Start-Service postgresql-x64-17
```

## 3. Create PostgreSQL user and database

Open **SQL Shell (psql)** and login as the PostgreSQL admin user, usually `postgres`.

At the prompts, use:

```text
Server [localhost]: press Enter
Database [postgres]: press Enter
Port [5432]: press Enter
Username [postgres]: postgres
Password for user postgres: your PostgreSQL password
```

Then run:

```sql
CREATE USER socialhub_user WITH PASSWORD 'socialhub123';
CREATE DATABASE socialhub OWNER socialhub_user;
GRANT ALL PRIVILEGES ON DATABASE socialhub TO socialhub_user;
```

Connect to the new database:

```sql
\c socialhub
```

Allow the user to create/use objects in the `public` schema:

```sql
GRANT ALL ON SCHEMA public TO socialhub_user;
ALTER SCHEMA public OWNER TO socialhub_user;
```

Check it exists:

```sql
\l
```

Exit SQL Shell:

```sql
\q
```

Alternative from PowerShell if PostgreSQL `bin` is on PATH:

```powershell
psql -U postgres -h localhost -p 5432 -d postgres -c "CREATE USER socialhub_user WITH PASSWORD 'socialhub123';"
psql -U postgres -h localhost -p 5432 -d postgres -c "CREATE DATABASE socialhub OWNER socialhub_user;"
psql -U postgres -h localhost -p 5432 -d socialhub -c "GRANT ALL ON SCHEMA public TO socialhub_user; ALTER SCHEMA public OWNER TO socialhub_user;"
```

## 4. Configure `.env`

`SocialHub/.env` should contain:

```env
DATABASE_URL=postgresql://socialhub_user:socialhub123@localhost:5432/socialhub
DATABASE_URL_ASYNC=postgresql+asyncpg://socialhub_user:socialhub123@localhost:5432/socialhub
```

## 5. Test connection and create tables

From VS Code PowerShell:

```powershell
cd "D:\social media\SocialHub\backend"
python test_db.py
```

Expected output includes:

```text
Connection successful!
PostgreSQL version:
PostgreSQL 17...
Tables are ready.
```

If you prefer Alembic migrations, `backend/alembic/env.py` now reads the same `DATABASE_URL` from `.env`, so Alembic uses the configured SQLite/PostgreSQL database.

## 6. Run the app

From VS Code PowerShell:

```powershell
cd "D:\social media\SocialHub\backend"
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Troubleshooting

### Password authentication failed

Use SQL Shell username `postgres` for admin login, not `admin`, unless you created an `admin` PostgreSQL role.

### database "socialhub" does not exist

Run the database creation commands in step 3.

### role "socialhub_user" does not exist

Run:

```sql
CREATE USER socialhub_user WITH PASSWORD 'socialhub123';
```

### permission denied for schema public

Login as `postgres`, connect to `socialhub`, then run:

```sql
GRANT ALL ON SCHEMA public TO socialhub_user;
ALTER SCHEMA public OWNER TO socialhub_user;
```
