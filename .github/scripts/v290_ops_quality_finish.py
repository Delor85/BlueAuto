from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')

def replace_once(text, old, new, label):
    if old in text:
        if text.count(old) != 1:
            raise SystemExit(f'{label}: expected one anchor, got {text.count(old)}')
        return text.replace(old, new, 1)
    if new in text:
        return text
    raise SystemExit(f'{label}: anchor missing')

# Native API allowlist -------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/ApiClient.java'
s = read(p)
s = replace_once(
    s,
    '|ops_cockpit|ops_escalate|ops_resolve|owner_ops_cockpit|owner_snapshot|',
    '|ops_cockpit|ops_escalate|ops_resolve|owner_ops_cockpit|owner_ops_resolve|owner_snapshot|',
    'ApiClient owner_ops_resolve allowlist')
write(p, s)

# Senior-friendly cockpit ----------------------------------------------------
p = 'app/src/main/assets/control-tower-v290-ops.js'
s = read(p)
old = "id('v290OpsSync').textContent=(s.sync_rate_percent==null?'—':s.sync_rate_percent+' %');id('v290OpsSyncText').textContent=t('événements confirmés serveur','server-confirmed events');"
new = "var confirmed=Number(s.sync_confirmed_events||0),pending=Number(s.pending_events_last_reported||0),hours=Number(s.sync_window_hours||24);id('v290OpsSync').textContent=(s.sync_rate_percent==null?confirmed+' ✓':s.sync_rate_percent+' %');id('v290OpsSyncText').textContent=t(confirmed+' confirmés / '+pending+' en attente (dernier état, '+hours+' h)',confirmed+' confirmed / '+pending+' pending (last known, '+hours+' h)');"
s = replace_once(s, old, new, 'honest continuity card')
old = "buttons[i].onclick=function(){req('ops_resolve',{escalation_id:this.getAttribute('data-v290-resolve')});};"
new = "buttons[i].onclick=function(){req(c.owner_admin_workspace?'owner_ops_resolve':'ops_resolve',{escalation_id:this.getAttribute('data-v290-resolve')});};"
s = replace_once(s, old, new, 'owner escalation resolution UI')
old = "else if(a==='ops_escalate'||a==='ops_resolve')load();"
new = "else if(a==='ops_escalate'||a==='ops_resolve'||a==='owner_ops_resolve')load();"
s = replace_once(s, old, new, 'owner resolution refresh')
write(p, s)

# Worker --------------------------------------------------------------------
p = 'cloudflare/src/index.js'
s = read(p)
s = replace_once(
    s,
    "        case 'owner_ops_cockpit': return await ownerOpsCockpit(request, env, auth, headers);",
    "        case 'owner_ops_cockpit': return await ownerOpsCockpit(request, env, auth, headers);\n        case 'owner_ops_resolve': return await ownerOpsResolve(request, env, auth, input, headers);",
    'owner_ops_resolve route')

old = '''async function continuitySummary(env, scopeNode) {
  const events = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT received_via,COUNT(*) AS c FROM offline_events e JOIN tree t ON t.node_code=e.source_node_code GROUP BY received_via").bind(scopeNode).all();
  let direct=0,relay=0; for (const row of events.results||[]) {if(row.received_via==='BIR_RELAY')relay+=Number(row.c||0);else direct+=Number(row.c||0);}
  return {direct,relay,total:direct+relay,rate:direct+relay?100:null};
}'''
new = '''async function continuitySummary(env, scopeNode) {
  const events = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT received_via,COUNT(*) AS c FROM offline_events e JOIN tree t ON t.node_code=e.source_node_code WHERE e.received_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') GROUP BY received_via").bind(scopeNode).all();
  const pending = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT COALESCE(SUM(d.offline_pending_events),0) AS pending FROM devices d JOIN tree t ON t.node_code=d.node_code WHERE d.active=1").bind(scopeNode).first();
  let direct=0,relay=0; for (const row of events.results||[]) {if(row.received_via==='BIR_RELAY')relay+=Number(row.c||0);else direct+=Number(row.c||0);}
  const total=direct+relay, pendingReported=Number(pending?.pending||0), denominator=total+pendingReported;
  return {direct,relay,total,pending_reported:pendingReported,window_hours:24,rate:denominator?Math.round(total*1000/denominator)/10:null};
}'''
s = replace_once(s, old, new, '24h continuity denominator')

