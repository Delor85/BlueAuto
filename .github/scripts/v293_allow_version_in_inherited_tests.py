from pathlib import Path

changed=[]
for p in Path('app/src/test').glob('*.mjs'):
    if p.name == 'bir-v293-coherence-contract.mjs':
        continue
    s=p.read_text(encoding='utf-8')
    old=s
    # Only widen literal metadata guards. Functional, safety, UX and finance assertions are untouched.
    s=s.replace("gradle.includes('versionCode 57')", "(gradle.includes('versionCode 57')||gradle.includes('versionCode 58'))")
    s=s.replace('gradle.includes(\'versionName "2.9.2"\')', '(gradle.includes(\'versionName "2.9.2"\')||gradle.includes(\'versionName "2.9.3"\'))')
    s=s.replace('versionName "2.9.2"', 'versionName "2.9.3"') if 'versionCode 58' in s and 'versionName "2.9.3"' not in s and 'versionName "2.9.2"' in s else s
    if s!=old:
        p.write_text(s,encoding='utf-8')
        changed.append(str(p))
print('Inherited tests metadata-only widening:', len(changed))
for item in changed: print(' -',item)
