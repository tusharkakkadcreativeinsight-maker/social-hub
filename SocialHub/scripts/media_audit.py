"""Dry-run media audit/repair helper. Does not modify DB or delete files."""
from __future__ import annotations
import sqlite3, sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "socialhub.db"
UPLOADS = ROOT / "frontend" / "uploads"
FIELDS = [("post_images","image_url"),("post_images","video_url"),("reels","video_url"),("reels","thumbnail_url"),("reels","cover_image"),("stories","media_url"),("profiles","profile_picture"),("profiles","cover_photo"),("marketplace_products","image_url"),("messages","file_url"),("music","audio_path"),("original_media_assets","file_path")]
missing=[]
with sqlite3.connect(f"file:{DB.resolve().as_posix()}?mode=ro", uri=True) as con:
    cur=con.cursor(); tables={r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table,col in FIELDS:
        if table not in tables: continue
        cols={r[1] for r in cur.execute(f'PRAGMA table_info("{table}")')}
        if col not in cols: continue
        for rid,val in cur.execute(f'SELECT id, "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL AND "{col}" != ""'):
            s=str(val).replace('\\','/').lstrip('/')
            if s.startswith(('http://','https://','default')): continue
            if not (UPLOADS / s).exists():
                matches=list(UPLOADS.rglob(Path(s).name)) if Path(s).name else []
                missing.append({"table":table,"id":rid,"field":col,"path":s,"candidate_matches":[str(m.relative_to(UPLOADS)).replace('\\','/') for m in matches[:5]]})
print(f"missing_count={len(missing)}")
for item in missing[:200]: print(item)
