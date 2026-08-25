import fs from 'node:fs';
const read=p=>fs.readFileSync(p,'utf8');
const must=(x,m)=>{if(!x)throw new Error(m);};
const loader=read('app/src/main/assets/intelligence-v297.js');
const js=read('app/src/main/assets/ai-guide-v2996.js');
const css=read('app/src/main/assets/ai-guide-v2996.css');

must(loader.includes("'intelligence-v297-core.js'")&&loader.includes("'field-runtime-v2993.js'")&&loader.includes("'convergence-v2995.js'")&&loader.includes("'ai-guide-v2996.js'"),'stable v297 -> v2993 -> v2995 -> v2996 chain missing');
must(loader.includes("'ai-guide-v2996.css'"),'v2996 guide stylesheet missing from loader');
for(const old of ['transaction-first-v298.js','reference-stability-v299.js','field-runtime-v2991.js','field-runtime-v2992.js'])must(!new RegExp("addScriptOnce\\([^\\n]+"+old.replaceAll('.','\\.')).test(loader),'unstable historical runtime must not be loaded: '+old);

for(const token of ['Pourquoi POS1 est en alerte ?','Donne-moi le brief complet','Diagnostique les boutons','Check réseau','Actualise tout','Synchronise','Ouvre le réseau','Vérifie le serveur','Quel est mon taux de commission ?','Prépare 5 000 FCFA pour POS1','Liste les services d’Accueil','Comment utiliser Tchoronko ?'])must(js.includes(token),'AI discovery prompt missing: '+token);
for(const token of ['Accueil','Réseau','Piloter / Fournir / Vendre','Activité','Gérer','Tchoronko 2G','CHECK RÉSEAU','Solde enfant','Journal des transactions','SIM & slots','Accessibilité & permissions'])must(js.includes(token),'service encyclopedia capability missing: '+token);
must(js.includes('Comment fonctionne l’Assistant B.I.R. ?')&&js.includes('Il ne soumet ni ne confirme seul une opération financière'),'assistant self-help/financial guard missing');
must(js.includes("setInput('childNode'")&&js.includes("setInput('childAmount'")&&js.includes('Opération préparée — non envoyée'),'natural-language preparation must only prefill certified form');
must(js.includes("String(c.role||'').toUpperCase()!=='DAE'")&&js.includes("String(c.role||'').toUpperCase()!=='DSM'"),'role guard for child supply preparation missing');

must(css.includes('width:42px!important')&&css.includes('max-width:42px!important')&&css.includes('flex:0 0 42px!important'),'compact EN/FR language control contract missing');
must(css.includes('.bir-v2996-ai-promo')&&css.includes('.bir-v2996-rail'),'AI discovery rail contract missing');

for(const re of [/\.createCommand\s*\(/,/\.previewCommand\s*\(/,/\.confirmCommand\s*\(/,/dialUssd\s*\(/,/rawUssd\s*\(/,/setInterval\s*\(/,/new\s+MutationObserver\s*\(/,/tel:/i,/\*550\*/])must(!re.test(js),'forbidden financial/unstable mechanism found in AI guide: '+re);
for(const re of [/querySelector\([^\n]*request-supply[^\n]*\)\.click\s*\(/,/querySelector\([^\n]*supply-child[^\n]*\)\.click\s*\(/,/querySelector\([^\n]*retail-sale[^\n]*\)\.click\s*\(/])must(!re.test(js),'AI guide must not submit finance: '+re);

must(js.includes('document.visibilityState')&&js.includes('window.setTimeout'),'promo rotation must be visibility-aware and non-polling');
console.log('B.I.R. 2.9.9.6 AI guide: compact language + discovery rail + service encyclopedia + safe preparation, no finance execution or unstable runtime mechanism: OK');
