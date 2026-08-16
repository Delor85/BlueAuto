from pathlib import Path
path = Path('app/src/test/v270-owner-mock-contract.mjs')
text = path.read_text(encoding='utf-8')
old = "new URL('../../cloudflare/src/index.js', import.meta.url)"
new = "new URL('../../../cloudflare/src/index.js', import.meta.url)"
if text.count(old) != 1:
    raise SystemExit(f'owner MOCK contract path marker count={text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('Owner MOCK contract worker path corrected')
