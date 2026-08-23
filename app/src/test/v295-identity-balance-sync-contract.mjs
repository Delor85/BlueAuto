import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const need = (condition, message) => { if (!condition) throw new Error(message); };

const gradle = read('app/build.gradle');
const worker = read('cloudflare/src/index.js');
const migration = read('cloudflare/migrations/0011_canonical_identity_participant_results.sql');
const config = read('app/src/main/java/com/profitloop/blueauto/AppConfig.java');
const main = read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const parser = read('app/src/main/java/com/profitloop/blueauto/BlueMessageParser.java');
const sms = read('app/src/main/java/com/profitloop/blueauto/SmsReceiver.java');
const accessibility = read('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java');
const warRoom = read('app/src/main/assets/war-room-v294.js');
const recovery = read('app/src/main/assets/field-recovery-v291.js');
const controlTower = read('app/src/main/assets/control-tower-v2611.js');
const balanceGuard = read('app/src/main/assets/control-tower-v271.js');
const app = read('app/src/main/assets/app.js');
const pilotage = read('app/src/main/assets/pilotage-v292.js');
const manifest = read('app/src/main/AndroidManifest.xml');

need((gradle.includes('versionCode 60')||gradle.includes('versionCode 61')) && (gradle.includes('versionName "2.9.5"')||gradle.includes('versionName "2.9.6"')),
  'v2.9.5 Android identity missing');
need((worker.includes("const API_VERSION = '2.9.5-cloudflare'")||worker.includes("const API_VERSION = '2.9.6-cloudflare'")), 'v2.9.5 Worker identity missing');

need(migration.includes("official_node_code='POS1_DSM1_SU1'")
  && migration.includes("phone_number='621081275'"), 'confirmed POS1 field correction missing');
need(migration.includes('node_identity_aliases') && migration.includes('scope_parent_node_code'),
  'local aliases must be scoped to a parent tree');
need(worker.includes('officialNodeIdentity') && worker.includes('identityReferenceMatches'),
  'canonical identity projection/resolution missing');
need(config.includes('official_node_code') && main.includes('rememberOfficialIdentity'),
  'official identity must persist and refresh in Android');
need(app.includes('configuration.official_node_code||configuration.node_code')
  && app.includes('escapeHtml(displayNode(n))') && pilotage.includes('displayCode(x)'),
  'official identity must be used consistently by the main operational surfaces');

need(migration.includes('recipient_result_message') && migration.includes('recipient_balance_after'),
  'participant-specific results schema missing');
need(worker.includes("view.result_audience = 'RECIPIENT'")
  && worker.includes('confirmation Blue destinée à votre SIM'),
  'child must never receive the superior result message');
need(worker.includes("parsed.kind === 'TRANSFER_RECEIVED'")
  && worker.includes('linked_command_public_id'), 'recipient SMS correlation missing');

need(parser.indexOf('firstMoney(CURRENT_BALANCE') < parser.indexOf('firstMoney(BALANCE_FALLBACK'),
  'explicit Current Balance must win over voucher-stock wording');
need(sms.includes('CertifiedBalanceStore.observeTrusted')
  && sms.includes('!"BALANCE_CHILD".equals(activeOperation)'),
  'trusted SMS balance promotion/child isolation missing');
need(accessibility.includes('!"BALANCE_CHILD".equals(operation)'),
  'child balance query may still overwrite the superior local balance');
need(worker.includes("balance_quality='NEEDS_RECHECK'")
  && worker.includes("balance_quality = 'ESTIMATED'"),
  'post-transaction stale balance invalidation missing');
need(balanceGuard.includes("Date.now()-ts>60*60*1000")
  && balanceGuard.includes("own.balance_reusable===true&&own.balance_quality==='EXACT'")
  && !balanceGuard.includes("own.balance_reusable=true"),
  'legacy local cache may still override a server recertification requirement');

need(warRoom.includes("role==='POS'?'<span>Mon unique solde")
  && warRoom.includes('Mes 3 soldes — aucune valeur estimée'),
  'one-PoS / three-DAE-DSM balance rule missing');
need(warRoom.includes("balance_reusable===true") && warRoom.includes("balance_quality==='EXACT'"),
  'War Room may still expose an uncertain balance');
need(warRoom.includes('main.insertBefore(host,main.firstChild)'), 'War Room is not first on app open');
need(controlTower.includes("balance.style.display='none'")
  && controlTower.includes("duplicate.style.display='none'"), 'duplicate balance cards remain visible');

need(recovery.includes('robot_last_telemetry_at||row.robot_last_seen_at')
  && recovery.includes('file conservée'), 'truthful Robot freshness/recovery message missing');
need(!recovery.includes('Données Robot/serveur reçues à'),
  'local receipt time still impersonates Robot freshness');
need(worker.includes("effective_modes: ['REMOTE','ROBOT']")
  && !worker.includes("mode IN ('ROBOT','HYBRID')"), 'two-mode invariant lost');
need(!manifest.includes('android.permission.SEND_SMS'), 'SMS fallback permission is forbidden');
need(main.includes('relay_permissions') && warRoom.includes("action==='relay'")
  && read('app/src/main/java/com/profitloop/blueauto/RobotService.java').includes('BirRelayManager.maybeStart(this)'),
  'automatic event-only Relay recovery and its permission action are missing');
need(worker.includes("if (kind !== 'LOCAL_COMMAND_RESULT') return;")
  && worker.includes('command && command.executor_node_code === sourceNode')
  && !worker.includes('financial_command_over_relay = true'),
  'Relay must carry signed evidence only and must never create/replay a financial command');

console.log('B.I.R. v2.9.5 identity, participant messaging, truthful balance and Robot freshness contract OK');
