from pathlib import Path

p=Path('app/src/main/java/com/profitloop/blueauto/RobotService.java')
s=p.read_text(encoding='utf-8')
old='PendingCommandStore.putLong(this, profileId, "accessibility_wait_started_at", 0L);'
new='try { command.remove("accessibility_wait_started_at"); PendingCommandStore.save(this, profileId, command); } catch (Exception ignored) {}'
if old not in s: raise SystemExit('RobotService accessibility wait cleanup anchor missing')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('B.I.R. v2.9.3 Android fixups applied')
