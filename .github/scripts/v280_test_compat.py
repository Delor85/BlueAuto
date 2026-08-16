from pathlib import Path

for path in Path('app/src/test').glob('*.mjs'):
    text = path.read_text(encoding='utf-8')
    before = text
    text = text.replace('versionCode (?:51|52)', 'versionCode (?:51|52|53)')
    text = text.replace('versionName \\"2\\\\.7\\\\.(?:0|1)\\"', 'versionName \\"(?:2\\\\.7\\\\.(?:0|1)|2\\\\.8\\\\.0)\\"')
    text = text.replace('versionName "2\\.7\\.(?:0|1)"', 'versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.0)"')
    # Explicit v2.7.1 API-version regexes become compatibility checks instead of metadata freezes.
    text = text.replace('2\\.7\\.1', '(?:2\\.7\\.1|2\\.8\\.0)')
    if text != before:
        path.write_text(text, encoding='utf-8')
print('v2.8 historical test metadata compatibility applied')
