from pathlib import Path

p=Path('app/src/test/v280-operations-admin-contract.mjs')
s=p.read_text(encoding='utf-8')
old="api.includes('\\\"2.9.1\\\"')"
new="(api.includes('\\\"2.9.1\\\"')||api.includes('\\\"2.9.3\\\"'))"
if old not in s:
    raise SystemExit('v280 ApiClient metadata guard anchor missing')
if "api.includes('\\\"2.9.3\\\"')" not in s:
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('v280 ApiClient metadata guard widened to 2.9.3; functional assertions unchanged')
