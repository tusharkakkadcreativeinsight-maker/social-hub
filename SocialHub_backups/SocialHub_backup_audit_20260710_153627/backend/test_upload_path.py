import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.config import settings

base = settings.UPLOAD_DIR
dirs = {
    'post_images': settings.get_post_images_dir(),
    'videos': settings.get_videos_dir(),
    'reels': settings.get_reels_dir(),
    'stories': settings.get_stories_dir(),
    'profile_pics': settings.get_profile_pics_dir(),
    'cover_photos': settings.get_cover_photos_dir(),
}
for name, path in dirs.items():
    try:
        rel = os.path.relpath(path, base)
    except Exception as e:
        rel = f'ERROR: {e}'
    print(f'{name}: upload_dir={path!r}  relpath={rel!r}')