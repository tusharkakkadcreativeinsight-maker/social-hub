"""Explicit local demo seeding command for SocialHub.

Run only when you intentionally want local demo users/content:

    cd backend
    python scripts/seed_demo.py

Normal application startup does not create or modify demo accounts.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import ensure_demo_accounts  # noqa: E402


if __name__ == "__main__":
    ensure_demo_accounts()