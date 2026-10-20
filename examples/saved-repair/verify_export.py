"""Check this saved export's hashes and local links; never run a model or project tests."""
import hashlib
import json
import re
from pathlib import Path

root = Path(__file__).resolve().parent
files = json.loads((root / 'files.sha256.json').read_text(encoding='utf-8'))
actual_names = {p.name for p in root.iterdir() if p.is_file() and p.name != 'files.sha256.json'}
assert actual_names == set(files), 'export inventory changed'
for name, expected in files.items():
    raw = (root / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected, name
    text = raw.decode('utf-8')
    assert not re.search(r'(?<![A-Za-z])[A-Za-z]:[/\\]', text), f'host path in {name}'
    assert not re.search(r'sk-[A-Za-z0-9_-]{20,}', text), f'credential pattern in {name}'
    if name.endswith('.html'):
        links = re.findall(r'href="([^"]+)"', text)
    elif name.endswith('.md'):
        links = re.findall(r'\[[^\]]+\]\(([^)]+)\)', text)
    else:
        links = []
    for link in links:
        if not link.startswith(('https://', 'http://', '#')):
            assert (root / link.split('#')[0]).exists(), (name, link)
result = json.loads((root / 'verification.public.json').read_bytes())['result']
assert result['acceptance'] == 'NOT_RUN' and result['requirement_fit'] == 'NOT_ASSESSED'
assert result['comparison']['status'] == 'OBSERVED_FAIL_THEN_PASS'
assert [c['observation']['summary']['failed'] for c in result['checks']] == [0, 1, 0]
print('Saved export hashes, local links, path/credential scan and result boundaries passed.')
