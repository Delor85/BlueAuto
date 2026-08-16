from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

changed = []
for rel in [
    'app/src/main/assets/index.html',
    'app/src/main/assets/app.js',
    'app/src/main/assets/control-tower-v271.js',
]:
    path = ROOT / rel
    text = path.read_text(encoding='utf-8')
    repaired = text.replace('birBlueBalance', 'birCamtelBalance')
    if repaired != text:
        path.write_text(repaired, encoding='utf-8')
        changed.append(rel)

html = (ROOT / 'app/src/main/assets/index.html').read_text(encoding='utf-8')
app = (ROOT / 'app/src/main/assets/app.js').read_text(encoding='utf-8')
overlay = (ROOT / 'app/src/main/assets/control-tower-v271.js').read_text(encoding='utf-8')

if 'id="birCamtelBalance"' not in html:
    raise SystemExit('canonical internal balance id not restored in HTML')
if 'SOLDE BLUE' not in html:
    raise SystemExit('visible Blue branding was accidentally reverted')
if "byId('birCamtelBalance')" not in app:
    raise SystemExit('canonical internal balance id not restored in app.js')
if "id('birCamtelBalance')" not in overlay:
    raise SystemExit('v2.7.1 overlay does not use canonical balance id')
if 'birBlueBalance' in html + app + overlay:
    raise SystemExit('accidental renamed internal id still present')

print('internal DOM contract repaired:', ', '.join(changed) or 'already clean')