old = "summary:{healthy_robots:healthy,robot_count:robots,sync_rate_percent:continuity.rate,max_severity:max,next_action:"
new = "summary:{healthy_robots:healthy,robot_count:robots,sync_rate_percent:continuity.rate,sync_confirmed_events:continuity.total,pending_events_last_reported:continuity.pending_reported,sync_window_hours:continuity.window_hours,max_severity:max,next_action:"
s = replace_once(s, old, new, 'role cockpit continuity metadata')

old = '''  const open=await env.DB.prepare("SELECT * FROM ops_escalations WHERE state='OPEN' AND assigned_to='ADMIN' ORDER BY created_at DESC LIMIT 200").all();const continuity=await env.DB.prepare("SELECT received_via,COUNT(*) AS c FROM offline_events GROUP BY received_via").all();let direct=0,relay=0;for(const x of continuity.results||[]){if(x.received_via==='BIR_RELAY')relay+=Number(x.c||0);else direct+=Number(x.c||0);}const tx=await env.DB.prepare("SELECT COALESCE(SUM(commission_amount),0) AS commission FROM commands WHERE state='SUCCEEDED' AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").first();const alerts=health.filter(x=>x.severity!=='OK');'''
new = '''  const open=await env.DB.prepare("SELECT * FROM ops_escalations WHERE state='OPEN' AND assigned_to='ADMIN' ORDER BY created_at DESC LIMIT 200").all();
  const continuity=await env.DB.prepare("SELECT received_via,COUNT(*) AS c FROM offline_events WHERE received_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') GROUP BY received_via").all();
  let direct=0,relay=0;for(const x of continuity.results||[]){if(x.received_via==='BIR_RELAY')relay+=Number(x.c||0);else direct+=Number(x.c||0);}
  const pendingRow=await env.DB.prepare("SELECT COALESCE(SUM(offline_pending_events),0) AS pending FROM devices WHERE active=1").first();
  const pendingReported=Number(pendingRow?.pending||0), confirmed=direct+relay, continuityDenominator=confirmed+pendingReported;
  const syncRate=continuityDenominator?Math.round(confirmed*1000/continuityDenominator)/10:null;
  const tx=await env.DB.prepare("SELECT COALESCE(SUM(commission_amount),0) AS commission FROM commands WHERE state='SUCCEEDED' AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").first();const alerts=health.filter(x=>x.severity!=='OK');'''
s = replace_once(s, old, new, 'owner continuity inputs')

old = "escalations:(open.results||[]).map(x=>({...x,can_resolve:false,routing_label:'Escalade DAE → ADMIN'})),summary:{healthy_robots:health.filter(x=>x.robot_enabled&&!x.telemetry_stale&&x.severity==='OK').length,robot_count:health.filter(x=>x.device_id).length,sync_rate_percent:direct+relay?100:null,max_severity:"
new = "escalations:(open.results||[]).map(x=>({...x,can_resolve:true,routing_label:'Escalade DAE → ADMIN'})),summary:{healthy_robots:health.filter(x=>x.robot_enabled&&!x.telemetry_stale&&x.severity==='OK').length,robot_count:health.filter(x=>x.device_id).length,sync_rate_percent:syncRate,sync_confirmed_events:confirmed,pending_events_last_reported:pendingReported,sync_window_hours:24,max_severity:"
s = replace_once(s, old, new, 'owner cockpit resolve and honest KPI')

