(function(){
'use strict';
/* B.I.R. 2.9.9.6 — role-aware Assistant capability guard.
 * This layer is UI/assistant authorization only. It never grants a right that the certified
 * transaction path does not already grant, and it never calls create/preview/confirm finance.
 */
var installed=false;
function id(x){return document.getElementById(x);}
function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function txt(v){return String(v==null?'':v);}
function esc(v){return txt(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function norm(v){var s=txt(v).toLowerCase();try{s=s.normalize('NFD').replace(/[\u0300-\u036f]/g,'');}catch(e){}return s.replace(/[^a-z0-9]+/g,' ').replace(/^\s+|\s+$/g,'');}
function cfg(){try{return JSON.parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}')||{};}catch(e){return {};}}
function role(){return txt(cfg().role).toUpperCase();}
function isPos(){return role()==='POS';}
function out(){return id('birV297Answer');}
function deny(title,detail){var e=out();if(!e)return false;e.innerHTML='<div class="bir-v2996-guide"><h4>'+esc(title)+'</h4><p>'+esc(detail)+'</p><span class="bir-v2996-guard">Le rôle PoS reste limité à ses propres services autorisés. L’Assistant ne révèle ni n’active les aides réservées au DAE/DSM.</span></div>';return true;}
function posCapabilities(){var e=out();if(!e)return false;e.innerHTML='<div class="bir-v2996-guide"><h4>Ce que l’Assistant peut faire pour un PoS</h4><ul>'+
'<li><b>Accueil :</b> expliquer votre compte, votre mode, votre SIM, votre solde et la fraîcheur des preuves.</li>'+
'<li><b>Achat de crédit :</b> expliquer comment demander du stock à votre supérieur et comment suivre la demande.</li>'+
'<li><b>Vente client :</b> expliquer la saisie du numéro, du montant, les vérifications et la confirmation normale.</li>'+
'<li><b>Activité :</b> expliquer la file, le journal, les états PENDING/UNKNOWN/FAILED et le rapprochement.</li>'+
'<li><b>Diagnostic :</b> diagnostiquer les boutons, le Robot/Remote, la SIM, l’Accessibilité, la synchronisation et le serveur.</li>'+
'<li><b>Navigation :</b> ouvrir Accueil, Vendre, Activité ou Gérer lorsque le service est autorisé.</li>'+
'</ul><p>Exemples : « donne-moi mon brief », « comment vendre ? », « comment demander du crédit ? », « diagnostique les boutons », « synchronise », « vérifie le serveur ».</p>'+
'<span class="bir-v2996-guard">Un PoS ne reçoit pas l’aide DAE/DSM concernant enfants, War Room enfants, Check Réseau hiérarchique, Tchoronko, politiques de commissions enfants ou préparation d’approvisionnement d’un enfant.</span></div>';return true;}
function posServices(){var e=out();if(!e)return false;e.innerHTML='<div class="bir-v2996-guide"><h4>Fonctionnalités disponibles pour le rôle PoS</h4>'+
'<p><b>Accueil</b></p><ul><li>Situation du compte</li><li>Solde & preuves</li><li>Brief personnel</li><li>Assistant B.I.R.</li><li>Rapprochement & preuves</li></ul>'+
'<p><b>Achat / Vente</b></p><ul><li>Demander du crédit à son supérieur</li><li>Vendre à un client final</li><li>Tester la SIM / route autorisée</li><li>Consulter les transactions disponibles</li></ul>'+
'<p><b>Activité</b></p><ul><li>File des commandes</li><li>Journal des transactions</li><li>Diagnostic boutons</li><li>Vérification serveur</li><li>SAV / diagnostic</li></ul>'+
'<p><b>Gérer</b></p><ul><li>Comptes</li><li>SIM & slots</li><li>Remote / Robot</li><li>PIN Blue</li><li>Accessibilité & permissions</li><li>Synchronisation</li><li>Batterie & continuité</li></ul>'+
'<span class="bir-v2996-guard">Les fonctions réseau hiérarchiques DAE/DSM ne sont ni proposées ni expliquées à un PoS.</span></div>';return true;}
function restricted(n){return /prepare.*(?:pos|dsm)|approvisionn.*enfant|recharg.*enfant|fourn.*(?:pos|dsm)|war room.*enfant|check reseau|audit.*reseau|solde.*enfant|tchoronko|politique.*commission|taux.*enfant|commission.*enfant|pourquoi.*pos\d.*alerte|reseau.*enfant/.test(n);}
function interceptQuestion(q){if(!isPos())return false;var n=norm(q);if(!n)return false;if(/que peux tu faire|que fait.*assistant|comment.*(?:ia|assistant)/.test(n))return posCapabilities();if(/(?:liste|montre|donne).*(?:fonction|service)|toutes.*(?:fonction|service)/.test(n))return posServices();if(restricted(n))return deny('Aide non disponible pour un PoS','Cette demande concerne une capacité hiérarchique réservée aux rôles DAE/DSM. Aucune préparation, navigation privilégiée ou information enfant n’a été fournie.');if(/commission|taux/.test(n))return deny('Commission hiérarchique non exposée','L’Assistant PoS ne consulte ni ne détaille les politiques de commission des enfants ou du réseau supérieur. Les informations personnelles éventuellement prévues par l’application restent soumises aux droits du profil.');return false;}
function queryValue(){var q=id('birV297Question');return q?txt(q.value):'';}
function captureClick(ev){if(!isPos())return;var p=ev.target;
 while(p&&p!==document.body){
  if(p.id==='birV297Ask'){if(interceptQuestion(queryValue())){ev.preventDefault();ev.stopImmediatePropagation();return;}}
  if(p.getAttribute&&p.getAttribute('data-v2996-all')!==null){ev.preventDefault();ev.stopImmediatePropagation();posServices();return;}
  if(p.id==='birV2996Promo'){var t=id('birV2996PromoText');if(t&&restricted(norm(t.textContent))){ev.preventDefault();ev.stopImmediatePropagation();posCapabilities();return;}}
  p=p.parentNode;
 }
}
function captureKey(ev){if(!isPos())return;var code=(ev||window.event).keyCode;if(code!==13)return;if(ev.target&&ev.target.id==='birV297Question'&&interceptQuestion(txt(ev.target.value))){ev.preventDefault();ev.stopImmediatePropagation();}}
function sanitizePosDiscovery(){if(!isPos())return;var promo=id('birV2996Promo'),text=id('birV2996PromoText');if(promo){promo.setAttribute('data-role-scope','POS');promo.title='Assistant PoS : aide personnelle, vente, achat, activité, diagnostic et réglages';}if(text){text.textContent='« Que peux-tu faire pour moi ? »';}var q=id('birV297Question');if(q)q.placeholder='PoS : solde, vente, achat de crédit, activité, diagnostic, synchronisation…';}
function install(){if(installed)return;installed=true;document.addEventListener('click',captureClick,true);document.addEventListener('keydown',captureKey,true);sanitizePosDiscovery();window.setTimeout(sanitizePosDiscovery,700);window.setTimeout(sanitizePosDiscovery,2400);}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',install);else install();
}());
