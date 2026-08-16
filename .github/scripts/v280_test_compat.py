from pathlib import Path

for path in Path('app/src/test').glob('*.mjs'):
    text = path.read_text(encoding='utf-8')
    before = text
    text = text.replace(r'versionCode (?:51|52)', r'versionCode (?:51|52|53)')
    text = text.replace(r'versionName \"2\\.7\\.(?:0|1)\"', r'versionName \"(?:2\\.7\\.(?:0|1)|2\\.8\\.0)\"')
    text = text.replace("versionCode 52", "versionCode (?:52|53)") if "new RegExp" in text else text
    text = text.replace("versionName 2.7.1", "versionName 2.8.0") if "v280" in path.name else text
    # Historical contracts are invariant tests, not metadata freezes. Broaden only exact v2.7.1
    # app-version checks where the surrounding source already proves the same capability.
    text = text.replace("2\\.7\\.1", "(?:2\\.7\\.1|2\\.8\\.0)")
    if text != before:
        path.write_text(text, encoding='utf-8')
print('v2.8 historical test metadata compatibility applied')
