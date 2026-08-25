import fs from 'node:fs';
const read=p=>fs.readFileSync(p,'utf8');
const must=(x,m)=>{if(!x)throw new Error(m);};
const gradle=read('app/build.gradle');
const loader=read('app/src/main/assets/intelligence-v297.js');
const js=read('app/src/main/assets/field-runtime-v2993.js');
const css=read('app/src/main/assets/field-runtime-v2993.css');
const app=read('app/src/main/java/com/profitloop/blueauto/BirApplication.java');
const v30=read('app/src/main/res/values-v30/bir_rendering.xml');
const manifest=read('app/src/main/AndroidManifest.xml');

must(/versionCode\s+67\b/.test(gradle)&&/versionName\s+"2\.9\.9\.3"/.test(gradle),'release identity 2.9.9.3/vc67 missing');
must(/function api30\(\)/.test(loader)&&/bir-v2993-api30-legacy/.test(loader),'Android 11 legacy-path selector missing');
must(/if\(api30\(\)\)[\s\S]*loadV2993\(\);[\s\S]*return;/.test(loader),'Android 11 must stop after v2993 instead of entering modern chain');
for(const token of ['transaction-first-v298','reference-stability-v299','field-runtime-v2991','field-runtime-v2992']){
  must(loader.includes(token),'modern chain asset missing for non-API30: '+token);
}
must(/Build\.VERSION\.SDK_INT != Build\.VERSION_CODES\.R/.test(app),'Android 11 must skip post-2.9.7 foreground lifecycle wake');
must(/<bool name="bir_main_hardware_accelerated">true<\/bool>/.test(v30),'Android 11 must match proven hardware-accelerated pre-2.9.9 rendering baseline');
must(/android:hardwareAccelerated="@bool\/bir_main_hardware_accelerated"/.test(manifest),'manifest rendering selector missing');

for(const token of ['shadow_enroll','platform_snapshot','commission_policy','transaction_ledger','ops_cockpit'])must(js.includes(token),'v2993 data/control action missing: '+token);
for(const token of ['WAR ROOM DES ENFANTS','TCHORONKO · 1G / 2G','Enregistrer un ','Commission à l’approvisionnement','Taux ponctuel / écart récent'])must(js.includes(token),'child War Room/Tchoronko feature missing: '+token);
must(/role\(\)==='DAE'\?'DSM':role\(\)==='DSM'\?'POS'/.test(js),'direct DAE→DSM / DSM→POS role gate missing');
must(/parent_node_code/.test(js)&&/directChildren/.test(js),'direct-child scoping missing');
must(/TIMEOUT/.test(js)&&/Aucune réponse du serveur/.test(js),'Tchoronko/platform request timeout feedback missing');
must(/data&&data\._action/.test(js)&&/p&&p\.action/.test(js),'error callback action recovery missing');
must(/terminal 1G\/2G Tchoronko/i.test(js),'2G child War Room identity missing');
must(/APPROVISIONNER/.test(js)&&/CONSULTER SOLDE/.test(js),'child War Room safe navigation actions missing');
for(const bad of ['createCommand','previewCommand','confirmCommand','dialUssd','rawUssd','setInterval'])must(!js.includes(bad),'v2993 must not introduce finance/raw-USSD/poll loop: '+bad);
must(!/backdrop-filter|filter:\s*blur|translate3d|will-change/.test(css),'v2993 must stay free of heavy compositor effects');
console.log('B.I.R. 2.9.9.3 Android11/child-WarRoom/Tchoronko contract: OK');