anchor = '''}


async function shadowEnroll(env, auth, input, headers) {'''
addition = '''}

async function ownerOpsResolve(request, env, auth, input, headers) {
  const owner=await authenticateOwnerAny(request,env,auth);
  const id=String(input.escalation_id||'').trim();
  if(!id)throw new ApiError('ESCALATION_ID_REQUIRED','Identifiant d’escalade requis.',422);
  const row=await env.DB.prepare("SELECT * FROM ops_escalations WHERE public_id=? AND state='OPEN' AND assigned_to='ADMIN'").bind(id).first();
  if(!row)throw new ApiError('ESCALATION_NOT_FOUND','Escalade ADMIN introuvable ou déjà clôturée.',404);
  await env.DB.prepare("UPDATE ops_escalations SET state='RESOLVED',resolved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE public_id=? AND state='OPEN' AND assigned_to='ADMIN'").bind(id).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_OPS_RESOLVE',row.target_node_code,auth.device_id,{escalation_id:id,raised_by_node_code:row.raised_by_node_code,severity:row.severity},'ACCEPTED');
  return success({public_id:id,state:'RESOLVED',target_node_code:row.target_node_code},200,headers);
}


async function shadowEnroll(env, auth, input, headers) {'''
s = replace_once(s, anchor, addition, 'owner resolver implementation')
write(p, s)

# Contract ------------------------------------------------------------------
p = 'app/src/test/v290-free-ops-contract.mjs'
s = read(p)
s = replace_once(
    s,
    "must(worker.includes(\"case 'ops_cockpit'\")&&worker.includes(\"case 'owner_ops_cockpit'\")&&worker.includes('opsEscalate'),'ops API missing');",
    "must(worker.includes(\"case 'ops_cockpit'\")&&worker.includes(\"case 'owner_ops_cockpit'\")&&worker.includes(\"case 'owner_ops_resolve'\")&&worker.includes('opsEscalate')&&worker.includes('ownerOpsResolve'),'ops API missing');",
    'contract owner resolver')
s = replace_once(
    s,
    "must(api.includes('ops_cockpit')&&api.includes('owner_ops_cockpit'),'native allowlist missing');",
    "must(api.includes('ops_cockpit')&&api.includes('owner_ops_cockpit')&&api.includes('owner_ops_resolve'),'native allowlist missing');\nmust(ops.includes(\"c.owner_admin_workspace?'owner_ops_resolve':'ops_resolve'\"),'owner escalation resolve routing missing');\nmust(worker.includes('pending_events_last_reported')&&worker.includes('sync_confirmed_events')&&worker.includes(\"'-24 hours'\"),'honest 24h continuity KPI missing');\nmust(!worker.includes('sync_rate_percent:direct+relay?100:null'),'misleading hard-coded 100% continuity KPI forbidden');\nmust(worker.includes(\"can_resolve:true,routing_label:'Escalade DAE → ADMIN'\"),'Admin must be able to resolve DAE escalations');",
    'contract honest continuity and admin resolve')
write(p, s)

# Decision record ------------------------------------------------------------
p = 'docs/BIR_V290_REPRISE_ET_DECISIONS.md'
s = read(p)
marker = '## Finition cockpit 2.9 — taux honnête et résolution Admin'
if marker not in s:
    s += '''\n\n## Finition cockpit 2.9 — taux honnête et résolution Admin\n- Le taux Continuity/Relay porte sur une fenêtre de 24 h et utilise les événements offline confirmés par le serveur plus les événements encore en attente selon la dernière télémétrie connue des appareils.\n- Le cockpit affiche simultanément le nombre confirmé et le nombre en attente ; aucune valeur 100 % n’est inventée lorsque le dénominateur est inconnu.\n- ADMIN / SUPER-ADMIN peuvent clôturer une escalade DAE → ADMIN via `owner_ops_resolve`, avec audit propriétaire.\n- La hiérarchie PoS → DSM → DAE → ADMIN reste inchangée ; cette finition ne donne aucun droit DAE direct supplémentaire sur les PoS.\n- Aucun PIN Blue, mot de passe, secret ou jeton n’est ajouté aux données du cockpit ou aux événements Relay.\n'''
write(p, s)

print('BIR v2.9 operations quality finish applied: honest continuity KPI + Admin escalation resolution')
