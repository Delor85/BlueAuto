from pathlib import Path


def read(path):
    return Path(path).read_text(encoding='utf-8')


def write(path, text):
    Path(path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit('missing patch anchor: ' + label)
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# Android commercial identity + version. Technical package/engine stay unchanged.
# -----------------------------------------------------------------------------
p='app/build.gradle'
s=read(p)
s=replace_once(s, 'versionCode 48\n        versionName "2.6.8"', 'versionCode 49\n        versionName "2.6.9"', 'android version')
write(p,s)

p='app/src/main/res/values/strings.xml'
s=read(p)
s=s.replace('<string name="app_name">Blue Magic</string>', '<string name="app_name">B.I.R. — Blue Infinity Retail</string>')
s=s.replace('Automatisation PIN Blue Magic', 'Automatisation PIN B.I.R.')
s=s.replace('Robot Blue Magic', 'Robot B.I.R.')
write(p,s)

# Expose the already-stored account phone number to the WebView identity block.
p='app/src/main/java/com/profitloop/blueauto/MainActivity.java'
s=read(p)
old='''                value.put("node_code", AppConfig.nodeCode(MainActivity.this));\n                value.put("profile_id", AppConfig.profileId(MainActivity.this));'''
new='''                value.put("node_code", AppConfig.nodeCode(MainActivity.this));\n                value.put("phone_number", AppConfig.phoneNumber(MainActivity.this));\n                value.put("profile_id", AppConfig.profileId(MainActivity.this));'''
s=replace_once(s,old,new,'phone number bridge')
write(p,s)

# -----------------------------------------------------------------------------
# Functional HTML. Existing command forms/cards/IDs are preserved; B.I.R. adds a
# real home dashboard and navigation on top of the same Blue Magic Engine.
# -----------------------------------------------------------------------------
p='app/src/main/assets/index.html'
s=read(p)
s=s.replace('<title>Blue Magic</title>','<title>B.I.R. — Blue Infinity Retail</title>')
old='''<header class="topbar">\n    <div><p class="eyebrow">PROFITLOOP TELECOM</p><h1>Blue Magic</h1></div>\n    <span id="nativeBadge" class="badge badge-warn">Vérification…</span>\n</header>'''
new='''<header class="topbar bir-topbar">\n    <div class="bir-brand-lockup">\n        <img class="bir-logo-image" src="bir-logo.png" alt="B.I.R.">\n        <div class="bir-brand-copy"><p class="eyebrow">BLUE INFINITY RETAIL</p><h1>B.I.R.</h1><p class="bir-tagline">Rapide. Puissant. Infini.</p></div>\n    </div>\n    <div class="bir-account-chip">\n        <span id="birAccountRole" class="bir-account-role">COMPTE</span>\n        <strong id="birAccountNode">—</strong>\n        <small id="birAccountPhone">SIM —</small>\n        <span id="nativeBadge" class="badge badge-warn">Vérification…</span>\n    </div>\n</header>'''
s=replace_once(s,old,new,'BIR topbar')

# Make the account identity strip more explicit without removing native state IDs.
s=s.replace('<p class="eyebrow">NŒUD ACTIF</p>', '<p class="eyebrow">COMPTE ACTIF</p>', 1)

# Add the chosen dense/light BIR home before the pre-existing reports content.
anchor='''    <section class="module-screen hidden" data-tab-panel="reports">\n        <article class="panel module-intro">'''
home='''    <section class="module-screen hidden" data-tab-panel="reports">\n        <article class="bir-balance-card">\n            <div class="bir-balance-head">\n                <div><p class="bir-kicker">SOLDE CAMTEL</p><strong id="birCamtelBalance">À actualiser</strong><span>FCFA</span><p id="birBalanceFreshness" class="bir-balance-note">Lecture du solde en cours…</p></div>\n                <div id="birRobotState" class="bir-robot-orb">ROBOT —</div>\n            </div>\n            <div class="bir-finance-grid">\n                <div><span>Disponible</span><b id="birAvailableBalance">—</b></div>\n                <div><span>Réservé confirmé</span><b id="birReservedBalance">—</b></div>\n                <div><span id="birThirdMetricLabel">Composante commission</span><b id="birThirdMetricValue">—</b></div>\n            </div>\n        </article>\n        <button type="button" class="bir-priority-action" data-tab-jump="flux">\n            <span class="bir-action-infinity">∞</span><span><b id="birRoleActionTitle">ACTION PRIORITAIRE</b><small id="birRoleActionSub">Accédez directement à votre opération principale.</small></span><i>›</i>\n        </button>\n        <div class="bir-section-title"><span></span><h2>MODULES B.I.R.</h2><span></span></div>\n        <div class="bir-modules-grid">\n            <button type="button" data-tab-jump="flux"><i>▣</i><b id="birTransactionModuleTitle">Transactions Blue</b><small>Vente, achat et approvisionnement selon votre rôle.</small></button>\n            <button type="button" data-tab-jump="fleet"><i>⌁</i><b>Réseau vivant</b><small>Comptes, SIM, terminaux et périmètre commercial.</small></button>\n            <button type="button" data-action="check-balance"><i>◫</i><b>Soldes & preuves</b><small>Solde Camtel, disponible, historique et justificatifs.</small></button>\n            <button type="button" data-tab-jump="config"><i>◉</i><b>Robot intelligent</b><small>Remote, Robot, permissions, PIN, reprise et sécurité.</small></button>\n            <button type="button" data-tab-jump="support"><i>▤</i><b>Activité & SAV</b><small>Commandes, diagnostic, serveur et assistance terrain.</small></button>\n            <button type="button" data-native-action="manage"><i>⚙</i><b>Centre Gérer</b><small>Comptes, SIM, PIN Camtel et réglages essentiels.</small></button>\n        </div>\n        <article class="bir-live-strip">\n            <div><span class="bir-pulse-dot"></span><p><b>ACTIVITÉ EN COURS</b><small id="birActivityLine">Aucune commande locale récente.</small></p></div>\n            <button type="button" data-tab-jump="support">Voir tout</button>\n        </article>\n        <article class="panel module-intro bir-existing-content">'''
s=replace_once(s,anchor,home,'BIR functional home')

# Activity tab keeps SAV but now starts with real local activity context.
s=s.replace('<p class="eyebrow">SAV & DIAGNOSTIC</p>\n            <h3>Contrôle sans fonds</h3>', '<p class="eyebrow">ACTIVITÉ & SAV</p>\n            <h3>Activité, preuves et diagnostic</h3>', 1)
s=s.replace('<p class="muted">Le test numéro reste dans l’onglet Flux et compose uniquement <code>*825*3*3#</code>. Commencez toujours par lui après une installation ou un changement de Robot.</p>', '<p id="birActivityDetail" class="muted">Vos dernières commandes, les preuves Camtel et les contrôles terrain restent accessibles ici. Le test numéro compose uniquement <code>*825*3*3#</code>.</p>', 1)

# Gérer receives direct account/SIM actions in addition to every existing Robot setting.
config_anchor='''    <section class="module-screen hidden" data-tab-panel="config">\n        <article class="panel module-intro">'''
config_new='''    <section class="module-screen hidden" data-tab-panel="config">\n        <article class="panel module-intro">'''
s=replace_once(s,config_anchor,config_new,'config screen')
intro_end='''            <p id="configRobotStatus" class="muted">Chargement de la configuration…</p>\n        </article>'''
intro_new='''            <p id="configRobotStatus" class="muted">Chargement de la configuration…</p>\n        </article>\n        <article class="panel module-card bir-manage-quick">\n            <p class="eyebrow">COMPTE & SIM</p><h3>Identité, liaison et comptes</h3>\n            <p class="muted">Toutes les fonctions historiques restent disponibles : compte actif, slots, SIM, mode Remote/Robot et centre natif Gérer.</p>\n            <div class="module-actions">\n                <button type="button" class="secondary" data-native-action="accounts">Comptes et slots</button>\n                <button type="button" class="secondary" data-native-action="verify-sim">Vérifier / lier la SIM</button>\n                <button type="button" class="secondary" data-native-action="manage">Ouvrir le centre Gérer</button>\n            </div>\n        </article>'''
s=replace_once(s,intro_end,intro_new,'config account actions')

# Exact chosen navigation semantics; all historical screens remain reachable.
old_nav='''<nav class="module-tabs" aria-label="Modules Blue Magic">\n    <button type="button" class="module-tab" data-tab="reports"><span class="module-icon">▥</span><span>Rapports</span></button>\n    <button type="button" class="module-tab" data-tab="fleet"><span class="module-icon">♧</span><span>Flotte</span></button>\n    <button type="button" class="module-tab module-tab-primary active" data-tab="flux"><span class="module-icon">⚡</span><span>Flux</span></button>\n    <button type="button" class="module-tab" data-tab="config"><span class="module-icon">⚙</span><span>Robot</span></button>\n    <button type="button" class="module-tab" data-tab="support"><span class="module-icon">◇</span><span>SAV</span></button>\n</nav>'''
new_nav='''<nav class="module-tabs bir-bottom-nav" aria-label="Navigation B.I.R.">\n    <button type="button" class="module-tab" data-tab="reports"><span class="module-icon">⌂</span><span>Accueil</span></button>\n    <button type="button" class="module-tab" data-tab="fleet"><span class="module-icon">⌁</span><span>Réseau</span></button>\n    <button type="button" class="module-tab module-tab-primary" data-tab="flux"><span class="module-icon bir-nav-infinity">∞</span><span>Piloter</span></button>\n    <button type="button" class="module-tab" data-tab="support"><span class="module-icon">▤</span><span>Activité</span></button>\n    <button type="button" class="module-tab" data-tab="config"><span class="module-icon">⚙</span><span>Gérer</span></button>\n</nav>'''
s=replace_once(s,old_nav,new_nav,'BIR bottom nav')
write(p,s)

# -----------------------------------------------------------------------------
# App JS: only view/navigation bindings and real dashboard projections change.
# Command/finance logic remains untouched.
# -----------------------------------------------------------------------------
p='app/src/main/assets/app.js'
s=read(p)
s=s.replace("var activeTab = 'flux'", "var activeTab = 'reports'", 1)
s=s.replace("var saved=localStorage.getItem('blue_magic_active_module')||'flux';", "var saved=localStorage.getItem('bir_active_module_v269')||'reports';", 1)
s=s.replace("localStorage.setItem('blue_magic_active_module',name);", "localStorage.setItem('bir_active_module_v269',name);", 1)

# POS keeps its self-only Network screen; do not hide the fleet view anymore.
s=s.replace("        if(configuration.role==='POS'&&saved==='fleet'){saved='flux';}\n", "")
s=s.replace("        if(configuration.role==='POS'&&name==='fleet'){name='flux';}\n", "")
s=s.replace("            if(configuration.role==='POS'&&tab==='fleet'){button.className='module-tab hidden';return;}\n", "")

old_init='''        byId('nodeCode').textContent=configuration.node_code||'Nœud non configuré';\n        byId('nodeMeta').textContent=(configuration.role||'—')+' • '+(configuration.mode||'—')+' • SIM '+((configuration.sim_slot||0)+1);\n        byId('robotState').textContent=configuration.robot_enabled?'ROBOT ACTIF':'ROBOT ARRÊTÉ';'''
new_init='''        byId('nodeCode').textContent=configuration.node_code||'Nœud non configuré';\n        var accountPhone=configuration.phone_number||'Numéro non renseigné';\n        byId('nodeMeta').textContent=(configuration.role||'—')+' • '+(configuration.mode||'—')+' • SIM '+((configuration.sim_slot||0)+1)+' • '+accountPhone;\n        byId('robotState').textContent=configuration.robot_enabled?'ROBOT ACTIF':'ROBOT ARRÊTÉ';\n        if(byId('birAccountRole')){byId('birAccountRole').textContent=configuration.role||'COMPTE';}\n        if(byId('birAccountNode')){byId('birAccountNode').textContent=configuration.node_code||'—';}\n        if(byId('birAccountPhone')){byId('birAccountPhone').textContent='SIM '+((configuration.sim_slot||0)+1)+' • '+accountPhone;}\n        if(byId('birRobotState')){byId('birRobotState').textContent=configuration.robot_enabled?'ROBOT ACTIF':'ROBOT ARRÊTÉ';}'''
s=replace_once(s,old_init,new_init,'BIR account identity')

# Positive role copy + action labels.
s=s.replace("showRoleNotice('Profil DAE : approvisionnement des DSM disponible. Un DAE n’achète pas auprès d’un supérieur et ne vend pas aux clients finaux.');", "showRoleNotice('DAE actif : pilotez vos DSM, leurs PoS, les soldes et les approvisionnements depuis votre propre pyramide.');if(byId('birRoleActionTitle')){byId('birRoleActionTitle').textContent='ACTIONS DAE PRIORITAIRES';byId('birRoleActionSub').textContent='Pilotez, approvisionnez et développez votre réseau.';byId('birTransactionModuleTitle').textContent='Approvisionnement Blue';}")
s=s.replace("showRoleNotice('Profil DSM : achat auprès du DAE et approvisionnement des PoS disponibles.');", "showRoleNotice('DSM actif : demandez du stock au DAE, approvisionnez vos PoS et suivez votre réseau direct.');if(byId('birRoleActionTitle')){byId('birRoleActionTitle').textContent='ACTIONS DSM PRIORITAIRES';byId('birRoleActionSub').textContent='Approvisionnez vos PoS et maîtrisez votre stock.';byId('birTransactionModuleTitle').textContent='Approvisionnement PoS';}")
s=s.replace("showRoleNotice('Profil PoS : achat auprès du DSM et vente aux clients finaux disponibles.');", "showRoleNotice('PoS actif : vendez du crédit Blue, demandez du stock à votre DSM et suivez votre propre activité.');if(byId('birRoleActionTitle')){byId('birRoleActionTitle').textContent='VENDRE & SUIVRE';byId('birRoleActionSub').textContent='Vendez du crédit Blue rapidement et gardez votre solde sous contrôle.';byId('birTransactionModuleTitle').textContent='Vente Blue';}")

# Bind the new functional home shortcuts after the normal tab handlers exist.
anchor='''        initializeInputErgonomics();\n        initializeTabs();\n        byId('refreshCommands').onclick=function(){refresh(true);};'''
new='''        initializeInputErgonomics();\n        initializeTabs();\n        each('[data-tab-jump]',function(button){button.onclick=function(){showTab(button.getAttribute('data-tab-jump'));};});\n        byId('refreshCommands').onclick=function(){refresh(true);};'''
s=replace_once(s,anchor,new,'BIR tab jumps')

# Role navigation exactly matches selected model while preserving every screen.
start=s.index('    function applyRoleNavigation(){')
end=s.index('    function showTab(name){', start)
nav_fn='''    function applyRoleNavigation(){\n        var fleet=document.querySelector('button[data-tab="fleet"]');\n        if(fleet){fleet.className='module-tab';fleet.setAttribute('aria-hidden','false');}\n        tabLabel('reports','Accueil');tabLabel('fleet','Réseau');tabLabel('support','Activité');tabLabel('config','Gérer');\n        if(configuration.role==='DAE'){tabLabel('flux','Piloter');}\n        else if(configuration.role==='DSM'){tabLabel('flux','Fournir');}\n        else if(configuration.role==='POS'){tabLabel('flux','Vendre');}\n        else{tabLabel('flux','Action');}\n        updateTabAttention();\n    }\n'''
s=s[:start]+nav_fn+s[end:]

# Project actual local metrics into the home without fabricating commercial values.
needle="""        byId('metricFinanceCount').textContent=String(finance);\n        byId('reportActivityTitle').textContent=last?(labels[last.state]||last.state||'Commande locale'):'Aucune activité locale';"""
replacement="""        byId('metricFinanceCount').textContent=String(finance);\n        if(byId('birActivityLine')){byId('birActivityLine').textContent=last?((labels[last.state]||last.state||'Commande')+' • '+(last.operation||'opération')+' • '+formatTime(last.updated_at||last.created_at||'')):'Aucune commande locale récente.';}\n        if(byId('birActivityDetail')){byId('birActivityDetail').textContent=last?('Dernière activité : '+(labels[last.state]||last.state||'Commande')+' • '+(last.operation||'opération')+' • '+formatTime(last.updated_at||last.created_at||'')):'Aucune activité locale récente. Les preuves Camtel et diagnostics restent disponibles ci-dessous.';}\n        byId('reportActivityTitle').textContent=last?(labels[last.state]||last.state||'Commande locale'):'Aucune activité locale';"""
s=replace_once(s,needle,replacement,'BIR activity projection')

# Fill the large real balance card from the existing dashboard object.
needle="""        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';\n        byId('balanceFreshness').textContent=own&&own.observed_at"""
replacement="""        byId('ownBalance').textContent=own&&own.balance!==null?formatMoney(own.balance)+' FCFA':'À actualiser';\n        if(byId('birCamtelBalance')){byId('birCamtelBalance').textContent=own&&own.balance!==null?formatMoney(own.balance):'À actualiser';}\n        if(byId('birAvailableBalance')){byId('birAvailableBalance').textContent=own&&own.available_balance!==null&&typeof own.available_balance!=='undefined'?formatMoney(own.available_balance)+' F':'—';}\n        if(byId('birReservedBalance')){byId('birReservedBalance').textContent=own?formatMoney(Number(own.reserved_amount||0))+' F':'—';}\n        if(byId('birThirdMetricLabel')&&byId('birThirdMetricValue')){\n            if(own&&(configuration.role==='DAE'||configuration.role==='DSM')){byId('birThirdMetricLabel').textContent='Composante commission';byId('birThirdMetricValue').textContent=formatMoney(Number(own.commission_component_balance||0))+' F';}\n            else{byId('birThirdMetricLabel').textContent='Commandes réussies';byId('birThirdMetricValue').textContent=byId('metricSuccessCount')?byId('metricSuccessCount').textContent:'0';}\n        }\n        if(byId('birBalanceFreshness')){byId('birBalanceFreshness').textContent=own&&own.observed_at?((own.balance_quality==='EXACT'?'Confirmé Camtel':'Estimé')+' • '+formatTime(own.operator_event_at||own.observed_at)):'Aucune lecture Camtel horodatée.';}\n        byId('balanceFreshness').textContent=own&&own.observed_at"""
s=replace_once(s,needle,replacement,'BIR balance projection')

s=s.replace("showToast('Serveur Blue Magic en ligne.');", "showToast('Serveur B.I.R. / Blue Magic Engine en ligne.');")
write(p,s)

# -----------------------------------------------------------------------------
# Visual system: selected blue/gold BIR model, readable secondary text, denser
# but still breathable small-phone layout. Existing classes remain functional.
# -----------------------------------------------------------------------------
p='app/src/main/assets/style.css'
s=read(p)
css=r'''

/* ========================================================================== */
/* B.I.R. v2.6.9 — commercial identity over the complete Blue Magic Engine.  */
/* ========================================================================== */
:root{color-scheme:light;--bir-navy:#041a3c;--bir-navy2:#082e69;--bir-blue:#087ff5;--bir-cyan:#22d6ff;--bir-gold:#f7b928;--bir-gold2:#ffe894;--bir-paper:#f5fbff;--bir-ink:#071b3c;--bir-muted:#526b86;--bir-line:#d8e8f5}
body{background:radial-gradient(circle at 87% 3%,rgba(26,159,255,.20),transparent 26%),radial-gradient(circle at 10% 17%,rgba(255,206,81,.14),transparent 20%),linear-gradient(180deg,#071d46 0,#082f6c 15%,#eef8ff 29%,#f9fdff 100%);color:var(--bir-ink)}
body::before{display:none}
.bir-topbar{position:sticky;top:0;z-index:11;min-height:86px;padding:9px 12px;background:linear-gradient(145deg,#031633,#082c65 58%,#084e95);border-bottom:1px solid rgba(91,218,255,.32);box-shadow:0 8px 25px rgba(2,25,60,.24);backdrop-filter:none}
.bir-brand-lockup{display:flex;align-items:center;gap:8px;min-width:0}.bir-logo-image{width:112px;height:auto;max-height:48px;object-fit:contain;border-radius:8px}.bir-brand-copy{min-width:0}.bir-brand-copy h1{margin:1px 0!important;font-size:1.32rem!important;color:#fff!important;background:none!important;-webkit-text-fill-color:initial!important}.bir-brand-copy .eyebrow{font-size:.61rem;color:#f8ca55;letter-spacing:.13em}.bir-tagline{margin:1px 0 0;color:#9feaff;font-size:.71rem;font-weight:800;white-space:nowrap}
.bir-account-chip{display:flex;flex-direction:column;align-items:flex-end;min-width:105px;color:#fff}.bir-account-role{font-size:.62rem;font-weight:900;color:#8fe8ff;letter-spacing:.08em}.bir-account-chip strong{font-size:.92rem;margin-top:2px}.bir-account-chip small{font-size:.68rem;color:#d2e9ff;margin-top:2px;max-width:150px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bir-account-chip .badge{margin-top:4px;font-size:.53rem;padding:4px 6px;background:rgba(255,255,255,.08);color:#8fe8ff;border-color:rgba(70,218,255,.30)}
main{padding:8px 10px 110px}.hero{padding:10px 12px;margin-bottom:8px;border-radius:16px;background:linear-gradient(110deg,rgba(5,31,71,.96),rgba(7,69,137,.94));border-color:rgba(80,209,255,.32);color:#fff;box-shadow:0 9px 23px rgba(4,41,86,.16)}.hero .muted{color:#c8e2f7}.hero h2{font-size:1.12rem}.status-orb{color:#74f4ad;border-color:rgba(87,245,166,.42);background:rgba(2,21,49,.32)}
.panel{background:#fff;color:var(--bir-ink);border:1px solid var(--bir-line);box-shadow:0 7px 20px rgba(9,66,119,.08)}.muted{color:var(--bir-muted);font-size:.82rem;line-height:1.48}.eyebrow{color:#087fa9;font-size:.69rem}.notice{background:#edf8ff;color:#214765;border-color:#cceafa;font-size:.79rem}.notice-danger{background:#fff0f2;color:#8e2235;border-color:#ffcbd3}
.bir-balance-card{position:relative;overflow:hidden;padding:17px 15px 14px;margin-bottom:9px;border-radius:23px;color:#fff;background:radial-gradient(circle at 82% 10%,rgba(38,207,255,.30),transparent 26%),radial-gradient(circle at 10% -10%,rgba(255,210,85,.24),transparent 29%),linear-gradient(135deg,#041b40,#073a7e 57%,#087ff5);border:1px solid rgba(92,221,255,.42);box-shadow:0 16px 38px rgba(3,44,95,.18)}
.bir-balance-card:after{content:"∞";position:absolute;right:-22px;bottom:-70px;color:rgba(255,255,255,.055);font-size:185px;font-weight:900;line-height:1}.bir-balance-head{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:flex-start;gap:10px}.bir-kicker{margin:0 0 3px;color:#6fe8ff;font-size:.76rem;font-weight:900;letter-spacing:.08em}.bir-balance-head strong{font-size:2.28rem;line-height:1;letter-spacing:-.04em;color:#fff}.bir-balance-head>div:first-child>span{margin-left:5px;font-size:.82rem;font-weight:900;color:#d7edff}.bir-balance-note{margin:5px 0 0;color:#a7ddff;font-size:.72rem}.bir-robot-orb{padding:9px 10px;border-radius:13px;border:1px solid rgba(107,242,175,.42);background:rgba(1,24,57,.30);color:#70f5aa;font-size:.68rem;font-weight:900;text-align:center}.bir-finance-grid{position:relative;z-index:1;display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:13px}.bir-finance-grid div{padding:9px 8px;border-radius:13px;background:rgba(2,22,53,.26);border:1px solid rgba(255,255,255,.12)}.bir-finance-grid span{display:block;color:#b9d9f2;font-size:.69rem;font-weight:750;line-height:1.2}.bir-finance-grid b{display:block;margin-top:4px;color:#fff;font-size:.92rem}
.bir-priority-action{display:flex;align-items:center;gap:10px;width:100%;min-height:72px;margin:0 0 11px;padding:10px 13px;border-radius:18px;color:#102445;background:linear-gradient(105deg,#e9a913,#ffd75f 58%,#fff0ae);box-shadow:0 10px 24px rgba(208,146,14,.20);text-align:left}.bir-priority-action .bir-action-infinity{width:48px;height:48px;flex:0 0 48px;display:grid;place-items:center;border-radius:15px;background:#072d66;color:#ffd45c;font-size:2rem;font-weight:900;box-shadow:0 0 14px rgba(255,197,51,.42),inset 0 0 0 1px rgba(255,231,154,.28)}.bir-priority-action span:nth-child(2){flex:1;min-width:0}.bir-priority-action b{display:block;font-size:.94rem;letter-spacing:.02em}.bir-priority-action small{display:block;margin-top:3px;color:#3f4b59;font-size:.78rem;line-height:1.25}.bir-priority-action i{font-style:normal;font-size:2rem}
.bir-section-title{display:flex;align-items:center;gap:9px;margin:10px 3px 8px}.bir-section-title span{height:1px;flex:1;background:linear-gradient(90deg,transparent,#1c8ee5)}.bir-section-title span:last-child{background:linear-gradient(90deg,#1c8ee5,transparent)}.bir-section-title h2{margin:0;color:#0a2a5f;font-size:1rem;letter-spacing:.04em}
.bir-modules-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:10px}.bir-modules-grid button{position:relative;min-height:105px;margin:0;padding:12px 10px 10px;border-radius:17px;background:#fff;color:#0b2853;border:1px solid #d4e7f6;box-shadow:0 7px 20px rgba(7,70,127,.07);text-align:left}.bir-modules-grid button i{display:grid;place-items:center;width:34px;height:34px;margin-bottom:7px;border-radius:11px;background:linear-gradient(145deg,#0b7cf1,#0747b5);color:#fff;font-style:normal;font-size:1.15rem;box-shadow:0 6px 14px rgba(8,100,219,.20)}.bir-modules-grid button b{display:block;font-size:.82rem;line-height:1.15}.bir-modules-grid button small{display:block;margin-top:4px;color:#526b86;font-size:.76rem;line-height:1.32;font-weight:500}
.bir-live-strip{display:flex;align-items:center;justify-content:space-between;gap:7px;padding:10px 11px;margin-bottom:10px;border-radius:16px;background:linear-gradient(100deg,#eafff5,#eef8ff 58%,#fff6db);border:1px solid #d9eaf4}.bir-live-strip>div{display:flex;align-items:center;gap:8px;min-width:0}.bir-pulse-dot{width:9px;height:9px;flex:0 0 auto;border-radius:50%;background:#18c87c;box-shadow:0 0 0 5px rgba(24,200,124,.12)}.bir-live-strip p{margin:0;min-width:0}.bir-live-strip b{display:block;font-size:.74rem;color:#0b2b59}.bir-live-strip small{display:block;margin-top:2px;color:#536e87;font-size:.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bir-live-strip button{width:auto;min-height:34px;margin:0;padding:0 8px;background:transparent;color:#0875d2;box-shadow:none;font-size:.72rem}
.module-intro,.module-card,.command-card,.history{padding:13px;margin-bottom:8px}.module-intro h3,.module-card h3,.command-card h3,.history h3{color:#0b2b59}.command-card p,.module-card p{font-size:.82rem}.metric-grid{margin:0 -3px 5px}.metric{width:calc(33.333% - 6px);min-height:86px;margin:3px;padding:10px;border-radius:14px}.metric strong{font-size:1.35rem;color:#087bf0}.metric span{font-size:.73rem;color:#5a718a;line-height:1.2}.metric-success strong{color:#0a9b68}.metric-warning strong{color:#bd7f00}.balance-row strong{font-size:1.7rem;color:#c58b00}.network-item{padding:9px 0}.network-item span{font-size:.75rem;color:#657b91}.network-balance{color:#173d65;font-size:.77rem}.compact-steps{color:#24425f;font-size:.82rem}
label{color:#173d65;font-size:.79rem}input{background:#f8fcff;color:#071b3c;border-color:#c8dfef;font-size:1rem}input:focus{border-color:#159ee5}.secondary,.transaction-action,button{background:linear-gradient(105deg,#0876df,#174ebc);color:#fff}.command-item{background:#f7fbff;border-color:#d7e8f4}.command-id{color:#56718b}.command-detail,.command-time{color:#627b93}.health-line{border-color:#dceaf3}
.module-tabs{left:8px;right:8px;bottom:6px;padding:5px 4px;background:rgba(3,24,56,.985);border-color:rgba(67,182,255,.30);border-radius:21px;box-shadow:0 13px 35px rgba(2,30,67,.38)}.module-tab{min-height:57px;color:#9cb1c9}.module-tab span{font-size:.66rem}.module-tab .module-icon{font-size:1.28rem}.module-tab.active{background:rgba(14,126,238,.20);color:#fff}.module-tab-primary{transform:translateY(-14px);border-radius:50%;min-width:66px;max-width:72px;height:72px;padding:5px;border:2px solid rgba(255,218,107,.80);background:radial-gradient(circle at 50% 35%,#785708,#1b3150 62%,#071a3a);box-shadow:0 0 0 4px rgba(255,196,43,.10),0 0 22px rgba(255,192,35,.58)}.module-tab-primary.active{background:radial-gradient(circle at 50% 35%,#a27608,#1e3857 62%,#061a3c);box-shadow:0 0 0 4px rgba(255,196,43,.12),0 0 28px rgba(255,192,35,.70)}.module-tab-primary .bir-nav-infinity{color:#ffd45b;font-size:2rem;line-height:.85;text-shadow:0 0 8px rgba(255,207,70,.82)}.module-tab-primary span:last-child{color:#ffe28a;font-size:.64rem;font-weight:900}
@media(max-width:360px),(max-height:600px){.bir-topbar{min-height:74px;padding:7px 8px}.bir-logo-image{width:86px;max-height:39px}.bir-brand-copy h1{font-size:1.12rem!important}.bir-brand-copy .eyebrow{font-size:.53rem}.bir-tagline{font-size:.62rem}.bir-account-chip{min-width:88px}.bir-account-chip strong{font-size:.8rem}.bir-account-chip small{font-size:.59rem;max-width:112px}main{padding:6px 7px 104px}.bir-balance-card{padding:13px 11px 11px;border-radius:19px}.bir-balance-head strong{font-size:1.95rem}.bir-balance-note{font-size:.68rem}.bir-finance-grid{gap:4px;margin-top:10px}.bir-finance-grid div{padding:7px 6px}.bir-finance-grid span{font-size:.63rem}.bir-finance-grid b{font-size:.82rem}.bir-priority-action{min-height:64px;padding:8px 9px}.bir-priority-action .bir-action-infinity{width:42px;height:42px;flex-basis:42px;font-size:1.75rem}.bir-priority-action b{font-size:.83rem}.bir-priority-action small{font-size:.72rem}.bir-modules-grid{gap:6px}.bir-modules-grid button{min-height:97px;padding:9px 8px}.bir-modules-grid button b{font-size:.76rem}.bir-modules-grid button small{font-size:.71rem}.muted,.command-card p,.module-card p{font-size:.77rem}.metric{width:calc(50% - 6px);min-height:78px}.metric span{font-size:.7rem}.module-tab span{font-size:.58rem}.module-tab-primary{min-width:62px;max-width:66px;height:66px;transform:translateY(-11px)}}
@media(max-width:300px){.bir-brand-copy .eyebrow,.bir-tagline{display:none}.bir-logo-image{width:78px}.bir-account-chip small{max-width:94px}.bir-finance-grid{grid-template-columns:1fr}.bir-modules-grid{grid-template-columns:1fr 1fr}.bir-modules-grid button small{font-size:.69rem}}
'''
if 'B.I.R. v2.6.9 — commercial identity' not in s:
    s += css
write(p,s)

# A contract test used by CI to prevent accidental loss of old functionality.
test=r'''import fs from 'node:fs';
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const js=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const main=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/MainActivity.java','utf8');
const gradle=fs.readFileSync('app/build.gradle','utf8');
for(const x of ['request-supply','supply-child','retail-sale','test-number','last-transactions','transaction-details','child-balance','freeze-self','init-child-pin-reset','suspend-child','reactivate-child','freeze-child','reactivate-frozen-child']){
  if(!html.includes('data-action="'+x+'"')) throw new Error('historical function missing: '+x);
}
for(const x of ['accounts','verify-sim','permissions','pin','change-pin','reset-pin','battery-settings','manage','start-robot','server-health','refresh-dashboard']){
  if(!html.includes('data-native-action="'+x+'"')) throw new Error('native function missing: '+x);
}
if(!main.includes('value.put("phone_number", AppConfig.phoneNumber')) throw new Error('SIM/account number missing from bridge');
for(const x of ['birCamtelBalance','birAvailableBalance','birReservedBalance','birAccountPhone','bir-nav-infinity','MODULES B.I.R.']){
  if(!(html+js+css).includes(x)) throw new Error('BIR functional UX missing: '+x);
}
if(!js.includes("bir_active_module_v269')||'reports'")) throw new Error('BIR home is not default');
if(!gradle.includes('versionCode 49')||!gradle.includes('versionName "2.6.9"')) throw new Error('version mismatch');
if(html.includes('une plateforme, pas un catalogue')||html.includes('Uniquement les capacités propres')) throw new Error('meta competitor/catalog copy must not appear');
console.log('BIR v2.6.9 functional UX + historical Blue Magic contract OK');
'''
write('app/src/test/bir-v269-functional-contract.mjs',test)
