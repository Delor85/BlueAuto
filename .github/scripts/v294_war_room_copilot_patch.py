from pathlib import Path
import re

ROOT = Path('.')

def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 anchor, got {count}')
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Version metadata + Android telemetry version
# ---------------------------------------------------------------------------
p='app/build.gradle'; s=read(p)
s=once(s,'versionCode 58','versionCode 59','versionCode')
s=once(s,'versionName "2.9.3"','versionName "2.9.4"','versionName')
write(p,s)

p='app/src/main/java/com/profitloop/blueauto/ApiClient.java'; s=read(p)
if s.count('payload.put("app_version", "2.9.3");') < 2:
    raise SystemExit('ApiClient app_version anchors missing')
s=s.replace('payload.put("app_version", "2.9.3");','payload.put("app_version", "2.9.4");')
write(p,s)

# ---------------------------------------------------------------------------
# Always open on the operational home/War Room. Navigation remains manual after.
# ---------------------------------------------------------------------------
p='app/src/main/assets/app.js'; s=read(p)
s=once(s,"        var saved=localStorage.getItem('bir_active_module_v269')||'reports';",
       "        var saved='reports'; // v2.9.4: every fresh app opening starts from the War Room summary.",
       'home tab')
write(p,s)

# ---------------------------------------------------------------------------
# Server: no operator-imposed commission defaults. Each DAE/DSM defines its own.
# Existing stored choices are preserved; only new accounts/default fallbacks change.
# ---------------------------------------------------------------------------
p='cloudflare/src/index.js'; s=read(p)
s=once(s,"const API_VERSION = '2.9.3-cloudflare';","const API_VERSION = '2.9.4-cloudflare';",'worker version')
s=once(s,
       "reconciliation_center: true, effective_modes: ['REMOTE','ROBOT']",
       "reconciliation_center: true, war_room: true, operational_copilot: true, commission_free_competition: true, effective_modes: ['REMOTE','ROBOT']",
       'worker capabilities')
s=once(s,
       ".bind(node, role, phoneNumber, role === 'DAE' ? 1000 : role === 'DSM' ? 800 : 0).run();",
       ".bind(node, role, phoneNumber, 0).run();",
       'root node commission default')
s=once(s,
       ".bind(desired, childRole, p, auth.node_code, childRole === 'DSM' ? 800 : 0).run();",
       ".bind(desired, childRole, p, auth.node_code, 0).run();",
       'shadow child commission default')
s=once(s,
       "const inboundRate = Number(row.inbound_commission_bps || (row.role === 'DAE' ? 1000 : row.role === 'DSM' ? 900 : row.role === 'POS' ? 800 : 0));",
       "const inboundRate = Number(row.inbound_commission_bps || 0);",
       'inbound commission fallback')
s=once(s,
       "stockout:daysCover==null?'UNKNOWN':daysCover<1?'CRITICAL':daysCover<3?'WATCH':'COMFORTABLE'",
       "stockout:balance!=null&&Number(balance)<=0?'OUT':daysCover==null?'UNKNOWN':daysCover<1?'CRITICAL':daysCover<3?'WATCH':'COMFORTABLE'",
       'stockout OUT state')
s=once(s,
       "stockout_critical:output.filter(n=>n.stockout==='CRITICAL').length,stockout_watch:output.filter(n=>n.stockout==='WATCH').length",
       "stockout_out:output.filter(n=>n.stockout==='OUT').length,stockout_critical:output.filter(n=>n.stockout==='CRITICAL').length,stockout_watch:output.filter(n=>n.stockout==='WATCH').length",
       'command center summary')
write(p,s)

