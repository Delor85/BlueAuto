from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / '.github/scripts/v290_ops_dashboard.py'
s = p.read_text(encoding='utf-8')

old = '''s=once(s,
'        if (mockSessionAuthorized || adminSessionAuthorized) touchOwnerSession();',
'        if (mockSessionAuthorized || adminSessionAuthorized || superAdminSessionAuthorized) touchOwnerSession();',
'super activity touch')'''
new = '''touch_old='        if (mockSessionAuthorized || adminSessionAuthorized) touchOwnerSession();'
touch_new='        if (mockSessionAuthorized || adminSessionAuthorized || superAdminSessionAuthorized) touchOwnerSession();'
if touch_old not in s:
    raise SystemExit('v290 ops anchor missing: super activity touch')
s=s.replace(touch_old,touch_new)'''
if old not in s:
    raise SystemExit('v290 ops generator self-heal anchor missing')
s = s.replace(old, new, 1)
s = s.replace("addition='''async function authenticateOwnerAny(request, env, auth, kinds=['OWNER_ADMIN','SUPER_ADMIN']) {", "addition=r'''async function authenticateOwnerAny(request, env, auth, kinds=['OWNER_ADMIN','SUPER_ADMIN']) {", 1)
p.write_text(s, encoding='utf-8')
print('v290 free-ops generator self-healed')
