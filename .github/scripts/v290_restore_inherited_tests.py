from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = 'eef53c4bf483ffc2557a57b0715561412f4c7e10'

def stable(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)

def put(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')

def replace_one(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f'Unexpected inherited identity anchor: {label} ({text.count(old)})')
    return text.replace(old, new, 1)

# Preserve the exact permanent-release hygiene workflow that protected v2.8.1.
put('.github/workflows/build.yml', stable('.github/workflows/build.yml'))

# Finance contract: only widen Android identity metadata.
p='app/src/test/finance-flow.mjs'; s=stable(p)
s=replace_one(s,'assert.match(gradleConfig, /versionCode (?:51|52|53|54)/);','assert.match(gradleConfig, /versionCode (?:51|52|53|54|55)/);','finance vc')
s=replace_one(s,r'''assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1))"/);''',r'''assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1)|2\.9\.0)"/);''','finance name')
put(p,s)

# v2.6.9 historical UX contract: only widen Android identity metadata.
p='app/src/test/bir-v269-functional-contract.mjs'; s=stable(p)
old=r'''if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName \"2.7.1\"')||gradle.includes('versionName \"2.8.0\"')||gradle.includes('versionName \"2.8.1\"'))) throw new Error('version mismatch');'''
new=r'''if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))||!(gradle.includes('versionName \"2.7.1\"')||gradle.includes('versionName \"2.8.0\"')||gradle.includes('versionName \"2.8.1\"')||gradle.includes('versionName \"2.9.0\"'))) throw new Error('version mismatch');'''
s=replace_one(s,old,new,'v269 identity'); put(p,s)

# v2.6.10 control-tower: keep one-off commission assertion, allow current Worker identity.
p='app/src/test/v2610-control-tower.mjs'; s=stable(p)
s=replace_one(s,"(worker.includes(\"const API_VERSION = '2.6.11-cloudflare'\")||worker.includes(\"const API_VERSION = '2.8.0-cloudflare'\"))","(worker.includes(\"const API_VERSION = '2.6.11-cloudflare'\")||worker.includes(\"const API_VERSION = '2.8.0-cloudflare'\")||worker.includes(\"const API_VERSION = '2.9.0-cloudflare'\"))",'v2610 worker identity'); put(p,s)

# v2.6.11 finalization: preserve capability/commission gates, widen only version identities.
p='app/src/test/v2611-finalization-contract.mjs'; s=stable(p)
s=replace_one(s,"(worker.includes(\"2.6.11-cloudflare\")||worker.includes(\"2.8.0-cloudflare\"))","(worker.includes(\"2.6.11-cloudflare\")||worker.includes(\"2.8.0-cloudflare\")||worker.includes(\"2.9.0-cloudflare\"))",'v2611 worker identity')
s=replace_one(s,"(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))","(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))",'v2611 vc')
s=replace_one(s,"(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))","(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')||gradle.includes('versionName \\\"2.9.0\\\"'))",'v2611 name')
s=replace_one(s,"(api.includes('\\\"2.7.1\\\"')||api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"'))","(api.includes('\\\"2.7.1\\\"')||api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"')||api.includes('\\\"2.9.0\\\"'))",'v2611 api identity'); put(p,s)

# v2.7 convergence: only Android identity metadata.
p='app/src/test/v270-finalization-contract.mjs'; s=stable(p)
s=replace_one(s,'assert.match(gradle,/versionCode (?:51|52|53|54)/);','assert.match(gradle,/versionCode (?:51|52|53|54|55)/);','v270 vc')
s=replace_one(s,r'''assert.match(gradle,/versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1))"/);''',r'''assert.match(gradle,/versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1)|2\.9\.0)"/);''','v270 name'); put(p,s)

# v2.7.1 stabilization: preserve all runtime guards, widen only identity.
p='app/src/test/v271-field-stabilization-contract.mjs'; s=stable(p)
s=replace_one(s,"(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))","(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))",'v271 vc')
s=replace_one(s,"(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))","(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')||gradle.includes('versionName \\\"2.9.0\\\"'))",'v271 name'); put(p,s)

# v2.8 operations/admin: preserve all admin/commission/accounting assertions, widen identities only.
p='app/src/test/v280-operations-admin-contract.mjs'; s=stable(p)
s=replace_one(s,"(gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))","(gradle.includes('versionCode 53')||gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))",'v280 vc')
s=replace_one(s,"(gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))","(gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')||gradle.includes('versionName \\\"2.9.0\\\"'))",'v280 name')
s=replace_one(s,"(api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"'))","(api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"')||api.includes('\\\"2.9.0\\\"'))",'v280 api')
s=replace_one(s,"worker.includes(\"const API_VERSION = '2.8.0-cloudflare'\")","(worker.includes(\"const API_VERSION = '2.8.0-cloudflare'\")||worker.includes(\"const API_VERSION = '2.9.0-cloudflare'\"))",'v280 worker'); put(p,s)

# v2.8.1 field quality: all runtime assertions remain exact; only release identity gets successor allowance.
p='app/src/test/v281-field-quality-contract.mjs'; s=stable(p)
s=replace_one(s,"need(gradle,'versionCode 54','vc54'); need(gradle,'versionName \"2.8.1\"','v2.8.1');","if(!(gradle.includes('versionCode 54')||gradle.includes('versionCode 55'))) throw new Error('Missing release identity: vc54/vc55'); if(!(gradle.includes('versionName \\\"2.8.1\\\"')||gradle.includes('versionName \\\"2.9.0\\\"'))) throw new Error('Missing release identity: v2.8.1/v2.9.0');",'v281 identity'); put(p,s)

print('Inherited v2.8.1 and historical functional contracts restored exactly; only v2.9/code55/API identity allowances added')
