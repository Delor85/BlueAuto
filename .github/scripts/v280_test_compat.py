from pathlib import Path

for path in Path('app/src/test').glob('*.mjs'):
    text = path.read_text(encoding='utf-8')
    before = text
    text = text.replace('versionCode (?:51|52)', 'versionCode (?:51|52|53)')
    text = text.replace('versionName \\"2\\\\.7\\\\.(?:0|1)\\"', 'versionName \\"(?:2\\\\.7\\\\.(?:0|1)|2\\\\.8\\\\.0)\\"')
    text = text.replace('versionName "2\\.7\\.(?:0|1)"', 'versionName "(?:2\\.7\\.(?:0|1)|2\\.8\\.0)"')
    text = text.replace("gradle.includes('versionCode 52')", "(gradle.includes('versionCode 52')||gradle.includes('versionCode 53'))")
    text = text.replace("gradle.includes('versionName \"2.7.1\"')", "(gradle.includes('versionName \"2.7.1\"')||gradle.includes('versionName \"2.8.0\"'))")
    text = text.replace("gradleConfig.includes('versionCode 52')", "(gradleConfig.includes('versionCode 52')||gradleConfig.includes('versionCode 53'))")
    text = text.replace("gradleConfig.includes('versionName \"2.7.1\"')", "(gradleConfig.includes('versionName \"2.7.1\"')||gradleConfig.includes('versionName \"2.8.0\"'))")
    # Explicit regex-escaped v2.7.1 metadata becomes a compatibility check, not a capability change.
    text = text.replace('2\\.7\\.1', '(?:2\\.7\\.1|2\\.8\\.0)')
    if text != before:
        path.write_text(text, encoding='utf-8')
print('v2.8 historical test metadata compatibility applied')
