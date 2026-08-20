import fs from 'node:fs';

const read = p => fs.readFileSync(p, 'utf8');
const must = (ok, msg) => { if (!ok) throw new Error(msg); };
const gradle = read('app/build.gradle');
const index = read('app/src/main/assets/index.html');
const pilot = read('app/src/main/assets/pilotage-v292.js');
const field = read('app/src/main/assets/field-recovery-v291.js');
const api = read('app/src/main/java/com/profitloop/blueauto/ApiClient.java');
const main = read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const manifest = read('app/src/main/AndroidManifest.xml');
const worker = read('cloudflare/src/index.js');

must((gradle.includes('versionCode 57')||gradle.includes('versionCode 58')||gradle.includes('versionCode 60')) && (gradle.includes('versionName "2.9.2"')||gradle.includes('versionName "2.9.3"')||gradle.includes('versionName "2.9.5"')), 'v2.9.2+ identity missing');
must(index.includes('pilotage-v292.css') && index.includes('pilotage-v292.js'), 'v2.9.2 dashboard assets not loaded');
must(((api.match(/app_version", "2\.9\.[235]/g) || []).length) >= 2, 'native heartbeat/activation does not report a supported v2.9 release');
must(api.includes('|ops_cockpit|ops_assist|ops_escalate|'), 'ops_assist is not allowed through native bridge');
must((worker.includes("const API_VERSION = '2.9.2-cloudflare'")||worker.includes("const API_VERSION = '2.9.3-cloudflare'")||worker.includes("const API_VERSION = '2.9.5-cloudflare'")), 'Worker version mismatch');
must(worker.includes('premium_for_all: true') && worker.includes('hierarchical_rescue: true') && worker.includes('simple_pilotage: true'), 'free premium capabilities missing');
must(worker.includes("case 'ops_assist': return await opsAssist(env, auth, input, headers);"), 'ops_assist route missing');

must(pilot.includes('PREMIUM POUR TOUS — 0 FCFA'), 'free premium promise missing from dashboard');
for (const tool of ['Continuité / Relay','Files en attente','Santé Robots','Audit & preuves','Secours / SAV','Prévision','Commissions','Business Health']) {
  must(pilot.includes(tool), `dashboard tool missing: ${tool}`);
}
must(pilot.includes('Les PoS restent gérés au quotidien par leur DSM'), 'DAE/DSM separation missing in UI');
must(pilot.includes('Vos PoS sont votre domaine direct'), 'DSM direct-PoS responsibility missing in UI');
must(pilot.includes("role==='DAE')return r==='DSM'||(r==='POS'&&(s==='HOT'||s==='CRITICAL'))"), 'DAE UI assistance is not restricted to DSM / escalated hot PoS');
must(pilot.includes("role==='DSM'&&r==='POS'&&(s==='HOT'||s==='CRITICAL')"), 'DSM-to-DAE escalation not restricted to hot/critical');
must(pilot.includes('Score opérationnel explicable'), 'Business Health explainability missing');
must(pilot.includes('Il ne bloque jamais un utilisateur'), 'Business Health non-blocking rule missing');
must(field.includes("n:'Tableau de bord simple / Pilotage'") && field.includes("n:'Business Health'"), 'global service finder does not index v2.9.2 pilotage');

const start = worker.indexOf('async function opsAssist(env, auth, input, headers)');
const end = worker.indexOf('async function opsEscalate(env, auth, input, headers)', start);
must(start >= 0 && end > start, 'unable to isolate opsAssist');
const assist = worker.slice(start, end);
must(assist.includes("auth.role === 'POS'") && assist.includes("target !== auth.node_code"), 'PoS self-only server rule missing');
must(assist.includes("resolveDirectChild(env, auth.node_code, target, 'POS')"), 'DSM direct PoS server rule missing');
must(assist.includes("resolveDirectChild(env, auth.node_code, target, 'DSM')"), 'DAE direct DSM server rule missing');
must(assist.includes("e.severity IN ('HOT','CRITICAL')"), 'DAE exceptional PoS intervention is not HOT/CRITICAL gated');
must(assist.includes("e.assigned_to=?") && assist.includes("p.parent_node_code=?"), 'DAE exceptional PoS intervention is not assigned/scope gated');
must(assist.includes("action !== 'WAKE_SYNC'"), 'ops_assist accepts more than the non-financial wake action');
for (const forbidden of ['createCommand(', 'previewCommand(', 'INSERT INTO commands', 'RETAIL_TRANSFER', 'DISTRIBUTION_TRANSFER', 'ussd_code']) {
  must(!assist.includes(forbidden), `financial/USSD primitive leaked into ops_assist: ${forbidden}`);
}
must(assist.includes('rejectSensitiveRemotePayload(input || {})'), 'sensitive payload guard missing');
must(assist.includes('non_financial:true'), 'non-financial response proof missing');

must(!manifest.includes('android.permission.SEND_SMS'), 'SMS fallback permission reintroduced');
must(main.includes('new String[]{"REMOTE", "ROBOT"}'), 'effective Android modes changed');

console.log('BIR v2.9.2: premium gratuit, pilotage simple, hiérarchie DSM/DAE et aide non financière OK');
