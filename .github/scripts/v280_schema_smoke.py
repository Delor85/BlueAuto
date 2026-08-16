from pathlib import Path
import sqlite3

conn=sqlite3.connect(':memory:')
conn.execute('PRAGMA foreign_keys=ON')
for migration in sorted(Path('cloudflare/migrations').glob('*.sql')):
    conn.executescript(migration.read_text(encoding='utf-8'))

# Prove the schema expected by v2.8 can be created in exact migration order without touching D1.
required={
    'nodes': {'node_code','role','default_commission_bps'},
    'devices': {'device_id','node_code','mode','robot_enabled','sim_verified','sim_slot'},
    'account_balances': {'node_code','balance','balance_quality','evidence_kind','observed_at','operator_event_at'},
    'commands': {'public_id','requested_base_amount','commission_rate_bps','commission_amount'},
    'shadow_accounts': {'node_code','terminal_type','display_name','zone'},
    'owner_entitlements': {'entitlement_id','kind','bound_device_id','token_hash','active'},
    'admin_audit_log': {'id','action','target_node_code','target_device_id'},
    'device_control_actions': {'id','target_device_id','target_node_code','action','state'},
    'admin_assist_requests': {'id','target_node_code','request_type','requires_user_confirmation'},
}
for table, expected in required.items():
    cols={row[1] for row in conn.execute('PRAGMA table_info(%s)' % table)}
    missing=expected-cols
    if missing: raise SystemExit('%s missing columns: %s' % (table,sorted(missing)))

# Owner national snapshot SQL must use only persisted columns.
conn.execute('''SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.created_at,
 n.default_commission_bps,b.balance,b.balance_quality,b.evidence_kind,b.observed_at,b.operator_event_at,
 s.terminal_type,s.display_name,s.zone
 FROM nodes n LEFT JOIN account_balances b ON b.node_code=n.node_code
 LEFT JOIN shadow_accounts s ON s.node_code=n.node_code ORDER BY n.role,n.node_code''').fetchall()
conn.execute('''SELECT device_id,node_code,mode,device_name,active,robot_enabled,sim_verified,sim_slot,
 app_version,android_version,last_seen_at,created_at FROM devices ORDER BY node_code,last_seen_at DESC''').fetchall()

print('B.I.R. v2.8 D1 migration chain + owner-admin schema smoke OK')
