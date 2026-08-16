from pathlib import Path


def read(p): return Path(p).read_text(encoding='utf-8')
def write(p,t): Path(p).write_text(t,encoding='utf-8')
def once(p,old,new):
    text=read(p)
    if old not in text: raise SystemExit('missing anchor in %s: %r' % (p,old[:120]))
    write(p,text.replace(old,new,1))

# Native action whitelist.
once('app/src/main/java/com/profitloop/blueauto/ApiClient.java',
'owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist)',
'owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist|owner_tchoronko_save)')

# Worker route.
once('cloudflare/src/index.js',
"        case 'owner_assist': return await ownerAssist(request, env, auth, input, headers);\n        case 'device_control_poll':",
"        case 'owner_assist': return await ownerAssist(request, env, auth, input, headers);\n        case 'owner_tchoronko_save': return await ownerTchoronkoSave(request, env, auth, input, headers);\n        case 'device_control_poll':")

# Audited owner-only Tchoronko upsert. It preserves the strict DAE->DSM->POS grammar.
worker=read('cloudflare/src/index.js')
anchor='async function deviceControlPoll(env, auth, headers) {'
fn=r'''async function ownerTchoronkoSave(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');
  const role = String(input.role||'').trim().toUpperCase();
  if (!['DSM','POS'].includes(role)) throw new ApiError('TCHORONKO_ROLE_INVALID','Un Tchoronko doit être DSM ou POS.',422);
  const node = nodeCode(input.node_code), parent = nodeCode(input.parent_node_code);
  const phone = String(input.phone_number||'').replace(/\D/g,'');
  if (!/^6\d{8}$/.test(phone)) throw new ApiError('PHONE_INVALID','Numéro Blue Tchoronko invalide.',422);
  const parentRow = await env.DB.prepare('SELECT node_code,role FROM nodes WHERE node_code=? AND active=1 LIMIT 1').bind(parent).first();
  const requiredParent = role === 'DSM' ? 'DAE' : 'DSM';
  if (!parentRow || parentRow.role !== requiredParent) throw new ApiError('TCHORONKO_PARENT_INVALID',`Un ${role} doit dépendre directement d'un ${requiredParent}.`,422);
  const existing = await env.DB.prepare('SELECT node_code,role,parent_node_code FROM nodes WHERE node_code=? LIMIT 1').bind(node).first();
  if (existing && existing.role !== role) throw new ApiError('TCHORONKO_ROLE_CONFLICT','Ce code existe déjà avec un autre rôle.',409);
  if (existing) {
    await env.DB.prepare('UPDATE nodes SET phone_number=?,parent_node_code=?,active=1 WHERE node_code=?').bind(phone,parent,node).run();
  } else {
    await env.DB.prepare('INSERT INTO nodes(node_code,role,phone_number,parent_node_code,active) VALUES(?,?,?,?,1)').bind(node,role,phone,parent).run();
  }
  await env.DB.prepare(`INSERT INTO shadow_accounts(node_code,terminal_type,display_name,zone,notes,updated_at)
      VALUES(?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))
      ON CONFLICT(node_code) DO UPDATE SET terminal_type=excluded.terminal_type,display_name=excluded.display_name,zone=excluded.zone,notes=excluded.notes,updated_at=excluded.updated_at`)
    .bind(node,'TCHORONKO_SHADOW',cleanText(input.display_name||node,120),cleanText(input.zone||'',120),cleanText(input.notes||'',500)).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_TCHORONKO_SAVE',node,null,{role,parent_node_code:parent,phone_number:phone},'ACCEPTED');
  return success({saved:true,node_code:node,role,parent_node_code:parent,terminal_type:'TCHORONKO_SHADOW'},200,headers);
}

'''
if 'async function ownerTchoronkoSave(' not in worker:
    if anchor not in worker: raise SystemExit('owner Tchoronko insertion anchor missing')
    worker=worker.replace(anchor,fn+anchor,1)
write('cloudflare/src/index.js',worker)

