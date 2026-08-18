from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def read(rel): return (ROOT / rel).read_text(encoding='utf-8')
def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
def once(text, old, new, label):
    count = text.count(old)
    if count != 1: raise SystemExit(f'v290 ops anchor {label}: expected 1, got {count}')
    return text.replace(old, new, 1)
def insert_before(text, anchor, addition, label):
    if anchor not in text: raise SystemExit(f'v290 ops anchor missing: {label}')
    if addition.strip() in text: return text
    return text.replace(anchor, addition + '\n' + anchor, 1)

# ---------------------------------------------------------------------------
# Android bridge/API: telemetry + free operations cockpit actions.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/ApiClient.java'; s=read(p)
# v2.9 generator already added JSONArray and offline methods.
old='payload.put("sim_slot", Math.max(0, AppConfig.simSlot(context, targetProfile)));\n        return postControl("heartbeat", payload, true);'
new='''payload.put("sim_slot", Math.max(0, AppConfig.simSlot(context, targetProfile)));
        payload.put("offline_pending_events", LocalEventStore.pendingCount(context));
        payload.put("accessibility_enabled", BlueAccessibilityService.isEnabled(context));
        payload.put("accessibility_connected", BlueAccessibilityService.isConnected());
        try {
            android.os.BatteryManager battery = (android.os.BatteryManager) context.getSystemService(Context.BATTERY_SERVICE);
            int level = battery == null ? -1 : battery.getIntProperty(android.os.BatteryManager.BATTERY_PROPERTY_CAPACITY);
            if (level >= 0 && level <= 100) payload.put("battery_percent", level);
        } catch (Exception ignored) {}
        return postControl("heartbeat", payload, true);'''
s=once(s,old,new,'heartbeat telemetry')
old='(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child|accounting_summary|transaction_ledger|owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist|owner_tchoronko_save)'
new='(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child|accounting_summary|transaction_ledger|ops_cockpit|ops_escalate|ops_resolve|owner_ops_cockpit|owner_snapshot|owner_transactions|owner_audit|owner_control|owner_assist|owner_tchoronko_save)'
s=once(s,old,new,'platform action allowlist')
write(p,s)

# ---------------------------------------------------------------------------
# MainActivity: distinct SUPERADMIN account. It shares the owner workspace shell
# but receives a separate SUPER_ADMIN entitlement. No PIN is ever bridged.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/MainActivity.java'; s=read(p)
s=once(s,
'    private static final String OWNER_ADMIN_WORKSPACE_KEY = "bir_owner_admin_workspace_v280";',
'    private static final String OWNER_ADMIN_WORKSPACE_KEY = "bir_owner_admin_workspace_v280";\n    private static final String SUPER_ADMIN_WORKSPACE_KEY = "bir_super_admin_workspace_v290";',
'super admin key')
s=once(s,
'    private static boolean adminSessionAuthorized;',
'    private static boolean adminSessionAuthorized;\n    private static boolean superAdminSessionAuthorized;',
'super admin session')
anchor='''    private boolean ownerSessionExpired() {'''
addition='''    private boolean isSuperAdminWorkspaceActive() {
        return superAdminSessionAuthorized && !ownerSessionExpired()
                && AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)
                && AppConfig.prefs(this).getBoolean(SUPER_ADMIN_WORKSPACE_KEY, false)
                && SecureOwnerStore.has(this, "SUPER_ADMIN");
    }
'''
s=insert_before(s,anchor,addition,'super workspace predicate')
s=once(s,
'        boolean hadOwnerSession = mockSessionAuthorized || adminSessionAuthorized\n                || AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false)\n                || AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false);',
'        boolean hadOwnerSession = mockSessionAuthorized || adminSessionAuthorized || superAdminSessionAuthorized\n                || AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false)\n                || AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                || AppConfig.prefs(this).getBoolean(SUPER_ADMIN_WORKSPACE_KEY, false);',
'expiry include super')
s=once(s,'        adminSessionAuthorized = false;','        adminSessionAuthorized = false;\n        superAdminSessionAuthorized = false;','expiry session clear')
s=once(s,
'                .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                .remove(MOCK_RETURN_PROFILE_KEY)',
'                .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                .putBoolean(SUPER_ADMIN_WORKSPACE_KEY, false)\n                .remove(MOCK_RETURN_PROFILE_KEY)',
'expiry workspace clear')
s=once(s,
'        if (mockSessionAuthorized || adminSessionAuthorized) touchOwnerSession();',
'        if (mockSessionAuthorized || adminSessionAuthorized || superAdminSessionAuthorized) touchOwnerSession();',
'super activity touch')
# Add super enrollment beside existing owner admin method.
anchor='''    private void showPairingScreen(boolean addingAccount) {'''
addition='''    private void openSuperAdminFromPairing(String code, TextView feedback) {
        if (!AppConfig.hasProfiles(this)) {
            feedback.setText(ui("Ajoutez d’abord au moins un compte Blue réel sur ce téléphone.",
                    "Add at least one real Blue account on this phone first."));
            feedback.setTextColor(Color.rgb(255, 139, 152)); return;
        }
        if (!SecureOwnerStore.has(this, "OWNER_ADMIN")) {
            feedback.setText(ui("Activez d’abord ADMIN sur ce même téléphone. SUPER-ADMIN est une promotion unique d’un ADMIN déjà autorisé.",
                    "Activate ADMIN on this same phone first. SUPER-ADMIN is a unique promotion of an already authorized ADMIN."));
            feedback.setTextColor(GOLD); return;
        }
        if (code == null || code.trim().length() < 24) {
            feedback.setText(ui("Code SUPER-ADMIN incomplet.", "Incomplete SUPER-ADMIN code."));
            feedback.setTextColor(Color.rgb(255, 139, 152)); return;
        }
        feedback.setTextColor(CYAN);
        feedback.setText(ui("Vérification de l’unique entitlement SUPER-ADMIN…", "Checking the unique SUPER-ADMIN entitlement…"));
        new Thread(() -> {
            try {
                JSONObject data = new ApiClient(this).ownerEnroll("SUPER_ADMIN", code.trim());
                String token = data.optString("owner_token", "");
                String entitlementId = data.optString("entitlement_id", "");
                SecureOwnerStore.save(this, "SUPER_ADMIN", entitlementId, token);
                superAdminSessionAuthorized = true; adminSessionAuthorized = false; touchOwnerSession();
                AppConfig.prefs(this).edit()
                        .putString(OWNER_ADMIN_RETURN_PROFILE_KEY, AppConfig.profileId(this))
                        .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, true)
                        .putBoolean(SUPER_ADMIN_WORKSPACE_KEY, true).commit();
                runOnUiThread(this::recreate);
            } catch (Exception error) {
                runOnUiThread(() -> { feedback.setTextColor(Color.rgb(255, 139, 152));
                    feedback.setText(ui("SUPER-ADMIN non activé : ", "SUPER-ADMIN not enabled: ") + readable(error)); });
            }
        }, "BIR-SuperAdminEnroll-v290").start();
    }
'''
s=insert_before(s,anchor,addition,'super enroll method')
# Pairing field/hints and routing. Reuse existing secret EditText so no additional secret surface exists.
s=s.replace('Identifiant Blue (ex. OU3, DSM7_OU3, POS16_DSM7_OU3) — ou MOCK / ADMIN',
            'Identifiant Blue (ex. OU3, DSM7_OU3, POS16_DSM7_OU3) — ou MOCK / ADMIN / SUPERADMIN')
