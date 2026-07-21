"""Read-only database integrity and row-count check for SocialHub."""
from __future__ import annotations
import sqlite3, sys
from pathlib import Path
DB = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "socialhub.db"
uri = f"file:{DB.resolve().as_posix()}?mode=ro"
important = ["users","posts","reels","stories","comments","followers","chats","messages","notifications","marketplace_products","reports","alembic_version"]
with sqlite3.connect(uri, uri=True) as con:
    cur = con.cursor()
    print("database", DB, "size", DB.stat().st_size)
    print("integrity_check", cur.execute("PRAGMA integrity_check").fetchall())
    fk = cur.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign_key_issues", len(fk), fk[:10])
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in important:
        if table in tables:
            print(table, cur.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
