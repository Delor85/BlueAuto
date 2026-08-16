from pathlib import Path
p=Path('app/src/main/assets/index.html')
s=p.read_text(encoding='utf-8')
s=s.replace('src="bir-logo.png"','src="bir-logo.svg"')
p.write_text(s,encoding='utf-8')

# B.I.R. changes commercial labels/navigation only; finance, Robot, SAV and diagnostics remain under full regression tests.
exec(Path('.github/scripts/bir_v269_test_patch.py').read_text(encoding='utf-8'), {'__name__':'__main__'})
