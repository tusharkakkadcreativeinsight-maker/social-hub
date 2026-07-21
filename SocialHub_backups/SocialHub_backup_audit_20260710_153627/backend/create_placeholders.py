import os

os.makedirs('../frontend/static/images', exist_ok=True)

# Default avatar SVG
avatar_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="#e0e0e0" rx="100"/>
  <circle cx="100" cy="75" r="35" fill="#bdbdbd"/>
  <path d="M30 185c0-38.6 31.4-70 70-70s70 31.4 70 70" fill="#bdbdbd"/>
</svg>'''

cover_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="800" height="200">
  <rect width="800" height="200" fill="#6C63FF" opacity="0.3"/>
</svg>'''

with open('../frontend/static/images/default-avatar.png', 'w') as f:
    f.write(avatar_svg)
print('Created default-avatar.png')

with open('../frontend/static/images/default_cover.svg', 'w') as f:
    f.write(cover_svg)
print('Created default_cover.svg')

print('All placeholders created successfully!')