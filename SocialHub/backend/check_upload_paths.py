import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import settings
from app.database import SessionLocal
from app.models.models import User, Post, PostImage, Reel, Story

db = SessionLocal()
issues = []
uploads_root = os.path.abspath(settings.UPLOAD_DIR)


def upload_exists(relative_path):
    """Check a DB upload path relative to frontend/uploads.

    Default placeholder names are rendered from /static/images by the frontend and
    are not expected to exist inside the uploads directory.
    """
    if not relative_path or str(relative_path).startswith(("http://", "https://", "default")):
        return True
    clean = str(relative_path).replace("\\", "/").lstrip("/")
    while clean.startswith("uploads/"):
        clean = clean[len("uploads/"):]
    candidate = os.path.abspath(os.path.join(uploads_root, clean.replace("/", os.sep)))
    return os.path.commonpath([uploads_root, candidate]) == uploads_root and os.path.exists(candidate)

for img in db.query(PostImage).all():
    if img.image_url:
        if not upload_exists(img.image_url):
            issues.append(('PostImage', img.id, img.image_url, 'MISSING'))
for r in db.query(Reel).all():
    if r.video_url:
        if not upload_exists(r.video_url):
            issues.append(('Reel', r.id, r.video_url, 'MISSING'))
for s in db.query(Story).all():
    if s.media_url:
        if not upload_exists(s.media_url):
            issues.append(('Story', s.id, s.media_url, 'MISSING'))
for u in db.query(User).all():
    for attr in ('profile_picture', 'cover_photo'):
        val = getattr(u, attr, None)
        if val:
            if not upload_exists(val):
                issues.append(('User', u.id, val, f'{attr} MISSING'))

if issues:
    print('ISSUES FOUND:')
    for t, id_, path, reason in issues:
        print(f'{t} {id_}: {path} -> {reason}')
else:
    print('No missing upload files detected from DB paths.')
db.close()