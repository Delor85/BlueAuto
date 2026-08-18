from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
p = ROOT / 'cloudflare/test/integration.mjs'
s = p.read_text(encoding='utf-8')
old = "    '0005_commission_policies_and_financial_quotes.sql']) {"
new = "    '0005_commission_policies_and_financial_quotes.sql', '0006_owner_admin_control_and_audit.sql',\n    '0007_offline_events_and_bir_relay.sql', '0008_v290_free_ops_cockpit.sql']) {"
if s.count(old) != 1:
    raise SystemExit(f'Unexpected integration migration anchor: {s.count(old)}')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('BIR v2.9 integration D1 harness aligned through migration 0008')
