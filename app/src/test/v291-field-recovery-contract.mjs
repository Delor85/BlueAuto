import fs from 'node:fs';
function read(path){return fs.readFileSync(path,'utf8');}
function must(ok,msg){if(!ok)throw new Error(msg);}
const gradle=read('app/build.gradle');
const main=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const api=read('app/src/main/java/com/profitloop/blueauto/ApiClient.java');
const app=read('app/src/main/assets/app.js');
const balance=read('app/src/main/assets/balance-engine-v280.js');
const field=read('app/src/main/assets/field-recovery-v291.js');
const index=read('app/src/main/assets/index.html');
const manifest=read('app/src/main/AndroidManifest.xml');

must((gradle.includes('versionCode 56')||gradle.includes('versionCode 58')||gradle.includes('versionCode 60'))&&(gradle.includes('versionName "2.9.1"')||gradle.includes('versionName "2.9.3"')||gradle.includes('versionName "2.9.5"')),'v2.9.1+ identity missing');
must(api.includes('payload.put("app_version", "2.9.1");')||api.includes('payload.put("app_version", "2.9.3");')||api.includes('payload.put("app_version", "2.9.5");'),'v2.9.1+ heartbeat telemetry missing');
must(main.includes('final boolean commissionPrompt')&&main.includes('final boolean supportPrompt'),'JS prompt routing not contextual');
must(main.includes('TYPE_TEXT_FLAG_MULTI_LINE')&&main.includes('"Secours / SAV"')&&main.includes('"ENVOYER"'),'Secours must be text, not commission numeric UI');
must(main.includes('"Taux de commission"')&&main.includes('TYPE_NUMBER_FLAG_DECIMAL'),'commission prompt compatibility lost');
must(main.includes('public void kickSynchronization()'),'silent synchronization wake bridge missing');
must(main.includes('AppConfig.profileId(MainActivity.this), 6_000L);'),'Remote dashboard cache must be short-lived');
must(robot.includes('REMOTE_SNAPSHOT_MS = 5_000L')&&robot.includes('REMOTE_HEARTBEAT_MS = 20_000L'),'fast Remote observer missing');
must(robot.includes('lastRemoteSnapshotByProfile.clear();'),'force sync must invalidate Remote snapshot schedule');
must(robot.includes('OfflineSyncManager.syncSome(this, 25);')&&robot.includes('retryDueFinalReports(8);'),'force sync must drain safe outbox/final reports');
const force=robot.slice(robot.indexOf('if (ACTION_FORCE_SYNC.equals(action))'),robot.indexOf('if (ACTION_CONTROL_POLL.equals(action))'));
must(force&&!/createCommand|placeUssdCall|previewCommand|checkPurchaseCapacity/.test(force),'Auto-Reveil must never simulate a financial/USSD command');
must(app.includes('now-dashboardLoadedAt<5000'),'foreground dashboard freshness gate must accept rapid explicit refresh');
must(app.includes('scheduleDashboardPoll();},60000);'),'normal dashboard polling must remain economical at 60s');
must(field.includes('staleAfterMs=60000')&&field.includes('pulseCooldownMs=45000')&&field.includes('setInterval(function()')&&field.includes('},5000);'),'recovery must be event-driven while keeping server polling economical');
must(app.includes('window.AndroidBridge.kickSynchronization()'),'command lifecycle must wake synchronization');
must(balance.includes('commission>0?total:amount'),'predictive supply balance must account for commission debit');
must(balance.includes('Valeur masquée • nouvelle preuve Blue exacte requise'),'uncertain balance must be hidden, not presented as real');
must(field.includes('AUTO-RÉVEIL B.I.R.')&&field.includes('TROUVER UN SERVICE'),'field recovery/search UI missing');
must(field.includes('silentPulse')&&!field.includes('SEND_SMS'),'self-healing must stay non-SMS');
must(index.includes('field-recovery-v291.css')&&index.includes('field-recovery-v291.js'),'v2.9.1 assets not wired');
must(!manifest.includes('android.permission.SEND_SMS'),'SMS fallback permission forbidden');
must(main.includes('new String[]{"REMOTE", "ROBOT"}')||main.includes('spinner(new String[]{"REMOTE", "ROBOT"})'),'only REMOTE/ROBOT must remain selectable');
console.log('BIR v2.9.1 field recovery: adaptive sync, balance, Secours, search and safety contract OK');
