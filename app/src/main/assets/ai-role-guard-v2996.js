(function(){
'use strict';
/* B.I.R. 2.9.9.6 — role-scoped Assistant guard.
 * A PoS must not receive prompts, guidance, network intelligence or preparation helpers
 * reserved to DAE/DSM child-network management. This layer never creates or submits finance.
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
function denyPos(){return answer('<div class="bir-v2996-guide"><h4>Aide limitée au rôle PoS</h4><p>Cette aide n’est pas disponible pour le rôle PoS actif. L’Assistant B.I.R. n’affiche, n’explique et ne prépare pas les fonctions réservées au pilotage DAE/DSM.</p><p>Je peux vous aider sur votre propre compte : vente client, demande de crédit à votre supérieur, solde et preuves, file et historique, Robot/Remote, SIM/PIN, synchronisation, serveur, diagnostic et SAV.</p><span class="bir-v2996-guard">Aucune opération n’a été créée, préremplie ou exécutée.</span></div>');}
function posServices(){return answer('<div class="bir-v2996-guide"><h4>Services disponibles pour votre rôle PoS</h4><p><b>Accueil</b></p><ul><li>Situation de votre compte, mode Remote/Robot et alertes locales.</li><li>Votre solde, sa fraîcheur et ses preuves.</li><li>Brief de votre propre activité et diagnostic local.</li></ul><p><b>Achat / Vente</b></p><ul><li>Demander du crédit à votre supérieur selon les règles B.I.R.</li><li>Vendre du crédit à un client final via le formulaire normal.</li><li>Tester votre SIM/route sans mouvement de fonds.</li><li>Consulter vos dernières transactions et les détails disponibles.</li></ul><p><b>Activité</b></p><ul><li>Suivre votre file, vos résultats et vos opérations à rapprocher.</li><li>Consulter votre journal et demander un diagnostic des boutons.</li><li>Vérifier le serveur et demander une synchronisation sûre.</li></ul><p><b>Gérer</b></p><ul><li>Comptes, SIM/slot, mode Remote/Robot, PIN, Accessibilité, permissions et batterie.</li></ul><span class="bir-v2996-guard">Les fonctions de pilotage d’enfants et de réseau réservées aux DAE/DSM ne sont ni listées ni expliquées au PoS.</span></div>');}
function posAiHelp(){return answer('<div class="bir-v2996-guide"><h4>Assistant B.I.R. pour un PoS</h4><p>L’Assistant adapte ses réponses au rôle PoS. Il peut expliquer l’état de votre propre compte, votre solde, votre file, vos ventes, vos demandes de crédit, votre SIM, votre PIN, le Robot/Remote, la synchronisation, le serveur et le SAV.</p><p>Il peut vous guider vers les formulaires que votre rôle est autorisé à utiliser, mais ne valide jamais une opération financière à votre place.</p><p>Essayez : « donne-moi le brief de mon compte », « pourquoi ma vente est en attente ? », « comment vendre à un client ? », « comment demander du crédit ? », « synchronise », « vérifie le serveur » ou « liste mes services ».</p><span class="bir-v2996-guard">Les aides DAE/DSM restent invisibles et inaccessibles depuis un compte PoS.</span></div>');}
function reservedForPos(q){var n=norm(q);if(!n)return false;
 if(/\bprepare\b/.test(n)&&/(?:pos|dsm|enfant)/.test(n))return true;
 if(/(?:approvision|fournir|recharger|crediter|transferer).*(?:pos|dsm|enfant)/.test(n))return true;
 if(/(?:pos|dsm|enfant).*(?:approvision|fournir|recharger|crediter|transferer)/.test(n))return true;
 if(/check reseau|verifie.*reseau|audite.*reseau|ouvre.*reseau|war room|tchoronko|solde enfant|enfant direct/.test(n))return true;
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
var POS_PROMOS_FR=['Donne-moi le brief de mon compte','Pourquoi ma vente est en attente ?','Comment vendre à un client ?','Comment demander du crédit ?','Quel est mon solde ?','Diagnostique les boutons','Actualise mon état','Synchronise','Vérifie le serveur','Liste mes services','Comment fonctionne l’IA ?'];
var POS_PROMOS_EN=['Give me my account brief','Why is my sale pending?','How do I sell to a customer?','How do I request credit?','What is my balance?','Diagnose the buttons','Refresh my status','Synchronize','Check the server','List my services','How does the AI work?'];
function promos(){return lang()==='en'?POS_PROMOS_EN:POS_PROMOS_FR;}
function askSafe(q){var input=id('birV297Question'),go=id('birV297Ask');if(posSpecial(q))return;if(input)input.value=q;if(go&&go.click)go.click();}
function showSafePromo(){var e=id('birV2996PosPromoText'),a=promos();if(!e||!a.length)return;e.textContent='« '+a[index%a.length]+' »';index=(index+1)%a.length;}
function schedule(){if(timer)window.clearTimeout(timer);if(document.visibilityState==='hidden')return;timer=window.setTimeout(function(){showSafePromo();schedule();},6500);}
function mountPosRail(){if(!isPos()||id('birV2996PosRail'))return;var old=id('birV2996Rail'),header=document.querySelector('.bir-topbar'),main=document.querySelector('main'),rail=document.createElement('div'),langSlot=document.createElement('div'),promo=document.createElement('button'),language=id('v271Language');if(!old&&!header&&!main)return;if(old)old.style.display='none';rail.id='birV2996PosRail';rail.className='bir-v2996-rail bir-v2996-pos-rail';langSlot.className='bir-v2996-lang-slot';promo.type='button';promo.className='bir-v2996-ai-promo';promo.innerHTML='<span class="bir-v2996-ai-mark">∞</span><span class="bir-v2996-ai-copy"><small>IA B.I.R. · PoS</small><strong id="birV2996PosPromoText">—</strong></span><span class="bir-v2996-ai-arrow">›</span>';rail.appendChild(langSlot);rail.appendChild(promo);if(old&&old.parentNode)old.parentNode.insertBefore(rail,old.nextSibling);else if(header&&header.parentNode)header.parentNode.insertBefore(rail,header.nextSibling);else main.parentNode.insertBefore(rail,main);if(language)langSlot.appendChild(language);showSafePromo();promo.onclick=function(){var a=promos(),i=(index+a.length-1)%a.length;askSafe(a[i]);};schedule();}
function captureQuery(e){if(!isPos())return;var t=e.target||e.srcElement,q='',key=(e||window.event).keyCode;if(e.type==='keydown'&&key!==13)return;if(!t)return;
 if(t.id==='birV297Question'||t.id==='birIntelSearch'||t.id==='v291ServiceQuery')q=t.value||'';
 else if(e.type==='click'&&(t.id==='birV297Ask'||t.id==='birIntelSearchGo')){var inp=t.id==='birIntelSearchGo'?id('birIntelSearch'):id('birV297Question');q=inp&&inp.value||'';}
 else return;
 if(!posSpecial(q))return;if(e.preventDefault)e.preventDefault();if(e.stopImmediatePropagation)e.stopImmediatePropagation();if(e.stopPropagation)e.stopPropagation();return false;
}
function wrapPublicGuide(){if(!isPos()||!window.BIRAIGuideV2996||window.BIRAIGuideV2996.__roleGuard)return;var old=window.BIRAIGuideV2996.ask;window.BIRAIGuideV2996.ask=function(q){if(posSpecial(q))return;if(typeof old==='function')return old(q);};window.BIRAIGuideV2996.services=function(){return {role:'POS',scoped:true,note:'DAE/DSM-only services are intentionally omitted.'};};window.BIRAIGuideV2996.__roleGuard=true;}
function markAssistant(){if(!isPos())return;var box=id('birV297Assistant');if(!box)return;box.setAttribute('data-bir-role-scope','POS');var h=box.querySelector('h3'),s=box.querySelector('small');if(h)h.textContent='Assistant B.I.R. — PoS';if(s)s.textContent='Aide adaptée à votre rôle • aucune fonction DAE/DSM exposée • aucune finance automatique';}
function install(){if(installed)return;installed=true;if(!isPos())return;mountPosRail();markAssistant();wrapPublicGuide();document.addEventListener('keydown',captureQuery,true);document.addEventListener('click',captureQuery,true);document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')schedule();else if(timer){window.clearTimeout(timer);timer=null;}});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){window.setTimeout(install,2900);});else window.setTimeout(install,2900);
window.BIRRoleGuardV2996={role:role,isPos:isPos,reservedForPos:reservedForPos};
}());
