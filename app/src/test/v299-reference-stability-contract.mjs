import fs from 'node:fs';

function read(p){return fs.readFileSync(p,'utf8');}
function must(v,m){if(!v)throw new Error(m);}
const js=read('app/src/main/assets/reference-stability-v299.js');
const css=read('app/src/main/assets/reference-stability-v299.css');
const loader=read('app/src/main/assets/intelligence-v297.js');
const app=read('app/src/main/java/com/profitloop/blueauto/BirApplication.java');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const server=read('cloudflare/src/index.js');
const gradle=read('app/build.gradle');

must(/versionCode 64/.test(gradle)&&/versionName "2\.9\.9"/.test(gradle),'v2.9.9/vc64 identity missing');
must(/reference-stability-v299\.css/.test(loader)&&/reference-stability-v299\.js/.test(loader),'v299 must load after Transaction First');
must(/bir-v299-buy/.test(css)&&/#168c50|#0d6f40/.test(css),'purchase/acquisition visual distinction must be green');
must(/Android\\s\+11/.test(js)&&/bir-v299-android11/.test(js),'Android 11 runtime guard missing');
must(/body\.bir-v299-android11::before\{display:none!important/.test(css),'Android 11 fixed animated dust must be removed');
must(/backdrop-filter:none!important/.test(css)&&/scroll-behavior:auto!important/.test(css),'Android 11 compositor simplification missing');

must(/REMOTE_SNAPSHOT_MS = 10_000L/.test(robot),'Remote dashboard cadence must stay 10 seconds');
must(/AppConfig\.anyRemoteProfile\(this\)/.test(app)&&/RobotService\.forceSync\(this\)/.test(app),'Remote process/foreground must wake the existing sync engine');
must(/onActivityResumed\(Activity activity\) \{ wakeRemoteTruth\(false\); \}/.test(app),'foreground Remote sync wake missing');
must(/FOREGR(?:OUND)?_SYNC_DEBOUNCE_MS|FOREGROUND_SYNC_DEBOUNCE_MS/.test(app),'Remote foreground wake must be debounced');
must(/INSERT INTO devices\(device_id, node_code, mode/.test(server),'server must keep device-per-installation model');
must(/const deviceId = replacement \? replacement\.device_id : crypto\.randomUUID\(\)/.test(server),'new Remote must be able to receive its own device id');
must(/liveRobotOwner\(env, node, deviceId\)/.test(server),'single-Robot ownership guard must remain separate from Remote devices');

must(/commission_policy/.test(js),'commission strategy must read existing policy');
must(/Taux habituel \/ défaut/.test(js)&&/Taux personnalisés/.test(js)&&/Taux ponctuels récents/.test(js),'commission strategy sections missing');
must(/CHILD_OVERRIDE/.test(js)&&/PONCTUEL › PERSO › DÉFAUT/.test(js),'commission precedence/dashboard missing');
must(!/commission_set_default|commission_set_child/.test(js),'v299 strategy dashboard must never mutate commission policy');

must(/assistantAnswer/.test(js)&&/scoreIntents/.test(js),'wide Assistant engine missing');
for(const token of ['sync','commission','android','robot','access','pin','sim','balance','buy','sell','queue','identity','proof','network'])must(js.includes("id:'"+token+"'"),'Assistant intent missing: '+token);
must(/\^\(ia\|ai\|assistant/.test(js),'IA/AI query must route to Assistant instead of unrelated service buttons');
must(/w\.length>=4/.test(js),'natural-language search must route to Assistant');

must(!/\bconst\b|\blet\b|=>/.test(js),'v299 runtime must remain ES5-friendly for Android 6 WebView');
must(!/setInterval\s*\(/.test(js),'v299 must not add a second polling loop');
must(!/createCommand\s*\(|previewCommand\s*\(|create_command|preview_command/.test(js),'v299 must not create/preview finance');
must(!/executeRawUSSD|placeUssdCall|mercenary_sale/.test(js),'v299 must not bypass historical finance/USSD path');

console.log('BIR v2.9.9 reference stability: Android11, multi-Remote, commissions, Assistant and finance guards OK');
