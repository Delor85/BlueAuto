from pathlib import Path

p=Path('.github/scripts/v293_server_command_center_patch.py')
lines=p.read_text(encoding='utf-8').splitlines()
out=[]
changed=0
for line in lines:
    if "'release owner fence'" in line and line.lstrip().startswith('once('):
        line=line.replace('once(', 's=s.replace(', 1)
        line=line.replace(",'release owner fence')", ',1)', 1)
        changed+=1
    out.append(line)
if changed!=1:
    raise SystemExit(f'expected one release owner fence patch call, got {changed}')
p.write_text('\n'.join(out)+'\n',encoding='utf-8')
print('v2.9.3 server patch script repaired: release owner fence scoped to first occurrence')
