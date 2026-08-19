from pathlib import Path

source = Path('.github/scripts/v294_war_room_copilot_convergence.py')
code = compile(source.read_text(encoding='utf-8'), str(source), 'exec')
exec(code, {'__name__': '__main__'})

# git diff --check rejects the old generated blank line at EOF.
p = Path('app/src/main/assets/war-room-v294.js')
p.write_text(p.read_text(encoding='utf-8').rstrip() + '\n', encoding='utf-8')
print('BIR v2.9.4 generated EOF normalized')
