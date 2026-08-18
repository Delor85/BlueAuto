from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
index = ROOT / 'cloudflare/src/index.js'
migration = ROOT / 'cloudflare/migrations/0007_offline_events_and_bir_relay.sql'
s = index.read_text(encoding='utf-8')
m = migration.read_text(encoding='utf-8')

required_index = [
    "const API_VERSION = '2.9.0-cloudflare';",
    "case 'sync_local_events': return await syncLocalEvents",
    "case 'relay_register': return await relayRegister",
    "case 'relay_sync': return await relaySync",
    'async function syncLocalEvents(env, auth, input, headers)',
    'async function relayRegister(env, auth, input, headers)',
    'async function relaySync(env, auth, input, headers)',
    "offline_sync: true",
    "bir_relay: true",
    "effective_modes: ['REMOTE','ROBOT']",
]
required_migration = [
    'CREATE TABLE IF NOT EXISTS relay_identities',
    'CREATE TABLE IF NOT EXISTS offline_events',
    'event_id TEXT PRIMARY KEY NOT NULL',
    "received_via TEXT NOT NULL CHECK (received_via IN ('DIRECT','BIR_RELAY'))",
]

missing = [x for x in required_index if x not in s] + [x for x in required_migration if x not in m]
if missing:
    raise SystemExit('v290 server source incomplete: ' + ' | '.join(missing))

for forbidden in ('DROP TABLE', 'DROP TABLE IF EXISTS'):
    if forbidden.lower() in m.lower():
        raise SystemExit('v290 migration must remain additive: ' + forbidden)

subprocess.check_call(['python3', '.github/scripts/v290_restore_inherited_tests.py'], cwd=ROOT)
print('BIR v2.9 server offline/Relay source already generated; idempotent verification OK')
