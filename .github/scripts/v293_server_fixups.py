from pathlib import Path

p=Path('cloudflare/src/index.js')
s=p.read_text(encoding='utf-8')
# devices exposes device_name, not a device_model column. Keep Android telemetry portable.
s=s.replace('battery_percent,last_seen_at AS robot_last_seen_at,app_version,android_version,device_model FROM devices',
            'battery_percent,last_seen_at AS robot_last_seen_at,app_version,android_version,device_name FROM devices')
# Terminal commands no longer need a lease owner. This is bookkeeping only; the DIALING fence remains.
old="+ 'leased_until = CASE WHEN ? = 1 THEN NULL ELSE leased_until END, '"
new="+ 'leased_until = CASE WHEN ? = 1 THEN NULL ELSE leased_until END, leased_by_device_id = CASE WHEN ? = 1 THEN NULL ELSE leased_by_device_id END, '"
if old not in s: raise SystemExit('terminal lease-owner cleanup anchor missing')
s=s.replace(old,new,1)
oldbind=".bind(nextState, message, operatorId, nextState, terminal ? 1 : 0, terminal ? 1 : 0, command.id, command.state),"
newbind=".bind(nextState, message, operatorId, nextState, terminal ? 1 : 0, terminal ? 1 : 0, terminal ? 1 : 0, command.id, command.state),"
if oldbind not in s: raise SystemExit('terminal bind anchor missing')
s=s.replace(oldbind,newbind,1)
p.write_text(s,encoding='utf-8')
print('B.I.R. v2.9.3 server fixups applied')