# ADMIN UI: dedicated audited management card.
ui=read('app/src/main/assets/control-tower-v280.js')
old="add(support,'<article id=\"v280AdminAssist\" class=\"panel v280-card\"><p class=\"eyebrow\">'+t('ASSISTANCE UTILISATEUR','USER ASSISTANCE')+"
if old not in ui: raise SystemExit('admin assist UI anchor missing')
card="add(fleet,'<article id=\"v280AdminTchoronko\" class=\"panel v280-card\"><p class=\"eyebrow\">TCHORONKOS</p><h3>'+t('Créer / rattacher un DSM ou PoS Tchoronko','Create / attach a DSM or PoS Tchoronko')+'</h3><select id=\"v280TchoRole\"><option value=\"DSM\">DSM</option><option value=\"POS\">PoS</option></select><input id=\"v280TchoNode\" placeholder=\"'+t('Code du nœud Tchoronko','Tchoronko node code')+'\"><input id=\"v280TchoParent\" placeholder=\"'+t('Supérieur direct DAE/DSM','Direct DAE/DSM superior')+'\"><input id=\"v280TchoPhone\" inputmode=\"numeric\" placeholder=\"'+t('Numéro Blue','Blue number')+'\"><input id=\"v280TchoName\" placeholder=\"'+t('Nom / libellé','Name / label')+'\"><input id=\"v280TchoZone\" placeholder=\"'+t('Zone','Area')+'\"><button id=\"v280TchoSave\">'+t('ENREGISTRER LE TCHORONKO','SAVE TCHORONKO')+'</button><p class=\"muted\">'+t('L’ADMIN peut réparer le rattachement, mais la hiérarchie DAE → DSM → PoS reste obligatoire et toute modification est auditée.','ADMIN can repair attachment, but the DAE → DSM → PoS hierarchy remains mandatory and every change is audited.')+'</p></article>',true);\n"
ui=ui.replace(old,card+old,1)
bind_anchor="bind('v280AdminRefresh',function(){request('owner_snapshot',{});});"
insert="bind('v280TchoSave',function(){request('owner_tchoronko_save',{role:val('v280TchoRole'),node_code:val('v280TchoNode'),parent_node_code:val('v280TchoParent'),phone_number:val('v280TchoPhone'),display_name:val('v280TchoName'),zone:val('v280TchoZone')});});"
if insert not in ui:
    if bind_anchor not in ui: raise SystemExit('admin bind anchor missing')
    ui=ui.replace(bind_anchor,insert+bind_anchor,1)
callback="else if(action==='owner_control'){alert(t('Commande de contrôle mise en file et auditée.','Control command queued and audited.'));}"
replacement="else if(action==='owner_tchoronko_save'){alert(t('Tchoronko enregistré et hiérarchie auditée.','Tchoronko saved and hierarchy audited.'));request('owner_snapshot',{});}else if(action==='owner_control'){alert(t('Commande de contrôle mise en file et auditée.','Control command queued and audited.'));}"
if callback not in ui: raise SystemExit('platform callback anchor missing')
ui=ui.replace(callback,replacement,1)
write('app/src/main/assets/control-tower-v280.js',ui)

# Contract.
p='app/src/test/v280-operations-admin-contract.mjs'
test=read(p)
anchor="ok(worker.includes(\"case 'owner_snapshot'\")&&worker.includes(\"case 'owner_control'\")&&worker.includes(\"case 'owner_assist'\")&&worker.includes('authenticateOwner'),'server owner control source');"
addition=anchor+"\nok(worker.includes(\"case 'owner_tchoronko_save'\")&&worker.includes('ownerTchoronkoSave')&&v280.includes('v280AdminTchoronko'),'ADMIN must manage Tchoronkos with audited strict hierarchy');"
if addition not in test:
    if anchor not in test: raise SystemExit('v280 owner contract anchor missing')
    test=test.replace(anchor,addition,1)
write(p,test)
print('B.I.R. v2.8 audited ADMIN Tchoronko management added')