s=s.replace('Blue ID (e.g. OU3, DSM7_OU3, POS16_DSM7_OU3) — or MOCK / ADMIN',
            'Blue ID (e.g. OU3, DSM7_OU3, POS16_DSM7_OU3) — or MOCK / ADMIN / SUPERADMIN')
s=s.replace('Code privé ADMIN propriétaire', 'Code privé ADMIN / SUPER-ADMIN propriétaire')
s=s.replace('Private owner ADMIN code', 'Private owner ADMIN / SUPER-ADMIN code')
s=once(s,
'                boolean admin = "ADMIN".equalsIgnoreCase(requested);',
'                boolean admin = "ADMIN".equalsIgnoreCase(requested) || "SUPERADMIN".equalsIgnoreCase(requested);',
'pair special super')
s=once(s,
'            if ("ADMIN".equals(node)) {\n                openOwnerAdminFromPairing(adminCode.getText().toString().trim(), feedback);\n                return;\n            }',
'            if ("ADMIN".equals(node)) {\n                openOwnerAdminFromPairing(adminCode.getText().toString().trim(), feedback);\n                return;\n            }\n            if ("SUPERADMIN".equals(node)) {\n                openSuperAdminFromPairing(adminCode.getText().toString().trim(), feedback);\n                return;\n            }',
'pair super route')
# Configuration only exposes role booleans and PIN presence, never PIN value.
s=once(s,
'                value.put("owner_admin_workspace", isOwnerAdminWorkspaceActive());',
'                value.put("owner_admin_workspace", isOwnerAdminWorkspaceActive() || isSuperAdminWorkspaceActive());\n                value.put("super_admin_workspace", isSuperAdminWorkspaceActive());',
'config super')
# Exit owner workspace clears both privilege workspaces.
s=s.replace('.putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                        .remove(OWNER_ADMIN_RETURN_PROFILE_KEY)',
            '.putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                        .putBoolean(SUPER_ADMIN_WORKSPACE_KEY, false)\n                        .remove(OWNER_ADMIN_RETURN_PROFILE_KEY)')
anchor='''        @JavascriptInterface
        public void exitOwnerAdminWorkspace() {'''
addition='''        @JavascriptInterface
        public boolean isSuperAdminWorkspace() { return isSuperAdminWorkspaceActive(); }
'''
s=insert_before(s,anchor,addition,'bridge super predicate')
# platformAction chooses entitlement by workspace and never passes any PIN.
old='''                    if (normalizedAction.startsWith("owner_")) {
                        if (!isOwnerAdminWorkspaceActive()) throw new SecurityException("Compte ADMIN propriétaire requis.");
                        String ownerToken = SecureOwnerStore.token(MainActivity.this, "OWNER_ADMIN");
                        if (ownerToken.isEmpty()) throw new SecurityException("Entitlement ADMIN absent ou illisible.");
                        client.withOwnerToken(ownerToken);
                    }'''
new='''                    if (normalizedAction.startsWith("owner_")) {
                        boolean superAdmin = isSuperAdminWorkspaceActive();
                        if (!superAdmin && !isOwnerAdminWorkspaceActive()) throw new SecurityException("Compte ADMIN / SUPER-ADMIN requis.");
                        String ownerKind = superAdmin ? "SUPER_ADMIN" : "OWNER_ADMIN";
                        String ownerToken = SecureOwnerStore.token(MainActivity.this, ownerKind);
                        if (ownerToken.isEmpty()) throw new SecurityException("Entitlement propriétaire absent ou illisible.");
                        client.withOwnerToken(ownerToken);
                    }'''
s=once(s,old,new,'platform owner token')
write(p,s)

