import fs from 'node:fs';

function read(p){return fs.readFileSync(p,'utf8');}
function must(v,m){if(!v)throw new Error(m);}
const js=read('app/src/main/assets/field-runtime-v2991.js');
const css=read('app/src/main/assets/field-runtime-v2991.css');
const loader=read('app/src/main/assets/intelligence-v297.js');
const gradle=read('app/build.gradle');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const api=read('app/src/main/java/com/profitloop/blueauto/ApiClient.java');
const server=read('cloudflare/src/index.js');

must(/versionCode 65/.test(gradle)&&/versionName "2\.9\.9\.1"/.test(gradle),'v2.9.9.1/vc65 identity missing');
must(/field-runtime-v2991\.css/.test(loader)&&/field-runtime-v2991\.js/.test(loader),'v2991 runtime must load after v299');

must(/bir-v2991-buy-card/.test(js)&&/insertBefore\(card,tx\.nextSibling\)/.test(js),'purchase card must be separated from yellow transaction shell');
must(/bir-v2991-buy-card/.test(css)&&/#168c50|#0d6f40/.test(css),'purchase card must be green');

must(/Android\\s\+11/.test(js)&&/bir-v2991-api30/.test(js),'Android 11/API30 runtime guard missing');
must(/body\.bir-v2991-api30 \*/.test(css)&&/backdrop-filter:none!important/.test(css),'API30 compositor simplification missing');
must(/markPaint/.test(js),'API30 paint scheduler guard missing');
must(!/\.offsetHeight\b/.test(js),'API30 guard must never force a synchronous full-layout read');
must(/body\.bir-v2991-api30 \.module-tabs\{position:relative!important/.test(css),'API30 bottom navigation must not stay on a sticky compositor layer');

must(/REMOTE_SNAPSHOT_MS = 10_000L/.test(robot),'historical Remote 10 s cadence must remain unchanged');
must(/kickSynchronization/.test(js)&&/directRead\('1\/3'/.test(js)&&/directRead\('2\/3'/.test(js)&&/directRead\('3\/3'/.test(js),'foreground Remote convergence burst missing');
must(/api30\(\)&&tag==='2\/3'/.test(js),'Android 11 convergence must avoid a redundant middle dashboard paint');
must(!/setInterval\s*\(/.test(js),'v2991 must not add another permanent polling loop');

must(/transaction_ledger/.test(js)&&/oneShotFromLedger/.test(js),'commission one-shot truth must prefer account server ledger');
must(/commission_policy/.test(js)&&/normalizePolicy/.test(js)&&/persistentRateFor/.test(js),'punctual rates must be compared with current server policy');
must(/commission_rate_bps/.test(js)&&/ÉCART AU TAUX PERSISTANT/.test(js),'ledger commission rate must support punctual inference');
must(/transaction_ledger/.test(api)&&/commission_policy/.test(api),'native bridge must allow ledger and commission policy');
must(/case 'transaction_ledger'/.test(server)&&/case 'commission_policy'/.test(server),'existing server must expose ledger and policy without v2991 Cloudflare change');
must(/commission_rate_bps/.test(server)&&/effective_rate_bps/.test(server),'server source must expose transactional and persistent commission rates');

must(/scoreTopics/.test(js)&&/localWideAnswer/.test(js)&&/bindAssistantSearch/.test(js),'Assistant must provide broad free-text intent routing and IA search interception');
must(/assistantLike/.test(js)&&/v291ServiceQuery/.test(js)&&/Assistant B\.I\.R\./.test(js),'global search must route IA/questions to Assistant instead of unrelated buttons');
must(!/ops_assist/.test(js),'free-text Assistant must never misuse ops_assist WAKE_SYNC as a conversational backend');
must(/primeEvidence/.test(js)&&/loadDashboard/.test(js)&&/refreshQueueSnapshot/.test(js),'Assistant may refresh only relevant read-only evidence');

must(!/createCommand\s*\(|previewCommand\s*\(|create_command|preview_command/.test(js),'v2991 runtime must not create/preview finance');
must(!/executeRawUSSD|placeUssdCall|mercenary_sale/.test(js),'v2991 runtime must not bypass historical finance/USSD path');
must(!/\bconst\b|\blet\b|=>/.test(js),'v2991 runtime must stay ES5-friendly for Android 6 WebView');

console.log('BIR v2.9.9.1 field runtime: purchase color, multi-Remote convergence, server-backed commission truth, Android11 no-reflow and side-effect-free Assistant guards OK');
