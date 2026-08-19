from pathlib import Path
import re

p=Path('cloudflare/src/index.js')
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    c=s.count(old)
    if c!=1: raise SystemExit(f'{label}: expected 1 anchor, got {c}')
    s=s.replace(old,new,1)

# Version/capabilities/routes.
once("const API_VERSION = '2.9.2-cloudflare';","const API_VERSION = '2.9.3-cloudflare';",'api version')
old="premium_for_all: true, hierarchical_rescue: true, simple_pilotage: true, dae_pro_free: true, region_national_ops_free: true, owner_mock_entitlement: true, accounting: true, tchoronko: true, event_balance: true, offline_sync: true, bir_relay: true, effective_modes: ['REMOTE','ROBOT']"
new="premium_for_all: true, hierarchical_rescue: true, simple_pilotage: true, dae_pro_free: true, region_national_ops_free: true, owner_mock_entitlement: true, accounting: true, tchoronko: true, event_balance: true, offline_sync: true, bir_relay: true, queue_reconciliation: true, lease_recovery: true, distribution_command_center: true, stockout_forecast: true, anomaly_detection: true, operator_incident_inference: true, reconciliation_center: true, effective_modes: ['REMOTE','ROBOT']"
once(old,new,'health capabilities')
once("        case 'lease_command': return await leaseCommand(env, auth, headers);","        case 'queue_snapshot': return await queueSnapshot(env, auth, headers);\n        case 'recover_lease': return await recoverLease(env, auth, input, headers);\n        case 'distribution_command_center': return await distributionCommandCenter(env, auth, headers);\n        case 'reconciliation_center': return await reconciliationCenter(env, auth, headers);\n        case 'owner_distribution_command_center': return await ownerDistributionCommandCenter(request, env, auth, headers);\n        case 'lease_command': return await leaseCommand(env, auth, headers);",'new routes')

# Duplicate attempts become telemetry, not another command.
old="""  if (previous) {\n    const availability = await robotAvailability(env, previous.executor_node_code);\n    return success({command: {...previous, ...availability}, duplicate: true}, 200, headers);\n  }\n"""
new="""  if (previous) {\n    try { await env.DB.prepare('INSERT INTO duplicate_request_audit(requester_node_code,existing_command_public_id,client_request_id,existing_state) VALUES(?,?,?,?)')\n      .bind(auth.node_code,previous.public_id,clientId,previous.state).run(); } catch (ignored) {}\n    const availability = await robotAvailability(env, previous.executor_node_code);\n    return success({command: {...previous, ...availability}, duplicate: true}, 200, headers);\n  }\n"""
once(old,new,'duplicate precheck telemetry')
old="""    if (duplicate) {\n      const availability = await robotAvailability(env, duplicate.executor_node_code);\n      return success({command: {...duplicate, ...availability}, duplicate: true}, 200, headers);\n    }\n"""
new="""    if (duplicate) {\n      try { await env.DB.prepare('INSERT INTO duplicate_request_audit(requester_node_code,existing_command_public_id,client_request_id,existing_state) VALUES(?,?,?,?)')\n        .bind(auth.node_code,duplicate.public_id,clientId,duplicate.state).run(); } catch (ignored) {}\n      const availability = await robotAvailability(env, duplicate.executor_node_code);\n      return success({command: {...duplicate, ...availability}, duplicate: true}, 200, headers);\n    }\n"""
once(old,new,'duplicate race telemetry')

# Dashboard: own/inbound commission is separate from downstream commercial policy.
once("'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, n.default_commission_bps, '","'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, n.default_commission_bps, n.inbound_commission_bps, '",'dashboard inbound select')
once("const defaultRate = Number(row.default_commission_bps || 0);\n      const baseEquivalent = balance == null ? null : maxBaseForTotal(balance, defaultRate);\n      return {...row, balance, default_commission_bps: defaultRate, reserved_amount: reserved,","const defaultRate = Number(row.default_commission_bps || 0);\n      const inboundRate = Number(row.inbound_commission_bps || (row.role === 'DAE' ? 1000 : row.role === 'DSM' ? 900 : row.role === 'POS' ? 800 : 0));\n      const baseEquivalent = balance == null ? null : maxBaseForTotal(balance, inboundRate);\n      return {...row, balance, default_commission_bps: defaultRate, inbound_commission_bps: inboundRate, reserved_amount: reserved,",'dashboard split rate')