# ---------------------------------------------------------------------------
# Simple, role-first, senior-friendly cockpit. No Academy/API Business in v2.9.
# ---------------------------------------------------------------------------
write('app/src/main/assets/control-tower-v290-ops.js', r'''(function(){
'use strict';
function id(x){return document.getElementById(x);}function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}function cfg(){try{return JSON.parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}');}catch(e){return {};}}function upper(v){return String(v||'').toUpperCase();}function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}function money(v){var n=Number(v);return isFinite(n)?String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' ')+' F':'—';}
var c=cfg(),last=null,lang='fr';try{lang=bridge()&&bridge().getUiLanguage&&bridge().getUiLanguage()==='en'?'en':'fr';}catch(e){}function t(fr,en){return lang==='en'?en:fr;}function req(a,p){var b=bridge();if(b&&b.platformAction)b.platformAction(a,JSON.stringify(p||{}));}
function level(n){n=upper(n);return n==='CRITICAL'?4:n==='HOT'?3:n==='WARN'?2:1;}function badge(sev){var s=upper(sev||'OK');return '<span class="v290ops-badge '+s.toLowerCase()+'">'+esc(s)+'</span>';}
function headline(){if(c.super_admin_workspace)return t('SUPER-ADMIN — gouvernance sensible','SUPER-ADMIN — sensitive governance');if(c.owner_admin_workspace)return t('RÉGION CONTROL & NATIONAL OPS','REGION CONTROL & NATIONAL OPS');if(upper(c.role)==='DAE')return t('DAE PRO — GRATUIT EN v2.9','DAE PRO — FREE IN v2.9');if(upper(c.role)==='DSM')return t('MES PoS — JE RÈGLE D’ABORD','MY PoS — I HANDLE FIRST');return t('MON PoS — SIMPLE ET DIRECT','MY PoS — SIMPLE AND DIRECT');}
function intro(){if(c.super_admin_workspace)return t('Vous êtes le seul niveau qui peut lancer les contrôles techniques sensibles. Même ici, aucun PIN Blue n’est lisible ni récupérable à distance.','You are the only level allowed to launch sensitive technical controls. Even here, no Blue PIN can be read or remotely retrieved.');if(c.owner_admin_workspace)return t('Pilotez les régions et le national. Les problèmes ordinaires des PoS restent chez leurs DSM; vous intervenez sur les escalades et les tendances.','Control regions and national operations. Routine PoS issues stay with their DSM; you intervene on escalations and trends.');if(upper(c.role)==='DAE')return t('Gérez vos DSM. Les PoS restent sous la conduite quotidienne de leur DSM; vous voyez surtout les alertes agrégées et venez au secours d’un DSM quand il escalade un cas chaud.','Manage your DSMs. PoS remain under daily DSM control; you mainly see aggregate alerts and assist a DSM when it escalates a hot case.');if(upper(c.role)==='DSM')return t('Vos PoS sont votre domaine d’action direct. Un bouton permet d’escalader au DAE seulement quand le problème devient chaud ou grave.','Your PoS are your direct action scope. One button escalates to the DAE only when an issue becomes hot or severe.');return t('B.I.R. vous montre seulement l’essentiel. Si quelque chose bloque, signalez-le à votre DSM.','B.I.R. shows only what matters. If something is blocked, report it to your DSM.');}
function shell(){var reports=document.querySelector('[data-tab-panel="reports"]');if(!reports||id('v290OpsCockpit'))return;var box=document.createElement('article');box.id='v290OpsCockpit';box.className='panel v290ops';box.innerHTML='<div class="v290ops-title"><div><p class="eyebrow">B.I.R. COPILOTE</p><h2>'+headline()+'</h2><p>'+intro()+'</p></div><button id="v290OpsRefresh">'+t('ACTUALISER','REFRESH')+'</button></div><div id="v290OpsNow" class="v290ops-now"><b>'+t('À faire maintenant','Do now')+'</b><p>'+t('Lecture intelligente en cours…','Smart check in progress…')+'</p></div><div class="v290ops-grid"><section><span>🤖</span><b>'+t('Santé Robots','Robot health')+'</b><strong id="v290OpsHealth">—</strong><small id="v290OpsHealthText">—</small></section><section><span>⇄</span><b>Continuity / Relay</b><strong id="v290OpsSync">—</strong><small id="v290OpsSyncText">—</small></section><section><span>📦</span><b>'+t('Prévision stock','Stock forecast')+'</b><strong id="v290OpsForecast">—</strong><small id="v290OpsForecastText">—</small></section><section><span>✓</span><b>Audit & Proof</b><strong id="v290OpsProof">—</strong><small id="v290OpsProofText">—</small></section><section><span>％</span><b>Smart Commission</b><strong id="v290OpsCommission">—</strong><small id="v290OpsCommissionText">—</small></section><section><span>🛟</span><b>Rescue / SAV</b><strong id="v290OpsRescue">—</strong><small id="v290OpsRescueText">—</small></section></div><div id="v290OpsEscalations" class="v290ops-list"></div><div id="v290OpsNodes" class="v290ops-list"></div><p class="v290ops-foot">'+t('Tous ces outils sont inclus gratuitement dans B.I.R. 2.9. Les données affichées comme « dernier état connu » peuvent être anciennes si le téléphone est hors ligne.','All these tools are included free in B.I.R. 2.9. Data marked “last known state” may be stale while a phone is offline.')+'</p>';reports.insertBefore(box,reports.firstChild);id('v290OpsRefresh').onclick=load;load();}
function load(){if(c.owner_admin_workspace)req('owner_ops_cockpit',{});else req('ops_cockpit',{});}
function render(d){last=d||{};var s=d.summary||{},f=d.forecast||{},a=d.audit||{},co=d.commission||{},r=d.rescue||{};id('v290OpsHealth').textContent=(s.healthy_robots||0)+' / '+(s.robot_count||0);id('v290OpsHealthText').textContent=t('Robots sains / connus','Healthy / known Robots');id('v290OpsSync').textContent=(s.sync_rate_percent==null?'—':s.sync_rate_percent+' %');id('v290OpsSyncText').textContent=t('événements confirmés serveur','server-confirmed events');id('v290OpsForecast').textContent=f.days_cover==null?'—':String(f.days_cover)+' j';id('v290OpsForecastText').textContent=f.message||t('Prévision selon activité confirmée','Forecast from confirmed activity');id('v290OpsProof').textContent=String(a.proof_count||0);id('v290OpsProofText').textContent=t('preuves / événements rapprochés','reconciled proofs / events');id('v290OpsCommission').textContent=money(co.last7d_commission||0);id('v290OpsCommissionText').textContent=t('commission confirmée sur 7 jours','confirmed commission over 7 days');id('v290OpsRescue').textContent=String(r.attention_count||0);id('v290OpsRescueText').textContent=t('cas à traiter','cases to handle');var now=id('v290OpsNow');now.className='v290ops-now '+(level(s.max_severity)>=3?'urgent':'');now.innerHTML='<b>'+t('À faire maintenant','Do now')+'</b><p>'+esc(s.next_action||t('Rien d’urgent. Continuez normalement.','Nothing urgent. Continue normally.'))+'</p>';renderEsc(d.escalations||[]);renderNodes(d.nodes||d.groups||[]);}
function renderEsc(items){var out=id('v290OpsEscalations'),h=['<h3>'+t('Alertes et escalades','Alerts and escalations')+'</h3>'];if(!items.length){h.push('<p class="muted">'+t('Aucune escalade ouverte.','No open escalation.')+'</p>');out.innerHTML=h.join('');return;}items.sort(function(x,y){return level(y.severity)-level(x.severity);});for(var i=0;i<items.length;i++){var x=items[i],canResolve=x.can_resolve===true;h.push('<div class="v290ops-row">'+badge(x.severity)+'<div><b>'+esc(x.target_node_code||x.node_code||'—')+'</b><p>'+esc(x.message||x.kind||'')+'</p><small>'+esc(x.routing_label||x.assigned_to||'')+'</small></div>'+(canResolve?'<button data-v290-resolve="'+esc(x.public_id)+'">'+t('RÉGLÉ','RESOLVED')+'</button>':'')+'</div>');}out.innerHTML=h.join('');var buttons=out.querySelectorAll('[data-v290-resolve]');for(i=0;i<buttons.length;i++)buttons[i].onclick=function(){req('ops_resolve',{escalation_id:this.getAttribute('data-v290-resolve')});};}
function renderNodes(items){var out=id('v290OpsNodes'),h=['<h3>'+t('Mon périmètre d’action','My action scope')+'</h3>'],i,x;if(!items.length){h.push('<p class="muted">'+t('Aucune donnée disponible.','No data available.')+'</p>');out.innerHTML=h.join('');return;}for(i=0;i<items.length;i++){x=items[i];h.push('<div class="v290ops-row">'+badge(x.severity||x.health_severity)+'<div><b>'+esc(x.node_code||x.label||'—')+'</b><p>'+esc(x.action_hint||x.health_message||'')+'</p><small>'+esc(x.telemetry_freshness||x.scope_note||'')+'</small></div>'+(x.can_escalate?'<button data-v290-escalate="'+esc(x.node_code)+'" data-kind="'+esc(x.escalation_kind||'ASSISTANCE')+'">'+t('SECOURS','HELP')+'</button>':'')+'</div>');}out.innerHTML=h.join('');var buttons=out.querySelectorAll('[data-v290-escalate]');for(i=0;i<buttons.length;i++)buttons[i].onclick=function(){var node=this.getAttribute('data-v290-escalate'),kind=this.getAttribute('data-kind');var msg=prompt(t('Décrivez très simplement le problème :','Describe the problem simply:'),'');if(msg===null)return;req('ops_escalate',{target_node_code:node,severity:'HOT',kind:kind,message:msg});};}
function privilegeUi(){if(!c.owner_admin_workspace)return;if(c.super_admin_workspace){if(id('birAccountRole'))id('birAccountRole').textContent='SUPER-ADMIN';return;}if(id('birAccountRole'))id('birAccountRole').textContent='ADMIN';var ctl=id('v280AdminControl'),tcho=id('v280AdminTchoronko');if(ctl)ctl.style.display='none';if(tcho)tcho.style.display='none';}
window.BlueMagicNative=window.BlueMagicNative||{};var old=window.BlueMagicNative.onPlatformAction;window.BlueMagicNative.onPlatformAction=function(d){if(typeof old==='function')try{old(d);}catch(e){};if(!d||d.error)return;var a=String(d._action||'');if(a==='ops_cockpit'||a==='owner_ops_cockpit')render(d);else if(a==='ops_escalate'||a==='ops_resolve')load();};
function init(){c=cfg();privilegeUi();shell();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(init,220);});else setTimeout(init,220);
})();
''')
write('app/src/main/assets/control-tower-v290-ops.css', r'''.v290ops{border:2px solid rgba(255,205,92,.55);padding:16px}.v290ops-title{display:flex;gap:12px;justify-content:space-between;align-items:flex-start}.v290ops-title h2{font-size:23px;margin:4px 0}.v290ops-title button,.v290ops-row button{min-height:48px;min-width:96px;font-weight:800}.v290ops-now{margin:14px 0;padding:15px;border-radius:18px;background:rgba(44,181,118,.14);border:2px solid rgba(44,181,118,.45);font-size:16px}.v290ops-now.urgent{background:rgba(255,91,107,.14);border-color:rgba(255,91,107,.6)}.v290ops-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.v290ops-grid section{min-height:116px;border:1px solid rgba(78,225,255,.23);border-radius:18px;padding:13px;background:rgba(3,18,48,.45)}.v290ops-grid span{font-size:24px}.v290ops-grid b,.v290ops-grid strong,.v290ops-grid small{display:block}.v290ops-grid strong{font-size:22px;margin:6px 0}.v290ops-list h3{margin:20px 0 8px}.v290ops-row{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.1)}.v290ops-row p{margin:4px 0}.v290ops-badge{font-size:11px!important;font-weight:900;padding:5px 7px;border-radius:999px;background:#365}.v290ops-badge.warn{background:#8a6414}.v290ops-badge.hot,.v290ops-badge.critical{background:#8b2736}.v290ops-foot{font-size:12px;opacity:.75;margin-top:16px}@media(max-width:380px){.v290ops-title{display:block}.v290ops-title button{width:100%;margin-top:8px}.v290ops-grid{grid-template-columns:1fr}.v290ops-row{grid-template-columns:auto 1fr}.v290ops-row button{grid-column:1/3;width:100%}}
''')
p='app/src/main/assets/index.html'; s=read(p)
s=once(s,'    <link rel="stylesheet" href="control-tower-v290.css">','    <link rel="stylesheet" href="control-tower-v290.css">\n    <link rel="stylesheet" href="control-tower-v290-ops.css">','ops css include')
s=once(s,'<script src="control-tower-v290.js"></script>','<script src="control-tower-v290.js"></script>\n<script src="control-tower-v290-ops.js"></script>','ops js include')
write(p,s)

