from pathlib import Path
p=Path('app/src/main/assets/index.html')
text=p.read_text(encoding='utf-8')
old='  <script src="control-tower-v271.js"></script>\n  <script src="control-tower-v280.js"></script>'
new='  <script src="control-tower-v271.js"></script>\n  <script src="balance-engine-v280.js"></script>\n  <script src="control-tower-v280.js"></script>'
if old not in text:
    raise SystemExit('v2.8 balance wiring anchor missing')
p.write_text(text.replace(old,new,1),encoding='utf-8')
print('v2.8 event-driven balance engine wired')
