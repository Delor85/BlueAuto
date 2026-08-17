from pathlib import Path
import re

p = Path(__file__).with_name('v281_field_quality_patch.py')
s = p.read_text(encoding='utf-8')
pattern = r"s = replace_once\(s,\n'''bind\('v280TchoSave'.*?'Admin account switch binding'\)\n"
replacement = """s = replace_once(s,\n'''bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''',\n'''bind('v280AdminAccounts',function(){var b=bridge();if(b&&b.openAccounts)b.openAccounts();});bind('v280AdminRefresh',function(){request('owner_snapshot',{});});''', 'Admin account switch binding')\n"""
s2, count = re.subn(pattern, replacement, s, count=1, flags=re.S)
if count != 1:
    raise SystemExit(f'Could not self-heal v281 admin binding anchor: {count}')
p.write_text(s2, encoding='utf-8')
print('v281 patch script admin binding anchor hardened')