# ---------------------------------------------------------------------------
# Additive D1 schema for telemetry + explicit hierarchical escalations.
# ---------------------------------------------------------------------------
write('cloudflare/migrations/0008_v290_free_ops_cockpit.sql', '''-- B.I.R. v2.9 free operations cockpit: additive telemetry and escalations only.\nALTER TABLE devices ADD COLUMN offline_pending_events INTEGER NOT NULL DEFAULT 0;\nALTER TABLE devices ADD COLUMN accessibility_enabled INTEGER NOT NULL DEFAULT 0;\nALTER TABLE devices ADD COLUMN accessibility_connected INTEGER NOT NULL DEFAULT 0;\nALTER TABLE devices ADD COLUMN battery_percent INTEGER;\nALTER TABLE devices ADD COLUMN last_telemetry_at TEXT;\n\nCREATE TABLE IF NOT EXISTS ops_escalations (\n  public_id TEXT PRIMARY KEY,\n  raised_by_node_code TEXT NOT NULL REFERENCES nodes(node_code),\n  target_node_code TEXT NOT NULL REFERENCES nodes(node_code),\n  assigned_to TEXT NOT NULL,\n  severity TEXT NOT NULL CHECK(severity IN ('INFO','WARN','HOT','CRITICAL')),\n  kind TEXT NOT NULL,\n  message TEXT NOT NULL DEFAULT '',\n  state TEXT NOT NULL DEFAULT 'OPEN' CHECK(state IN ('OPEN','RESOLVED')),\n  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),\n  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),\n  resolved_at TEXT\n);\nCREATE INDEX IF NOT EXISTS idx_ops_escalations_assigned ON ops_escalations(assigned_to,state,created_at);\nCREATE INDEX IF NOT EXISTS idx_ops_escalations_target ON ops_escalations(target_node_code,state,created_at);\n''')

