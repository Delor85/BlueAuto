from pathlib import Path
import re

p = Path(__file__).with_name('v281_field_quality_patch.py')
s = p.read_text(encoding='utf-8')

pattern = r"s = replace_once\(s,\n'''bind\('v280TchoSave'.*?'Admin account switch binding'\)\n"
replacement = """s = replace_once(s,\n'''bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''',\n'''bind('v280AdminAccounts',function(){var b=bridge();if(b&&b.openAccounts)b.openAccounts();});bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''', 'Admin account switch binding')\n"""
s, count = re.subn(pattern, replacement, s, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f'Could not self-heal v281 admin binding anchor: {count}')

old = "''' 'Actualiser tout':'Refresh all','Aucune donnée':'No data'\\n};'''"
new = "'''Actualiser tout':'Refresh all','Aucune donnée':'No data'\\n};'''"
if old not in s:
    raise SystemExit('Could not self-heal v281 bilingual dictionary anchor')
s = s.replace(old, new, 1)

needle = "write(p, s)\n\np = 'app/src/main/java/com/profitloop/blueauto/ApiClient.java'"
compat = """write(p, s)\n\n# Extend the inherited release identity contract to the new additive candidate.\np = 'app/src/test/finance-flow.mjs'\ns = read(p)\ns = replace_once(s,\n'''assert.match(gradleConfig, /versionCode (?:51|52|53)/);\nassert.match(gradleConfig, /versionName \\\"(?:2\\\\.7\\\\.(?:0|1)|2\\\\.8\\\\.0)\\\"/);''',\n'''assert.match(gradleConfig, /versionCode (?:51|52|53|54)/);\nassert.match(gradleConfig, /versionName \\\"(?:2\\\\.7\\\\.(?:0|1)|2\\\\.8\\\\.(?:0|1))\\\"/);''', 'Inherited v2.8.1 release identity contract')\nwrite(p, s)\n\np = 'app/src/main/java/com/profitloop/blueauto/ApiClient.java'"""
if needle not in s:
    raise SystemExit('Could not inject v281 inherited version contract update')
s = s.replace(needle, compat, 1)

p.write_text(s, encoding='utf-8')
print('v281 patch script anchors and inherited version contract hardened')
