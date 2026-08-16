from pathlib import Path
p=Path('app/src/main/assets/index.html')
s=p.read_text(encoding='utf-8')
s=s.replace('src="bir-logo.png"','src="bir-logo.svg"')
p.write_text(s,encoding='utf-8')

# Adapt historical contracts to the new commercial home while keeping finance logic unchanged.
exec(Path('.github/scripts/bir_v269_test_patch.py').read_text(encoding='utf-8'), {'__name__':'__main__'})