# ---------------------------------------------------------------------------
# War Room + no-cost local operational Copilot.
# No external AI/API dependency. No financial execution. Buttons only navigate,
# prefill safe fields, refresh, or request non-financial WAKE_SYNC assistance.
# ---------------------------------------------------------------------------
war_js = r'''(function(){
'use strict';
function id(x){return document.getElementById(x);}function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function safe(raw,f){try{return JSON.parse(raw);}catch(e){return f;}}function cfg(){try{return safe((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}',{});}catch(e){return {};}}
function up(v){return String(v||'').toUpperCase();}function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function money(v){var n=Number(v);return isFinite(n)?String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' ')+' F':'—';}
function req(a,p){var b=bridge();if(b&&b.platformAction)b.platformAction(a,JSON.stringify(p||{}));}
function lang(){try{return bridge()&&bridge().getUiLanguage&&bridge().getUiLanguage()==='en'?'en':'fr';}catch(e){return 'fr';}}
var L=lang();function t(fr,en){return L==='en'?en:fr;}
var C=cfg(),D=null,CC=null,OPS=null,actions=[];var key='bir_war_room_v294_'+String(C.profile_id||C.node_code||'default');
function loadCache(part){try{return safe(localStorage.getItem(key+'_'+part)||'null',null);}catch(e){return null;}}
function saveCache(part,v){try{localStorage.setItem(key+'_'+part,JSON.stringify(v));}catch(e){}}
D=loadCache('dashboard');CC=loadCache('cc');OPS=loadCache('ops');
function goTab(name){var b=document.querySelector('button[data-tab="'+name+'"]');if(b&&b.click)b.click();}
function own(){var list=(D&&D.nodes)||[];for(var i=0;i<list.length;i++)if(String(list[i].node_code)===String(C.node_code))return list[i];return null;}
function ccOwn(){var list=(CC&&CC.nodes)||[];for(var i=0;i<list.length;i++)if(String(list[i].node_code)===String(C.node_code))return list[i];return null;}
function directChildren(){var list=(CC&&CC.nodes)||[],out=[];for(var i=0;i<list.length;i++)if(String(list[i].parent_node_code||'')===String(C.node_code||''))out.push(list[i]);return out;}
function flow7(){var f=(CC&&CC.flows_7d)||[],n=0;for(var i=0;i<f.length;i++)n+=Number(f[i].amount||0);return n;}
function queueCount(){var q=C.unified_queue||{},n=0,i,a;if(Array.isArray(q))return q.length;for(var k in q){if(!Object.prototype.hasOwnProperty.call(q,k))continue;a=q[k];if(Array.isArray(a)){for(i=0;i<a.length;i++){var s=up(a[i]&&a[i].state);if(!/^(SUCCEEDED|FAILED|UNKNOWN|BLOCKED|CANCELLED)$/.test(s))n++;}}}return n+Number(C.offline_pending_events||0);}
function sickChildren(kids){var an=(CC&&CC.anomalies)||[],m={},i,c;for(i=0;i<an.length;i++){c=String(an[i].node_code||'');if(c)m[c]=true;}for(i=0;i<kids.length;i++){c=kids[i];if(Number(c.failure_rate_24h||0)>=20||Number(c.oldest_queue_age_seconds||0)>=900||Number(c.robot_age_seconds||0)>=1800)m[String(c.node_code)]=true;}var n=0;for(i=0;i<kids.length;i++)if(m[String(kids[i].node_code)])n++;return n;}
function days(v){if(v==null||!isFinite(Number(v)))return '—';var n=Number(v);if(n<1)return Math.max(0,Math.round(n*24))+' h';return (Math.round(n*10)/10)+' j';}
function shell(){var reports=document.querySelector('[data-tab-panel="reports"]');if(!reports||id('v294WarRoom'))return;var box=document.createElement('article');box.id='v294WarRoom';box.className='v294-war';box.innerHTML='<div class="v294-head"><div><span class="v294-badge">∞ '+t('WAR ROOM B.I.R.','B.I.R. WAR ROOM')+'</span><h2>'+t('Ma situation maintenant','My situation now')+'</h2><small id="v294Fresh">'+t('Dernières données connues','Latest known data')+'</small></div><button id="v294Refresh">'+t('ACTUALISER','REFRESH')+'</button></div><div id="v294Balances" class="v294-balances"></div><div class="v294-kpis"><div><span>⏳ '+t('Autonomie stock','Stock runway')+'</span><b id="v294Runway">—</b><small id="v294RunwaySub">—</small></div><div><span>🔴 '+t('En rupture','Out of stock')+'</span><b id="v294Out">0</b><small>'+t('enfants directs','direct children')+'</small></div><div><span>🟠 '+t('À surveiller','Approaching')+'</span><b id="v294Watch">0</b><small>'+t('enfants directs','direct children')+'</small></div><div><span>🩺 '+t('En difficulté','Needs help')+'</span><b id="v294Sick">0</b><small>'+t('santé / file / synchro','health / queue / sync')+'</small></div><div><span>📈 '+t('Activité 7 jours','7-day activity')+'</span><b id="v294Week">—</b><small>'+t('réseau visible','visible network')+'</small></div></div><section class="v294-urgent"><div class="v294-section"><div><small>'+t('PRIORITÉS','PRIORITIES')+'</small><h3>'+t('5 actions à traiter','5 actions to handle')+'</h3></div><span id="v294State" class="v294-state">—</span></div><div id="v294Actions"></div></section><section class="v294-copilot"><div class="v294-copilot-head"><div><span>✦ B.I.R. Copilot</span><small>'+t('Guide intelligent local • 0 FCFA • fonctionne hors ligne','Local smart guide • 0 FCFA • works offline')+'</small></div><button id="v294Explain">?</button></div><p id="v294Brief">'+t('J’analyse les dernières informations connues.','I am analyzing the latest known information.')+'</p><div class="v294-ask"><input id="v294Question" type="text" autocomplete="off" placeholder="'+t('Ex. ma file est bloquée','E.g. my queue is stuck')+'"><button id="v294Ask">'+t('AIDER','HELP')+'</button></div><p id="v294Answer" class="v294-answer"></p><div class="v294-quick"><button data-v294-q="file">'+t('File bloquée','Queue stuck')+'</button><button data-v294-q="sync">'+t('Synchronisation','Synchronization')+'</button><button data-v294-q="access">'+t('Accessibilité','Accessibility')+'</button><button data-v294-q="stock">'+t('Rupture stock','Stockout')+'</button></div></section>';reports.insertBefore(box,reports.firstChild);id('v294Refresh').onclick=refresh;id('v294Ask').onclick=ask;id('v294Question').onkeydown=function(e){if((e||window.event).keyCode===13)ask();};id('v294Explain').onclick=function(){id('v294Answer').textContent=t('Le Copilot 2.9.4 n’est pas un gros chatbot : il lit seulement l’état B.I.R. déjà disponible, applique des règles opérationnelles explicables et vous conduit vers le bon écran. Il ne lance jamais une transaction financière.','Copilot 2.9.4 is not a large chatbot: it only reads B.I.R. state already available, applies explainable operational rules and takes you to the right screen. It never executes a financial transaction.');};var qs=box.querySelectorAll('[data-v294-q]');for(var i=0;i<qs.length;i++)qs[i].onclick=function(){id('v294Question').value=this.getAttribute('data-v294-q');ask();};render();window.setTimeout(function(){if(!D||!CC)refresh();},1200);}
function refresh(){var b=bridge();if(b&&b.loadDashboard)b.loadDashboard();req(C.owner_admin_workspace?'owner_distribution_command_center':'distribution_command_center',{});req(C.owner_admin_workspace?'owner_ops_cockpit':'ops_cockpit',{});try{if(b&&b.refreshQueueSnapshot)b.refreshQueueSnapshot();}catch(e){}id('v294Fresh').textContent=t('Actualisation en cours…','Refreshing…');}
function priorityActions(){var a=[],me=ccOwn(),kids=directChildren(),q=queueCount(),an=(CC&&CC.anomalies)||[],i,x,code;
function add(p,title,detail,type,node){a.push({p:p,title:title,detail:detail,type:type,node:node||''});}
if(C.mode==='ROBOT'&&C.pin_blocked)add(120,t('Corriger le PIN Robot','Fix Robot PIN'),t('Les opérations financières sont bloquées tant que le PIN n’est pas corrigé.','Financial operations are blocked until the PIN is fixed.'),'pin');
if(C.mode==='ROBOT'&&!C.accessibility_enabled)add(115,t('Réactiver l’Accessibilité','Re-enable Accessibility'),t('Le Robot conserve sa file mais attend cette autorisation Android.','The Robot keeps its queue but waits for this Android permission.'),'access');
else if(C.mode==='ROBOT'&&C.accessibility_enabled&&!C.accessibility_connected)add(110,t('Accessibilité en reconnexion','Accessibility reconnecting'),t('Autorisation présente : vérifier la reconnexion du service sans recréer la file.','Permission present: check service reconnection without rebuilding the queue.'),'config');
if(q>0)add(105,t('Vérifier la file en attente','Check pending queue'),q+' '+t('élément(s) attendent encore une synchronisation ou un résultat.','item(s) still await synchronization or a result.'),'queue');
if(me&&(me.stockout==='OUT'||me.stockout==='CRITICAL'))add(100,t('Sécuriser mon stock','Secure my stock'),me.stockout==='OUT'?t('Votre stock connu est épuisé.','Your known stock is depleted.'):t('Votre autonomie estimée est inférieure à un jour.','Estimated runway is under one day.'),(up(C.role)==='DAE'?'balance':'request-stock'));
for(i=0;i<kids.length;i++){x=kids[i];if(x.stockout==='OUT')add(98,t('Approvisionner ','Supply ')+x.node_code,t('Cet enfant est en rupture de stock.','This child is out of stock.'),'supply-child',x.node_code);else if(x.stockout==='CRITICAL')add(92,t('Approvisionner ','Supply ')+x.node_code,t('Moins d’un jour de couverture estimée.','Less than one day of estimated coverage.'),'supply-child',x.node_code);else if(x.stockout==='WATCH')add(72,t('Préparer ','Prepare ')+x.node_code,t('Couverture estimée inférieure à 3 jours.','Estimated coverage is under 3 days.'),'supply-child',x.node_code);}
for(i=0;i<an.length;i++){x=an[i];code=String(x.node_code||'');if(!code||code===String(C.node_code)||!/QUEUE_STALE|ROBOT_STALE|ACCESSIBILITY_DISCONNECTED|FAILURE_SPIKE/.test(String(x.code||'')))continue;for(var j=0;j<kids.length;j++)if(String(kids[j].node_code)===code){add(80,t('Aider ','Help ')+code,x.message||t('Un problème opérationnel demande votre attention.','An operational issue needs attention.'),'assist',code);break;}}
if(CC&&CC.service_signal&&CC.service_signal.code==='PROBABLE_OPERATOR_INCIDENT')add(90,t('Vérifier l’incident réseau','Check network incident'),CC.service_signal.message||t('Plusieurs comptes présentent la même anomalie.','Several accounts show the same anomaly.'),'support');
if(!a.length)add(10,t('Actualiser la situation','Refresh situation'),t('Aucune urgence détectée. Garder les données fraîches.','No urgency detected. Keep data fresh.'),'refresh');
a.sort(function(x,y){return y.p-x.p;});var seen={},out=[];for(i=0;i<a.length&&out.length<5;i++){var k=a[i].type+'|'+a[i].node;if(!seen[k]){seen[k]=1;out.push(a[i]);}}return out;}
function act(x){var b=bridge(),el;if(!x)return;if(x.type==='pin'){try{b.openPinSettings();}catch(e){goTab('config');}return;}if(x.type==='access'){try{b.prepareRobotPermissions();}catch(e){}goTab('config');return;}if(x.type==='config'){goTab('config');return;}if(x.type==='queue'){try{if(b.syncOfflineNow)b.syncOfflineNow();if(b.refreshQueueSnapshot)b.refreshQueueSnapshot();}catch(e){}goTab('support');return;}if(x.type==='request-stock'){goTab('flux');el=id('requestSupplyCard');if(el&&el.scrollIntoView)el.scrollIntoView(true);return;}if(x.type==='supply-child'){goTab('flux');el=id('childNode');if(el){el.value=x.node;try{el.dispatchEvent(new Event('input',{bubbles:true}));}catch(e){}}var card=id('supplyChildCard');if(card&&card.scrollIntoView)card.scrollIntoView(true);return;}if(x.type==='assist'){req('ops_assist',{target_node_code:x.node,action:'WAKE_SYNC',reason:'WAR_ROOM_V294'});return;}if(x.type==='balance'){var bt=document.querySelector('button[data-action="check-balance"]');if(bt&&bt.click)bt.click();else goTab('reports');return;}if(x.type==='support'){goTab('support');return;}refresh();}
function render(){if(!id('v294WarRoom'))return;C=cfg();var o=own(),me=ccOwn(),kids=directChildren(),out=0,watch=0,i;for(i=0;i<kids.length;i++){if(kids[i].stockout==='OUT')out++;else if(kids[i].stockout==='CRITICAL'||kids[i].stockout==='WATCH')watch++;}var bal=id('v294Balances');if(up(C.role)==='POS'){bal.innerHTML='<div class="v294-balance v294-balance-main"><span>'+t('SOLDE BLUE','BLUE BALANCE')+'</span><b>'+money(o&&o.balance)+'</b><small>'+t('Dernière preuve disponible','Latest available evidence')+'</small></div>';}else{var real=o&&o.commission_base_balance!=null?o.commission_base_balance:o&&o.balance;var com=o&&o.commission_component_balance!=null?o.commission_component_balance:0;bal.innerHTML='<div class="v294-balance v294-balance-main"><span>'+t('CRÉDIT RÉEL','REAL CREDIT')+'</span><b>'+money(real)+'</b><small>'+t('hors composante commission','excluding commission component')+'</small></div><div class="v294-balance"><span>'+t('COMMISSION','COMMISSION')+'</span><b>'+money(com)+'</b><small>'+t('selon vos règles commerciales','according to your commercial rules')+'</small></div><div class="v294-balance"><span>'+t('TOTAL BLUE','BLUE TOTAL')+'</span><b>'+money(o&&o.balance)+'</b><small>'+t('crédit réel + commission','real credit + commission')+'</small></div>';}
id('v294Runway').textContent=days(me&&me.days_cover);id('v294RunwaySub').textContent=me?(me.stockout==='OUT'?t('RUPTURE','OUT OF STOCK'):me.stockout==='CRITICAL'?t('urgence < 1 jour','urgent < 1 day'):me.stockout==='WATCH'?t('surveiller < 3 jours','watch < 3 days'):t('niveau confortable','comfortable level')):t('données insuffisantes','insufficient data');id('v294Out').textContent=String(out);id('v294Watch').textContent=String(watch);id('v294Sick').textContent=String(sickChildren(kids));id('v294Week').textContent=money(flow7());
actions=priorityActions();var h=[];for(i=0;i<actions.length;i++)h.push('<button class="v294-action" data-v294-action="'+i+'"><span class="v294-num">'+(i+1)+'</span><span><b>'+esc(actions[i].title)+'</b><small>'+esc(actions[i].detail)+'</small></span><i>›</i></button>');id('v294Actions').innerHTML=h.join('');var bs=id('v294Actions').querySelectorAll('[data-v294-action]');for(i=0;i<bs.length;i++)bs[i].onclick=function(){act(actions[Number(this.getAttribute('data-v294-action'))]);};var urgent=actions.length&&actions[0].p>=90;id('v294State').textContent=urgent?t('URGENT','URGENT'):(actions.length&&actions[0].p>=70?t('À SURVEILLER','WATCH'):t('STABLE','STABLE'));id('v294State').className='v294-state '+(urgent?'bad':(actions.length&&actions[0].p>=70?'warn':'ok'));id('v294Brief').textContent=brief();var at=(CC&&CC.generated_at)||(D&&D.generated_at)||'';id('v294Fresh').textContent=at?t('Données : ','Data: ')+String(at).replace('T',' ').replace(/\.\d+Z$/,' UTC'):t('Dernières données connues — actualisation conseillée','Latest known data — refresh recommended');}
function brief(){var me=ccOwn(),kids=directChildren(),out=0,watch=0,i;for(i=0;i<kids.length;i++){if(kids[i].stockout==='OUT')out++;else if(kids[i].stockout==='CRITICAL'||kids[i].stockout==='WATCH')watch++;}var a=priorityActions();if(a.length&&a[0].p>=90)return t('Priorité : ','Priority: ')+a[0].title+'. '+a[0].detail;if(out)return out+' '+t('enfant(s) sont en rupture.','child(ren) are out of stock.');if(watch)return watch+' '+t('enfant(s) approchent d’une zone de risque.','child(ren) are approaching a risk zone.');if(me&&me.days_cover!=null)return t('Situation stable. Autonomie estimée : ','Stable situation. Estimated runway: ')+days(me.days_cover)+'.';return t('Aucune urgence confirmée avec les données actuellement disponibles.','No confirmed urgency with currently available data.');}
function ask(){var q=up(id('v294Question').value),ans='',a=priorityActions(),me=ccOwn();if(/FILE|ATTENTE|QUEUE/.test(q)){var n=queueCount();ans=n?t('Je vois ','I see ')+n+t(' élément(s) encore en attente. Touchez l’action File en priorité : B.I.R. relancera la synchronisation sans recréer la transaction.',' pending item(s). Use the Queue action first: B.I.R. will restart synchronization without recreating the transaction.'):t('Aucune file active n’est signalée. Si l’écran semble ancien, actualisez avant de recréer quoi que ce soit.','No active queue is reported. If the screen looks stale, refresh before recreating anything.');}else if(/SYNC|INTERNET|RELA/.test(q)){ans=C.offline_pending_events?t('Des événements locaux attendent la synchronisation. Utilisez Synchroniser; B.I.R. conservera les preuves et pourra aussi les relayer entre appareils B.I.R. compatibles.','Local events await synchronization. Use Sync; B.I.R. keeps evidence and may relay it between compatible B.I.R. devices.'):t('La synchronisation ne nécessite aucune nouvelle transaction USSD. Actualisez la War Room ou ouvrez Activité pour voir le dernier état.','Synchronization never requires a new USSD financial transaction. Refresh the War Room or open Activity for the latest state.');}else if(/ACCESS|AUTORIS/.test(q)){ans=!C.accessibility_enabled?t('L’autorisation Accessibilité est réellement absente. Ouvrez Gérer et réactivez-la. La file doit être conservée.','Accessibility permission is actually missing. Open Manage and enable it again. The queue must be preserved.'):!C.accessibility_connected?t('L’autorisation est toujours accordée mais le service Android se reconnecte. Ne recréez aucune transaction; laissez B.I.R. reprendre puis vérifiez la file.','Permission is still granted but the Android service is reconnecting. Do not recreate any transaction; let B.I.R. resume then check the queue.'):t('Accessibilité autorisée et connectée. Cherchons plutôt la file, la SIM, le PIN ou la synchronisation.','Accessibility is enabled and connected. Check the queue, SIM, PIN or synchronization instead.');}else if(/STOCK|RUPTURE|SOLDE|CREDIT/.test(q)){ans=me?t('Autonomie estimée : ','Estimated runway: ')+days(me.days_cover)+'. '+(a.length?a[0].title+'. ':'')+t('Les prévisions assistent la décision mais n’envoient jamais de crédit automatiquement.','Forecasts assist decisions but never send credit automatically.'):t('Je n’ai pas encore assez de données de stock. Actualisez le solde ou la War Room.','I do not yet have enough stock data. Refresh the balance or War Room.');}else if(/ROBOT|SIM|PIN/.test(q)){ans=C.pin_blocked?t('Le PIN est bloqué : corrigez-le avant toute finance.','PIN is blocked: fix it before any financial operation.'):C.mode==='REMOTE'?t('Ce téléphone est en mode Remote : il pilote, il ne doit pas exécuter l’USSD local.','This phone is in Remote mode: it controls, it should not execute local USSD.'):t('Vérifiez dans Gérer : SIM vérifiée, Robot actif, PIN configuré et Accessibilité connectée.','Check Manage: verified SIM, active Robot, configured PIN and connected Accessibility.');}else{ans=brief()+' '+t('Vous pouvez aussi écrire : file, synchro, accessibilité, stock, Robot, SIM ou PIN.','You can also type: queue, sync, accessibility, stock, Robot, SIM or PIN.');}id('v294Answer').textContent=ans;}
window.BlueMagicNative=window.BlueMagicNative||{};var od=window.BlueMagicNative.onDashboard;window.BlueMagicNative.onDashboard=function(d){if(typeof od==='function')try{od(d);}catch(e){}if(d&&!d.error){D=d;saveCache('dashboard',D);render();}};var op=window.BlueMagicNative.onPlatformAction;window.BlueMagicNative.onPlatformAction=function(d){if(typeof op==='function')try{op(d);}catch(e){}if(!d||d.error)return;var a=String(d._action||'');if(a==='distribution_command_center'||a==='owner_distribution_command_center'){CC=d;saveCache('cc',CC);render();}else if(a==='ops_cockpit'||a==='owner_ops_cockpit'){OPS=d;saveCache('ops',OPS);render();}else if(a==='ops_assist'){id('v294Answer').textContent=d.queued?t('Aide de synchronisation envoyée.','Synchronization assistance sent.'):t('Aucun Robot actif à réveiller pour le moment.','No active Robot to wake at the moment.');window.setTimeout(refresh,700);}};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){window.setTimeout(shell,520);});else window.setTimeout(shell,520);
})();
'''

