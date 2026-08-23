import fs from 'node:fs';
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const js=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
const field297=fs.readFileSync('app/src/main/assets/field-ops-v297.js','utf8');
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
if(!js.includes("var saved='reports'")) throw new Error('BIR home is not default');
const acceptedCodes=['versionCode 52','versionCode 53','versionCode 54','versionCode 55','versionCode 56','versionCode 58','versionCode 60','versionCode 61','versionCode 62','versionCode 63','versionCode 64'];
const acceptedNames=['versionName "2.7.1"','versionName "2.8.0"','versionName "2.8.1"','versionName "2.9.0"','versionName "2.9.1"','versionName "2.9.3"','versionName "2.9.5"','versionName "2.9.6"','versionName "2.9.7"','versionName "2.9.8"','versionName "2.9.9"'];
if(!acceptedCodes.some(x=>gradle.includes(x))||!acceptedNames.some(x=>gradle.includes(x))) throw new Error('version mismatch');
for(const x of ['field-ops-v297.css','field-ops-v297.js']) if(!html.includes(x)) throw new Error('v2.9.7 field module not loaded: '+x);
for(const x of ['File & activité en direct','ACTUALISER SOLDE','ASSISTANT OPÉRATIONNEL LOCAL','Pourquoi ça ne part pas ?','requestQueue(false)','function requestDashboard(force)','10000']) if(!field297.includes(x)) throw new Error('v2.9.7 field contract missing: '+x);
if(!field297.includes('insertBefore(detail,btn.nextSibling)')) throw new Error('Mes outils must render detail under selected tool');
if(!field297.includes('aucune opération financière automatique')&&!field297.includes('ne crée, ne confirme')) throw new Error('local assistant financial guard missing');
if(html.includes('une plateforme, pas un catalogue')||html.includes('Uniquement les capacités propres')) throw new Error('meta competitor/catalog copy must not appear');
console.log('BIR v2.9.7+ functional UX + historical Blue Magic contract OK');
