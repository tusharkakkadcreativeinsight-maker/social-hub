import os

base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
# Ensure uploads subdirs exist
for sub in ["uploads/profile_pics", "uploads/cover_photos", "uploads/post_images", "uploads/videos", "uploads/reels", "uploads/stories", "uploads/chat_files"]:
    os.makedirs(os.path.join(base, sub), exist_ok=True)

# Create default images if missing
img_dir = os.path.join(base, "static", "images")
os.makedirs(img_dir, exist_ok=True)

defaults = {
    "default-avatar.png": os.path.join(img_dir, "default_avatar.svg"),
    "default-cover.jpg": os.path.join(img_dir, "default_cover.svg"),
    "default_profile.png": os.path.join(img_dir, "default_profile.svg"),
}

for dst_name, src_path in defaults.items():
    dst_path = os.path.join(img_dir, dst_name)
    if not os.path.exists(dst_path):
        if os.path.exists(src_path):
            with open(src_path, "rb") as f:
                data = f.read()
            with open(dst_path, "wb") as f:
                f.write(data)
            print(f"Created {dst_name} from {os.path.basename(src_path)}")
        else:
            print(f"Warning: source {src_path} not found, skipping {dst_name}")

print("Done.")