# Lease expiry/release must clear device ownership.
once("+ 'lease_token_hash = NULL, leased_until = NULL, '","+ 'lease_token_hash = NULL, leased_until = NULL, leased_by_device_id = NULL, '",'expired lease owner clear')
old="""  const active = await env.DB.prepare(\n    \"SELECT public_id, state FROM commands WHERE executor_node_code = ? \"\n"""
new="""  const active = await env.DB.prepare(\n    \"SELECT public_id, state, leased_by_device_id, leased_until, updated_at FROM commands WHERE executor_node_code = ? \"\n"""
once(old,new,'active lease visibility')
old="""  const command = await env.DB.prepare(\n    \"UPDATE commands SET state = 'LEASED', attempt = attempt + 1, lease_token_hash = ?, \"\n    + \"leased_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'), \"\n    + \"updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') \"\n    + \"WHERE id = (SELECT id FROM commands WHERE executor_node_code = ? AND state = 'PENDING' ORDER BY id LIMIT 1) \"\n    + \"AND state = 'PENDING' RETURNING id, public_id, requester_node_code, executor_node_code, \"\n    + \"target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, requires_pin\"\n  ).bind(await sha256(leaseToken), auth.node_code).first();\n"""
new="""  const command = await env.DB.prepare(\n    \"UPDATE commands SET state = 'LEASED', attempt = attempt + 1, lease_token_hash = ?, leased_by_device_id = ?, \"\n    + \"leased_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'), \"\n    + \"updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') \"\n    + \"WHERE id = (SELECT id FROM commands WHERE executor_node_code = ? AND state = 'PENDING' ORDER BY id LIMIT 1) \"\n    + \"AND state = 'PENDING' RETURNING id, public_id, requester_node_code, executor_node_code, \"\n    + \"target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, requires_pin\"\n  ).bind(await sha256(leaseToken), auth.device_id, auth.node_code).first();\n"""
once(old,new,'lease owner assignment')
once("'SELECT id, state, executor_node_code, lease_token_hash FROM commands WHERE public_id = ?'","'SELECT id, state, executor_node_code, lease_token_hash, leased_by_device_id FROM commands WHERE public_id = ?'",'release owner select')
once("  if (!command.lease_token_hash || command.lease_token_hash !== await sha256(leaseToken)) {\n    throw new ApiError('LEASE_INVALID', 'Lease invalide ou expiré.', 409);\n  }","  if (command.leased_by_device_id && command.leased_by_device_id !== auth.device_id) {\n    throw new ApiError('LEASE_OWNER_MISMATCH', 'Ce lease appartient à un autre appareil Robot.', 409);\n  }\n  if (!command.lease_token_hash || command.lease_token_hash !== await sha256(leaseToken)) {\n    throw new ApiError('LEASE_INVALID', 'Lease invalide ou expiré.', 409);\n  }",'release owner fence')
once("+ 'lease_token_hash = NULL, leased_until = NULL, result_message = ?, '","+ 'lease_token_hash = NULL, leased_until = NULL, leased_by_device_id = NULL, result_message = ?, '",'release owner clear')

# Successful downstream supply records the effective inbound rate on the child, without altering
# the parent's chosen default/child pricing policy.
old="""async function applyTerminalEffects(env, command, state, message, publicId) {\n  await applyMercenaryTerminal(env, publicId, state);\n  const explicitEvidence = state === 'SUCCEEDED' ? explicitBalanceEvidence(command, message) : null;\n"""
new="""async function applyTerminalEffects(env, command, state, message, publicId) {\n  await applyMercenaryTerminal(env, publicId, state);\n  if (state === 'SUCCEEDED' && command.operation === 'DISTRIBUTION_TRANSFER'\n      && command.target_node_code && Number.isInteger(Number(command.commission_rate_bps))) {\n    const inbound = Math.max(0, Math.min(5000, Number(command.commission_rate_bps || 0)));\n    await env.DB.prepare('UPDATE nodes SET inbound_commission_bps=? WHERE node_code=?')\n      .bind(inbound, command.target_node_code).run();\n  }\n  const explicitEvidence = state === 'SUCCEEDED' ? explicitBalanceEvidence(command, message) : null;\n"""
once(old,new,'inbound commission terminal effect')

