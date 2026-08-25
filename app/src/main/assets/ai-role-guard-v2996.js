(function(){
'use strict';
/* B.I.R. 2.9.9.6 — role + hierarchy scoped Assistant guard.
 * Defense in depth for the UI/help plane. A PoS never receives DAE/DSM child-network guidance,
 * prompts or guided child-supply preparation. DAE and DSM preparation is also limited to the
 * direct-child role allowed by the hierarchy: DAE -> DSM, DSM -> PoS.
 * No financial command is created, previewed, confirmed, composed or submitted here.
 * ES5 / Android 6+ compatible. No MutationObserver, no setInterval.
 */
var installed=false,timer=null,index=0;
function id(x){return document.getElementById(x);}
function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function txt(v){return String(v==null?'':v);}
function norm(v){var s=txt(v).toLowerCase();try{s=s.normalize('NFD').replace(/[\u0300-\u036f]/g,'');}catch(e){}return s.replace(/[^a-z0-9]+/g,' ').replace(/^\s+|\s+$/g,'');}
function cfg(){try{return JSON.parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}')||{};}catch(e){return {};}}
function role(){return txt(cfg().role).toUpperCase();}
function isPos(){return role()==='POS';}
function lang(){try{return bridge()&&bridge().getUiLanguage&&bridge().getUiLanguage()==='en'?'en':'fr';}catch(e){return 'fr';}}
function esc(v){return txt(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function answer(html){var out=id('birV297Answer');if(!out)return false;out.innerHTML=html;try{out.scrollIntoView(false);}catch(e){}return true;}
function scopedBox(title,body){return answer('<div class="bir-v2996-guide"><h4>'+esc(title)+'</h4><p>'+esc(body)+'</p><span class="bir-v2996-guard">Les droits B.I.R. sont déterminés par le rôle du compte actif et la hiérarchie directe. L’Assistant ne les contourne jamais.</span></div>');}
function denyPos(){return scopedBox('Aide limitée au rôle PoS','Cette aide est réservée au pilotage DAE/DSM. Depuis un compte PoS, l’Assistant ne l’affiche pas, ne l’explique pas, n’ouvre pas la rubrique correspondante et ne préremplit aucun approvisionnement d’enfant.');}
function denyHierarchy(targetRole){var r=role(),allowed=r==='DAE'?'DSM':r==='DSM'?'POS':'aucun enfant';return scopedBox('Préparation refusée par la hiérarchie','Le compte '+r+' ne peut préparer un approvisionnement que pour un enfant direct '+allowed+'. La cible demandée est de type '+targetRole+'. Aucune donnée financière n’a été préremplie.');}
function posServices(){return answer('<div class="bir-v2996-guide"><h4>Fonctionnalités disponibles pour votre rôle PoS</h4><p><b>Accueil</b></p><ul><li>Situation de votre compte, mode Remote/Robot et alertes locales.</li><li>Votre solde, sa fraîcheur et ses preuves.</li><li>Brief de votre propre activité et diagnostic local.</li></ul><p><b>Achat / Vente</b></p><ul><li>Demander du crédit à votre DSM supérieur selon les règles B.I.R.</li><li>Vendre du crédit à un client final via le formulaire normal.</li><li>Tester votre SIM/route sans mouvement de fonds.</li><li>Consulter vos dernières transactions et les détails disponibles.</li></ul><p><b>Activité</b></p><ul><li>Suivre votre file, vos résultats et vos opérations à rapprocher.</li><li>Consulter votre journal et demander un diagnostic des boutons.</li><li>Vérifier le serveur et demander une synchronisation sûre.</li></ul><p><b>Gérer</b></p><ul><li>Comptes, SIM/slot, mode Remote/Robot, PIN, Accessibilité, permissions et batterie.</li></ul><span class="bir-v2996-guard">Les fonctions réseau hiérarchiques DAE/DSM ne sont ni proposées ni expliquées à un PoS.</span></div>');}
function posAiHelp(){return answer('<div class="bir-v2996-guide"><h4>Assistant B.I.R. pour un PoS</h4><p>L’Assistant adapte ses réponses au rôle PoS. Il peut expliquer l’état de votre propre compte, votre solde, votre file, vos ventes, vos demandes de crédit, votre SIM, votre PIN, le Robot/Remote, la synchronisation, le serveur et le SAV.</p><p>Il peut vous guider vers les formulaires autorisés à votre rôle, mais ne valide jamais une opération financière à votre place.</p><p>Essayez : « donne-moi le brief de mon compte », « pourquoi ma vente est en attente ? », « comment vendre à un client ? », « comment demander du crédit ? », « synchronise », « vérifie le serveur » ou « liste mes services ».</p><span class="bir-v2996-guard">War Room enfants, Check Réseau, Tchoronko, solde enfant, politiques de commissions enfant et préparation d’approvisionnement d’un enfant restent réservés aux rôles habilités DAE/DSM.</span></div>');}
function prepareTarget(q){var n=norm(q),m=txt(q).match(/\b((?:POS|DSM)[A-Z0-9_\/-]*)\b/i);if(!/\bprepare\b/.test(n)||!m)return null;return {code:m[1].toUpperCase(),type:/^DSM/i.test(m[1])?'DSM':'POS'};}
function hierarchySpecial(q){var t=prepareTarget(q),r=role();if(!t)return false;if(r==='POS'){denyPos();return true;}if(r==='DAE'&&t.type!=='DSM'){denyHierarchy(t.type);return true;}if(r==='DSM'&&t.type!=='POS'){denyHierarchy(t.type);return true;}return false;}
function reservedForPos(q){var n=norm(q);if(!n)return false;
 if(/\bprepare\b/.test(n)&&/(?:pos|dsm|enfant)/.test(n))return true;
 if(/(?:approvision|fournir|recharger|crediter|transferer).*(?:pos|dsm|enfant)/.test(n))return true;
 if(/(?:pos|dsm|enfant).*(?:approvision|fournir|recharger|crediter|transferer)/.test(n))return true;
 if(/check reseau|verifie.*reseau|audite.*reseau|ouvre.*reseau|war room|tchoronko|solde.*enfant|enfant.*solde|enfant direct/.test(n))return true;
 if(/(?:alerte|stock|inactif|activite|solde).*(?:pos\d|dsm\d|enfant)/.test(n))return true;
 if(/(?:pos\d|dsm\d|enfant).*(?:alerte|stock|inactif|activite|solde)/.test(n))return true;
 if(/(?:commission|taux).*(?:enfant|pos\d|dsm\d)/.test(n))return true;
 if(/(?:liste|montre|donne).*(?:service|fonction).*(?:reseau|fournir|piloter)/.test(n))return true;
 return false;
}
function posSpecial(q){var n=norm(q);if(!isPos())return false;if(reservedForPos(q)){denyPos();return true;}
 if(/(?:liste|montre|donne).*(?:toutes|tous|mes).*(?:fonction|service)|(?:liste|montre|donne).*(?:fonction|service)/.test(n)){posServices();return true;}
 if(/comment.*(?:ia|assistant)|que peux tu faire|que fait.*assistant|fonctionne.*(?:ia|assistant)/.test(n)){posAiHelp();return true;}
 return false;
}
function scopedSpecial(q){if(hierarchySpecial(q))return true;return posSpecial(q);}
var POS_PROMOS_FR=['Donne-moi le brief de mon compte','Pourquoi ma vente est en attente ?','Comment vendre à un client ?','Comment demander du crédit ?','Quel est mon solde ?','Diagnostique les boutons','Actualise mon état','Synchronise','Vérifie le serveur','Liste mes services','Comment fonctionne l’IA ?'];
var POS_PROMOS_EN=['Give me my account brief','Why is my sale pending?','How do I sell to a customer?','How do I request credit?','What is my balance?','Diagnose the buttons','Refresh my status','Synchronize','Check the server','List my services','How does the AI work?'];
function promos(){return lang()==='en'?POS_PROMOS_EN:POS_PROMOS_FR;}
function askSafe(q){var input=id('birV297Question'),go=id('birV297Ask');if(scopedSpecial(q))return;if(input)input.value=q;if(go&&go.click)go.click();}
function showSafePromo(){var e=id('birV2996PosPromoText'),a=promos();if(!e||!a.length)return;e.textContent='« '+a[index%a.length]+' »';index=(index+1)%a.length;}
function schedule(){if(timer)window.clearTimeout(timer);if(document.visibilityState==='hidden')return;timer=window.setTimeout(function(){showSafePromo();schedule();},6500);}
function mountPosRail(){if(!isPos()||id('birV2996PosRail'))return;var old=id('birV2996Rail'),header=document.querySelector('.bir-topbar'),main=document.querySelector('main'),rail=document.createElement('div'),langSlot=document.createElement('div'),promo=document.createElement('button'),language=id('v271Language');if(!old&&!header&&!main)return;if(old)old.style.display='none';rail.id='birV2996PosRail';rail.className='bir-v2996-rail bir-v2996-pos-rail';langSlot.className='bir-v2996-lang-slot';promo.type='button';promo.className='bir-v2996-ai-promo';promo.innerHTML='<span class="bir-v2996-ai-mark">∞</span><span class="bir-v2996-ai-copy"><small>IA B.I.R. · PoS</small><strong id="birV2996PosPromoText">—</strong></span><span class="bir-v2996-ai-arrow">›</span>';rail.appendChild(langSlot);rail.appendChild(promo);if(old&&old.parentNode)old.parentNode.insertBefore(rail,old.nextSibling);else if(header&&header.parentNode)header.parentNode.insertBefore(rail,header.nextSibling);else main.parentNode.insertBefore(rail,main);if(language)langSlot.appendChild(language);showSafePromo();promo.onclick=function(){var a=promos(),i=(index+a.length-1)%a.length;askSafe(a[i]);};schedule();}
function hideRestrictedQuickActions(){if(!isPos())return;var bs=document.querySelectorAll('[data-v2995-task], [data-v2996-open]'),i,b,k;for(i=0;i<bs.length;i++){b=bs[i];k=txt(b.getAttribute('data-v2995-task')||b.getAttribute('data-v2996-open')).toLowerCase();if(k==='network'||k==='fleet')b.style.display='none';}}
function queryFromEvent(e){var t=e.target||e.srcElement,key=(e||window.event).keyCode,inp;if(e.type==='keydown'&&key!==13)return '';if(!t)return '';
 if(t.id==='birV297Question'||t.id==='birIntelSearch'||t.id==='v291ServiceQuery')return t.value||'';
 if(e.type==='click'&&(t.id==='birV297Ask'||t.id==='birIntelSearchGo')){inp=t.id==='birIntelSearchGo'?id('birIntelSearch'):id('birV297Question');return inp&&inp.value||'';}
 return '';
}
function captureQuery(e){var q=queryFromEvent(e);if(!q)return;if(!scopedSpecial(q))return;if(e.preventDefault)e.preventDefault();if(e.stopImmediatePropagation)e.stopImmediatePropagation();if(e.stopPropagation)e.stopPropagation();return false;}
function captureQuickAction(e){if(!isPos()||e.type!=='click')return;var t=e.target||e.srcElement,k;while(t&&t!==document.body&&!(t.getAttribute&&t.getAttribute('data-v2995-task')))t=t.parentNode;if(!t||t===document.body)return;k=txt(t.getAttribute('data-v2995-task')).toLowerCase();if(k!=='network')return;denyPos();if(e.preventDefault)e.preventDefault();if(e.stopImmediatePropagation)e.stopImmediatePropagation();if(e.stopPropagation)e.stopPropagation();return false;}
function wrapPublicGuide(){if(!window.BIRAIGuideV2996||window.BIRAIGuideV2996.__roleGuard)return;var old=window.BIRAIGuideV2996.ask;window.BIRAIGuideV2996.ask=function(q){if(scopedSpecial(q))return;if(typeof old==='function')return old(q);};if(isPos())window.BIRAIGuideV2996.services=function(){return {role:'POS',scoped:true,note:'DAE/DSM-only services are intentionally omitted.'};};window.BIRAIGuideV2996.__roleGuard=true;}
function markAssistant(){if(!isPos())return;var box=id('birV297Assistant');if(!box)return;box.setAttribute('data-bir-role-scope','POS');var h=box.querySelector('h3'),s=box.querySelector('small');if(h)h.textContent='Assistant B.I.R. — PoS';if(s)s.textContent='Aide adaptée à votre rôle • aucune fonction DAE/DSM exposée • aucune finance automatique';}
function install(){if(installed)return;installed=true;mountPosRail();markAssistant();hideRestrictedQuickActions();wrapPublicGuide();document.addEventListener('keydown',captureQuery,true);document.addEventListener('click',captureQuery,true);document.addEventListener('click',captureQuickAction,true);document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible'&&isPos())schedule();else if(timer){window.clearTimeout(timer);timer=null;}});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){window.setTimeout(install,2900);});else window.setTimeout(install,2900);
window.BIRRoleGuardV2996={role:role,isPos:isPos,reservedForPos:reservedForPos,prepareTarget:prepareTarget};
}());
