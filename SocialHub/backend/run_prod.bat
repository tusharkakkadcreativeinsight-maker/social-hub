@echo off
echo Starting SocialHub in production mode...
set DEBUG=False
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning
