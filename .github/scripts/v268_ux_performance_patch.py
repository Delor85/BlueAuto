from pathlib import Path


def read(path):
    return Path(path).read_text()


def write(path, text):
    Path(path).write_text(text)


def one(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing patch anchor: {label}')
    return text.replace(old, new, 1)


# -----------------------------------------------------------------------------
# 1) app.js — role-aware navigation and adaptive polling.
# -----------------------------------------------------------------------------
p = 'app/src/main/assets/app.js'
s = read(p)
s = one(s,
'''    var configuration = {}, commands = [], pendingPreview = null, capacityPolls = 0, dashboard = null;''',
'''    var configuration = {}, commands = [], pendingPreview = null, capacityPolls = 0, dashboard = null;
    var activeTab = 'flux', commandPollTimer = null, dashboardPollTimer = null;
    var commandPollCursor = 0, dashboardLoadedAt = 0;''',
'polling state')

s = one(s,
'''        onCommandCreated:function(data){setBusy(false);pendingPreview=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}upsert(command);render();if(command.robot_ready===false){showActionProgress((command.robot_status||'ROBOT_OFFLINE')+' — '+(command.robot_message||'Commande créée, mais le Robot ne communique pas encore.'));showToast('Commande créée, mais Robot hors ligne.');return;}showActionProgress('Commande créée. Le Robot détenteur de la SIM est connecté et va la prendre.');showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},
        onCommandStatus:function(data){if(data&&data.command){upsert(data.command);render();if(TERMINAL[data.command.state]){window.AndroidBridge.loadDashboard();}}},''',
'''        onCommandCreated:function(data){setBusy(false);pendingPreview=null;if(data.error){showActionError(data);return;}clearActionError();var command=data.command||{};if(!command.public_id){showActionError({code:'INVALID_RESPONSE',message:'Réponse serveur incomplète.'});return;}upsert(command);render();scheduleCommandPoll(1200);if(command.robot_ready===false){showActionProgress((command.robot_status||'ROBOT_OFFLINE')+' — '+(command.robot_message||'Commande créée, mais le Robot ne communique pas encore.'));showToast('Commande créée, mais Robot hors ligne.');return;}showActionProgress('Commande créée. Le Robot détenteur de la SIM est connecté et va la prendre.');showToast(data.duplicate?'Cette demande existait déjà.':'Commande créée et transmise au Robot exact.');},
        onCommandStatus:function(data){if(data&&data.command){upsert(data.command);render();if(TERMINAL[data.command.state]){requestDashboard(true);}scheduleCommandPoll(5000);}},''',
'command callbacks')

s = one(s,
'''        onDashboard:function(data){if(data&&data.error){showToast((data.code||'DASHBOARD_ERROR')+' — '+(data.message||'Rapport indisponible.'));return;}dashboard=data||{};renderDashboard();}''',
'''        onDashboard:function(data){if(data&&data.error){showToast((data.code||'DASHBOARD_ERROR')+' — '+(data.message||'Rapport indisponible.'));scheduleDashboardPoll();return;}dashboard=data||{};dashboardLoadedAt=new Date().getTime();renderDashboard();scheduleDashboardPoll();}''',
'dashboard callback')

old_init = '''        render();refresh();window.AndroidBridge.loadDashboard();window.setInterval(refresh,15000);
        window.setInterval(function(){if(document.visibilityState!=='hidden'){try{window.AndroidBridge.loadDashboard();}catch(ignored){}}},30000);
        document.addEventListener('visibilitychange',function(){if(document.visibilityState!=='hidden'){try{window.AndroidBridge.loadDashboard();}catch(ignored){}}});'''
new_init = '''        render();refresh(true);scheduleCommandPoll(5000);
        if(dashboardRelevant()){requestDashboard(true);}scheduleDashboardPoll();
        document.addEventListener('visibilitychange',function(){
            if(document.visibilityState==='hidden'){clearPollingTimers();return;}
            scheduleCommandPoll(250);
            if(dashboardRelevant()){requestDashboard(false);}
            scheduleDashboardPoll();
        });'''
s = one(s, old_init, new_init, 'adaptive initialize polling')

old_tabs = '''    function initializeTabs(){
        var saved=localStorage.getItem('blue_magic_active_module')||'flux';
        each('button[data-tab]',function(button){button.onclick=function(){showTab(button.getAttribute('data-tab'));};});
        showTab(saved);
    }
    function showTab(name){
        var found=false;
        each('[data-tab-panel]',function(panel){var active=panel.getAttribute('data-tab-panel')===name;found=found||active;panel.className=active?'module-screen':'module-screen hidden';});
        if(!found&&name!=='flux'){showTab('flux');return;}
        each('button[data-tab]',function(button){button.className=button.getAttribute('data-tab')===name?'module-tab active':'module-tab';});
        each('button[data-tab="flux"]',function(button){button.className=button.getAttribute('data-tab')===name?'module-tab module-tab-primary active':'module-tab module-tab-primary';});
        localStorage.setItem('blue_magic_active_module',name);
        window.scrollTo(0,0);
    }
'''
new_tabs = r'''    function initializeTabs(){
        var saved=localStorage.getItem('blue_magic_active_module')||'flux';
        applyRoleNavigation();
        if(configuration.role==='POS'&&saved==='fleet'){saved='flux';}
        each('button[data-tab]',function(button){button.onclick=function(){showTab(button.getAttribute('data-tab'));};});
        showTab(saved);
    }
    function tabLabel(tab,value){
        var button=document.querySelector('button[data-tab="'+tab+'"]'),spans;
        if(!button){return;}spans=button.querySelectorAll('span');
        if(spans.length>1){spans[spans.length-1].textContent=value;}
    }
    function applyRoleNavigation(){
        var fleet=document.querySelector('button[data-tab="fleet"]');
        if(fleet){fleet.className='module-tab';fleet.setAttribute('aria-hidden','false');}
        if(configuration.role==='DAE'){
            tabLabel('reports','Pilotage');tabLabel('fleet','Réseau');tabLabel('flux','Flux');tabLabel('config','Robot');tabLabel('support','SAV');
        }else if(configuration.role==='DSM'){
            tabLabel('reports','Soldes');tabLabel('fleet','Réseau');tabLabel('flux','Flux');tabLabel('config','Robot');tabLabel('support','SAV');
        }else if(configuration.role==='POS'){
            tabLabel('reports','Solde');tabLabel('flux','Vente');tabLabel('config','Robot');tabLabel('support','Aide');
            if(fleet){fleet.className='module-tab hidden';fleet.setAttribute('aria-hidden','true');}
        }
        updateTabAttention();
    }
    function showTab(name){
        var found=false;
        if(configuration.role==='POS'&&name==='fleet'){name='flux';}
        activeTab=name;
        each('[data-tab-panel]',function(panel){var active=panel.getAttribute('data-tab-panel')===name;found=found||active;panel.className=active?'module-screen':'module-screen hidden';});
        if(!found&&name!=='flux'){showTab('flux');return;}
        each('button[data-tab]',function(button){
            var tab=button.getAttribute('data-tab'),isActive=tab===name,isPrimary=tab==='flux';
            if(configuration.role==='POS'&&tab==='fleet'){button.className='module-tab hidden';return;}
            button.className='module-tab'+(isPrimary?' module-tab-primary':'')+(isActive?' active':'');
        });
        localStorage.setItem('blue_magic_active_module',name);
        if(dashboardRelevant()){requestDashboard(false);}scheduleDashboardPoll();
        updateTabAttention();
        window.scrollTo(0,0);
    }
    function ensureTabBadge(tab){
        var button=document.querySelector('button[data-tab="'+tab+'"]'),badge;
        if(!button){return null;}badge=button.querySelector('.module-tab-attention');
        if(!badge){badge=document.createElement('b');badge.className='module-tab-attention hidden';button.appendChild(badge);}return badge;
    }
    function updateTabAttention(){
        var pending=0,i,flux=ensureTabBadge('flux'),robot=ensureTabBadge('config'),needsRobot=false;
        for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){pending+=1;}}
        if(flux){flux.textContent=pending>9?'9+':String(pending);flux.className=pending?'module-tab-attention':'module-tab-attention hidden';}
        needsRobot=configuration.mode==='ROBOT'&&(!configuration.sim_verified||!configuration.pin_configured||!configuration.accessibility_enabled||!configuration.robot_enabled||configuration.pin_blocked);
        if(robot){robot.textContent='!';robot.className=needsRobot?'module-tab-attention module-tab-warning':'module-tab-attention hidden';}
    }
'''
s = one(s, old_tabs, new_tabs, 'role-aware tabs')

old_refresh = '''    function refresh(){var i;if(!bridge()){return;}for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){window.AndroidBridge.getCommandStatus(commands[i].public_id);}}}'''
new_refresh = r'''    function hasPendingCommands(){var i;for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){return true;}}return false;}
    function clearPollingTimers(){if(commandPollTimer){window.clearTimeout(commandPollTimer);commandPollTimer=null;}if(dashboardPollTimer){window.clearTimeout(dashboardPollTimer);dashboardPollTimer=null;}}
    function scheduleCommandPoll(delay){
        if(commandPollTimer){window.clearTimeout(commandPollTimer);commandPollTimer=null;}
        if(document.visibilityState==='hidden'||!hasPendingCommands()){return;}
        commandPollTimer=window.setTimeout(function(){commandPollTimer=null;refresh(false);},Math.max(250,delay||5000));
    }
    function refresh(forceAll){
        var pending=[],i,start,count=0,max=forceAll?999:4;
        if(!bridge()||document.visibilityState==='hidden'){return;}
        for(i=0;i<commands.length;i+=1){if(!TERMINAL[commands[i].state]){pending.push(commands[i]);}}
        if(!pending.length){updateTabAttention();return;}
        start=commandPollCursor%pending.length;
        for(i=0;i<pending.length&&count<max;i+=1){
            window.AndroidBridge.getCommandStatus(pending[(start+i)%pending.length].public_id);count+=1;
        }
        commandPollCursor=(start+count)%pending.length;
        updateTabAttention();scheduleCommandPoll(5000);
    }
    function dashboardRelevant(){return activeTab==='reports'||activeTab==='fleet';}
    function requestDashboard(force){
        var now=new Date().getTime();
        if(!bridge()||document.visibilityState==='hidden'){return;}
        if(!force&&dashboardLoadedAt&&now-dashboardLoadedAt<15000){return;}
        try{window.AndroidBridge.loadDashboard();dashboardLoadedAt=now;}catch(ignored){}
    }
    function scheduleDashboardPoll(){
        if(dashboardPollTimer){window.clearTimeout(dashboardPollTimer);dashboardPollTimer=null;}
        if(document.visibilityState==='hidden'||!dashboardRelevant()){return;}
        dashboardPollTimer=window.setTimeout(function(){dashboardPollTimer=null;requestDashboard(false);scheduleDashboardPoll();},60000);
    }'''
s = one(s, old_refresh, new_refresh, 'smart polling functions')

# Manual refresh should query the complete visible pending set immediately.
s = s.replace("byId('refreshCommands').onclick=refresh;", "byId('refreshCommands').onclick=function(){refresh(true);};", 1)

# Every render updates navigation attention; every upsert keeps polling alive.
s = one(s,
'''    function upsert(command){var i,index=-1,key;for(i=0;i<commands.length;i+=1){if(commands[i].public_id===command.public_id){index=i;break;}}if(index<0){commands.unshift(command);}else{for(key in command){if(Object.prototype.hasOwnProperty.call(command,key)){commands[index][key]=command[key];}}}commands=commands.slice(0,20);localStorage.setItem(storageKey(),JSON.stringify(commands));}''',
'''    function upsert(command){var i,index=-1,key;for(i=0;i<commands.length;i+=1){if(commands[i].public_id===command.public_id){index=i;break;}}if(index<0){commands.unshift(command);}else{for(key in command){if(Object.prototype.hasOwnProperty.call(command,key)){commands[index][key]=command[key];}}}commands=commands.slice(0,20);localStorage.setItem(storageKey(),JSON.stringify(commands));updateTabAttention();if(hasPendingCommands()){scheduleCommandPoll(5000);}}''',
'upsert scheduling')

s = s.replace("byId('supportStatus').textContent=support;\n    }", "byId('supportStatus').textContent=support;updateTabAttention();\n    }", 1)
write(p, s)


# -----------------------------------------------------------------------------
# 2) CSS — flexible 4/5-tab dock, low-end static visuals, compact two-column actions.
# -----------------------------------------------------------------------------
p = 'app/src/main/assets/style.css'
s = read(p)
s = s.replace('.module-tab{width:20%;min-width:0;', '.module-tab{flex:1 1 0;width:auto;min-width:0;', 1)
s = s.replace('.module-tab{position:relative;width:20%;min-width:0;', '.module-tab{position:relative;flex:1 1 0;width:auto;min-width:0;', 1)
old_media = '''@media(max-width:360px),(max-height:600px){.module-tabs{left:6px;right:6px;bottom:5px;padding:5px 3px;border-radius:16px}.module-tab{min-height:51px;font-size:.56rem}.module-tab span{font-size:.5rem}.module-tab .module-icon{font-size:1.08rem}.module-tab-primary{transform:translateY(-10px)}.module-actions button{width:calc(100% - 8px)}}'''
new_media = '''@media(max-width:360px),(max-height:600px){.module-tabs{left:6px;right:6px;bottom:5px;padding:5px 3px;border-radius:16px}.module-tab{min-height:51px;font-size:.56rem}.module-tab span{font-size:.5rem}.module-tab .module-icon{font-size:1.08rem}.module-tab-primary{transform:translateY(-10px)}}
@media(max-width:329px){.module-actions button{width:calc(100% - 8px)}}
@media(min-width:330px) and (max-width:360px),(min-width:330px) and (max-height:600px){.module-actions button{width:calc(50% - 8px);font-size:.68rem}.admin-actions button{width:calc(100% - 8px)}}'''
s = one(s, old_media, new_media, 'compact action media rules')

s += '''

/* v2.6.8 — navigation adaptative et mode léger pour terminaux anciens. */
.module-tab-attention{position:absolute;right:8px;top:4px;display:flex!important;align-items:center;justify-content:center;min-width:18px;height:18px;margin:0!important;padding:0 4px;border-radius:999px;background:#ffd56a;color:#07152d;font-size:.58rem!important;font-weight:900;line-height:1;box-shadow:0 2px 8px rgba(0,0,0,.35)}
.module-tab-warning{background:#ff8b98;color:#27040a}
@media(max-width:360px),(max-height:600px){body::before{animation:none;opacity:.42}.topbar{backdrop-filter:none}.panel{box-shadow:0 5px 14px rgba(0,0,0,.18)}.module-tabs{box-shadow:0 8px 22px rgba(0,0,0,.42)}.module-tab-primary{box-shadow:0 5px 14px rgba(38,112,255,.36)}}
'''
write(p, s)


# -----------------------------------------------------------------------------
# 3) Dedicated regression contract.
# -----------------------------------------------------------------------------
test = r'''import fs from 'node:fs';
const ui=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
for(const tab of ['reports','fleet','flux','config','support']){
  if(!html.includes('data-tab="'+tab+'"')) throw new Error('historical module missing: '+tab);
}
for(const roleLabel of ["configuration.role==='DAE'","configuration.role==='DSM'","configuration.role==='POS'","tabLabel('reports','Pilotage')","tabLabel('reports','Soldes')","tabLabel('reports','Solde')","tabLabel('flux','Vente')"]){
  if(!ui.includes(roleLabel)) throw new Error('role navigation contract missing: '+roleLabel);
}
if(!ui.includes("fleet.className='module-tab hidden'")) throw new Error('POS fleet hiding missing');
if(ui.includes('window.setInterval(refresh,15000)')) throw new Error('legacy unconditional command polling remains');
if(ui.includes('},30000)')) throw new Error('legacy unconditional dashboard polling remains');
for(const contract of ['scheduleCommandPoll','scheduleDashboardPoll','dashboardRelevant','commandPollCursor','document.visibilityState','updateTabAttention']){
  if(!ui.includes(contract)) throw new Error('adaptive runtime contract missing: '+contract);
}
if(!css.includes('flex:1 1 0;width:auto')) throw new Error('flexible 4/5 tab dock missing');
if(!css.includes('.module-tab-attention')) throw new Error('tab attention badge styling missing');
if(!css.includes('body::before{animation:none;opacity:.42}')) throw new Error('low-end static magic mode missing');
if(!css.includes('@media(max-width:329px)')) throw new Error('ultra-narrow one-column actions missing');
if(!css.includes('.admin-actions button{width:calc(100% - 8px)}')) throw new Error('long admin actions compact fallback missing');
console.log('v2.6.8 UX/performance: role dock, adaptive polling, attention badges and low-end mode OK');
'''
write('app/src/test/v268-ux-performance.mjs', test)
