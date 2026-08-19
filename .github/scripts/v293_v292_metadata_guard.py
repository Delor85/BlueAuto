from pathlib import Path

p=Path('app/src/test/v292-free-premium-pilotage-contract.mjs')
s=p.read_text(encoding='utf-8')
old="must((api.match(/app_version\", \"2\\.9\\.2/g) || []).length >= 2, 'native heartbeat/activation does not report 2.9.2');"
new="must(((api.match(/app_version\", \"2\\.9\\.2/g) || []).length + (api.match(/app_version\", \"2\\.9\\.3/g) || []).length) >= 2, 'native heartbeat/activation does not report 2.9.2');"
if old not in s:
    raise SystemExit('v292 ApiClient telemetry metadata guard anchor missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('v292 native telemetry metadata guard widened to 2.9.3; pilotage assertions unchanged')
