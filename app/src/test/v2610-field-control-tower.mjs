import fs from 'node:fs';

const root='app/src/main/';
const html=fs.readFileSync(root+'assets/index.html','utf8');
const ui=fs.readFileSync(root+'assets/app.js','utf8');
const css=fs.readFileSync(root+'assets/style.css','utf8');
const activity=fs.readFileSync(root+'java/com/profitloop/blueauto/MainActivity.java','utf8');
const accessibility=fs.readFileSync(root+'java/com/profitloop/blueauto/BlueAccessibilityService.java','utf8');
const sim=fs.readFileSync(root+'java/com/profitloop/blueauto/SimIdentityManager.java','utf8');
const pending=fs.readFileSync(root+'java/com/profitloop/blueauto/PendingCommandStore.java','utf8');
const robot=fs.readFileSync(root+'java/com/profitloop/blueauto/RobotService.java','utf8');
const api=fs.readFileSync(root+'java/com/profitloop/blueauto/ApiClient.java','utf8');
const worker=fs.readFileSync('cloudflare/src/index.js','utf8');
const gradle=fs.readFileSync('app/build.gradle','utf8');

function need(haystack, needle, message){if(!haystack.includes(needle)) throw new Error(message+' — missing: '+needle);}

need(gradle,'versionCode 50','versionCode v2.6.10');
need(gradle,'versionName "2.6.10"','versionName v2.6.10');
need(worker,"const API_VERSION = '2.6.10-cloudflare';",'worker version');
need(api,'payload.put("app_version", "2.6.10")','Android heartbeat version');

const balanceAt=html.indexOf('id="birCamtelBalance"');
const reportsAt=html.indexOf('data-tab-panel="reports"');
if(balanceAt<0||reportsAt<0||balanceAt>reportsAt) throw new Error('top balance is not always visible before tab content');
for(const id of ['robotState','fatalNotice','birRobotHealth','birSyncState','commissionControlCard','financialConfirmModal','birInfoResult']) need(html,'id="'+id+'"','control tower '+id);
need(html,'data-native-action="toggle-robot"','clickable robot state');
need(html,'data-native-action="synchronize"','manual synchronization');
need(css,'.form-editing .module-tabs{display:flex!important}','Android 6 dock stays visible while editing');
need(css,'.bir-main-balance strong{font-size:38px','large balance typography');

for(const contract of [
  "childLabel.textContent='Code du DSM'", "child.placeholder='Ex. DSM1'",
  "childLabel.textContent='Code du PoS'", "child.placeholder='Ex. POS1'",
  "requestSupplyTitle').textContent='Demander à mon DAE'",
  "requestSupplyTitle').textContent='Demander à mon DSM'"
]) need(ui,contract,'role-specific hierarchy fields');
need(ui,"Vous êtes le supérieur qui approvisionne cet enfant",'parent-owned commission confirmation');
need(ui,"Ce taux est fixé par votre supérieur direct",'child purchase commission complaint wording');
need(ui,'pendingPreview.commission_rate_bps','one-time transaction commission');
need(ui,"op==='BALANCE_CHILD'",'visible child-balance result');
need(ui,'surfaceCommandResult','readable Remote information feedback');

const manage=activity.slice(activity.indexOf('private void showManagementCenter()'),activity.indexOf('private TextView managementSectionTitle'));
if(manage.includes('VÉRIFIER / LIER SIM')) throw new Error('SIM verification is still duplicated in overloaded native Gérer');
if(manage.includes('DÉMARRER ROBOT')||manage.includes('ARRÊTER ROBOT')) throw new Error('Robot start/stop is still duplicated in overloaded native Gérer');
need(activity,'public void synchronizeNow()','native sync bridge');
need(accessibility,'static boolean isConnected()','live accessibility connectivity');
need(accessibility,'RobotService.startEnabled(this)','Robot wake on accessibility service connection');

const iccid=sim.indexOf('String iccId = safeIccId(info);');
const phoneFallback=sim.indexOf('} else if (!observed.isEmpty())',iccid);
if(iccid<0||phoneFallback<iccid) throw new Error('ICCID is not the primary stable SIM fingerprint');
need(sim,'migrer une seule fois vers l’ICCID stable','safe legacy binding migration');
need(pending,'Math.min(30_000L, 5_000L * multiplier)','bounded final report retry');
need(pending,'forceFinalReportRetry','manual result sync retry');
need(robot,'wakeRequested.set(true)','wake coalescing');
need(robot,'ACTION_SYNC','explicit Robot synchronization');
need(robot,'reprise automatique','logical Robot persistence');
const unsafe=robot.slice(robot.indexOf('private void disableUnsafeRobot'),robot.indexOf('private void releaseUnexecutedLease'));
if(unsafe.includes('setRobotEnabled')) throw new Error('transient readiness still permanently switches Robot off');

need(worker,"commissionSource = 'ONE_TIME_PARENT_OVERRIDE'",'parent transaction rate override');
need(worker,"commission_decider: requestType === 'SUPPLY_CHILD' ? 'REQUESTER_PARENT'",'commission decider semantics');
need(worker,'officialStoredIdentity','official DAE/DSM/POS display identity');
need(worker,'viewer_identity: viewerIdentity','Remote official viewer identity');

console.log('v2.6.10 field control tower: persistent Robot, sync, hierarchy, commissions, readable evidence and reference UX OK');
