(function(){
'use strict';
/* B.I.R. commercial pages — additive Android 6 / ES5 shell.
 * Reuses native bridges and existing certified financial forms; never creates/dials transactions.
 * Ads and forum are RESERVED SLOTS, not active services.
 */
var mounted=false, route='home', navigating=false, nativeGuard=null;
function el(id){return document.getElementById(id);}
function cfg(){try{var b=window.AndroidBridge;return b&&b.getConfiguration?JSON.parse(b.getConfiguration()||'{}'):{};}catch(e){return {};}}
function t(s){return String(s==null?'':s);}
function esc(s){return t(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function role(c){var r=t(c.role).toUpperCase();return r==='DAE'||r==='DSM'||r==='POS'?r:'';}
function lang(){try{return window.AndroidBridge&&window.AndroidBridge.getUiLanguage&&window.AndroidBridge.getUiLanguage()==='en'?'en':'fr';}catch(e){return 'fr';}}
function L(fr,en){return lang()==='en'?en:fr;}
function bridge(action){var b=window.AndroidBridge;if(!b)return false;var calls={accounts:'openAccounts',manage:'openManagement',permissions:'prepareRobotPermissions',pin:'openPinSettings',sim:'verifySim',start:'startRobot',battery:'openBatteryOptimizationSettings'};var fn=calls[action];if(!fn||typeof b[fn]!=='function')return false;try{b[fn]();return true;}catch(e){return false;}}
function openTab(tab){var n=document.querySelector('button[data-tab="'+tab+'"]');if(!n)return false;navigating=true;try{n.click();}finally{navigating=false;}return true;}
function a(label,action,style,small){return '<button type="button" class="bir-v2996-action '+(style||'')+'" data-bir-commerce="'+esc(action)+'"><span class="bir-v2996-action-label">'+esc(label)+'</span>'+(small?'<small>'+esc(small)+'</small>':'')+'<span aria-hidden="true" class="bir-v2996-arrow">›</span></button>';}
function roles(c){var r=role(c),actions;if(r==='POS')actions=[['Vendre du crédit','retail','Charger le numéro client et le montant'],['Acheter du crédit','buy','Demander du stock au DSM']];else if(r==='DSM')actions=[['Approvisionner un PoS','supply','Servir un enfant direct'],['Acheter du crédit','buy','Demander du stock au DAE']];else if(r==='DAE')actions=[['Approvisionner un DSM','supply','Servir un DSM direct'],['Mon réseau','network','Demandes et disponibilité']];else actions=[['Gérer mon compte','accounts','Vérifier le profil'],['Voir l’activité','support','Historique et diagnostics']];return actions;}
function guard(c){if(t(c.mode).toUpperCase()!=='ROBOT')return {kind:'remote',title:L('Compte en mode Remote','Remote account'),detail:L('Consultez votre Robot distant et les dernières preuves depuis Activité.','See the remote Robot and latest evidence from Activity.'),action:'manage',label:L('Gérer le mode','Manage mode')};if(c.pin_blocked)return {kind:'warn',title:L('PIN Blue bloqué','Blue PIN blocked'),detail:L('Corrigez votre PIN local. Aucune tentative automatique supplémentaire.','Correct your local PIN. No more automatic attempts.'),action:'pin',label:L('Corriger le PIN','Correct PIN')};if(!c.sim_verified)return {kind:'warn',title:L('SIM non vérifiée','SIM not verified'),detail:L('Liez ou vérifiez la SIM avant toute composition financière.','Verify your SIM before any financial dialing.'),action:'sim',label:L('Vérifier SIM','Verify SIM')};if(!c.pin_configured)return {kind:'warn',title:L('PIN local manquant','Local PIN missing'),detail:L('Enregistrez le PIN sur ce téléphone Robot, jamais dans le cloud.','Keep the PIN on this Robot, never in the cloud.'),action:'pin',label:L('Configurer PIN','Set PIN')};if(!c.accessibility_enabled)return {kind:'warn',title:L('Accessibilité désactivée','Accessibility off'),detail:L('Autorisez le service BIR dans les réglages Android.','Allow the BIR service in Android settings.'),action:'permissions',label:L('Autorisations','Permissions')};if(!c.accessibility_connected)return {kind:'warn',title:L('Accessibilité en reconnexion','Accessibility reconnecting'),detail:L('L’autorisation existe ; vérifiez le service et son état.','Permission exists; check the service status.'),action:'permissions',label:L('Vérifier le service','Check service')};if(!c.robot_enabled)return {kind:'warn',title:L('Robot arrêté','Robot stopped'),detail:L('La SIM est configurée ; démarrez le Robot pour prendre les commandes.','The SIM is configured; start the Robot for orders.'),action:'start',label:L('Démarrer Robot','Start Robot')};return {kind:'ok',title:L('Robot activé','Robot enabled'),detail:L('État local favorable. La ligne et la connexion doivent encore être vérifiées au moment de l’USSD.','Local readiness reported; line and network must still be checked at dial time.'),action:'manage',label:L('Gérer le Robot','Manage Robot')};}
function fmtMoney(value){var n=Number(value);if(!isFinite(n)||n<0)return '—';return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' ')+' FCFA';}
function robotHtml(c){var s=guard(c);return '<section class="bir-v2996-robot bir-v2996-'+s.kind+'" aria-label="'+esc(L('État du Robot','Robot status'))+'"><div class="bir-v2996-robot-head"><div><small>'+esc(L('MON ROBOT / REMOTE','MY ROBOT / REMOTE'))+'</small><strong>'+esc(s.title)+'</strong></div><span class="bir-v2996-led" aria-hidden="true"></span></div><p>'+esc(s.detail)+'</p><div class="bir-v2996-robot-actions">'+a(s.label,s.action,'bir-v2996-small','')+a(L('Autres réglages','More settings'),'manage','bir-v2996-small bir-v2996-outline','')+'</div><div class="bir-v2996-robot-tools">'+a(L('Vérifier SIM','Verify SIM'),'sim','bir-v2996-text','')+a(L('Autorisations','Permissions'),'permissions','bir-v2996-text','')+a(L('Batterie','Battery'),'battery','bir-v2996-text','')+'</div></section>';}
function renderHome(){var home=el('birV2996CommercialHome');if(!home)return;var c=cfg(),r=role(c),actions=roles(c);var title=r==='POS'?L('Mon point de vente','My retail point'):r==='DSM'?L('Ma distribution','My distribution'):r==='DAE'?L('Mon réseau commercial','My sales network'):L('Mon commerce','My business');
home.innerHTML='<section class="bir-v2996-intro"><div><small>'+esc(L('PRÊT POUR LE COMMERCE BLUE','READY FOR BLUE BUSINESS'))+'</small><h2>'+esc(title)+'</h2><span>'+esc(t(c.official_node_code||c.node_code||'Compte à configurer'))+' · '+esc(t(c.mode||'—'))+'</span></div>'+a(L('Changer de compte','Switch account'),'accounts','bir-v2996-switch','')+'</section>'+
'<div class="bir-v2996-commerce-primary">'+a(actions[0][0],actions[0][1],'bir-v2996-main',actions[0][2])+a(actions[1][0],actions[1][1],'bir-v2996-main bir-v2996-secondary',actions[1][2])+'</div>'+
robotHtml(c)+
'<nav class="bir-v2996-shortcuts" aria-label="'+esc(L('Raccourcis','Shortcuts'))+'">'+a(L('Solde & preuves','Balance & evidence'),'dashboard','bir-v2996-shortcut','')+a(L('Transactions','Transactions'),'support','bir-v2996-shortcut','')+a(L('Mon réseau','My network'),'network','bir-v2996-shortcut','')+a(L('Tableaux de bord','Dashboards'),'dashboard','bir-v2996-shortcut','')+a(L('Comptabilité','Accounting'),'accounting','bir-v2996-shortcut','')+a(L('Assistant BIR IA','BIR AI assistant'),'assistant','bir-v2996-shortcut','')+'</nav>'+
'<section class="bir-v2996-community"><div><strong>'+esc(L('Forum BIR','BIR Forum'))+'</strong><p>'+esc(L('Espace réservé aux échanges entre utilisateurs. Les publications ne sont pas encore activées.','Reserved community space. Posting is not yet enabled.'))+'</p></div>'+a(L('Découvrir','Explore'),'forum','bir-v2996-small','')+'</section>'+
'<aside class="bir-v2996-ad" aria-label="'+esc(L('Emplacement publicitaire réservé','Reserved ad slot'))+'"><small>'+esc(L('ESPACE PUBLICITAIRE RÉSERVÉ','RESERVED ADVERTISING SPACE'))+'</small><span>'+esc(L('Aucune publicité active. Les opérations financières restent prioritaires.','No active ads. Financial work stays first.'))+'</span></aside>';
}
var FORM={retail:{id:'retailCard',focus:'retailPhone',title:'Vendre du crédit',roles:['POS']},buy:{id:'requestSupplyCard',focus:'requestSupplyAmount',title:'Acheter du crédit',roles:['POS','DSM']},supply:{id:'supplyChildCard',focus:'childNode',title:'Approvisionner un enfant',roles:['DSM','DAE']},test:{id:null,focus:null,title:'Test sans fonds',roles:['POS','DSM','DAE']},details:{id:null,focus:'transactionId',title:'Détail de transaction',roles:['POS','DSM','DAE']},balanceChild:{id:'childBalanceCard',focus:'balanceChildNode',title:'Solde enfant',roles:['DSM','DAE']}};
function renderFlow(routeName){var flux=document.querySelector('[data-tab-panel="flux"]');if(!flux)return;var head=el('birV2996FlowHead'),hub=el('birV2996FlowHub'),form=routeName.indexOf('form:')===0?routeName.substring(5):'',meta=FORM[form],c=cfg(),r=role(c),cards=flux.querySelectorAll('.grid > .command-card'),i,selected;
for(i=0;i<cards.length;i++)cards[i].classList.remove('bir-v2996-selected');
if(meta&&meta.roles.indexOf(r)<0){meta=null;form='';}
if(form==='test')selected=flux.querySelector('button[data-action="test-number"]');else if(form==='details')selected=flux.querySelector('button[data-action="transaction-details"]');else selected=meta&&el(meta.id);
var selectedCard=selected&&selected.closest?selected.closest('.command-card'):selected&&selected.parentNode;
if(selectedCard && /command-card/.test(selectedCard.className) && !/hidden/.test(selectedCard.className))selectedCard.classList.add('bir-v2996-selected');
else if(meta){meta=null;form='';}
flux.classList.add('bir-v2996-flow-focus');
if(head)head.innerHTML=meta?'<button class="bir-v2996-back" type="button" data-bir-commerce="commerce">← '+esc(L('Commerce','Commerce'))+'</button><h2>'+esc(meta.title)+'</h2>':'<h2>'+esc(L('Commerce Blue','Blue Commerce'))+'</h2><p>'+esc(L('Choisissez une opération. Chaque formulaire conserve les contrôles financiers BIR.','Choose a task. Every form retains BIR financial safeguards.'))+'</p>';
if(hub){hub.style.display=meta?'none':'grid';if(!meta){var aa=roles(c),html='';for(i=0;i<aa.length;i++)html+=a(aa[i][0],aa[i][1],'bir-v2996-flow-link',aa[i][2]);html+=a(L('Tester la ligne','Test line'),'test','bir-v2996-flow-link',L('Code sans fonds *825*3*3#','Non-financial *825*3*3#'));html+=a(L('Détail transaction','Transaction details'),'details','bir-v2996-flow-link','');if(r==='DSM'||r==='DAE')html+=a(L('Solde enfant','Child balance'),'balanceChild','bir-v2996-flow-link','');html+=a(L('Historique et suivi','History and tracking'),'support','bir-v2996-flow-link','');hub.innerHTML=html;}}
if(meta&&meta.focus){window.setTimeout(function(){var inp=el(meta.focus);if(inp&&inp.offsetParent!==null){try{inp.focus();}catch(e){}}},120);}
}
var accountingRevision=0;
function renderAccounting(payload){
 var host=el('birV2996Accounting');if(!host)return;
 var data=payload||{},valid=!data.error&&data.source==='SERVER';
 var intro='<button type="button" class="bir-v2996-back" data-bir-commerce="home">← '+esc(L('Accueil','Home'))+'</button><h2>'+esc(L('Mon activité commerciale','My sales activity'))+'</h2>';
 if(!valid){host.innerHTML=intro+'<p>'+esc(data.error?L('Rapport momentanément indisponible.','Report temporarily unavailable.'):L('Chargement des écritures serveur…','Loading server records…'))+'</p>'+a(L('Actualiser','Refresh'),'accounting-refresh','bir-v2996-small','');return;}
 host.innerHTML=intro+'<small>'+esc(L('Agrégats des commandes BIR déclarées réussies. Non assimilables à une preuve opérateur ou un bénéfice net.','Aggregates of BIR commands declared successful; not operator proof or net profit.'))+'</small>'+
 '<div class="bir-v2996-accounting-grid">'+
 '<article><strong>'+esc(fmtMoney(data.purchase_amount))+'</strong><span>'+esc(L('Achats reçus','Purchases received'))+' · '+esc(data.purchase_count)+'</span></article>'+
 '<article><strong>'+esc(fmtMoney(data.sale_amount))+'</strong><span>'+esc(L('Ventes/approvisionnements sortants','Sales/outgoing supply'))+' · '+esc(data.sale_count)+'</span></article>'+
 '</div><p class="bir-v2996-accounting-note">'+esc(L('Commissions acquises, bénéfice et solde de caisse : non calculés ici tant que les bénéficiaires, règlements, charges et preuves ne sont pas rapprochés. Une opération UNKNOWN n’est pas un échec prouvé.','Earned commission, profit and cash balance are not calculated until beneficiary, payment, expense and evidence are reconciled. UNKNOWN is not a confirmed failure.'))+'</p>'+a(L('Actualiser','Refresh'),'accounting-refresh','bir-v2996-small','');
}
function loadAccounting(){
 renderAccounting(null);
 var b=window.AndroidBridge;if(!b||typeof b.platformAction!=='function'){renderAccounting({error:'OFFLINE'});return;}
 accountingRevision++;var rev=accountingRevision;
 try{b.platformAction('accounting_summary','{"period":"day"}');}
 catch(e){renderAccounting({error:'NO_BRIDGE'});}
 window.setTimeout(function(){if(rev===accountingRevision&&route==='accounting'&&el('birV2996Accounting')&&el('birV2996Accounting').textContent.indexOf('Chargement')>=0)renderAccounting({error:'TIMEOUT'});},12000);
}
function bindAccounting(){
 if(!window.BlueMagicNative)return;var previous=window.BlueMagicNative.onPlatformAction;
 window.BlueMagicNative.onPlatformAction=function(data){
   if(data&&data._action==='accounting_summary'){accountingRevision++;renderAccounting(data);}
   if(typeof previous==='function')return previous.apply(this,arguments);
 };
}
function setView(name,noHistory){if(!mounted)return;if(name==='assistant'){name='dashboard';window.setTimeout(function(){var q=el('birV297Question');if(q&&q.focus)q.focus();},260);}route=name;var h=document.documentElement;h.classList.remove('bir-v2996-dashboard','bir-v2996-forum','bir-v2996-accounting');var tab=(name==='home'||name==='dashboard'||name==='forum')?'reports':name==='network'?'fleet':(name==='support'||name==='accounting')?'support':name==='manage'?'config':'flux';openTab(tab);
if(name==='dashboard')h.classList.add('bir-v2996-dashboard');
if(name==='forum')h.classList.add('bir-v2996-forum');if(name==='accounting'){h.classList.add('bir-v2996-accounting');loadAccounting();}
if(name==='home')renderHome();
if(tab==='flux')renderFlow(name);
if(!noHistory&&window.history&&window.history.pushState){try{window.history.pushState({birCommercial:name},'',window.location.pathname+window.location.search+'#bir-'+encodeURIComponent(name));}catch(e){}}
window.scrollTo(0,0);
}
function toRoute(action){if(action==='retail'||action==='buy'||action==='supply'||action==='test'||action==='details'||action==='balanceChild')return 'form:'+action;return action;}
function click(e){var target=e.target;while(target&&target!==document&&!target.getAttribute('data-bir-commerce'))target=target.parentNode;if(!target||target===document)return;var action=target.getAttribute('data-bir-commerce');if(!action)return;e.preventDefault();if(action==='accounts'||action==='manage'||action==='permissions'||action==='sim'||action==='pin'||action==='start'||action==='battery'){if(!bridge(action)){if(action==='manage')setView('manage');else if(action==='accounts')setView('manage');}else window.setTimeout(renderHome,450);return;}if(action==='dashboard'||action==='assistant'||action==='forum'||action==='home'||action==='commerce'||action==='network'||action==='support'||action==='accounting')setView(action);else if(action==='accounting-refresh')loadAccounting();else setView(toRoute(action));}
function mount(){if(mounted)return;var reports=document.querySelector('[data-tab-panel="reports"]'),flux=document.querySelector('[data-tab-panel="flux"]');if(!reports||!flux)return;
var support=document.querySelector('[data-tab-panel="support"]');if(support){var ledger=document.createElement('section');ledger.id='birV2996Accounting';ledger.className='bir-v2996-accounting-page';support.insertBefore(ledger,support.firstChild);}
var home=document.createElement('div');home.id='birV2996CommercialHome';home.className='bir-v2996-home';reports.insertBefore(home,reports.firstChild);
var forum=document.createElement('section');forum.id='birV2996Forum';forum.innerHTML='<button type="button" class="bir-v2996-back" data-bir-commerce="home">← '+esc(L('Accueil','Home'))+'</button><h2>'+esc(L('Forum BIR','BIR Forum'))+'</h2><p>'+esc(L('Espace communautaire réservé. Aucun message ne peut encore être publié : l’authentification, les droits, la modération, les signalements et les données doivent être définis.','Community space reserved. Posting is not enabled until identity, access rules, moderation, reporting and storage are ready.'))+'</p>';reports.insertBefore(forum,home.nextSibling);
var heading=document.createElement('div');heading.id='birV2996FlowHead';heading.className='bir-v2996-flow-head';var hub=document.createElement('div');hub.id='birV2996FlowHub';hub.className='bir-v2996-flow-hub';flux.insertBefore(hub,flux.firstChild);flux.insertBefore(heading,hub);
var account=document.querySelector('.bir-account-chip');if(account){account.setAttribute('role','button');account.setAttribute('tabindex','0');account.setAttribute('aria-label',L('Changer de compte','Switch account'));account.setAttribute('title',L('Changer de compte','Switch account'));account.addEventListener('click',function(){bridge('accounts');});account.addEventListener('keydown',function(e){if(e.keyCode===13||e.keyCode===32){e.preventDefault();bridge('accounts');}});}
bindAccounting();
document.addEventListener('click',click,false);
function assistantVisibleLater(){window.setTimeout(function(){if(mounted){setView('dashboard',true);}},330);}
document.addEventListener('click',function(ev){
 var n=ev.target;
 while(n&&n!==document){
  if(n.id==='birV297Ask'||n.id==='birIntelSearchGo'){
   assistantVisibleLater();break;
  }
  n=n.parentNode;
 }
},true);
document.addEventListener('keydown',function(ev){
 if(ev.keyCode===13&&ev.target&&ev.target.id==='birV297Question')assistantVisibleLater();
},true);
var tabs=document.querySelectorAll('button[data-tab]'),i;for(i=0;i<tabs.length;i++)(function(b){b.addEventListener('click',function(){if(navigating)return;var name=b.getAttribute('data-tab');if(name==='flux')setView('commerce');else if(name==='reports')setView('home');else if(name==='fleet')setView('network');else if(name==='support')setView('support');else if(name==='config')setView('manage');});})(tabs[i]);
window.addEventListener('popstate',function(e){setView(e.state&&e.state.birCommercial||'home',true);});
document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible'&&(route==='home'))renderHome();});
var tab= document.querySelector('button[data-tab="flux"]'),labels;if(tab){labels=tab.querySelectorAll('span');if(labels.length>1)labels[labels.length-1].textContent=L('Commerce','Commerce');}
mounted=true;document.documentElement.classList.add('bir-v2996-commerce');setView('home',true);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){window.setTimeout(mount,1200);});else window.setTimeout(mount,1200);
window.BIRCommercialShell={open:function(page){if(!mounted)return false;setView(page);return true;},refresh:function(){if(mounted)renderHome();}};
}());