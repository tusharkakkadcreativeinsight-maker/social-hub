"""Non-destructive SQLite backup utility for SocialHub."""
from __future__ import annotations
import hashlib, shutil, sqlite3
from datetime import datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / f"SocialHub_manual_db_backup_{datetime.now():%Y%m%d_%H%M%S}"
OUT.mkdir(exist_ok=False)
for db in ROOT.rglob("*.db"):
    if any(part in {"__pycache__", ".pytest_cache"} for part in db.parts):
        continue
    target = OUT / db.relative_to(ROOT).as_posix().replace("/", "__")
    shutil.copy2(db, target)
    print(hashlib.sha256(target.read_bytes()).hexdigest(), target)
print(f"backup_dir={OUT}")