# ---------------------------------------------------------------------------
# Worker: role-aware cockpit, escalation ladder, SuperAdmin hard boundary.
# ---------------------------------------------------------------------------
p='cloudflare/src/index.js'; s=read(p)
s=once(s,
"capabilities: {commissions: true, commission_override: true, remote_results: true, force_sync: true, network_audit: true, owner_admin: true, owner_mock_entitlement: true, accounting: true, tchoronko: true, event_balance: true, offline_sync: true, bir_relay: true, effective_modes: ['REMOTE','ROBOT']}",
"capabilities: {commissions: true, commission_override: true, remote_results: true, force_sync: true, network_audit: true, owner_admin: true, super_admin: true, free_ops_cockpit: true, dae_pro_free: true, region_national_ops_free: true, owner_mock_entitlement: true, accounting: true, tchoronko: true, event_balance: true, offline_sync: true, bir_relay: true, effective_modes: ['REMOTE','ROBOT']}",
'health free ops')
s=once(s,
"        case 'platform_snapshot': return await platformSnapshot(env, auth, headers);",
"        case 'platform_snapshot': return await platformSnapshot(env, auth, headers);\n        case 'ops_cockpit': return await opsCockpit(env, auth, headers);\n        case 'ops_escalate': return await opsEscalate(env, auth, input, headers);\n        case 'ops_resolve': return await opsResolve(env, auth, input, headers);\n        case 'owner_ops_cockpit': return await ownerOpsCockpit(request, env, auth, headers);",
'ops routes')
# heartbeat telemetry: expand existing UPDATE and bind.
old="""    + 'sim_verified = ?, sim_fingerprint = ?, sim_slot = ?, '\n    + 'app_version = ?, android_version = ?, device_model = ? WHERE device_id = ?'"""
new="""    + 'sim_verified = ?, sim_fingerprint = ?, sim_slot = ?, '\n    + 'app_version = ?, android_version = ?, device_model = ?, offline_pending_events = ?, '\n    + 'accessibility_enabled = ?, accessibility_connected = ?, battery_percent = ?, '\n    + \"last_telemetry_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE device_id = ?\""""
s=once(s,old,new,'worker heartbeat SQL')
old='''    cleanText(input.device_model, 160),
    auth.device_id
  ).run();'''
new='''    cleanText(input.device_model, 160),
    Math.max(0, Math.min(100000, Number(input.offline_pending_events || 0))),
    input.accessibility_enabled === true ? 1 : 0,
    input.accessibility_connected === true ? 1 : 0,
    input.battery_percent == null ? null : Math.max(0, Math.min(100, Number(input.battery_percent))),
    auth.device_id
  ).run();'''
s=once(s,old,new,'worker heartbeat binds')
# Super admin enrollment uses same high-entropy owner secret but can only promote an already enrolled Admin device, once globally.
s=once(s,
"  if (!['OWNER_ADMIN','MOCK_OWNER'].includes(kind)) throw new ApiError('OWNER_KIND_INVALID','Entitlement propriétaire invalide.',422);\n  const expected = String(kind === 'OWNER_ADMIN' ? env.OWNER_ADMIN_SECRET || '' : env.MOCK_OWNER_SECRET || '');",
"  if (!['OWNER_ADMIN','MOCK_OWNER','SUPER_ADMIN'].includes(kind)) throw new ApiError('OWNER_KIND_INVALID','Entitlement propriétaire invalide.',422);\n  const expected = String(kind === 'MOCK_OWNER' ? env.MOCK_OWNER_SECRET || '' : env.OWNER_ADMIN_SECRET || '');",
'owner kinds')
anchor="  const token = randomHex(32), tokenHash = await sha256(token), entitlementId = crypto.randomUUID();"
addition='''  if (kind === 'SUPER_ADMIN') {
    const admin = await env.DB.prepare("SELECT entitlement_id FROM owner_entitlements WHERE kind='OWNER_ADMIN' AND bound_device_id=? AND active=1 LIMIT 1").bind(auth.device_id).first();
    if (!admin) throw new ApiError('SUPER_ADMIN_REQUIRES_ADMIN','Activez d’abord ADMIN sur ce même appareil.',403);
    const existingSuper = await env.DB.prepare("SELECT entitlement_id,bound_device_id FROM owner_entitlements WHERE kind='SUPER_ADMIN' AND active=1 LIMIT 1").first();
    if (existingSuper && existingSuper.bound_device_id !== auth.device_id) throw new ApiError('SUPER_ADMIN_ALREADY_ASSIGNED','Le SUPER-ADMIN unique est déjà lié à un autre appareil.',409);
  }
'''
s=insert_before(s,anchor,addition,'unique super enrollment')
# Add owner-any helper before adminAudit.
anchor='''async function adminAudit(env, entitlementId, action, targetNode, targetDevice, payload, outcome='ACCEPTED') {'''
addition='''async function authenticateOwnerAny(request, env, auth, kinds=['OWNER_ADMIN','SUPER_ADMIN']) {
  const token = String(request.headers.get('X-Owner-Token') || '').trim();
  if (!token) throw new ApiError('OWNER_AUTH_REQUIRED','Jeton propriétaire requis.',401);
  const row = await env.DB.prepare('SELECT entitlement_id,kind,bound_device_id,active FROM owner_entitlements WHERE token_hash=? LIMIT 1')
    .bind(await sha256(token)).first();
  if (!row || !row.active || row.bound_device_id !== auth.device_id || !kinds.includes(row.kind))
    throw new ApiError('OWNER_AUTH_INVALID','Entitlement propriétaire invalide pour cet appareil.',403);
  await env.DB.prepare("UPDATE owner_entitlements SET last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE entitlement_id=?").bind(row.entitlement_id).run();
  return row;
}
function rejectSensitiveRemotePayload(input) {
  const raw = JSON.stringify(input || {}).toLowerCase();
  if (/\"[^\"]*(?:pin|password|secret|token)[^\"]*\"\s*:/.test(raw))
    throw new ApiError('REMOTE_SECRET_FORBIDDEN','Aucun PIN, mot de passe, secret ou jeton ne peut être transmis par une action distante.',422);
}
'''
s=insert_before(s,anchor,addition,'owner any + secret guard')
# Read-only national functions accept Admin or SuperAdmin; sensitive controls require SuperAdmin.
s=s.replace("const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');", "const owner = await authenticateOwnerAny(request,env,auth);", 3)
# The first 3 are ownerSnapshot, ownerTransactions, ownerAudit. ownerControl remains next exact occurrence.
old="""async function ownerControl(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');"""
new="""async function ownerControl(request, env, auth, input, headers) {
  rejectSensitiveRemotePayload(input);
  const owner = await authenticateOwner(request,env,auth,'SUPER_ADMIN');"""
