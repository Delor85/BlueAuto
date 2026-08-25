import fs from 'node:fs';
const read=p=>fs.readFileSync(p,'utf8');
const must=(x,m)=>{if(!x)throw new Error(m);};
const gradle=read('app/build.gradle');
const loader=read('app/src/main/assets/intelligence-v297.js');
const js=read('app/src/main/assets/convergence-v2995.js');
const core=read('app/src/main/assets/intelligence-v297-core.js');

must(/versionCode\s+69\b/.test(gradle)&&/versionName\s+"2\.9\.9\.5"/.test(gradle),'release identity 2.9.9.5/vc69 missing');
must(loader.includes("'intelligence-v297-core.js'")&&loader.includes("'field-runtime-v2993.js'")&&loader.includes("'convergence-v2995.js'"),'stable v297 -> v2993 -> v2995 chain missing');
for(const old of ['transaction-first-v298.js','reference-stability-v299.js','field-runtime-v2991.js','field-runtime-v2992.js'])must(!new RegExp("addScriptOnce\\([^\\n]+"+old.replaceAll('.','\\.')).test(loader),'unstable historical runtime must not be loaded: '+old);

for(const token of ['FICHE DE VÉRITÉ','Pourquoi cette priorité ?','URGENCES RÉELLES','CONTRÔLES UTILES','CHECK RÉSEAU & SAV COMMERCIAL','Mon tableau de commissions','Autodiagnostic non financier','Assistant B.I.R. — Copilote opérationnel','IA OPÉRATIONNELLE · À LA DEMANDE'])must(js.includes(token),'convergence capability missing: '+token);
for(const token of ['network_balance_audit','platform_snapshot','commission_policy','transaction_ledger','CertifiedBalanceStore local','STOCK FAIBLE','INACTIF ≥48H','SOLDE À VÉRIFIER','TCHORONKO'])must(js.includes(token),'restored 2.9.9.x evidence/network capability missing: '+token);
must(js.includes("localStorage.getItem(pkey('ai'))!=='00'"),'existing per-profile AI enable/disable preference not honored');
must(js.includes('Numéro reconnu :')&&js.includes('Les contrôles serveur restent obligatoires'),'phone -> node convenience guard missing');
must(js.includes('Formulaire d’approvisionnement préparé')&&js.includes('Aucune demande n’a été envoyée')&&js.includes('Aucune vente n’a été exécutée'),'assistant guided-form task guards missing');
must(js.includes('Aucun bouton financier n’a été cliqué pendant ce diagnostic'),'button self-diagnostic safety statement missing');

for(const re of [/\.createCommand\s*\(/,/\.previewCommand\s*\(/,/\.confirmCommand\s*\(/,/dialUssd\s*\(/,/rawUssd\s*\(/,/setInterval\s*\(/,/new\s+MutationObserver\s*\(/,/\.offsetHeight\b/,/\.offsetParent\b/])must(!re.test(js),'forbidden unstable/financial mechanism found: '+re);
for(const re of [/querySelector\([^\n]*request-supply[^\n]*\)\.click\s*\(/,/querySelector\([^\n]*supply-child[^\n]*\)\.click\s*\(/,/querySelector\([^\n]*retail-sale[^\n]*\)\.click\s*\(/])must(!re.test(js),'assistant must not submit finance: '+re);

must(core.includes("ai:true")&&core.includes('birIntelToggle')&&core.includes("profileKey('ai')"),'stable core AI toggle contract missing');
console.log('B.I.R. 2.9.9.5 convergence: restored truth/why/diagnostic/network/commission/assistant capabilities with no finance or Android 11 regression mechanism: OK');