war_css = r'''.v294-war{border:2px solid rgba(255,205,92,.88);border-radius:26px;padding:16px;margin-bottom:14px;background:linear-gradient(145deg,rgba(5,18,42,.99),rgba(9,42,80,.98));box-shadow:0 14px 34px rgba(0,0,0,.28)}.v294-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.v294-head h2{font-size:26px;margin:5px 0}.v294-head small{opacity:.76}.v294-badge{display:inline-block;padding:6px 10px;border-radius:999px;font-size:11px;font-weight:900;letter-spacing:.04em;background:rgba(255,205,92,.12);border:1px solid rgba(255,205,92,.45)}#v294Refresh{min-height:48px;font-weight:900}.v294-balances{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:14px 0}.v294-balance{padding:13px;border-radius:19px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.11)}.v294-balance-main{background:rgba(78,225,255,.08);border-color:rgba(78,225,255,.30)}.v294-balance span,.v294-balance b,.v294-balance small{display:block}.v294-balance span{font-size:11px;font-weight:900;opacity:.78}.v294-balance b{font-size:24px;margin:6px 0}.v294-balance small{font-size:11px;opacity:.68}.v294-kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.v294-kpis>div{min-height:95px;padding:11px;border-radius:17px;background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.09)}.v294-kpis span,.v294-kpis b,.v294-kpis small{display:block}.v294-kpis span{font-size:11px;opacity:.76}.v294-kpis b{font-size:22px;margin:5px 0}.v294-kpis small{font-size:10px;opacity:.62}.v294-urgent{margin-top:13px;padding:13px;border-radius:20px;background:rgba(0,0,0,.17);border:1px solid rgba(255,255,255,.09)}.v294-section{display:flex;justify-content:space-between;align-items:center;gap:10px}.v294-section h3{margin:2px 0 8px}.v294-state{padding:6px 9px;border-radius:999px;font-size:10px;font-weight:900}.v294-state.ok{background:rgba(44,181,118,.18);border:1px solid rgba(44,181,118,.5)}.v294-state.warn{background:rgba(255,188,62,.16);border:1px solid rgba(255,188,62,.55)}.v294-state.bad{background:rgba(255,91,107,.16);border:1px solid rgba(255,91,107,.62)}.v294-action{width:100%;display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;text-align:left;min-height:62px;margin:7px 0;padding:10px 11px;border-radius:16px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.10)}.v294-action b,.v294-action small{display:block}.v294-action b{font-size:14px}.v294-action small{font-size:11px;line-height:1.25;opacity:.72;margin-top:2px}.v294-action i{font-style:normal;font-size:22px}.v294-num{width:30px;height:30px;display:grid;place-items:center;border-radius:50%;font-weight:900;background:rgba(255,205,92,.16);border:1px solid rgba(255,205,92,.42)}.v294-copilot{margin-top:13px;padding:13px;border-radius:20px;background:rgba(78,225,255,.065);border:1px solid rgba(78,225,255,.22)}.v294-copilot-head{display:flex;justify-content:space-between;gap:10px}.v294-copilot-head span,.v294-copilot-head small{display:block}.v294-copilot-head span{font-weight:900;font-size:16px}.v294-copilot-head small{font-size:10px;opacity:.7;margin-top:2px}#v294Explain{width:42px;min-height:40px;border-radius:50%;font-weight:900}.v294-ask{display:grid;grid-template-columns:1fr auto;gap:7px;margin-top:9px}.v294-ask input{min-width:0}.v294-ask button{font-weight:900}.v294-answer{min-height:20px;font-size:12px;line-height:1.4;opacity:.82}.v294-quick{display:flex;gap:6px;flex-wrap:wrap}.v294-quick button{min-height:40px;font-size:11px;padding:7px 9px}@media(max-width:760px){.v294-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.v294-balances{grid-template-columns:1fr 1fr}.v294-balance-main{grid-column:1/-1}.v294-kpis>div:last-child{grid-column:1/-1}}@media(max-width:480px){.v294-war{padding:12px;border-radius:21px}.v294-head{display:block}#v294Refresh{width:100%;margin-top:8px}.v294-balances{grid-template-columns:1fr}.v294-balance-main{grid-column:auto}.v294-kpis{grid-template-columns:1fr 1fr}.v294-action{grid-template-columns:auto 1fr}.v294-action i{display:none}.v294-ask{grid-template-columns:1fr}.v294-ask button{min-height:48px}}'''
write('app/src/main/assets/war-room-v294.js',war_js)
write('app/src/main/assets/war-room-v294.css',war_css+'\n')

# Include the assets after all inherited layers so callbacks chain instead of replace.
p='app/src/main/assets/index.html'; s=read(p)
s=once(s,'    <link rel="stylesheet" href="pilotage-v292.css">',
       '    <link rel="stylesheet" href="pilotage-v292.css">\n    <link rel="stylesheet" href="war-room-v294.css">',
       'war room css include')
s=once(s,'<script src="pilotage-v292.js"></script>',
       '<script src="pilotage-v292.js"></script>\n<script src="war-room-v294.js"></script>',
       'war room js include')
write(p,s)

# ---------------------------------------------------------------------------
# New contract: explicit safety and UX requirements.
# ---------------------------------------------------------------------------
contract = r'''import fs from 'node:fs';
const read=p=>fs.readFileSync(p,'utf8');
const gradle=read('app/build.gradle');
const html=read('app/src/main/assets/index.html');
const war=read('app/src/main/assets/war-room-v294.js');
const worker=read('cloudflare/src/index.js');
const manifest=read('app/src/main/AndroidManifest.xml');
function ok(v,m){if(!v)throw new Error(m);}
ok(gradle.includes('versionCode 59')&&gradle.includes('versionName "2.9.4"'),'v2.9.4 metadata');
ok(html.includes('war-room-v294.css')&&html.includes('war-room-v294.js'),'War Room assets not wired');
ok(war.includes('WAR ROOM B.I.R.')&&war.includes('5 actions')&&war.includes('B.I.R. Copilot'),'War Room/Copilot vocabulary missing');
ok(war.includes('commission_base_balance')&&war.includes('commission_component_balance'),'three-balance semantics missing');
ok(war.includes("stockout==='OUT'")&&war.includes("stockout==='WATCH'"),'stockout priority semantics missing');
ok(war.includes("reason:'WAR_ROOM_V294'")&&war.includes("action:'WAKE_SYNC'"),'safe assistance missing');
ok(!war.includes('createCommand(')&&!war.includes('create_command')&&!war.includes('sendEvent('),'War Room must not execute finance');
ok(!/https?:\/\//.test(war)&&!war.includes('fetch('),'Copilot must have no external AI/API dependency');
ok(worker.includes("const API_VERSION = '2.9.4-cloudflare'"),'Worker version mismatch');
ok(worker.includes('war_room: true')&&worker.includes('operational_copilot: true')&&worker.includes('commission_free_competition: true'),'Worker capabilities missing');
ok(worker.includes(".bind(node, role, phoneNumber, 0).run();"),'new root account still has imposed commission');
ok(worker.includes(".bind(desired, childRole, p, auth.node_code, 0).run();"),'new child account still has imposed outbound commission');
ok(worker.includes('const inboundRate = Number(row.inbound_commission_bps || 0);'),'inbound commission fallback must be neutral');
ok(!worker.includes("row.role === 'DAE' ? 1000 : row.role === 'DSM' ? 900 : row.role === 'POS' ? 800"),'role-imposed commission fallback remains');
ok(worker.includes("stockout:balance!=null&&Number(balance)<=0?'OUT'"),'explicit OUT stock state missing');
ok(worker.includes('stockout_out:'),'OUT summary missing');
ok(worker.includes("effective_modes: ['REMOTE','ROBOT']"),'effective modes regressed');
ok(!manifest.includes('android.permission.SEND_SMS'),'SMS permission regression');
console.log('BIR v2.9.4 War Room/Copilot contract: OK');
'''
write('app/src/test/bir-v294-war-room-contract.mjs',contract)

# ---------------------------------------------------------------------------
# Historical tests: metadata-only widening to accept 2.9.4/code59.
# Functional assertions are untouched.
# ---------------------------------------------------------------------------
for test in Path('app/src/test').glob('*.mjs'):
    if test.name == 'bir-v294-war-room-contract.mjs':
        continue
    old = test.read_text(encoding='utf-8')
    z = old
    if "gradle.includes('versionCode 58')" in z and "versionCode 59" not in z:
        z=z.replace("gradle.includes('versionCode 58')","(gradle.includes('versionCode 58')||gradle.includes('versionCode 59'))")
    if "gradle.includes('versionName \"2.9.3\"')" in z and 'versionName \"2.9.4\"' not in z:
        z=z.replace("gradle.includes('versionName \"2.9.3\"')","(gradle.includes('versionName \"2.9.3\"')||gradle.includes('versionName \"2.9.4\"'))")
    if 'worker.includes("const API_VERSION = \'2.9.3-cloudflare\'")' in z and '2.9.4-cloudflare' not in z:
        z=z.replace('worker.includes("const API_VERSION = \'2.9.3-cloudflare\'")','(worker.includes("const API_VERSION = \'2.9.3-cloudflare\'")||worker.includes("const API_VERSION = \'2.9.4-cloudflare\'"))')
    if 'worker.includes("2.9.3-cloudflare")' in z and '2.9.4-cloudflare' not in z:
        z=z.replace('worker.includes("2.9.3-cloudflare")','(worker.includes("2.9.3-cloudflare")||worker.includes("2.9.4-cloudflare"))')
    z=re.sub(r'versionCode \(\?:([0-9|]+)\)',lambda m:'versionCode (?:'+m.group(1)+('|59' if '59' not in m.group(1).split('|') else '')+')',z)
    # Common finance-flow regex ending in the previous release.
    z=z.replace('2\\.9\\.3)"','2\\.9\\.(?:3|4))"') if '2\\.9\\.3)"' in z and '2\\.9\\.(?:3|4)' not in z else z
    # Literal ApiClient metadata guards.
    if '2.9.3' in z and 'api client version mismatch' in z and '2.9.4' not in z:
        z=z.replace("api.includes('\\\"2.9.3\\\"')","(api.includes('\\\"2.9.3\\\"')||api.includes('\\\"2.9.4\\\"'))")
    if z != old:
        test.write_text(z,encoding='utf-8')

print('BIR v2.9.4 War Room + local Copilot patch applied')
