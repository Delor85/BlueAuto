from pathlib import Path


def read(p): return Path(p).read_text(encoding='utf-8')
def write(p,t): Path(p).write_text(t,encoding='utf-8')
def once(p,old,new):
    text=read(p)
    if old not in text: raise SystemExit('missing anchor in %s: %r' % (p,old))
    write(p,text.replace(old,new,1))

once('cloudflare/src/index.js', "const API_VERSION = '2.6.11-cloudflare';", "const API_VERSION = '2.8.0-cloudflare';")
once('cloudflare/src/index.js',
"capabilities: {commissions: true, commission_override: true, remote_results: true, force_sync: true, network_audit: true}",
"capabilities: {commissions: true, commission_override: true, remote_results: true, force_sync: true, network_audit: true, owner_admin: true, owner_mock_entitlement: true, accounting: true, tchoronko: true, event_balance: true}")

pkg=read('cloudflare/package.json')
if '"version": "2.6.11"' not in pkg: raise SystemExit('package version anchor missing')
write('cloudflare/package.json',pkg.replace('"version": "2.6.11"','"version": "2.8.0"',1))
lock=read('cloudflare/package-lock.json')
if lock.count('"version": "2.6.11"') < 2: raise SystemExit('package-lock version anchors missing')
write('cloudflare/package-lock.json',lock.replace('"version": "2.6.11"','"version": "2.8.0"',2))

# The launcher now follows the original SVG's exact cyan #16D7FF and gold #FFE26F geometry.
test='app/src/test/v280-operations-admin-contract.mjs'
text=read(test)
old="ok(icon.includes('strokeColor=\"#19D7FF\"')&&icon.includes('strokeColor=\"#FFE26F\"'),'launcher icon must preserve blue/gold infinity identity');"
new="ok(icon.includes('strokeColor=\"#16D7FF\"')&&icon.includes('strokeColor=\"#FFE26F\"')&&icon.includes('M194,77 C154,26 110,16 71,25'),'launcher icon must reuse the in-app BIR blue/gold infinity geometry');"
if old not in text: raise SystemExit('launcher test anchor missing')
text=text.replace(old,new,1)
insert="ok(worker.includes(\"const API_VERSION = '2.8.0-cloudflare'\")&&worker.includes('owner_admin: true')&&worker.includes('event_balance: true'),'v2.8 Worker source metadata and capabilities');\n"
anchor="ok(worker.includes(\"case 'owner_snapshot'\")&&worker.includes(\"case 'owner_control'\")&&worker.includes(\"case 'owner_assist'\")&&worker.includes('authenticateOwner'),'server owner control source');\n"
if insert not in text:
    if anchor not in text: raise SystemExit('worker contract anchor missing')
    text=text.replace(anchor,anchor+insert,1)
write(test,text)
print('B.I.R. v2.8 metadata + launcher contract finalized')
