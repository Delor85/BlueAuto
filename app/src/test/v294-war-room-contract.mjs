import fs from 'node:fs';

const war=fs.readFileSync('app/src/main/assets/war-room-v294.js','utf8');
const index=fs.readFileSync('app/src/main/assets/index.html','utf8');
const gradle=fs.readFileSync('app/build.gradle','utf8');
const ct=fs.readFileSync('app/src/main/assets/control-tower-v2611.js','utf8');
const worker=fs.readFileSync('cloudflare/src/index.js','utf8');
function need(ok,msg){if(!ok)throw new Error(msg);}
need(index.includes('war-room-v294.js'),'War Room not loaded');
need(gradle.includes('versionCode 59')&&gradle.includes('versionName "2.9.4"'),'v2.9.4 metadata missing');
need(war.includes('Situation maintenant'),'War Room summary missing');
need(war.includes('Mes 3 soldes'),'three balances summary missing');
need(war.includes('Avant rupture'),'stockout ETA missing');
need(war.includes('Ventes 7 jours'),'weekly sales missing');
need(war.includes('Enfants en rupture'),'child stockout summary missing');
need(war.includes('Enfants à assister'),'network health summary missing');
need(war.includes('5 actions prioritaires'),'priority actions missing');
need(war.includes('Assistant B.I.R.')&&war.includes('LOCAL • GRATUIT'),'local free assistant missing');
need(war.includes("prepareRobotPermissions")&&war.includes("openManagement")&&war.includes("check-balance"),'operational repair shortcuts missing');
need(war.includes("data-bir-war-target")&&war.includes("fill('childNode',target)"),'child action prefill missing');
need(!war.includes('fetch(')&&!war.includes('XMLHttpRequest')&&!war.includes('WebSocket'),'assistant must not add external AI/network dependency');
need(ct.includes('Mon taux habituel (%)'),'free commission wording missing');
need(ct.includes('Vos règles, taux par enfant'),'commission freedom copy missing');
need(!ct.includes("r==='DAE'?'10':'8'"),'role-prescribed commission example still present');
need(worker.includes("effective_modes: ['REMOTE','ROBOT']"),'two-mode invariant lost');
need(!fs.readFileSync('app/src/main/AndroidManifest.xml','utf8').includes('android.permission.SEND_SMS'),'SMS invariant lost');
console.log('BIR v2.9.4 War Room/local assistant contract OK');
