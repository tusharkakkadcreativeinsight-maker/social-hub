# Security

- Secrets must live only in .env or a deployment secret manager.
- .env, ackend/.env, SQLite databases, uploads, backups and ZIP archives are ignored by Git.
- Rotate any credentials that existed in old ZIP files or shared backups.
- Production requires a strong SECRET_KEY, explicit CORS origins, and valid database/provider configuration.
- Local fallback features must not be represented as production integrations.
- Uploaded files are normalized to relative paths and served via /uploads/<relative-path>.
