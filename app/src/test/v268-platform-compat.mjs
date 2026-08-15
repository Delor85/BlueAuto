import fs from 'node:fs';
const js=fs.readFileSync('app/src/main/assets/platform-v267.js','utf8');
for(const required of ['platform_snapshot','operator_insights','shadow_enroll','mercenary_save','commission_policy','commission_set_child','kyc_save','executeRawUSSD']){
  if(!js.includes(required)) throw new Error('platform function lost: '+required);
}
for(const banned of ['=>','?.','??','const ','let ','`']){
  if(js.includes(banned)) throw new Error('old WebView incompatible syntax remains: '+banned);
}
if(!js.includes("configuration.role === 'DAE'")||!js.includes("configuration.role === 'DSM'")) throw new Error('role gating missing');
if(!js.includes('if (isDae())')||!js.includes('if (isManager())')) throw new Error('advanced module role scope missing');
if(!js.includes('if (isRobot())')) throw new Error('Robot-only Sandbox gating missing');
if(!js.includes('var formatter = null')) throw new Error('cached number formatter missing');
if(!js.includes('<details class="card v267-extra"')) throw new Error('collapsible advanced modules missing');
console.log('v2.6.8 platform extension: ES5 WebView compatibility and role-scoped advanced modules OK');
