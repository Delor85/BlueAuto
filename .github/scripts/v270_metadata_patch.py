from pathlib import Path

api = Path('app/src/main/java/com/profitloop/blueauto/ApiClient.java')
text = api.read_text(encoding='utf-8')
count = text.count('"2.6.11"')
if count != 2:
    raise SystemExit(f'Expected exactly 2 Android app_version references, found {count}')
api.write_text(text.replace('"2.6.11"', '"2.7.0"'), encoding='utf-8')

# Historical contracts remain useful; only their Android-version expectations move forward.
for path in Path('app/src/test').glob('*.mjs'):
    source = path.read_text(encoding='utf-8')
    updated = source.replace('versionName "2\\.6\\.11"', 'versionName "2\\.7\\.0"')
    updated = updated.replace('versionName "2.6.11"', 'versionName "2.7.0"')
    # The v2.6.11 finalization contract also checks the native app_version while preserving Worker 2.6.11 checks.
    if path.name == 'v2611-finalization-contract.mjs':
        updated = updated.replace("if(!api.includes('\"2.6.11\"'))", "if(!api.includes('\"2.7.0\"'))")
    if updated != source:
        path.write_text(updated, encoding='utf-8')

print('BIR v2.7 Android metadata and inherited version assertions synchronized')