# Insert queue recovery + command center before leaseCommand.
anchor='async function leaseCommand(env, auth, headers) {'
if anchor not in s: raise SystemExit('leaseCommand anchor missing')
block=r'''
async function queueSnapshot(env, auth, headers) {
  const rows = await env.DB.prepare(
    "SELECT public_id,requester_node_code,executor_node_code,target_node_code,operation,command_kind,target_phone,amount,requested_base_amount,commission_rate_bps,commission_amount,state,result_message,operator_transaction_id,created_at,started_at,completed_at,updated_at "
    + "FROM commands WHERE requester_node_code=? OR executor_node_code=? OR target_node_code=? "
    + "ORDER BY CASE WHEN state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT') THEN 0 ELSE 1 END,id DESC LIMIT 80"
  ).bind(auth.node_code,auth.node_code,auth.node_code).all();
  const commands=(rows.results||[]).map(commandView);
  const active=commands.filter(c=>!TERMINAL_STATES.has(c.state));
  const pending=active.filter(c=>c.state==='PENDING');
  let oldest=0;
  for(const row of active){const age=row.created_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.created_at))/1000)):0;if(age>oldest)oldest=age;}
  return success({node_code:auth.node_code,generated_at:new Date().toISOString(),server_time_ms:Date.now(),pending_count:pending.length,active_count:active.length,oldest_pending_age_seconds:oldest,commands},200,headers);
}

async function recoverLease(env, auth, input, headers) {
  const publicId=String(input.command_id||'').trim();
  if(!publicId)throw new ApiError('COMMAND_REQUIRED','Commande à récupérer requise.',422);
  const current=await env.DB.prepare(
    'SELECT * FROM commands WHERE public_id=? AND executor_node_code=?'
  ).bind(publicId,auth.node_code).first();
  if(!current)throw new ApiError('COMMAND_NOT_FOUND','Commande introuvable pour ce Robot.',404);
  if(current.state!=='LEASED'){
    const verifyOnly=['DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT'].includes(current.state);
    return success({recovered:false,verify_only:verifyOnly,state:current.state,command:commandView(current)},200,headers);
  }
  if(!current.leased_by_device_id || current.leased_by_device_id!==auth.device_id){
    return success({recovered:false,verify_only:false,state:current.state,reason:'LEASE_OWNED_BY_ANOTHER_DEVICE'},200,headers);
  }
  const leaseToken=randomHex(24),hash=await sha256(leaseToken);
  const command=await env.DB.prepare(
    "UPDATE commands SET lease_token_hash=?,leased_until=strftime('%Y-%m-%dT%H:%M:%fZ','now','+120 seconds'),last_recovery_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
    + "WHERE id=? AND state='LEASED' AND leased_by_device_id=? RETURNING *"
  ).bind(hash,current.id,auth.device_id).first();
  if(!command)throw new ApiError('COMMAND_RACE','La commande a changé pendant la récupération.',409);
  await env.DB.prepare("INSERT INTO command_events(command_id,device_id,state,message) VALUES(?,?,'LEASED','Lease restauré sur le même appareil après perte de la copie locale; aucune recomposition préalable.')")
    .bind(command.id,auth.device_id).run();
  command.executor_phone=auth.phone_number;command.integrity_version=3;
  const integrityDigest=await commandDigest(command);
  return success({recovered:true,verify_only:false,command:{
    public_id:command.public_id,lease_token:leaseToken,requester_node_code:command.requester_node_code,
    executor_node_code:command.executor_node_code,executor_phone:command.executor_phone,
    target_node_code:command.target_node_code,operation:command.operation,command_kind:command.command_kind||'',
    command_argument:command.command_argument||'',target_phone:command.target_phone,amount:command.amount,
    requested_base_amount:command.requested_base_amount,commission_rate_bps:Number(command.commission_rate_bps||0),
    commission_amount:Number(command.commission_amount||0),ussd_code:command.ussd_code,requires_pin:Boolean(command.requires_pin),
    integrity_version:3,integrity_digest:integrityDigest
  }},200,headers);
}

function commandCenterRow(row){
  const balance=row.balance==null?null:Number(row.balance),out7=Number(row.outflow_7d||0),daily=out7/7;
  const daysCover=balance==null||daily<=0?null:Math.round((balance/daily)*10)/10;
  const terminal24=Number(row.success_24h||0)+Number(row.bad_24h||0);
  const failRate=terminal24?Math.round(Number(row.bad_24h||0)*1000/terminal24)/10:0;
  const balanceAge=row.balance_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.balance_at))/1000)):null;
  const robotAge=row.robot_last_seen_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.robot_last_seen_at))/1000)):null;
  const queueAge=row.oldest_queue_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.oldest_queue_at))/1000)):0;
  const anomalies=[];
  if(daysCover!=null&&daysCover<1)anomalies.push({code:'STOCKOUT_RISK',severity:'CRITICAL',message:'Couverture estimée inférieure à 1 jour.'});
  else if(daysCover!=null&&daysCover<3)anomalies.push({code:'STOCKOUT_RISK',severity:'WARN',message:'Couverture estimée inférieure à 3 jours.'});
  if(queueAge>900)anomalies.push({code:'QUEUE_STALE',severity:queueAge>3600?'CRITICAL':'WARN',message:'Commande active trop ancienne.'});
  if(terminal24>=5&&failRate>=20)anomalies.push({code:'FAILURE_SPIKE',severity:failRate>=50?'CRITICAL':'WARN',message:`Taux d'échec/à vérifier ${failRate} % sur 24 h.`});
  if(Number(row.duplicate_24h||0)>=3)anomalies.push({code:'DUPLICATE_SPIKE',severity:'WARN',message:`${Number(row.duplicate_24h)} tentative(s) anti-doublon sur 24 h.`});
  if(balanceAge==null||balanceAge>6*3600)anomalies.push({code:'BALANCE_STALE',severity:'INFO',message:'Preuve de solde ancienne ou absente.'});
  if(row.robot_enabled&&robotAge!=null&&robotAge>15*60)anomalies.push({code:'ROBOT_STALE',severity:'CRITICAL',message:'Robot déclaré actif mais télémétrie ancienne.'});
  if(row.robot_enabled&&row.accessibility_enabled&&!row.accessibility_connected)anomalies.push({code:'ACCESSIBILITY_DISCONNECTED',severity:'WARN',message:'Accessibilité autorisée mais service Android non connecté.'});
  return {...row,balance,outflow_7d:out7,daily_outflow_estimate:Math.round(daily*100)/100,days_cover:daysCover,stockout:daysCover==null?'UNKNOWN':daysCover<1?'CRITICAL':daysCover<3?'WATCH':'COMFORTABLE',failure_rate_24h:failRate,balance_age_seconds:balanceAge,robot_age_seconds:robotAge,oldest_queue_age_seconds:queueAge,anomalies};
}

async function distributionCommandCenterCore(env, rootNode, national=false) {
  const nodeSql=national
    ? "SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.default_commission_bps,n.inbound_commission_bps FROM nodes n WHERE n.active=1"
    : "WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree t ON n.parent_node_code=t.node_code WHERE n.active=1) SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.default_commission_bps,n.inbound_commission_bps FROM nodes n JOIN tree t ON t.node_code=n.node_code WHERE n.active=1";
  const nodes=national?(await env.DB.prepare(nodeSql).all()).results||[]:(await env.DB.prepare(nodeSql).bind(rootNode).all()).results||[];
  const output=[];
  for(const n of nodes){
    const balance=await env.DB.prepare('SELECT balance,balance_quality,evidence_kind,COALESCE(operator_event_at,observed_at) AS balance_at,last_transaction_id FROM account_balances WHERE node_code=?').bind(n.node_code).first();
    const flow=await env.DB.prepare("SELECT COALESCE(SUM(CASE WHEN state='SUCCEEDED' AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') THEN amount ELSE 0 END),0) outflow_7d,COALESCE(SUM(CASE WHEN created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') AND state='SUCCEEDED' THEN 1 ELSE 0 END),0) success_24h,COALESCE(SUM(CASE WHEN created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') AND state IN ('FAILED','UNKNOWN','BLOCKED') THEN 1 ELSE 0 END),0) bad_24h FROM commands WHERE executor_node_code=? AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").bind(n.node_code).first();
    const queue=await env.DB.prepare("SELECT COUNT(*) queue_count,MIN(created_at) oldest_queue_at FROM commands WHERE executor_node_code=? AND state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT')").bind(n.node_code).first();
    const dev=await env.DB.prepare("SELECT robot_enabled,accessibility_enabled,accessibility_connected,offline_pending_events,battery_percent,last_seen_at AS robot_last_seen_at,app_version,android_version,device_model FROM devices WHERE node_code=? AND active=1 ORDER BY robot_enabled DESC,last_seen_at DESC LIMIT 1").bind(n.node_code).first();
    const dup=await env.DB.prepare("SELECT COUNT(*) total FROM duplicate_request_audit WHERE requester_node_code=? AND observed_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours')").bind(n.node_code).first();
    output.push(commandCenterRow({...n,...(balance||{}),...(flow||{}),...(queue||{}),...(dev||{}),duplicate_24h:Number(dup?.total||0)}));
  }
  const anomalies=[];for(const n of output)for(const a of n.anomalies||[])anomalies.push({...a,node_code:n.node_code,role:n.role});
  const recent=national
    ? await env.DB.prepare("SELECT COUNT(*) total,COUNT(DISTINCT CASE WHEN state IN ('FAILED','UNKNOWN','BLOCKED') THEN executor_node_code END) bad_nodes,SUM(CASE WHEN state IN ('FAILED','UNKNOWN','BLOCKED') THEN 1 ELSE 0 END) bad FROM commands WHERE updated_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes') AND state IN ('SUCCEEDED','FAILED','UNKNOWN','BLOCKED')").first()
    : await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree t ON n.parent_node_code=t.node_code WHERE n.active=1) SELECT COUNT(*) total,COUNT(DISTINCT CASE WHEN c.state IN ('FAILED','UNKNOWN','BLOCKED') THEN c.executor_node_code END) bad_nodes,SUM(CASE WHEN c.state IN ('FAILED','UNKNOWN','BLOCKED') THEN 1 ELSE 0 END) bad FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.updated_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes') AND c.state IN ('SUCCEEDED','FAILED','UNKNOWN','BLOCKED')").bind(rootNode).first();
  const bad=Number(recent?.bad||0),total=Number(recent?.total||0),badNodes=Number(recent?.bad_nodes||0),ratio=total?bad/total:0;
  const serviceSignal=badNodes>=3&&total>=5&&ratio>=0.35
    ? {code:'PROBABLE_OPERATOR_INCIDENT',severity:'CRITICAL',message:'Des échecs ou états à vérifier sont corrélés sur plusieurs nœuds. Suspendre les répétitions inutiles et vérifier le service Blue.'}
    : badNodes===1&&bad>0?{code:'NODE_SPECIFIC_ANOMALY',severity:'WARN',message:'Le signal récent semble concentré sur un seul nœud/appareil.'}
    : {code:'SERVICE_STABLE',severity:'OK',message:'Aucun incident transversal significatif détecté dans les données B.I.R. récentes.'};
  const flows=national
    ? await env.DB.prepare("SELECT operation,COUNT(*) count,COALESCE(SUM(amount),0) amount FROM commands WHERE state='SUCCEEDED' AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') GROUP BY operation").all()
    : await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree t ON n.parent_node_code=t.node_code WHERE n.active=1) SELECT c.operation,COUNT(*) count,COALESCE(SUM(c.amount),0) amount FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.state='SUCCEEDED' AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') AND c.created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') GROUP BY c.operation").bind(rootNode).all();
  const critical=anomalies.filter(a=>a.severity==='CRITICAL').length,warn=anomalies.filter(a=>a.severity==='WARN').length;
  return {generated_at:new Date().toISOString(),scope:national?'NATIONAL':rootNode,summary:{nodes:output.length,critical,warn,stockout_critical:output.filter(n=>n.stockout==='CRITICAL').length,stockout_watch:output.filter(n=>n.stockout==='WATCH').length},service_signal:serviceSignal,flows_7d:flows.results||[],nodes:output,anomalies:anomalies.slice(0,500)};
}

async function distributionCommandCenter(env, auth, headers){return success(await distributionCommandCenterCore(env,auth.node_code,false),200,headers);}
async function ownerDistributionCommandCenter(request,env,auth,headers){const owner=await authenticateOwnerAny(request,env,auth);const data=await distributionCommandCenterCore(env,auth.node_code,true);await adminAudit(env,owner.entitlement_id,'DISTRIBUTION_COMMAND_CENTER',null,auth.device_id,{nodes:data.summary.nodes},'READ');return success(data,200,headers);}

async function reconciliationCenter(env,auth,headers){
  const commands=await env.DB.prepare("SELECT c.public_id,c.state,c.operation,c.amount,c.operator_transaction_id,c.created_at,c.completed_at,om.transaction_id,om.receipt_number,om.status AS operator_status,om.current_balance FROM commands c LEFT JOIN operator_messages om ON om.command_public_id=c.public_id WHERE (c.requester_node_code=? OR c.executor_node_code=? OR c.target_node_code=?) AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') ORDER BY c.id DESC LIMIT 300").bind(auth.node_code,auth.node_code,auth.node_code).all();
  const blueOnly=await env.DB.prepare("SELECT transaction_id,receipt_number,status,amount,current_balance,transaction_date,transaction_time,created_at FROM operator_messages WHERE node_code=? AND message_kind IN ('TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT') AND command_public_id IS NULL ORDER BY id DESC LIMIT 100").bind(auth.node_code).all();
  const evidence=await env.DB.prepare("SELECT COUNT(*) total,SUM(CASE WHEN accepted=1 THEN 1 ELSE 0 END) accepted,SUM(CASE WHEN accepted=0 THEN 1 ELSE 0 END) rejected FROM balance_evidence_log WHERE node_code=?").bind(auth.node_code).first();
  let matched=0,mismatch=0,birOnly=0;const rows=[];
  for(const r of commands.results||[]){let state='MATCHED',reason='Commande et preuve opérateur reliées.';if(!r.transaction_id&&!r.receipt_number){state='BIR_ONLY';reason='Commande financière sans preuve opérateur liée.';birOnly++;}else if(r.state==='SUCCEEDED'&&String(r.operator_status||'').toUpperCase()==='FAILED'){state='MISMATCH';reason='B.I.R. et preuve opérateur portent des états incompatibles.';mismatch++;}else matched++;rows.push({...r,reconciliation_state:state,reconciliation_reason:reason});}
  const imported=await env.DB.prepare("SELECT match_state,COUNT(*) total FROM reconciliation_rows GROUP BY match_state").all();
  return success({generated_at:new Date().toISOString(),node_code:auth.node_code,summary:{matched,mismatch,bir_only:birOnly,blue_only:(blueOnly.results||[]).length,balance_evidence_total:Number(evidence?.total||0),balance_evidence_accepted:Number(evidence?.accepted||0),balance_evidence_rejected:Number(evidence?.rejected||0)},transactions:rows,blue_only:blueOnly.results||[],imported_reconciliation:imported.results||[]},200,headers);
}

'''
s=s.replace(anchor,block+anchor,1)

p.write_text(s,encoding='utf-8')
print('B.I.R. v2.9.3 server queue/command-center patch applied')
