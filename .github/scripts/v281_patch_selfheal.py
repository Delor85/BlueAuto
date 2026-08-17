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

legacy_old = '⚠ Accessibilité désactivée par Android • Robot conservé • achat/vente en attente'
legacy_new = '⚠ Accessibilité à activer avant achat/vente • désactivée par Android • Robot conservé • file conservée • TEST_NUMBER reste direct'
if legacy_old not in s:
    raise SystemExit('Could not preserve inherited accessibility status wording')
s = s.replace(legacy_old, legacy_new, 1)

p.write_text(s, encoding='utf-8')
print('v281 patch anchors hardened')