s=once(s,old,new,'super ownerControl')
old="""async function ownerAssist(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');"""
new="""async function ownerAssist(request, env, auth, input, headers) {
  rejectSensitiveRemotePayload(input);
  const owner = await authenticateOwnerAny(request,env,auth);"""
s=once(s,old,new,'safe ownerAssist')
old="""async function ownerTchoronkoSave(request, env, auth, input, headers) {
  const owner = await authenticateOwner(request,env,auth,'OWNER_ADMIN');"""
new="""async function ownerTchoronkoSave(request, env, auth, input, headers) {
  rejectSensitiveRemotePayload(input);
  const owner = await authenticateOwner(request,env,auth,'SUPER_ADMIN');"""
s=once(s,old,new,'super tchoronko')
# Core cockpit implementation inserted before shadowEnroll.
anchor='''async function shadowEnroll(env, auth, input, headers) {'''
addition=r'''async function cockpitRows(env, scopeNode) {
  const rows = await env.DB.prepare(
    "WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) " +
    "SELECT n.node_code,n.role,n.parent_node_code,n.default_commission_bps,b.balance,b.balance_quality,b.observed_at, " +
    "d.device_id,d.robot_enabled,d.sim_verified,d.offline_pending_events,d.accessibility_enabled,d.accessibility_connected,d.battery_percent,d.last_seen_at,d.last_telemetry_at " +
    "FROM tree t JOIN nodes n ON n.node_code=t.node_code LEFT JOIN account_balances b ON b.node_code=n.node_code " +
    "LEFT JOIN devices d ON d.device_id=(SELECT d2.device_id FROM devices d2 WHERE d2.node_code=n.node_code AND d2.active=1 ORDER BY d2.robot_enabled DESC,d2.last_seen_at DESC LIMIT 1) ORDER BY n.role,n.node_code")
    .bind(scopeNode).all();
  return rows.results || [];
}
function healthView(row) {
  const last = row.last_telemetry_at || row.last_seen_at || '';
  const age = last ? Math.max(0, Date.now()-Date.parse(last)) : Infinity;
  const stale = age > 15*60*1000;
  let severity='OK', message='Robot prêt';
  if (!row.device_id) {severity='CRITICAL';message='Aucun appareil actif connu';}
  else if (stale) {severity='HOT';message='Nœud silencieux : dernier état connu ancien';}
  else if (row.robot_enabled && (!row.sim_verified || !row.accessibility_enabled || !row.accessibility_connected)) {severity='WARN';message='Robot à vérifier : SIM ou Accessibilité';}
  else if (row.battery_percent != null && Number(row.battery_percent) < 15) {severity='WARN';message='Batterie faible';}
  return {severity,message,telemetry_freshness: stale ? 'DERNIER ÉTAT CONNU — '+last : 'CONFIRMÉ SERVEUR — '+last,
    robot_enabled:Boolean(row.robot_enabled),sim_verified:Boolean(row.sim_verified),accessibility_enabled:Boolean(row.accessibility_enabled),
    accessibility_connected:Boolean(row.accessibility_connected),battery_percent:row.battery_percent == null ? null:Number(row.battery_percent),
    offline_pending_events_last_reported:Number(row.offline_pending_events||0),telemetry_stale:stale};
}
async function openEscalationsFor(env, auth) {
  let assigned = auth.role === 'POS' ? auth.node_code : auth.node_code;
  const rows = await env.DB.prepare("SELECT * FROM ops_escalations WHERE state='OPEN' AND (assigned_to=? OR raised_by_node_code=? OR target_node_code=?) ORDER BY CASE severity WHEN 'CRITICAL' THEN 4 WHEN 'HOT' THEN 3 WHEN 'WARN' THEN 2 ELSE 1 END DESC,created_at DESC LIMIT 100")
    .bind(assigned,auth.node_code,auth.node_code).all();
  return (rows.results||[]).map(x=>({...x,can_resolve:x.assigned_to===auth.node_code,routing_label:'Assigné à '+x.assigned_to}));
}
async function continuitySummary(env, scopeNode) {
  const events = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT received_via,COUNT(*) AS c FROM offline_events e JOIN tree t ON t.node_code=e.source_node_code GROUP BY received_via").bind(scopeNode).all();
  let direct=0,relay=0; for (const row of events.results||[]) {if(row.received_via==='BIR_RELAY')relay+=Number(row.c||0);else direct+=Number(row.c||0);}
  return {direct,relay,total:direct+relay,rate:direct+relay?100:null};
}
async function forecastSummary(env, scopeNode) {
  const row = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT COALESCE(SUM(CASE WHEN c.state='SUCCEEDED' AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') THEN c.amount ELSE 0 END),0) AS outflow FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").bind(scopeNode).first();
  const b = await env.DB.prepare('SELECT balance FROM account_balances WHERE node_code=?').bind(scopeNode).first();
  const daily=Number(row?.outflow||0)/7, balance=b?.balance==null?null:Number(b.balance), days=balance==null||daily<=0?null:Math.round(balance/daily*10)/10;
  return {days_cover:days,message:days==null?'Données insuffisantes':days<1?'Rupture probable : approvisionnement urgent':days<3?'Stock à surveiller':'Couverture de stock confortable'};
}
async function opsCockpit(env, auth, headers) {
  const all = await cockpitRows(env,auth.node_code), health=all.map(r=>({...r,...healthView(r)}));
  const escalations=await openEscalationsFor(env,auth), continuity=await continuitySummary(env,auth.node_code), forecast=await forecastSummary(env,auth.node_code);
  let nodes=[];
  if(auth.role==='POS') nodes=health.filter(x=>x.node_code===auth.node_code).map(x=>({...x,can_escalate:true,action_hint:'Si un blocage persiste, signalez-le à votre DSM.'}));
  else if(auth.role==='DSM') nodes=health.filter(x=>x.node_code===auth.node_code||x.parent_node_code===auth.node_code).map(x=>({...x,can_escalate:x.role==='POS',action_hint:x.role==='POS'?'Ce PoS relève directement de vous. Traitez-le ici; escaladez seulement si nécessaire.':'Votre compte DSM.'}));
  else if(auth.role==='DAE') {
    const dsms=health.filter(x=>x.parent_node_code===auth.node_code&&x.role==='DSM');
    nodes=dsms.map(d=>{const children=health.filter(x=>x.parent_node_code===d.node_code&&x.role==='POS');const hot=children.filter(x=>['HOT','CRITICAL'].includes(x.severity)).length;return {...d,pos_count:children.length,pos_attention:hot,can_escalate:false,action_hint:hot?`${hot} PoS à suivre par ${d.node_code}; intervenez via votre DSM si le cas est escaladé.`:'Ce DSM gère ses PoS; aucune intervention DAE requise.'};});
    const escalatedPos=new Set(escalations.filter(e=>e.assigned_to===auth.node_code).map(e=>e.target_node_code));
    for(const pos of health.filter(x=>x.role==='POS'&&escalatedPos.has(x.node_code))) nodes.push({...pos,can_escalate:false,action_hint:'Détail visible car le DSM a demandé votre secours.'});
  }
  const healthy=health.filter(x=>x.robot_enabled&&!x.telemetry_stale&&x.severity==='OK').length, robots=health.filter(x=>x.device_id).length;
  const severities=health.map(x=>x.severity).concat(escalations.map(x=>x.severity)); const rank={OK:1,INFO:1,WARN:2,HOT:3,CRITICAL:4}; let max='OK'; for(const x of severities)if((rank[x]||1)>(rank[max]||1))max=x;
  const tx=await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT COUNT(*) AS c,COALESCE(SUM(commission_amount),0) AS commission FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') AND c.state='SUCCEEDED'").bind(auth.node_code).first();
  return success({generated_at:new Date().toISOString(),scope_role:auth.role,scope_node_code:auth.node_code,nodes,escalations,
    summary:{healthy_robots:healthy,robot_count:robots,sync_rate_percent:continuity.rate,max_severity:max,next_action:escalations.length?`Traitez d’abord ${escalations[0].target_node_code} — ${escalations[0].severity}.`:(max==='HOT'||max==='CRITICAL'?'Un nœud silencieux ou critique demande votre attention.':'Rien d’urgent. Continuez normalement.'),continuity_source:'SERVER_CONFIRMED_ONLY'},
    forecast,audit:{proof_count:continuity.total,direct_events:continuity.direct,relay_events:continuity.relay},commission:{last7d_commission:Number(tx?.commission||0)},rescue:{attention_count:health.filter(x=>x.severity!=='OK').length+escalations.length}},200,headers);
}
async function opsEscalate(env, auth, input, headers) {
  const target=nodeCode(input.target_node_code||auth.node_code), severity=String(input.severity||'WARN').toUpperCase();
  if(!['INFO','WARN','HOT','CRITICAL'].includes(severity))throw new ApiError('ESCALATION_SEVERITY_INVALID','Sévérité invalide.',422);
  let assigned='';
  if(auth.role==='POS') {if(target!==auth.node_code)throw new ApiError('ESCALATION_SCOPE','Un PoS ne signale que son propre problème.',403);assigned=auth.parent_node_code;}
  else if(auth.role==='DSM') {const child=await resolveDirectChild(env,auth.node_code,target,'POS');if(!child)throw new ApiError('ESCALATION_SCOPE','Le DSM ne peut escalader qu’un de ses PoS directs.',403);assigned=auth.parent_node_code;}
  else if(auth.role==='DAE') {const child=await resolveDirectChild(env,auth.node_code,target,'DSM');if(!child)throw new ApiError('ESCALATION_SCOPE','Le DAE ne peut escalader qu’un DSM direct.',403);assigned='ADMIN';}
  else throw new ApiError('ESCALATION_SCOPE','Rôle non autorisé.',403);
  const publicId=crypto.randomUUID();await env.DB.prepare('INSERT INTO ops_escalations(public_id,raised_by_node_code,target_node_code,assigned_to,severity,kind,message) VALUES(?,?,?,?,?,?,?)')
    .bind(publicId,auth.node_code,target,assigned,severity,cleanText(input.kind||'ASSISTANCE',80),cleanText(input.message,600)).run();
  return success({public_id:publicId,target_node_code:target,assigned_to:assigned,severity,state:'OPEN'},201,headers);
}
async function opsResolve(env, auth, input, headers) {
  const id=String(input.escalation_id||'').trim();const row=await env.DB.prepare("SELECT * FROM ops_escalations WHERE public_id=? AND state='OPEN'").bind(id).first();
  if(!row)throw new ApiError('ESCALATION_NOT_FOUND','Escalade introuvable.',404);if(row.assigned_to!==auth.node_code)throw new ApiError('ESCALATION_NOT_ASSIGNED','Seul le niveau actuellement responsable peut clôturer ce cas.',403);
  await env.DB.prepare("UPDATE ops_escalations SET state='RESOLVED',resolved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE public_id=?").bind(id).run();return success({public_id:id,state:'RESOLVED'},200,headers);
}
async function ownerOpsCockpit(request, env, auth, headers) {
  const owner=await authenticateOwnerAny(request,env,auth);const nodes=(await env.DB.prepare("SELECT n.node_code,n.role,n.parent_node_code,d.robot_enabled,d.sim_verified,d.offline_pending_events,d.accessibility_enabled,d.accessibility_connected,d.battery_percent,d.last_seen_at,d.last_telemetry_at FROM nodes n LEFT JOIN devices d ON d.device_id=(SELECT d2.device_id FROM devices d2 WHERE d2.node_code=n.node_code AND d2.active=1 ORDER BY d2.robot_enabled DESC,d2.last_seen_at DESC LIMIT 1) WHERE n.active=1 ORDER BY n.role,n.node_code").all()).results||[];
  const health=nodes.map(r=>({...r,...healthView(r)})), dae=health.filter(x=>x.role==='DAE').map(d=>{const desc=health.filter(x=>x.node_code===d.node_code||x.parent_node_code===d.node_code||health.some(m=>m.role==='DSM'&&m.parent_node_code===d.node_code&&x.parent_node_code===m.node_code));return {node_code:d.node_code,label:d.node_code,severity:desc.some(x=>x.severity==='CRITICAL')?'CRITICAL':desc.some(x=>x.severity==='HOT')?'HOT':desc.some(x=>x.severity==='WARN')?'WARN':'OK',action_hint:`${desc.length} nœud(s) dans ce réseau DAE. Les PoS restent gérés par leurs DSM.`,scope_note:'Vue région/nationale agrégée',can_escalate:false};});
  const open=await env.DB.prepare("SELECT * FROM ops_escalations WHERE state='OPEN' AND assigned_to='ADMIN' ORDER BY created_at DESC LIMIT 200").all();const continuity=await env.DB.prepare("SELECT received_via,COUNT(*) AS c FROM offline_events GROUP BY received_via").all();let direct=0,relay=0;for(const x of continuity.results||[]){if(x.received_via==='BIR_RELAY')relay+=Number(x.c||0);else direct+=Number(x.c||0);}const tx=await env.DB.prepare("SELECT COALESCE(SUM(commission_amount),0) AS commission FROM commands WHERE state='SUCCEEDED' AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").first();const alerts=health.filter(x=>x.severity!=='OK');
  await adminAudit(env,owner.entitlement_id,'OWNER_OPS_COCKPIT',null,auth.device_id,{nodes:nodes.length,alerts:alerts.length},'READ');
  return success({generated_at:new Date().toISOString(),scope_role:owner.kind,groups:dae,escalations:(open.results||[]).map(x=>({...x,can_resolve:false,routing_label:'Escalade DAE → ADMIN'})),summary:{healthy_robots:health.filter(x=>x.robot_enabled&&!x.telemetry_stale&&x.severity==='OK').length,robot_count:health.filter(x=>x.device_id).length,sync_rate_percent:direct+relay?100:null,max_severity:alerts.some(x=>x.severity==='CRITICAL')?'CRITICAL':alerts.some(x=>x.severity==='HOT')?'HOT':alerts.length?'WARN':'OK',next_action:(open.results||[]).length?`${(open.results||[]).length} escalade(s) DAE à examiner.`:alerts.length?`${alerts.length} nœud(s) à surveiller; laissez DSM/DAE traiter leur périmètre.`:'Rien d’urgent au niveau national.',continuity_source:'SERVER_CONFIRMED_ONLY'},forecast:{days_cover:null,message:'Prévision détaillée disponible par DAE'},audit:{proof_count:direct+relay,direct_events:direct,relay_events:relay},commission:{last7d_commission:Number(tx?.commission||0)},rescue:{attention_count:alerts.length+(open.results||[]).length}},200,headers);
}

'''
s=insert_before(s,anchor,addition,'ops implementation')
write(p,s)

