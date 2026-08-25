import fs from 'node:fs';
const read=p=>fs.readFileSync(p,'utf8');
const must=(x,m)=>{if(!x)throw new Error(m);};

const html=read('app/src/main/assets/index.html');
const app=read('app/src/main/assets/app.js');
const war=read('app/src/main/assets/war-room-v294.js');
const field=read('app/src/main/assets/field-runtime-v2993.js');
const intel=read('app/src/main/assets/intelligence-v297-core.js');
const native=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const gradle=read('app/build.gradle');

must(/versionCode\s+68\b/.test(gradle)&&/versionName\s+"2\.9\.9\.4"/.test(gradle),'B.I.R. 2.9.9.4/vc68 identity missing');

// Every static HTML button must have an explicit generic route or the historical refreshCommands handler.
const buttons=[...html.matchAll(/<button\b([^>]*)>/g)].map(m=>m[1]);
must(buttons.length>20,'unexpectedly few static buttons found');
for(const attrs of buttons){
  const routed=/\bdata-action=|\bdata-native-action=|\bdata-tab-jump=|\bdata-tab=|\bid="refreshCommands"/.test(attrs);
  must(routed,'static button without explicit route: <button '+attrs+'>');
}

const values=(name)=>[...html.matchAll(new RegExp(name+'="([^"]+)"','g'))].map(m=>m[1]);
const uniq=a=>[...new Set(a)];
const dataActions=uniq(values('data-action'));
const fallbackActions=[];
for(const action of dataActions){
  if(app.includes("action==='"+action+"'"))continue;
  fallbackActions.push(action);
}
// Historical app.js deliberately maps its sole final fallback to TEST_NUMBER. Keep that legacy path
// covered without pretending arbitrary actions are valid: among the current UI, only test-number may use it.
must(fallbackActions.length===1&&fallbackActions[0]==='test-number','unexpected data-action using execute() fallback: '+fallbackActions.join(','));
must(/else\s*\{\s*type='TEST_NUMBER';\s*\}/.test(app),'historical TEST_NUMBER fallback is no longer present');
for(const action of uniq(values('data-native-action'))){
  must(app.includes("action==='"+action+"'"),'data-native-action not handled by app.js: '+action);
}
must(app.includes("each('[data-tab-jump]'")&&app.includes("each('button[data-tab]'")&&app.includes("byId('refreshCommands').onclick"),'generic tab/refresh bindings missing');

// Native methods behind buttons must still exist. go-test is intentionally WebView-only.
for(const method of ['openAccounts','verifySim','prepareRobotPermissions','openPinSettings','changeOperatorPin','resetOperatorPin','openBatteryOptimizationSettings','openManagement','startRobot','checkServerHealth','refreshDashboardLive','loadDashboard']){
  must(native.includes(' '+method+'('),'Android bridge method missing: '+method);
}

// War Room must never suppress an old known balance merely because it is not currently reusable.
for(const token of ['balanceFacts','AUCUN SOLDE CONNU','CERTIFIÉ RÉCENT','ANCIEN','CONNU / À VÉRIFIER','Dernier total Blue connu','valeurs connues, jamais inventées']){
  must(war.includes(token),'War Room truth fallback token missing: '+token);
}
must(!war.includes('Solde masqué : une nouvelle preuve Blue exacte est requise.'),'War Room still hides stale known balance');
must(war.includes('commission!==null?Math.max(0,total-commission):null'),'commission/base must not be invented when component proof is absent');

// Explicit refresh must cover live dashboard, command center and queue; no raw USSD is added here.
for(const token of ['refreshDashboardLive','distribution_command_center','refreshQueueSnapshot'])must(war.includes(token),'War Room refresh source missing: '+token);
for(const bad of ['dialUssd','rawUssd','createCommand(','previewCommand(','confirmCommand('])must(!war.includes(bad),'War Room must remain supervision-only: '+bad);

// Every War Room action produced by urgencyList/fallbacks must have a concrete, observable route.
for(const action of ['buy','supply','permissions','relay','manage','balance','queue','activity','network','sync','refresh']){
  must(war.includes("action==='"+action+"'"),'War Room action has no runAction route: '+action);
}
for(const token of ['birWarActionStatus','notify(','Action War Room inconnue','Aucun effet silencieux','War Room actualisée avec les meilleures preuves disponibles']){
  must(war.includes(token),'observable War Room feedback missing: '+token);
}

// Dynamic buttons added by the current additive runtime remain explicitly bound.
for(const token of ['birV2993Refresh','birV2993TchoSave','birV2993Close','birV2993Supply','birV2993Balance','birV2993WarRefresh','bindChildClicks'])must(field.includes(token),'v2993 dynamic button binding missing: '+token);
for(const token of ['data-intel-quick','data-intel-family','data-intel-ask','birIntelReconcile','birIntelSearchGo','birIntelOptionalUssd','bindResults'])must(intel.includes(token),'Intelligence/Cockpit button binding missing: '+token);

console.log('B.I.R. 2.9.9.4 War Room + static/dynamic button audit: OK');