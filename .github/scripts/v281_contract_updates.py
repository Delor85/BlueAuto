from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def rw(path, old, new, label):
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    if old not in s:
        raise SystemExit(f'contract anchor missing: {label}')
    if s.count(old) != 1:
        raise SystemExit(f'contract anchor not unique: {label} count={s.count(old)}')
    p.write_text(s.replace(old, new, 1), encoding='utf-8')

rw('app/src/test/finance-flow.mjs',
   'assert.match(gradleConfig, /versionCode (?:51|52|53)/);\nassert.match(gradleConfig, /versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.0)"/);',
   'assert.match(gradleConfig, /versionCode (?:51|52|53|54)/);\nassert.match(gradleConfig, /versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1))"/);',
   'finance-flow identity')

rw('app/src/test/bir-v269-functional-contract.mjs',
   "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"'))) throw new Error('version mismatch');",
   "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))) throw new Error('version mismatch');",
   'v269 identity')

rw('app/src/test/v2611-finalization-contract.mjs',
   "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"'))) throw new Error('android version mismatch');\nif(!(api.includes('\\\\\"2.7.1\\\\\"')||api.includes('\\\\\"2.8.0\\\\\"'))) throw new Error('api client version mismatch');",
   "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))) throw new Error('android version mismatch');\nif(!(api.includes('\\\\\"2.7.1\\\\\"')||api.includes('\\\\\"2.8.0\\\\\"')||api.includes('\\\\\"2.8.1\\\\\"'))) throw new Error('api client version mismatch');",
   'v2611 identity')

rw('app/src/test/v270-finalization-contract.mjs',
   'assert.match(gradle,/versionCode (?:51|52|53)/);\nassert.match(gradle,/versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.0)"/);',
   'assert.match(gradle,/versionCode (?:51|52|53|54)/);\nassert.match(gradle,/versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1))"/);',
   'v270 identity')

rw('app/src/test/v271-field-stabilization-contract.mjs',
   "ok((gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))&&(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')),'v2.7.1 identity');",
   "ok((gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))&&(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')),'v2.7.1+ identity');",
   'v271 identity')
rw('app/src/test/v271-field-stabilization-contract.mjs',
   "ok(!main.includes('labelsList.add((mockActive'),'MOCK must not be inserted into normal account list');",
   "ok(main.includes('MOCK_PROFILE_ID.equals(selected)')&&main.includes('ADMIN_PROFILE_ID.equals(selected)'),'enrolled MOCK/ADMIN must be selectable alongside normal accounts');",
   'v271 owner account list')
rw('app/src/test/v271-field-stabilization-contract.mjs',
   "ok(main.includes('mockSessionAuthorized = false')&&main.includes('recreate();'),'MOCK must exit/rebuild cleanly');",
   "ok(main.includes('OWNER_SESSION_IDLE_MS = 30L * 60_000L')&&main.includes('expireOwnerSessionIfIdle'),'owner sessions must re-lock after bounded inactivity');",
   'v271 owner idle lock')

rw('app/src/test/v280-operations-admin-contract.mjs',
   "ok(gradle.includes('versionCode 53')&&gradle.includes('versionName \\\"2.8.0\\\"'),'v2.8 identity');\nok(api.includes('\\\"2.8.0\\\"')&&api.includes('X-Owner-Token')&&api.includes('ownerEnroll'),'native owner entitlement transport');",
   "ok((gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))&&(gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')),'v2.8 identity');\nok((api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"'))&&api.includes('X-Owner-Token')&&api.includes('ownerEnroll'),'native owner entitlement transport');",
   'v280 identity')

rw('app/src/test/v2611-shell-contract.mjs',
   "if(!main.includes('nativeStatus.setVisibility(View.GONE)')||!main.includes('compactBar.setVisibility(View.GONE)')) throw new Error('duplicate native shell remains visible');",
   "if(!main.includes('nativeStatus.setVisibility(View.GONE)')) throw new Error('duplicate native status remains visible');\nif(!main.includes('Build.VERSION.SDK_INT <= Build.VERSION_CODES.O')||!main.includes('compactBar.addView(manageButton, weighted())')) throw new Error('Android 6/8 native Manage safety bar missing');",
   'v2611 old Android Manage safety')

print('BIR v2.8.1 inherited app contracts aligned')
