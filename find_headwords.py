import re

with open('2026-02-23.xhtml', 'r', encoding='utf-8') as f:
    content = f.read()

classes = set(re.findall(r'class="([^"]*headword[^"]*)"', content))
for c in sorted(classes):
    print(c)
