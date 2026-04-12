"""Fix remaining issues: double separator and table formatting in Sub-fase 2.0."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'c:\Users\ALEX\Github\AgriSearch\docs\plan_a_seguir.md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines_before = content.count('\r\n')
print(f"Lines before: {lines_before}")

# 1. Fix double "---" at line 493-495
content = content.replace('---\r\n\r\n---\r\n\r\n####', '---\r\n\r\n####')

# 2. Fix tables: remove blank lines between table rows in the Sub-fase 2.0 section only
# Find the section
sf20_start = content.find('#### Sub-fase 2.0:')
sf20_end = content.find('#### Sub-fase 2.1:', sf20_start)
if sf20_end == -1:
    sf20_end = content.find('#### Sub-fase 2.2:', sf20_start)
if sf20_end == -1:
    sf20_end = content.find('#### Sub-fase 2.3:', sf20_start)

print(f"Sub-fase 2.0 range: chars {sf20_start} to {sf20_end}")

section = content[sf20_start:sf20_end]

# Fix table rows - remove blank lines between pipe-delimited lines
fixed_section = re.sub(r'(\|[^\r\n]+\|)\r\n\r\n(\|)', r'\1\r\n\2', section)

# Fix numbered items in the "Acciones" list - remove extra blank lines
fixed_section = re.sub(r'(\d+\. \*\*[^\r\n]+)\r\n\r\n(\d+\. \*\*)', r'\1\r\n\2', fixed_section)

# Fix other excessive blank lines (3+ blank lines → 1 blank line)
fixed_section = re.sub(r'(\r\n){4,}', '\r\n\r\n', fixed_section)

# Fix mermaid code block: remove blank lines inside
mermaid_pattern = re.compile(r'(```mermaid\r\n)(.*?)(```)', re.DOTALL)
def fix_mermaid(match):
    code = match.group(2)
    # Remove blank lines inside mermaid
    code = re.sub(r'\r\n\r\n', '\r\n', code)
    return match.group(1) + code + match.group(3)

fixed_section = mermaid_pattern.sub(fix_mermaid, fixed_section)

content = content[:sf20_start] + fixed_section + content[sf20_end:]

lines_after = content.count('\r\n')
print(f"Lines after: {lines_after} (removed {lines_before - lines_after} lines)")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
lines = content.split('\r\n')
sf20_idx = None
for i, l in enumerate(lines):
    if 'Sub-fase 2.0: Pre-procesamiento' in l:
        sf20_idx = i
        break

if sf20_idx:
    print(f"\n--- Sub-fase 2.0 starts at line {sf20_idx + 1} ---")
    for i in range(sf20_idx, min(sf20_idx + 80, len(lines))):
        print(f"  L{i+1}: {lines[i][:100]}")

print("\n✅ SUCCESS: Tables and formatting fixed")
