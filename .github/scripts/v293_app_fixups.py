from pathlib import Path

p=Path('app/src/main/java/com/profitloop/blueauto/RobotService.java')
s=p.read_text(encoding='utf-8')
old='PendingCommandStore.putLong(this, profileId, "accessibility_wait_started_at", 0L);'
new='try { command.remove("accessibility_wait_started_at"); PendingCommandStore.save(this, profileId, command); } catch (Exception ignored) {}'
if old not in s: raise SystemExit('RobotService accessibility wait cleanup anchor missing')
s=s.replace(old,new,1)

# Preserve the historically stable field wording while adding the v2.9.3 distinction
# between a granted permission and a temporarily disconnected Android service.
old_status='Accessibilité toujours autorisée — reconnexion Android en cours, lease conservé'
new_status='Accessibilité en reconnexion — autorisation toujours accordée, lease conservé'
if old_status not in s: raise SystemExit('RobotService accessibility reconnect status anchor missing')
s=s.replace(old_status,new_status,1)

p.write_text(s,encoding='utf-8')
print('B.I.R. v2.9.3 Android fixups applied')
