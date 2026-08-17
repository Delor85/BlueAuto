from pathlib import Path
import re

p = Path(__file__).with_name('v281_field_quality_patch.py')
s = p.read_text(encoding='utf-8')

# Minified v280 JS binding anchor.
pattern = r"s = replace_once\(s,\n'''bind\('v280TchoSave'.*?'Admin account switch binding'\)\n"
replacement = """s = replace_once(s,\n'''bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''',\n'''bind('v280AdminAccounts',function(){var b=bridge();if(b&&b.openAccounts)b.openAccounts();});bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''', 'Admin account switch binding')\n"""
s, count = re.subn(pattern, replacement, s, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f'Could not self-heal v281 admin binding anchor: {count}')

# Bilingual dictionary anchor has no leading space in the actual minified object.
old = "''' 'Actualiser tout':'Refresh all','Aucune donnée':'No data'\\n};'''"
new = "'''Actualiser tout':'Refresh all','Aucune donnée':'No data'\\n};'''"
if old not in s:
    raise SystemExit('Could not self-heal v281 bilingual dictionary anchor')
s = s.replace(old, new, 1)

# Preserve useful historical wording while making the reconnect state clearer.
legacy_old = '⚠ Accessibilité désactivée par Android • Robot conservé • achat/vente en attente'
legacy_new = '⚠ Accessibilité à activer avant achat/vente • désactivée par Android • Robot conservé • file conservée • TEST_NUMBER reste direct'
if legacy_old not in s:
    raise SystemExit('Could not preserve inherited accessibility status wording')
s = s.replace(legacy_old, legacy_new, 1)

# Inject additive test-contract migrations immediately after build.gradle is updated.
needle = "write(p, s)\n\np = 'app/src/main/java/com/profitloop/blueauto/ApiClient.java'"
compat = r'''write(p, s)

# Historical contracts are kept, but release identity and account-list semantics are extended
# for the explicit v2.8.1 requirements rather than falsely pinning the prior candidate.
p = 'app/src/test/finance-flow.mjs'
s = read(p)
s = replace_once(s,
'''assert.match(gradleConfig, /versionCode (?:51|52|53)/);
assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.0)"/);''',
'''assert.match(gradleConfig, /versionCode (?:51|52|53|54)/);
assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1))"/);''', 'finance-flow v2.8.1 identity')
write(p, s)

p = 'app/src/test/bir-v269-functional-contract.mjs'
s = read(p)
s = replace_once(s,
'''if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))||!(gradle.includes('versionName "2.7.1"')||gradle.includes('versionName "2.8.0"'))) throw new Error('version mismatch');''',
'''if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName "2.7.1"')||gradle.includes('versionName "2.8.0"')||gradle.includes('versionName "2.8.1"'))) throw new Error('version mismatch');''', 'v269 inherited identity')
write(p, s)

p = 'app/src/test/v2611-finalization-contract.mjs'
s = read(p)
s = replace_once(s,
'''if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))||!(gradle.includes('versionName "2.7.1"')||gradle.includes('versionName "2.8.0"'))) throw new Error('android version mismatch');
if(!(api.includes('\\"2.7.1\\"')||api.includes('\\"2.8.0\\"'))) throw new Error('api client version mismatch');''',
'''if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName "2.7.1"')||gradle.includes('versionName "2.8.0"')||gradle.includes('versionName "2.8.1"'))) throw new Error('android version mismatch');
if(!(api.includes('\\"2.7.1\\"')||api.includes('\\"2.8.0\\"')||api.includes('\\"2.8.1\\"'))) throw new Error('api client version mismatch');''', 'v2611 inherited identity')
write(p, s)

p = 'app/src/test/v270-finalization-contract.mjs'
s = read(p)
s = replace_once(s, 'assert.match(gradle,/versionCode (?:51|52|53)/);',
                 'assert.match(gradle,/versionCode (?:51|52|53|54)/);', 'v270 code54')
s = replace_once(s, 'assert.match(gradle,/versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.0)"/);',
                 'assert.match(gradle,/versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1))"/);', 'v270 name281')
write(p, s)

p = 'app/src/test/v271-field-stabilization-contract.mjs'
s = read(p)
s = replace_once(s,
'''ok((gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))&&(gradle.includes('versionName "2.7.1"')||gradle.includes('versionName "2.8.0"')),'v2.7.1 identity');''',
'''ok((gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))&&(gradle.includes('versionName "2.7.1"')||gradle.includes('versionName "2.8.0"')||gradle.includes('versionName "2.8.1"')),'v2.7.1+ identity');''', 'v271 identity')
s = replace_once(s,
'''ok(!main.includes('labelsList.add((mockActive'),'MOCK must not be inserted into normal account list');''',
'''ok(main.includes('MOCK_PROFILE_ID.equals(selected)')&&main.includes('ADMIN_PROFILE_ID.equals(selected)'),'enrolled MOCK/ADMIN must be selectable alongside normal accounts');''', 'v271 owner list requirement')
s = replace_once(s,
'''ok(main.includes('mockSessionAuthorized = false')&&main.includes('recreate();'),'MOCK must exit/rebuild cleanly');''',
'''ok(main.includes('OWNER_SESSION_IDLE_MS = 30L * 60_000L')&&main.includes('expireOwnerSessionIfIdle'),'owner sessions must re-lock after bounded inactivity');''', 'v271 owner idle lock')
write(p, s)

p = 'app/src/test/v280-operations-admin-contract.mjs'
s = read(p)
s = replace_once(s,
'''ok(gradle.includes('versionCode 53')&&gradle.includes('versionName "2.8.0"'),'v2.8 identity');
ok(api.includes('"2.8.0"')&&api.includes('X-Owner-Token')&&api.includes('ownerEnroll'),'native owner entitlement transport');''',
'''ok((gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))&&(gradle.includes('versionName "2.8.0"')||gradle.includes('versionName "2.8.1"')),'v2.8 identity');
ok((api.includes('"2.8.0"')||api.includes('"2.8.1"'))&&api.includes('X-Owner-Token')&&api.includes('ownerEnroll'),'native owner entitlement transport');''', 'v280 identity')
write(p, s)

p = 'app/src/test/v2611-shell-contract.mjs'
s = read(p)
s = replace_once(s,
'''if(!main.includes('nativeStatus.setVisibility(View.GONE)')||!main.includes('compactBar.setVisibility(View.GONE)')) throw new Error('duplicate native shell remains visible');''',
'''if(!main.includes('nativeStatus.setVisibility(View.GONE)')) throw new Error('duplicate native status remains visible');
if(!main.includes('Build.VERSION.SDK_INT <= Build.VERSION_CODES.O')||!main.includes('compactBar.addView(manageButton, weighted())')) throw new Error('Android 6/8 native Manage safety bar missing');''', 'v2611 old Android Manage safety net')
write(p, s)

p = 'app/src/main/java/com/profitloop/blueauto/ApiClient.java' '''
if needle not in s:
    raise SystemExit('Could not inject v281 inherited contract migrations')
s = s.replace(needle, compat, 1)

p.write_text(s, encoding='utf-8')
print('v281 patch script anchors and inherited app contracts aligned')
