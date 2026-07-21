"""Fix XSS vulnerability in app.js escapeHtml function."""
import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "frontend", "static", "js", "app.js")

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Check current state
idx = content.find('function escapeHtml')
if idx >= 0:
    end_idx = content.find('\n}', idx)
    func_text = content[idx:end_idx+2]
    print("Current function:")
    print(repr(func_text))

# Fix using binary-safe approach
# Replace the unsafe & with & in escapeHtml only
amp_amp = '&'
amp = '&'

lines = content.split('\n')
new_lines = []
in_escape = False
fixed_count = 0

for line in lines:
    stripped = line.strip()
    if 'function escapeHtml(t)' in stripped:
        in_escape = True
        new_lines.append(line)
        continue
    
    if in_escape:
        if stripped == '}':
            in_escape = False
            new_lines.append(line)
            continue
        
        # Fix each line
        if ".replace(/&/g, '&')" in line:
            line = line.replace(".replace(/&/g, '&')", ".replace(/&/g, '&" + "amp" + ";')")
            fixed_count += 1
        elif ".replace(/</g, '<')" in line:
            line = line.replace(".replace(/</g, '<')", ".replace(/</g, '&l" + "t;')")
            fixed_count += 1
        elif ".replace(/>/g, '>')" in line:
            line = line.replace(".replace(/>/g, '>')", ".replace(/>/g, '&g" + "t;')")
            fixed_count += 1
        elif '.replace(/"/g, \'"\')' in line:
            line = line.replace('.replace(/"/g, \'"\')', '.replace(/"/g, \'&qu' + 'ot;\')')
            fixed_count += 1
        
        new_lines.append(line)
        continue
    
    new_lines.append(line)

if fixed_count > 0:
    content = '\n'.join(new_lines)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\nApplied {fixed_count} fixes to escapeHtml")
else:
    print("\nNo fixes applied")

# Verify
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
    
if '&' in content:
    print("SUCCESS: escapeHtml now uses &")
else:
    print("WARNING: & not found in file")

# Print the fixed function
idx = content.find('function escapeHtml')
if idx >= 0:
    end_idx = content.find('\n}', idx)
    print("\nFixed function:")
    print(content[idx:end_idx+2])