# ---------------------------------------------------------------------------
# Contract: free in v2.9, role ladder, SuperAdmin, no PIN/Academy/API Business.
# ---------------------------------------------------------------------------
write('app/src/test/v290-free-ops-contract.mjs', r'''import fs from 'node:fs';
const t=p=>fs.readFileSync(p,'utf8'), must=(v,m)=>{if(!v)throw new Error(m)};
const main=t('app/src/main/java/com/profitloop/blueauto/MainActivity.java'),api=t('app/src/main/java/com/profitloop/blueauto/ApiClient.java'),html=t('app/src/main/assets/index.html'),ops=t('app/src/main/assets/control-tower-v290-ops.js'),worker=t('cloudflare/src/index.js'),mig=t('cloudflare/migrations/0008_v290_free_ops_cockpit.sql'),manifest=t('app/src/main/AndroidManifest.xml');
must(html.includes('control-tower-v290-ops.js')&&html.includes('control-tower-v290-ops.css'),'free ops cockpit not loaded');
for(const x of ['DAE PRO — GRATUIT EN v2.9','RÉGION CONTROL & NATIONAL OPS','SUPER-ADMIN','MES PoS — JE RÈGLE D’ABORD'])must(ops.includes(x),'missing UX contract '+x);
must(!ops.includes('Academy Offline')&&!ops.includes('API Business'),'Academy/API Business must remain out of v2.9 cockpit');
must(main.includes('SUPERADMIN')&&main.includes('SUPER_ADMIN_WORKSPACE_KEY')&&main.includes('SecureOwnerStore.has(this, "SUPER_ADMIN")'),'SuperAdmin account missing');
must(main.includes('value.put("pin_configured"')&&!main.includes('value.put("pin_value"')&&!main.includes('value.put("operator_pin"'),'PIN must never be bridged');
must(worker.includes("authenticateOwner(request,env,auth,'SUPER_ADMIN')"),'sensitive owner control not SuperAdmin-only');
must(worker.includes("case 'ops_cockpit'")&&worker.includes("case 'owner_ops_cockpit'")&&worker.includes('opsEscalate'),'ops API missing');
must(worker.includes("if(auth.role==='POS')")&&worker.includes("else if(auth.role==='DSM')")&&worker.includes("else if(auth.role==='DAE')"),'hierarchy ladder missing');
must(worker.includes("assigned='ADMIN'")&&worker.includes('resolveDirectChild'),'no-skip escalation ladder missing');
must(worker.includes('rejectSensitiveRemotePayload')&&worker.includes('REMOTE_SECRET_FORBIDDEN'),'remote secret rejection missing');
for(const x of ['offline_pending_events','accessibility_enabled','accessibility_connected','battery_percent','ops_escalations'])must(mig.includes(x),'migration missing '+x);
must(!/DROP\s+TABLE|DELETE\s+FROM/i.test(mig),'destructive migration forbidden');
must(!manifest.includes('SEND_SMS'),'SMS fallback forbidden');
must(api.includes('ops_cockpit')&&api.includes('owner_ops_cockpit'),'native allowlist missing');
console.log('BIR v2.9 free hierarchical operations cockpit contract: OK');
''')

