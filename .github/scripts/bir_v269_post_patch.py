from pathlib import Path
p=Path('app/src/main/assets/index.html')
s=p.read_text(encoding='utf-8')
s=s.replace('src="bir-logo.png"','src="bir-logo.svg"')
p.write_text(s,encoding='utf-8')
