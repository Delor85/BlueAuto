import fs from 'node:fs';

const read = p => fs.readFileSync(p,'utf8');
const gradle=read('app/build.gradle');
const local=read('app/src/main/java/com/profitloop/blueauto/LocalEventStore.java');
const balance=read('app/src/main/java/com/profitloop/blueauto/CertifiedBalanceStore.java');
const mirror=read('app/src/main/java/com/profitloop/blueauto/ServerQueueMirrorStore.java');
const access=read('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java');
const api=read('app/src/main/java/com/profitloop/blueauto/ApiClient.java');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const main=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const engine=read('app/src/main/assets/balance-engine-v280.js');
const ct=read('app/src/main/assets/control-tower-v271.js');
const pilot=read('app/src/main/assets/pilotage-v292.js');
const worker=read('cloudflare/src/index.js');
const migration=read('cloudflare/migrations/0010_coherence_recovery_and_reconciliation.sql');

function need(ok,msg){if(!ok)throw new Error(msg);}
need((gradle.includes('versionCode 58')&&gradle.includes('versionName "2.9.3"'))||(gradle.includes('versionCode 60')&&gradle.includes('versionName "2.9.5"')),'v2.9.3+ release identity required');
need(local.includes('LOCAL_COMMAND_QUEUED')&&local.includes('REMOTE_ORDER_RECEIVED')&&local.includes('LOCAL_PROGRESS'),'safe local events must become syncable');
need(balance.includes('TRUSTED_TELEPHONY')&&balance.includes('transaction_id')&&balance.includes('receipt_number'),'trusted local balance evidence must be durable and identifiable');
need(access.includes('CertifiedBalanceStore.observeTrusted'),'accessibility result must promote trusted Blue proof locally');
need(main.includes('getCertifiedBalance')&&main.includes('getUnifiedQueueSnapshot'),'WebView must see native truth for balance and queue');
need(api.includes('queueSnapshot()')&&api.includes('recoverLease('),'client must support queue reconciliation and safe lease recovery');
need(robot.includes('ServerQueueMirrorStore.observeBusy')&&robot.includes('recoverLease'),'Robot must reconcile server-active commands after local loss');
need(robot.includes('ACCESSIBILITY_RECONNECT_GRACE_MS'),'temporarily disconnected accessibility must have a safe reconnect grace');
need(engine.includes('sameEvidenceMovement')&&engine.includes('last_transaction_id'),'balance engine must not double-apply movement already included in certified proof');
need(ct.includes('operator_transaction_id')&&ct.includes('last_transaction_id'),'journal/proof must carry operator transaction identity');
need(pilot.includes('distribution_command_center')&&pilot.includes('anomal'),'pilotage must surface the distribution command center and anomaly signals');
need(worker.includes("const API_VERSION = '2.9.3-cloudflare'")||worker.includes("const API_VERSION = '2.9.5-cloudflare'"),'Worker v2.9.3+ required');
need(worker.includes("case 'queue_snapshot'")&&worker.includes("case 'recover_lease'")&&worker.includes("case 'distribution_command_center'")&&worker.includes("case 'reconciliation_center'"),'v2.9.3 server routes missing');
need(worker.includes('leased_by_device_id'),'lease ownership fence required');
need(worker.includes('PROBABLE_OPERATOR_INCIDENT')&&worker.includes('stockout'),'outage correlation and stockout prediction required');
need(migration.includes('inbound_commission_bps')&&migration.includes('duplicate_request_audit')&&migration.includes('reconciliation_rows'),'accounting/reconciliation schema missing');
need(!/sms[_ -]?fallback/i.test(worker+robot),'no SMS fallback may be introduced');
need(!/financial_command_over_relay\s*=\s*true/i.test(worker+robot),'Relay must not carry financial commands');
console.log('B.I.R. v2.9.3 coherence/recovery contract OK');
