$env:DEBUG = "False"
Write-Host "Starting SocialHub in production mode..."
uvicorn main:app --host 0.0.0.0 --port 8000 --log-level warning
