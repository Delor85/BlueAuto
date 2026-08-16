import fs from 'node:fs';
const html=fs.readFileSync('app/src/main/assets/index.html','utf8');
const js=fs.readFileSync('app/src/main/assets/app.js','utf8');
const css=fs.readFileSync('app/src/main/assets/style.css','utf8');
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
if(!js.includes("bir_active_module_v269')||'reports'")) throw new Error('BIR home is not default');
if(!gradle.includes('versionCode 49')||!gradle.includes('versionName "2.6.9"')) throw new Error('version mismatch');
if(html.includes('une plateforme, pas un catalogue')||html.includes('Uniquement les capacités propres')) throw new Error('meta competitor/catalog copy must not appear');
console.log('BIR v2.6.9 functional UX + historical Blue Magic contract OK');
