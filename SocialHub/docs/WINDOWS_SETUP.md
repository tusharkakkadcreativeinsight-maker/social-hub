# Windows PowerShell Setup Guide

```powershell
cd "D:\social media\SocialHub"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall -q backend
python -m pytest -q
cd backend
python -m alembic upgrade head
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Use SocialHub/.env for local configuration. Do not create a conflicting active backend/.env.
