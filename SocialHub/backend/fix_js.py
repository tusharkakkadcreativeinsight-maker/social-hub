import os

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                     "frontend", "static", "js", "app.js")

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# The fix: replace unsafe HTML entity encoding
# Current (vulnerable): &  <  >  "
# Correct (safe):      & < > "

# Use raw strings for replacement
old_replacements = [
    "        .replace(/&/g, '&')\n        .replace(/</g, '<')\n        .replace(/>/g, '>')\n        .replace(/\"/g, '\"')\n        .replace(/\\n/g, '<br>')",
]

new_replacement = """        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"')
        .replace(/\\n/g, '<br>')"""

# Check if already fixed
if '&' in content:
    print("escapeHtml already fixed - & found")
    # Still check
    if '.replace(/&/g' in content and '&' not in content[content.find('.replace(/&/g'):content.find('.replace(/&/g')+50]:
        print("But & replacement is still wrong!")
    else:
        print("All good!")
else:
    count = 0
    for old in old_replacements:
        if old in content:
            content = content.replace(old, new_replacement)
            count += 1
            print("Fixed one replacement block")
        else:
            # Try byte-by-byte approach
            print("Exact block not found, trying line-by-line...")
            
    if count == 0:
        # Direct line-by-line fix
        lines = content.split('\n')
        new_lines = []
        in_escape = False
        for line in lines:
            l = line.strip()
            if l == ".replace(/&/g, '&'):":
                new_lines.append("        .replace(/&/g, '&'):")
                in_escape = True
                continue
            elif l == ".replace(/&/g, '&')" and in_escape:
                new_lines.append("        .replace(/&/g, '&')")
                continue
            elif l == ".replace(/</g, '<')":
                new_lines.append("        .replace(/</g, '<')")
                continue
            elif l == ".replace(/>/g, '>')":
                new_lines.append("        .replace(/>/g, '>')")
                continue
            elif l == '.replace(/"/g, \'"\')' or l == '.replace(/"/g, "\'")':
                new_lines.append('        .replace(/"/g, \'"\')')
                continue
            elif l == ".replace(/\\n/g, '<br>');":
                in_escape = False
                new_lines.append("        .replace(/\\n/g, '<br>');")
                continue
            new_lines.append(line)
        
        if new_lines != lines:
            content = '\n'.join(new_lines)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Applied line-by-line fix")
        else:
            print("Could not fix - unknown format")
            idx = content.find('function escapeHtml')
            print(content[idx:idx+350])

if '&' in content and '<' in content:
    print("SUCCESS: escapeHtml now properly escapes HTML entities")
else:
    print("FAILED: escapeHtml still has XSS vulnerability!")