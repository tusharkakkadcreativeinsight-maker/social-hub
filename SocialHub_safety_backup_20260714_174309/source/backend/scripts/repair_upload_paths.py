"""One-time maintenance command to normalize legacy upload paths.

This preserves files and rows; it only rewrites stored DB path strings to clean
relative upload paths such as posts/file.jpg or reels/file.mp4.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import normalize_existing_upload_paths  # noqa: E402


if __name__ == "__main__":
    normalize_existing_upload_paths()