from pathlib import Path


def replace_once(text, old, new, label):
    if old not in text:
        if new in text:
            return text
        raise SystemExit(f'missing anchor for {label}')
    return text.replace(old, new, 1)

# Android release identity
p = Path('app/build.gradle')
s = p.read_text()
s = replace_once(s, 'versionCode 56', 'versionCode 57', 'versionCode')
s = replace_once(s, 'versionName "2.9.1"', 'versionName "2.9.2"', 'versionName')
p.write_text(s)

# Load the additive dashboard without disturbing the existing UI.
p = Path('app/src/main/assets/index.html')
s = p.read_text()
if 'pilotage-v292.css' not in s:
    s = replace_once(s, '<link rel="stylesheet" href="field-recovery-v291.css">', '<link rel="stylesheet" href="field-recovery-v291.css">\n    <link rel="stylesheet" href="pilotage-v292.css">', 'v292 css include')
if 'pilotage-v292.js' not in s:
    s = replace_once(s, '<script src="field-recovery-v291.js"></script>', '<script src="field-recovery-v291.js"></script>\n<script src="pilotage-v292.js"></script>', 'v292 js include')
p.write_text(s)

# Make the global service finder lead directly to the new simple cockpit and its free tools.
p = Path('app/src/main/assets/field-recovery-v291.js')
s = p.read_text()
anchor = "function serviceIndex(){return [\n"
items = "{n:'Tableau de bord simple / Pilotage',k:'tableau bord pilotage premium gratuit aujourd hui aider prevision gerer reseau',s:'#v292Pilot'},\n{n:'Continuité / Relay',k:'continuite relay synchronisation wifi bluetooth offline',s:'button[data-v292-tool=\"continuity\"]'},\n{n:'Files en attente',k:'file attente backlog evenement synchroniser bloquer',s:'button[data-v292-tool=\"queues\"]'},\n{n:'Santé Robots',k:'sante robot accessibilite batterie sim silencieux',s:'button[data-v292-tool=\"health\"]'},\n{n:'Business Health',k:'business health score qualite reseau disponibilite performance',s:'button[data-v292-tool=\"score\"]'},\n"
if "n:'Tableau de bord simple / Pilotage'" not in s:
    s = replace_once(s, anchor, anchor + items, 'service finder v292 entries')
p.write_text(s)

# Keep the old cockpit as a fallback but remove the impression that only DAE is Pro.
p = Path('app/src/main/assets/control-tower-v290-ops.js')
s = p.read_text()
s = s.replace("DAE PRO — GRATUIT EN v2.9", "B.I.R. COMPLET — GRATUIT")
s = s.replace("DAE PRO — FREE IN v2.9", "FULL B.I.R. — FREE")
s = s.replace("Tous ces outils sont inclus gratuitement dans B.I.R. 2.9.", "Tous ces outils sont inclus gratuitement pour tous dans B.I.R.")
s = s.replace("All these tools are included free in B.I.R. 2.9.", "All these tools are included free for everyone in B.I.R.")
p.write_text(s)

# Worker: free-for-all capability + strict hierarchical non-financial assistance.
p = Path('cloudflare/src/index.js')
s = p.read_text()
s = replace_once(s, "const API_VERSION = '2.9.1-cloudflare';", "const API_VERSION = '2.9.2-cloudflare';", 'worker version')
old_caps = "free_ops_cockpit: true, dae_pro_free: true, region_national_ops_free: true, owner_mock_entitlement: true"
new_caps = "free_ops_cockpit: true, premium_for_all: true, hierarchical_rescue: true, simple_pilotage: true, dae_pro_free: true, region_national_ops_free: true, owner_mock_entitlement: true"
if 'premium_for_all: true' not in s:
    s = replace_once(s, old_caps, new_caps, 'free premium capabilities')
if "case 'ops_assist':" not in s:
    s = replace_once(s, "case 'ops_cockpit': return await opsCockpit(env, auth, headers);", "case 'ops_cockpit': return await opsCockpit(env, auth, headers);\n        case 'ops_assist': return await opsAssist(env, auth, input, headers);", 'ops assist route')

