import re
from pathlib import Path

# Read the CSS file
css = Path('frontend/static/css/style.css').read_text()

# Extract all CSS class definitions (after .className)
css_classes = set(re.findall(r'\.([\w-]+)\s*\{', css))

# Extract all class uses from all HTML templates
templates = Path('frontend/templates').glob('*.html')
template_classes = set()
for t in templates:
    html = t.read_text()
    for match in re.findall(r'class="([^"]+)"', html):
        for cls in match.split():
            template_classes.add(cls)

# Find missing classes - filter out dynamic template vars and fontawesome
missing = set()
for m in sorted(template_classes):
    if (not m.startswith('${') and 
        not m.startswith('{') and 
        not m.startswith('fa-') and 
        not m.startswith('fab-') and 
        not m.startswith('fas-') and 
        not m.startswith('far-') and
        m not in css_classes):
        missing.add(m)

if missing:
    print(f'WARNING: {len(missing)} potentially missing CSS classes:')
    for m in sorted(missing):
        print(f'  - .{m}')
else:
    print('SUCCESS: All template CSS classes are defined in style.css!')