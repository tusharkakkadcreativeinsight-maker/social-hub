# Deployment

## Local

`powershell
cd "D:\social media\SocialHub"
python -m pip install -r requirements.txt
cd backend
python -m alembic upgrade head
python -m uvicorn main:app --host 127.0.0.1 --port 8000
`

## Production Startup Command

`ash
cd backend && python -m alembic upgrade head && python -m uvicorn main:app --host 0.0.0.0 --port 8000
`

Set DEBUG=false, strong SECRET_KEY, explicit CORS_ORIGINS, and production DATABASE_URL.
