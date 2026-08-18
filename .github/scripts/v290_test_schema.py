from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / 'cloudflare/test/integration.mjs'
s = p.read_text(encoding='utf-8')

old = "    '0005_commission_policies_and_financial_quotes.sql']) {"
new = "    '0005_commission_policies_and_financial_quotes.sql', '0006_owner_admin_control_and_audit.sql',\n    '0007_offline_events_and_bir_relay.sql', '0008_v290_free_ops_cockpit.sql']) {"
if old in s:
    s = s.replace(old, new, 1)
elif "'0008_v290_free_ops_cockpit.sql']) {" not in s:
    raise SystemExit('Unexpected integration migration list')

old_loop = "    for (const statement of schema.split(';').map(value => value.trim()).filter(Boolean)) {"
new_loop = "    for (const statement of schema.split(';').map(value => value.replace(/^--.*$/gm, '').trim()).filter(Boolean)) {"
if old_loop in s:
    s = s.replace(old_loop, new_loop, 1)
elif new_loop not in s:
    raise SystemExit('Unexpected integration SQL statement parser')

p.write_text(s, encoding='utf-8')
print('BIR v2.9 integration D1 harness aligned through migration 0008; comment-only SQL fragments ignored')
