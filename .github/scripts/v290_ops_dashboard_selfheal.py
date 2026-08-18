from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Self-heal the free operations generator without weakening any functional guard.
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
if old in s:
    s = s.replace(old, new, 1)
elif new not in s:
    raise SystemExit('v290 ops generator self-heal anchor missing')
s = s.replace("addition='''async function authenticateOwnerAny(request, env, auth, kinds=['OWNER_ADMIN','SUPER_ADMIN']) {", "addition=r'''async function authenticateOwnerAny(request, env, auth, kinds=['OWNER_ADMIN','SUPER_ADMIN']) {", 1)
finish = "print('BIR v2.9 free hierarchical operations cockpit patch prepared')"
call = "import subprocess\nsubprocess.check_call(['python3', '.github/scripts/v290_test_schema.py'], cwd=ROOT)\n"
if call not in s:
    if s.count(finish) != 1:
        raise SystemExit('v290 ops finalization anchor missing')
    s = s.replace(finish, call + finish, 1)
p.write_text(s, encoding='utf-8')

# The convergence branch inherited the Relay layer without the experimental OfflineLedgerDb.
# Keep Relay independent: its identity component owns the tiny SHA-256 helper it needs.
p = ROOT / '.github/scripts/v290_final_convergence.py'
s = p.read_text(encoding='utf-8')
old_fp = '    static String fingerprint() throws Exception { return OfflineLedgerDb.sha256(publicKeyBase64()); }'
new_fp = '''    static String fingerprint() throws Exception { return sha256(publicKeyBase64()); }

    static String sha256(String value) {
        try {
            java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
            byte[] raw = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder(raw.length * 2);
            for (byte b : raw) out.append(String.format(java.util.Locale.US, "%02x", b & 0xff));
            return out.toString();
        } catch (Exception error) { throw new IllegalStateException("SHA-256 unavailable", error); }
    }'''
if old_fp in s:
    s = s.replace(old_fp, new_fp, 1)
elif new_fp not in s:
    raise SystemExit('v290 Relay fingerprint self-heal anchor missing')
old_verify = '        if(!fp.equals(OfflineLedgerDb.sha256(pub)))return false;'
new_verify = '        if(!fp.equals(RelayIdentityStore.sha256(pub)))return false;'
if old_verify in s:
    s = s.replace(old_verify, new_verify, 1)
elif new_verify not in s:
    raise SystemExit('v290 Relay verification self-heal anchor missing')
p.write_text(s, encoding='utf-8')

print('v290 free-ops and Relay SHA-256 generators self-healed')
