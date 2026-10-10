import fs from 'node:fs';
const main=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/MainActivity.java','utf8');
if(!main.includes('REMOTE • Télécommande prête')) throw new Error('compact Remote status missing');
const remoteStart=main.indexOf('if (!robotMode)');
const remoteEnd=main.indexOf('String profileId',remoteStart);
const remoteBlock=main.slice(remoteStart,remoteEnd);
if(remoteBlock.includes('BlueAccessibilityService')||remoteBlock.includes('SimIdentityManager.verify')) throw new Error('Remote still performs Robot-only status checks');
for(const text of ['Accessibilité à activer avant achat/vente','TEST_NUMBER reste direct','Écran sécurisé : déverrouillage humain requis','Verrou simple : assistance ponctuelle']){
  if(!main.includes(text)) throw new Error('Robot actionable status missing: '+text);
}
if(!main.includes('activeCount > 1')) throw new Error('multi-Robot count is not compacted');
if(main.includes('• Robots actifs : ')) throw new Error('legacy always-visible Robot counter remains');
console.log('v2.6.8 native status: compact Remote and actionable Robot-only alerts OK');
