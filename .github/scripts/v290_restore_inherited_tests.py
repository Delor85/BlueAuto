from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'eef53c4bf483ffc2557a57b0715561412f4c7e10'

# Preserve the exact permanent-release hygiene workflow that protected v2.8.1.
# v2.9 uses separate convergence/release workflows; it must not erase the historical signer gate.
build_path = '.github/workflows/build.yml'
build = subprocess.check_output(['git', 'show', f'{BASE}:{build_path}'], cwd=ROOT, text=True)
(ROOT / build_path).write_text(build, encoding='utf-8')

# Preserve the complete v2.8.1 finance contract and extend only its release identity allowance.
path = 'app/src/test/finance-flow.mjs'
original = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)
old_code = r'/versionCode (?:51|52|53|54)/'
new_code = r'/versionCode (?:51|52|53|54|55)/'
old_name = r'/versionName \"(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1))\"/'
new_name = r'/versionName \"(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1)|2\\.9\\.0)\"/'
if original.count(old_code) != 1 or original.count(old_name) != 1:
    raise SystemExit('Unexpected v2.8.1 finance-flow release anchors')
updated = original.replace(old_code, new_code, 1).replace(old_name, new_name, 1)
(ROOT / path).write_text(updated, encoding='utf-8')

# Preserve the historical v2.6.9 functional contract and widen only its version gate.
path = 'app/src/test/bir-v269-functional-contract.mjs'
original = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)
old = "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))) throw new Error('version mismatch');"
new = "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')||gradle.includes('versionName \\\"2.9.0\\\"'))) throw new Error('version mismatch');"
if original.count(old) != 1:
    raise SystemExit('Unexpected v2.6.9 functional version anchor')
(ROOT / path).write_text(original.replace(old, new, 1), encoding='utf-8')

print('Inherited v2.8.1 finance/release hygiene and v2.6.9 functional contract restored; only v2.9/code55 allowance added')
