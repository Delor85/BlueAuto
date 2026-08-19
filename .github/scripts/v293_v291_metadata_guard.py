from pathlib import Path

p=Path('app/src/test/v291-field-recovery-contract.mjs')
s=p.read_text(encoding='utf-8')
old="must(gradle.includes('versionCode 56')&&gradle.includes('versionName \"2.9.1\"'),'v2.9.1/code56 identity missing');"
new="must((gradle.includes('versionCode 56')||gradle.includes('versionCode 58'))&&(gradle.includes('versionName \"2.9.1\"')||gradle.includes('versionName \"2.9.3\"')),'v2.9.1/code56 identity missing');"
if old not in s: raise SystemExit('v291 Gradle metadata guard anchor missing')
s=s.replace(old,new,1)
old="must(api.includes('payload.put(\"app_version\", \"2.9.1\");'),'v2.9.1 heartbeat telemetry missing');"
new="must(api.includes('payload.put(\"app_version\", \"2.9.1\");')||api.includes('payload.put(\"app_version\", \"2.9.3\");'),'v2.9.1 heartbeat telemetry missing');"
if old not in s: raise SystemExit('v291 ApiClient metadata guard anchor missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('v291 metadata guards widened to 2.9.3; all recovery/safety assertions unchanged')
