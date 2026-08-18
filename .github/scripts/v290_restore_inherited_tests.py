from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'eef53c4bf483ffc2557a57b0715561412f4c7e10'
path = 'app/src/test/finance-flow.mjs'

original = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)
old_code = r'/versionCode (?:51|52|53|54)/'
new_code = r'/versionCode (?:51|52|53|54|55)/'
old_name = r'/versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1))"/'
new_name = r'/versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1)|2\.9\.0)"/'

if original.count(old_code) != 1 or original.count(old_name) != 1:
    raise SystemExit('Unexpected v2.8.1 finance-flow release anchors')

updated = original.replace(old_code, new_code, 1).replace(old_name, new_name, 1)
(ROOT / path).write_text(updated, encoding='utf-8')
print('Inherited finance-flow restored from v2.8.1; only version 2.9/code55 allowance added')
