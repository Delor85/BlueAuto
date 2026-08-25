(function(){
'use strict';
/* B.I.R. 2.9.9.6 — additive AI discovery + in-app guide.
 * ES5 / Android 6+ compatible. No financial command is created, previewed or confirmed here.
 * Natural-language finance may only prefill an existing certified form.
 */
var installed=false,promoIndex=0,promoTimer=null;
function id(x){return document.getElementById(x);}function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function txt(v){return String(v==null?'':v);}function esc(v){return txt(v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function norm(v){var s=txt(v).toLowerCase();try{s=s.normalize('NFD').replace(/[\u0300-\u036f]/g,'');}catch(e){}return s.replace(/[^a-z0-9]+/g,' ').replace(/^\s+|\s+$/g,'');}
function cfg(){try{return JSON.parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}')||{};}catch(e){return {};}}
function lang(){try{return bridge()&&bridge().getUiLanguage&&bridge().getUiLanguage()==='en'?'en':'fr';}catch(e){return 'fr';}}
function tab(name){var e=document.querySelector('button[data-tab="'+name+'"]')||document.querySelector('button[data-tab-jump="'+name+'"]');if(e&&e.click){e.click();return true;}return false;}
function setInput(name,value){var e=id(name);if(!e)return false;e.value=txt(value);try{var ev=document.createEvent('HTMLEvents');ev.initEvent('input',true,false);e.dispatchEvent(ev);}catch(ignore){}return true;}
function money(n){return String(Math.round(Number(n)||0)).replace(/\B(?=(\d{3})+(?!\d))/g,' ')+' FCFA';}
var SERVICES={
 reports:{fr:'Accueil',en:'Home',items:[
  ['Situation du compte','Voir le compte, le rôle, le mode Remote/Robot, la SIM et les alertes principales.','Ouvrez Accueil : la situation utile est affichée en premier.'],
  ['Solde & preuves','Voir le dernier solde connu, sa fraîcheur et sa qualité.','Dans Accueil, ouvrez Solde & preuves. Une donnée ancienne reste signalée comme telle.'],
  ['Brief complet','Obtenir une synthèse du solde, Robot, file, réseau, commissions et preuves.','Demandez « donne-moi le brief complet ».'],
  ['Assistant B.I.R.','Poser une question, comprendre un état et être guidé vers la bonne action.','Posez votre question en langage simple. L’Assistant explique, diagnostique, navigue et peut préremplir un formulaire.'],
  ['Rapprochement & preuves','Recouper les informations B.I.R. avec les preuves disponibles.','Utilisez les blocs de vérité et le rapprochement avant de répéter une opération incertaine.']
 ]},
 fleet:{fr:'Réseau',en:'Network',items:[
  ['War Room des enfants','Voir les DSM/PoS directs, leurs alertes, activité, solde et état connu.','Ouvrez Réseau puis touchez un enfant pour sa War Room.'],
  ['CHECK RÉSEAU','Actualiser intelligemment la situation du réseau.','Demandez « check réseau » ou utilisez le bouton prévu. Les preuves récentes sont réutilisées quand elles sont encore valables.'],
  ['Solde enfant','Consulter le solde d’un DSM ou PoS autorisé.','Ouvrez Piloter/Fournir puis Consulter le solde enfant, ou partez de la War Room.'],
  ['Tchoronko 2G','Enregistrer et suivre les call boxeurs sans téléphone Android afin qu’ils restent visibles dans l’arborescence.','Dans Réseau, utilisez Tchoronko pour créer ou mettre à jour le DSM2G/PoS2G, son numéro, son repère et sa zone.'],
  ['Alertes stock & inactivité','Repérer stock faible, solde à vérifier et baisse d’activité.','Ouvrez Réseau ou demandez « pourquoi POS1 est en alerte ? ».'],
  ['Commissions','Voir le taux habituel, les taux enfants et les taux ponctuels prouvés.','Demandez « quel est mon taux de commission ? » ou ouvrez la rubrique Commissions.']
 ]},
 flux:{fr:'Piloter / Fournir / Vendre',en:'Control / Supply / Sell',items:[
  ['Approvisionner un enfant','DAE→DSM ou DSM→PoS selon le rôle.','Choisissez l’enfant, saisissez le montant puis suivez le parcours normal de vérification et confirmation.'],
  ['Demander du crédit','DSM/PoS demande du stock à son supérieur.','Saisissez le montant dans Achat de crédit puis validez le parcours normal.'],
  ['Vendre à un client','Fonction PoS de recharge du client final.','Saisissez le numéro client et le montant puis vérifiez avant confirmation.'],
  ['Préparer une opération par l’IA','Préremplir un formulaire sans envoyer ni confirmer la transaction.','Exemple : « Prépare 5 000 FCFA pour POS1 ». Vérifiez ensuite le formulaire et confirmez vous-même.'],
  ['Test numéro','Tester la route SIM sans mouvement de fonds.','Utilisez Tester la SIM Robot avant de diagnostiquer une transaction financière.'],
  ['5 dernières transactions','Consulter l’historique Blue disponible.','Utilisez Mes 5 dernières transactions.'],
  ['Détails transaction','Rechercher une transaction Blue par identifiant.','Saisissez l’identifiant puis lancez la consultation.']
 ]},
 support:{fr:'Activité',en:'Activity',items:[
  ['File des commandes','Voir ce qui attend, s’exécute, réussit, échoue ou reste À vérifier.','Ouvrez Activité. Ne recréez pas une commande UNKNOWN sans rapprochement.'],
  ['Journal des transactions','Retrouver les achats/ventes mémorisés avec les informations disponibles.','Ouvrez Activité puis utilisez la recherche du journal.'],
  ['Diagnostic boutons','Vérifier les boutons visibles sans déclencher une finance.','Demandez « diagnostique les boutons ».'],
  ['Vérifier le serveur','Contrôler l’accessibilité du service B.I.R.','Demandez « vérifie le serveur ».'],
  ['SAV / diagnostic','Comprendre une panne de Robot, SIM, Accessibilité, file ou synchronisation.','Décrivez simplement le symptôme à l’Assistant.']
 ]},
 config:{fr:'Gérer',en:'Manage',items:[
  ['Comptes','Ajouter, ouvrir et gérer plusieurs profils.','Ouvrez Gérer puis Comptes.'],
  ['SIM & slots','Vérifier la SIM et le slot liés au profil.','Ouvrez Gérer puis Vérifier / lier la SIM.'],
  ['Remote / Robot','Choisir le rôle du téléphone pour un profil sans changer son identité métier.','Ouvrez Gérer puis le réglage de mode disponible.'],
  ['PIN Blue','Enregistrer ou modifier le PIN local du profil.','Ouvrez Gérer puis PIN. Le PIN n’est pas transmis par l’Assistant.'],
  ['Accessibilité & permissions','Préparer les autorisations nécessaires au Robot.','Ouvrez Gérer puis Permissions/Accessibilité et suivez les indications.'],
  ['Synchronisation','Rapprocher l’état local, Remote, Robot et serveur.','Demandez « synchronise » ; aucune finance n’est recréée pour synchroniser.'],
  ['Batterie & continuité','Configurer Android pour maintenir le service utile sans garder inutilement l’écran allumé.','Ouvrez les réglages batterie depuis Gérer quand B.I.R. le demande.']
 ]}
};
function allServicesHtml(){var order=['reports','fleet','flux','support','config'],h=['<div class="bir-v2996-guide"><h4>Fonctionnalités B.I.R. par rubrique</h4>'],i,k,j,x;for(i=0;i<order.length;i++){k=order[i];h.push('<p><b>'+esc(SERVICES[k].fr)+'</b></p><ul>');for(j=0;j<SERVICES[k].items.length;j++){x=SERVICES[k].items[j];h.push('<li><b>'+esc(x[0])+'</b> — '+esc(x[1])+'</li>');}h.push('</ul>');}h.push('<span class="bir-v2996-guard">L’Assistant peut expliquer, diagnostiquer, actualiser, synchroniser, naviguer et préparer certains formulaires. Il ne soumet ni ne confirme seul une opération financière.</span></div>');return h.join('');}
function sectionFrom(q){var n=norm(q);if(/accueil|home/.test(n))return 'reports';if(/reseau|network/.test(n))return 'fleet';if(/piloter|fournir|vendre|transaction|flux|control|supply|sell/.test(n))return 'flux';if(/activite|activity|sav|support|file|journal/.test(n))return 'support';if(/gerer|manage|reglage|configuration/.test(n))return 'config';return '';}
function sectionHtml(key){var s=SERVICES[key],h=['<div class="bir-v2996-guide"><h4>Services de '+esc(s.fr)+'</h4><ul>'],i,x;for(i=0;i<s.items.length;i++){x=s.items[i];h.push('<li><b>'+esc(x[0])+'</b> — '+esc(x[1])+'<br><small>'+esc(x[2])+'</small></li>');}h.push('</ul><div class="bir-v2996-guide-tabs"><button data-v2996-open="'+key+'">OUVRIR '+esc(s.fr.toUpperCase())+'</button><button data-v2996-all="1">TOUTES LES RUBRIQUES</button></div></div>');return h.join('');}
function findService(q){var n=norm(q),keys=['reports','fleet','flux','support','config'],i,j,x,hay;for(i=0;i<keys.length;i++){for(j=0;j<SERVICES[keys[i]].items.length;j++){x=SERVICES[keys[i]].items[j];hay=norm(x[0]+' '+x[1]);if(n.indexOf(norm(x[0]))>=0||norm(x[0]).indexOf(n.replace(/^(comment utiliser|comment faire|comment fonctionne|a quoi sert) /,''))>=0)return {key:keys[i],item:x};}}return null;}
function serviceHtml(found){var x=found.item;return '<div class="bir-v2996-guide"><h4>'+esc(x[0])+'</h4><p>'+esc(x[1])+'</p><p><b>Comment l’utiliser :</b> '+esc(x[2])+'</p><div class="bir-v2996-guide-tabs"><button data-v2996-open="'+found.key+'">OUVRIR LA RUBRIQUE</button></div></div>';}
function aiHelpHtml(){return '<div class="bir-v2996-guide"><h4>Comment fonctionne l’Assistant B.I.R. ?</h4><p>Il lit uniquement les états et preuves que B.I.R. possède réellement pour votre compte et votre rôle. Il peut vous expliquer une alerte, faire un brief, rechercher une fonction, ouvrir la bonne rubrique, demander une actualisation, lancer une synchronisation sûre, vérifier le serveur et diagnostiquer l’interface.</p><p>Pour une opération financière, il peut <b>préparer</b> le formulaire à votre demande. Exemple : « Prépare 5 000 FCFA pour POS1 ». Il renseigne l’enfant et le montant, puis s’arrête. Vous devez vérifier et utiliser vous-même le bouton normal ; les contrôles et confirmations habituels restent obligatoires.</p><p>Vous pouvez aussi demander : « liste les services d’Accueil », « comment utiliser Tchoronko ? », « comment consulter le solde d’un enfant ? », « pourquoi POS1 est en alerte ? », « quel est mon taux de commission ? ».</p><span class="bir-v2996-guard">L’IA ne connaît pas votre PIN Blue, ne contourne pas les droits du rôle et ne transforme jamais une phrase en transfert silencieux.</span></div>';}
function answer(html){var out=id('birV297Answer');if(!out)return false;out.innerHTML=html;bindGuideButtons(out);return true;}
function bindGuideButtons(root){var bs=root.querySelectorAll('[data-v2996-open]'),i;for(i=0;i<bs.length;i++)bs[i].onclick=function(){tab(this.getAttribute('data-v2996-open'));};bs=root.querySelectorAll('[data-v2996-all]');for(i=0;i<bs.length;i++)bs[i].onclick=function(){answer(allServicesHtml());};}
function prepare(q){var n=norm(q),m=txt(q).match(/(\d[\d .]{0,10})\s*(?:fcfa|f\b)?/i),node=txt(q).match(/\b((?:POS|DSM)[A-Z0-9_\/-]*)\b/i),amount,c=cfg();if(!/\bprepare\b/.test(n)||!m||!node)return false;amount=Number(m[1].replace(/\D/g,''));if(!amount)return false;if(String(c.role||'').toUpperCase()!=='DAE'&&String(c.role||'').toUpperCase()!=='DSM'){answer('<div class="bir-v2996-guide"><h4>Préparation impossible pour ce rôle</h4><p>Le compte actif n’est pas autorisé à approvisionner un enfant direct. Je n’ai créé aucune opération.</p></div>');return true;}tab('flux');setInput('childNode',node[1].toUpperCase());setInput('childAmount',String(amount));answer('<div class="bir-v2996-guide"><h4>Opération préparée — non envoyée</h4><p><b>'+esc(node[1].toUpperCase())+'</b> · <b>'+esc(money(amount))+'</b></p><p>J’ai uniquement prérempli le formulaire d’approvisionnement. Vérifiez l’enfant et le montant, puis utilisez vous-même le bouton normal si tout est correct.</p><span class="bir-v2996-guard">Aucune transaction n’a été créée, prévisualisée, confirmée ou exécutée par l’Assistant.</span></div>');return true;}
function special(q){var n=norm(q),key,found;if(prepare(q))return true;if(/(?:liste|montre|donne).*(?:toutes|tous).*(?:fonction|service)|(?:toutes|tous).*(?:fonction|service)/.test(n)){return answer(allServicesHtml());}if(/(?:liste|montre|donne).*(?:fonction|service)/.test(n)){key=sectionFrom(q);if(key)return answer(sectionHtml(key));return answer(allServicesHtml());}if(/comment.*(?:ia|assistant)|que peux tu faire|que fait.*assistant|fonctionne.*(?:ia|assistant)/.test(n))return answer(aiHelpHtml());if(/comment utiliser|comment faire|comment fonctionne|a quoi sert/.test(n)){found=findService(q);if(found)return answer(serviceHtml(found));key=sectionFrom(q);if(key)return answer(sectionHtml(key));}return false;}
var PROMOS_FR=['Pourquoi POS1 est en alerte ?','Donne-moi le brief complet','Diagnostique les boutons','Check réseau','Actualise tout','Synchronise','Ouvre le réseau','Vérifie le serveur','Quel est mon taux de commission ?','Prépare 5 000 FCFA pour POS1','Liste les services d’Accueil','Comment utiliser Tchoronko ?','Que peux-tu faire pour moi ?'];
var PROMOS_EN=['Why is POS1 on alert?','Give me the full brief','Diagnose the buttons','Check network','Refresh everything','Synchronize','Open the network','Check the server','What is my commission rate?','Prepare 5,000 FCFA for POS1','List Home services','How do I use Tchoronko?','What can you do for me?'];
function promos(){return lang()==='en'?PROMOS_EN:PROMOS_FR;}
function showPromo(){var e=id('birV2996PromoText'),a=promos();if(!e||!a.length)return;e.textContent='« '+a[promoIndex%a.length]+' »';promoIndex=(promoIndex+1)%a.length;}
function schedulePromo(){if(promoTimer)window.clearTimeout(promoTimer);if(document.visibilityState==='hidden')return;promoTimer=window.setTimeout(function(){showPromo();schedulePromo();},6500);}
function askPrompt(q){tab('reports');window.setTimeout(function(){var input=id('birV297Question'),go=id('birV297Ask');if(input)input.value=q;if(special(q))return;if(go&&go.click)go.click();},80);}
function mountRail(){if(id('birV2996Rail'))return;var header=document.querySelector('.bir-topbar'),main=document.querySelector('main'),old=id('v271Language'),rail=document.createElement('div'),langSlot=document.createElement('div'),promo=document.createElement('button');if(!header&&!main)return;rail.id='birV2996Rail';rail.className='bir-v2996-rail';langSlot.className='bir-v2996-lang-slot';promo.type='button';promo.className='bir-v2996-ai-promo';promo.innerHTML='<span class="bir-v2996-ai-mark">∞</span><span class="bir-v2996-ai-copy"><small>IA B.I.R. · ESSAYEZ</small><strong id="birV2996PromoText">—</strong></span><span class="bir-v2996-ai-arrow">›</span>';rail.appendChild(langSlot);rail.appendChild(promo);if(header&&header.parentNode)header.parentNode.insertBefore(rail,header.nextSibling);else main.parentNode.insertBefore(rail,main);if(old)langSlot.appendChild(old);else{var retry=0,wait=function(){var x=id('v271Language');if(x){langSlot.appendChild(x);return;}retry++;if(retry<20)window.setTimeout(wait,150);};wait();}showPromo();promo.onclick=function(){var a=promos(),idx=(promoIndex+a.length-1)%a.length,q=a[idx];askPrompt(q);};schedulePromo();}
function bindAssistant(){var q=id('birV297Question'),go=id('birV297Ask');if(q&&!q.__v2996){q.__v2996=true;q.addEventListener('keydown',function(e){if((e||window.event).keyCode!==13)return;if(!special(this.value))return;if(e&&e.preventDefault)e.preventDefault();if(e&&e.stopImmediatePropagation)e.stopImmediatePropagation();return false;},true);}if(go&&!go.__v2996){go.__v2996=true;go.addEventListener('click',function(e){var v=q&&q.value||'';if(!special(v))return;if(e&&e.preventDefault)e.preventDefault();if(e&&e.stopImmediatePropagation)e.stopImmediatePropagation();},true);}}
function bindVisibility(){document.addEventListener('visibilitychange',function(){if(document.visibilityState==='visible')schedulePromo();else if(promoTimer){window.clearTimeout(promoTimer);promoTimer=null;}});}
function install(){if(installed)return;installed=true;mountRail();bindAssistant();bindVisibility();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){window.setTimeout(install,2450);});else window.setTimeout(install,2450);
window.BIRAIGuideV2996={ask:function(q){askPrompt(q);},services:function(){return SERVICES;}};
}());
