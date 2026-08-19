from pathlib import Path
import subprocess

BASE='eef53c4bf483ffc2557a57b0715561412f4c7e10'
source=f'{BASE}:.github/workflows/build.yml'
try:
    content=subprocess.check_output(['git','show',source], text=True)
except subprocess.CalledProcessError as exc:
    raise SystemExit(f'cannot restore permanent release hygiene fixture from {BASE}: {exc}')

required=[
    'publish_permanent',
    'authorized_sha',
    'BLUE_MAGIC_ANDROID_KEYSTORE_BASE64',
    'BLUE_MAGIC_ANDROID_KEYSTORE_PASSWORD',
    'f51e1d84271d3c4e229ce3cb424b36c8d564832b939e496bfc50352339b769b5',
]
missing=[x for x in required if x not in content]
if missing:
    raise SystemExit('permanent release hygiene fixture incomplete: '+', '.join(missing))

Path('.github/workflows/build.yml').write_text(content,encoding='utf-8')
print('Permanent release hygiene restored in CI workspace only from',BASE)