# Keep restart decision doc explicit and additive.
p='docs/BIR_V290_REPRISE_ET_DECISIONS.md'; s=read(p)
marker='## Décisions produit gratuites v2.9 — 18 août 2026'
if marker not in s:
    s += '''\n\n## Décisions produit gratuites v2.9 — 18 août 2026\n- DAE Pro, Continuity/Relay, Fleet Health, Audit & Proof, Rescue/SAV, Treasury Forecast et Smart Commission sont inclus gratuitement dès la v2.9.\n- Région Control et National Ops sont réservés au compte ADMIN.\n- SUPERADMIN est un entitlement unique, promu depuis un ADMIN déjà autorisé sur le même appareil ; il est seul à recevoir les contrôles techniques sensibles.\n- Hiérarchie opérationnelle : PoS → DSM d'abord ; DSM → DAE en escalade ; DAE → ADMIN pour les cas de son DSM. Le DAE ne micro-gère pas les PoS hors escalade.\n- Le PIN Blue reste exclusivement dans le stockage sécurisé Android du Robot. Aucun endpoint, Relay, dashboard, ADMIN ou SUPERADMIN ne peut obtenir sa valeur en clair.\n- Academy Offline et API Business sont explicitement hors périmètre de la v2.9.\n- Les files offline non joignables ne sont jamais inventées : le cockpit distingue télémétrie confirmée et dernier état connu.\n'''
write(p,s)
print('BIR v2.9 free hierarchical operations cockpit patch prepared')
