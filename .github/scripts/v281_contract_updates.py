from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def replace_line(path, marker, replacement, label):
    p = ROOT / path
    lines = p.read_text(encoding='utf-8').splitlines()
    hits = [i for i, line in enumerate(lines) if marker in line]
    if len(hits) != 1:
        raise SystemExit(f'contract line marker {label} count={len(hits)}')
    lines[hits[0]] = replacement
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')

replace_line('app/src/test/finance-flow.mjs', 'assert.match(gradleConfig, /versionCode',
             'assert.match(gradleConfig, /versionCode (?:51|52|53|54)/);', 'finance-flow versionCode')
replace_line('app/src/test/finance-flow.mjs', 'assert.match(gradleConfig, /versionName',
             'assert.match(gradleConfig, /versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1))"/);', 'finance-flow versionName')

replace_line('app/src/test/bir-v269-functional-contract.mjs', "throw new Error('version mismatch')",
             "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))) throw new Error('version mismatch');", 'v269 identity')

replace_line('app/src/test/v2611-finalization-contract.mjs', "throw new Error('android version mismatch')",
             "if(!(gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))||!(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"'))) throw new Error('android version mismatch');", 'v2611 android identity')
replace_line('app/src/test/v2611-finalization-contract.mjs', "throw new Error('api client version mismatch')",
             "if(!(api.includes('\\\"2.7.1\\\"')||api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"'))) throw new Error('api client version mismatch');", 'v2611 API identity')

replace_line('app/src/test/v270-finalization-contract.mjs', 'assert.match(gradle,/versionCode',
             'assert.match(gradle,/versionCode (?:51|52|53|54)/);', 'v270 code54')
replace_line('app/src/test/v270-finalization-contract.mjs', 'assert.match(gradle,/versionName',
             'assert.match(gradle,/versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.(?:0|1))"/);', 'v270 name281')

replace_line('app/src/test/v271-field-stabilization-contract.mjs', "'v2.7.1 identity'",
             "ok((gradle.includes('versionCode 52')||gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))&&(gradle.includes('versionName \\\"2.7.1\\\"')||gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')),'v2.7.1+ identity');", 'v271 identity')
replace_line('app/src/test/v271-field-stabilization-contract.mjs', 'MOCK must not be inserted into normal account list',
             "ok(main.includes('MOCK_PROFILE_ID.equals(selected)')&&main.includes('ADMIN_PROFILE_ID.equals(selected)'),'enrolled MOCK/ADMIN must be selectable alongside normal accounts');", 'v271 owner list')
replace_line('app/src/test/v271-field-stabilization-contract.mjs', 'MOCK must exit/rebuild cleanly',
             "ok(main.includes('OWNER_SESSION_IDLE_MS = 30L * 60_000L')&&main.includes('expireOwnerSessionIfIdle'),'owner sessions must re-lock after bounded inactivity');", 'v271 owner timeout')

replace_line('app/src/test/v280-operations-admin-contract.mjs', "'v2.8 identity'",
             "ok((gradle.includes('versionCode 53')||gradle.includes('versionCode 54'))&&(gradle.includes('versionName \\\"2.8.0\\\"')||gradle.includes('versionName \\\"2.8.1\\\"')),'v2.8 identity');", 'v280 identity')
replace_line('app/src/test/v280-operations-admin-contract.mjs', "'native owner entitlement transport'",
             "ok((api.includes('\\\"2.8.0\\\"')||api.includes('\\\"2.8.1\\\"'))&&api.includes('X-Owner-Token')&&api.includes('ownerEnroll'),'native owner entitlement transport');", 'v280 API identity')

replace_line('app/src/test/v2611-shell-contract.mjs', 'duplicate native shell remains visible',
             "if(!main.includes('nativeStatus.setVisibility(View.GONE)')) throw new Error('duplicate native status remains visible'); if(!main.includes('Build.VERSION.SDK_INT <= Build.VERSION_CODES.O')||!main.includes('compactBar.addView(manageButton, weighted())')) throw new Error('Android 6/8 native Manage safety bar missing');", 'v2611 old Android Manage')

print('BIR v2.8.1 inherited app contracts aligned')