helper = r'''
async function queueOpsSyncWake(env, targetNode, requestedByDeviceId, reason) {
  await env.DB.prepare("UPDATE sync_wake_requests SET state='EXPIRED' WHERE node_code=? AND state='PENDING' AND created_at<strftime('%Y-%m-%dT%H:%M:%fZ','now','-10 minutes')")
    .bind(targetNode).run();
  const robot = await env.DB.prepare("SELECT device_id,last_seen_at FROM devices WHERE node_code=? AND active=1 AND robot_enabled=1 AND sim_verified=1 AND mode IN ('ROBOT','HYBRID') ORDER BY last_seen_at DESC LIMIT 1")
    .bind(targetNode).first();
  if (!robot) return {queued:false,node_code:targetNode,reason:'NO_ACTIVE_ROBOT'};
  const pending = await env.DB.prepare("SELECT id,created_at FROM sync_wake_requests WHERE node_code=? AND state='PENDING' ORDER BY id DESC LIMIT 1")
    .bind(targetNode).first();
  if (pending) return {queued:true,duplicate_safe:true,wake_id:pending.id,node_code:targetNode,robot_device_id:robot.device_id};
  const result = await env.DB.prepare("INSERT INTO sync_wake_requests(node_code,requested_by_device_id,reason) VALUES(?,?,?)")
    .bind(targetNode,requestedByDeviceId,cleanText(reason||'OPS_ASSIST_SYNC',80)||'OPS_ASSIST_SYNC').run();
  return {queued:true,duplicate_safe:false,wake_id:Number(result.meta?.last_row_id||0),node_code:targetNode,robot_device_id:robot.device_id};
}

async function opsAssist(env, auth, input, headers) {
  rejectSensitiveRemotePayload(input || {});
  const action = String(input.action || 'WAKE_SYNC').trim().toUpperCase();
  if (action !== 'WAKE_SYNC') throw new ApiError('OPS_ASSIST_ACTION_INVALID','Seule la réparation de synchronisation non financière est autorisée ici.',422);
  const target = nodeCode(input.target_node_code || auth.node_code);
  let relation = '';
  if (auth.role === 'POS') {
    if (target !== auth.node_code) throw new ApiError('OPS_ASSIST_SCOPE','Un PoS ne répare que son propre compte.',403);
    relation = 'SELF';
  } else if (auth.role === 'DSM') {
    const child = await resolveDirectChild(env, auth.node_code, target, 'POS');
    if (!child) throw new ApiError('OPS_ASSIST_SCOPE','Le DSM aide uniquement un PoS direct.',403);
    relation = 'DSM_TO_DIRECT_POS';
  } else if (auth.role === 'DAE') {
    const dsm = await resolveDirectChild(env, auth.node_code, target, 'DSM');
    if (dsm) {
      relation = 'DAE_TO_DIRECT_DSM';
    } else {
      const escalated = await env.DB.prepare(
        "SELECT e.target_node_code,n.parent_node_code FROM ops_escalations e " +
        "JOIN nodes n ON n.node_code=e.target_node_code JOIN nodes p ON p.node_code=n.parent_node_code " +
        "WHERE e.state='OPEN' AND e.assigned_to=? AND e.target_node_code=? " +
        "AND e.severity IN ('HOT','CRITICAL') AND n.role='POS' AND p.role='DSM' AND p.parent_node_code=? LIMIT 1")
        .bind(auth.node_code,target,auth.node_code).first();
      if (!escalated) throw new ApiError('OPS_ASSIST_SCOPE','Le DAE aide ses DSM; un PoS exige une escalade HOT/CRITICAL du DSM.',403);
      relation = 'DAE_EXCEPTION_ESCALATED_POS';
    }
  } else {
    throw new ApiError('OPS_ASSIST_SCOPE','Rôle non autorisé pour cette aide.',403);
  }
  const queued = await queueOpsSyncWake(env,target,auth.device_id,input.reason||'PILOTAGE_V292');
  return success({...queued,assist_relation:relation,non_financial:true},queued.queued?202:200,headers);
}

'''
if 'async function opsAssist(env, auth, input, headers)' not in s:
    anchor = 'async function opsEscalate(env, auth, input, headers) {'
    if anchor not in s:
        raise SystemExit('missing opsEscalate anchor')
    s = s.replace(anchor, helper + anchor, 1)
p.write_text(s)

print('BIR v2.9.2 free premium pilotage patch applied')
