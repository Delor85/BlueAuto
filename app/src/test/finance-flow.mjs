import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const elements = new Map();
const ids = [
  'nativeBadge', 'browserNotice', 'nodeCode', 'nodeMeta', 'robotState', 'fatalNotice',
  'actionNotice', 'roleNotice', 'requestSupplyCard', 'supplyChildCard', 'retailCard',
  'requestSupplyAmount', 'childNode', 'childAmount', 'retailPhone', 'retailAmount',
  'refreshCommands', 'commandList', 'toast', 'serverHealthStatus', 'metricCommandCount',
  'metricSuccessCount', 'metricPendingCount', 'metricLastDuration', 'metricSuccessRate',
  'metricFinanceCount', 'reportActivityTitle', 'reportActivityDetail', 'fleetNodeStatus',
  'fleetSimStatus', 'configRobotStatus', 'supportStatus', 'ownBalance', 'balanceFreshness',
  'networkList', 'fleetNetworkTitle', 'fleetNetworkList', 'transactionId',
  'childBalanceCard', 'balanceChildNode', 'childAdminCard', 'adminChildNode'
];

function element(id = '') {
  return {
    id, className: '', textContent: '', innerHTML: '', value: '', disabled: false,
    tagName: id.includes('Amount') || id.includes('Phone') ? 'INPUT' : 'DIV',
    getAttribute(name) {
      if (name === 'data-action') return this.action || '';
      if (name === 'data-tab') return this.tab || '';
      if (name === 'data-tab-panel') return this.panel || '';
      return '';
    }
  };
}

for (const id of ids) elements.set(id, element(id));
const actions = ['request-supply', 'supply-child', 'retail-sale', 'test-number', 'check-balance',
  'last-transactions', 'transaction-details', 'child-balance', 'init-child-pin-reset',
  'suspend-child', 'reactivate-child', 'freeze-child', 'reactivate-frozen-child', 'freeze-self']
  .map(action => Object.assign(element(action), {action, tagName: 'BUTTON'}));
const moduleNames = ['reports', 'flux', 'fleet', 'config', 'support'];
const tabButtons = moduleNames.map(tab => Object.assign(element(tab), {tab, tagName: 'BUTTON'}));
const tabPanels = moduleNames.map(panel => Object.assign(element(panel), {panel}));
const nativeActions = ['accounts', 'verify-sim', 'permissions', 'pin', 'manage', 'start-robot',
  'server-health', 'go-test', 'refresh-dashboard'].map(action => Object.assign(element(action), {
    nativeAction: action, tagName: 'BUTTON'
  }));
const bridgeCalls = [];
let confirmResult = true;
let confirmationText = '';

const document = {
  readyState: 'complete', activeElement: null, body: {className: ''},
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element(id));
    return elements.get(id);
  },
  querySelectorAll(selector) {
    if (selector === 'button[data-action]') return actions;
    if (selector === 'button[data-tab]') return tabButtons;
    if (selector === 'button[data-tab="flux"]') return tabButtons.filter(item => item.tab === 'flux');
    if (selector === 'button[data-native-action]') return nativeActions;
    if (selector === '[data-tab-panel]') return tabPanels;
    return [];
  },
  querySelector() { return null; },
  addEventListener() {}
};

const window = {
  AndroidBridge: {
    getConfiguration() {
      return JSON.stringify({
        profile_id: 'pos-test', node_code: 'POS1_DSM1_OU1', role: 'POS', mode: 'REMOTE',
        sim_slot: 0, robot_enabled: false, pin_blocked: false, pin_configured: true,
        accessibility_enabled: true, sim_verified: true
      });
    },
    previewCommand(...args) { bridgeCalls.push(['preview', ...args]); },
    createCommand(...args) { bridgeCalls.push(['create', ...args]); },
    getCommandStatus() {}, cancelCommand() {}, setFormEditing() {}, openAccounts() {},
    verifySim() {}, prepareRobotPermissions() {}, openPinSettings() {}, openManagement() {},
    startRobot() {}, checkServerHealth() {}, loadDashboard() {},
    checkPurchaseCapacity(...args) { bridgeCalls.push(['capacity', ...args]); },
    getPurchaseCapacityStatus(...args) { bridgeCalls.push(['capacity-status', ...args]); }
  },
  confirm(message) { confirmationText = message; return confirmResult; },
  setTimeout() {}, setInterval() {}, scrollTo() {}
};
const localStorage = {
  values: new Map(),
  getItem(key) { return this.values.get(key) || null; },
  setItem(key, value) { this.values.set(key, value); }
};

const script = await readFile(new URL('../main/assets/app.js', import.meta.url), 'utf8');
vm.runInNewContext(script, {window, document, localStorage, Date, Math, JSON, String, Object, isNaN});

assert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);
assert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');
assert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');
tabButtons.find(item => item.tab === 'flux').onclick();
assert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);
assert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');
assert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen hidden');
assert.equal(localStorage.getItem('bir_active_module_v269'), 'flux');

elements.get('retailPhone').value = '620550255';
elements.get('retailAmount').value = '1';
actions.find(item => item.action === 'retail-sale').onclick();
assert.equal(bridgeCalls.length, 1);
assert.equal(bridgeCalls[0][0], 'preview');
assert.equal(bridgeCalls[0][1], 'RETAIL_SALE');
assert.equal(bridgeCalls[0][3], '620550255');
assert.equal(actions.every(item => item.disabled), true);

window.BlueMagicNative.onCommandPreview({preview: {
  operation: 'RETAIL_TRANSFER', executor_node_code: 'POS1_DSM1_OU1',
  executor_phone: '699000003', target_phone: '620550255', amount: 1,
  confirmation_fingerprint: 'f'.repeat(64), robot_ready: true, robot_status: 'ONLINE'
}});
assert.match(confirmationText, /FOURNISSEUR : POS1_DSM1_OU1 — 699000003/);
assert.match(confirmationText, /BÉNÉFICIAIRE : CLIENT — 620550255/);
assert.match(confirmationText, /MONTANT : 1 FCFA/);
assert.equal(bridgeCalls.length, 2);
assert.deepEqual(bridgeCalls[1].slice(0, 5), ['create', 'RETAIL_SALE', '', '620550255', '1']);
assert.equal(bridgeCalls[1][6], 'f'.repeat(64));
assert.equal(bridgeCalls[1][7], '');
window.BlueMagicNative.onCommandCreated({command: {public_id: 'command-123456789', state: 'PENDING'}});
assert.equal(actions.every(item => !item.disabled), true);

confirmResult = false;
elements.get('retailPhone').value = '620550255';
elements.get('retailAmount').value = '1';
const callsBeforeCancel = bridgeCalls.length;
actions.find(item => item.action === 'retail-sale').onclick();
window.BlueMagicNative.onCommandPreview({preview: {
  operation: 'RETAIL_TRANSFER', executor_node_code: 'POS1_DSM1_OU1',
  executor_phone: '699000003', target_phone: '620550255', amount: 1,
  confirmation_fingerprint: 'e'.repeat(64)
}});
assert.equal(bridgeCalls.length, callsBeforeCancel + 1);
assert.equal(actions.every(item => !item.disabled), true);

confirmResult = true;
const previewsBeforeTest = bridgeCalls.filter(call => call[0] === 'preview').length;
actions.find(item => item.action === 'test-number').onclick();
assert.equal(bridgeCalls.at(-1)[0], 'create');
assert.equal(bridgeCalls.at(-1)[1], 'TEST_NUMBER');
assert.equal(bridgeCalls.at(-1)[6], '');
assert.equal(bridgeCalls.filter(call => call[0] === 'preview').length, previewsBeforeTest);
window.BlueMagicNative.onCommandCreated({command: {public_id: 'test-number-command-01', state: 'PENDING', operation: 'TEST_NUMBER'}});
assert.equal(actions.every(item => !item.disabled), true);

elements.get('requestSupplyAmount').value = '700';
actions.find(item => item.action === 'request-supply').onclick();
assert.equal(bridgeCalls.at(-1)[0], 'capacity');
window.BlueMagicNative.onPurchaseCapacity({capacity: {
  capacity_check_id: 'capacity-insufficient', state: 'INSUFFICIENT',
  supplier_node_code: 'DSM1', requested_amount: 700, available_balance: 650
}});
assert.match(elements.get('actionNotice').textContent, /650 FCFA/);
assert.match(elements.get('actionNotice').textContent, /autre DSM\/PoS/);
assert.equal(actions.every(item => !item.disabled), true);

elements.get('requestSupplyAmount').value = '500';
actions.find(item => item.action === 'request-supply').onclick();
window.BlueMagicNative.onPurchaseCapacity({capacity: {
  capacity_check_id: 'capacity-available-123456', state: 'AVAILABLE',
  supplier_node_code: 'DSM1', requested_amount: 500, available_balance: 650
}});
assert.equal(bridgeCalls.at(-1)[0], 'preview');
assert.equal(bridgeCalls.at(-1)[6], 'capacity-available-123456');
window.BlueMagicNative.onCommandPreview({preview: {
  operation: 'DISTRIBUTION_TRANSFER', executor_node_code: 'DSM1',
  executor_phone: '699000002', target_node_code: 'POS1_DSM1_OU1',
  target_phone: '699000003', amount: 500, confirmation_fingerprint: 'a'.repeat(64)
}});
assert.equal(bridgeCalls.at(-1)[0], 'create');
assert.equal(bridgeCalls.at(-1)[7], 'capacity-available-123456');
window.BlueMagicNative.onCommandCreated({command: {public_id: 'capacity-command-123456', state: 'PENDING'}});

elements.get('adminChildNode').value = 'POS5';
actions.find(item => item.action === 'freeze-child').onclick();
assert.deepEqual(bridgeCalls.at(-1).slice(0, 3), ['preview', 'FREEZE_CHILD', 'POS5']);
window.BlueMagicNative.onCommandPreview({preview: {
  operation: 'FREEZE_CHILD', operation_label: 'Geler la SIM enfant', dangerous: true,
  executor_node_code: 'DSM1', executor_phone: '699000002',
  target_node_code: 'POS5_DSM1', target_phone: '699000003',
  confirmation_fingerprint: 'b'.repeat(64)
}});
assert.match(confirmationText, /COMMANDE (?:CAMTEL|BLUE) SENSIBLE/);
assert.match(confirmationText, /Geler la SIM enfant/);
assert.equal(bridgeCalls.at(-1)[0], 'create');
assert.equal(bridgeCalls.at(-1)[1], 'FREEZE_CHILD');
window.BlueMagicNative.onCommandCreated({command: {public_id: 'admin-command-1234567', state: 'PENDING'}});

const css = await readFile(new URL('../main/assets/style.css', import.meta.url), 'utf8');
const literalGradient = 'background:linear-gradient(105deg,#2670ff,#875cff)';
const variableGradient = 'background:linear-gradient(105deg,var(--blue),var(--violet))';
assert.ok(css.indexOf(literalGradient) >= 0);
assert.ok(css.indexOf(literalGradient) < css.indexOf(variableGradient));
assert.match(css, /\.transaction-action\{background:linear-gradient\(105deg,#087eae,#1668df\)/);

const activity = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/MainActivity.java', import.meta.url), 'utf8');
assert.match(activity, /setWebChromeClient\(new WebChromeClient\(\)/);
assert.match(activity, /boolean onJsConfirm\(/);
assert.match(activity, /new ApiClient\(this\)\.heartbeat\(true\)/);
assert.doesNotMatch(activity.slice(activity.indexOf('private boolean startRobotSafely()'),
  activity.indexOf('private void confirmAndBindCurrentSim()')), /verifyCallRoute/);
assert.match(activity, /Entrer dans le hall Robot/);
assert.match(activity, /changeActiveMode\("ROBOT"\)/);
assert.match(activity, /replaceRobotWithVerifiedSim/);
assert.match(activity, /activateRobot\(current, AppConfig\.simSlot\(this\), true\)/);
assert.match(activity, /deleteActiveProfileSafely/);

const accessibility = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/BlueAccessibilityService.java', import.meta.url), 'utf8');
assert.match(accessibility, /ACTION_SET_TEXT/);
assert.match(accessibility, /ACTION_PASTE/);
assert.match(accessibility, /currentAttempt == 0[\s\S]*pastePin/);
assert.doesNotMatch(accessibility, /setText\(refreshed\.field, pin\)[\s\S]{0,120}pastePin\(refreshed\.field, pin\)/);
assert.match(accessibility, /finalFallback/);
assert.match(accessibility, /compact\.matches\("\[•●∙\*×\]\{4\}"\)/);
assert.match(accessibility, /trustedUssdResult/);
assert.match(accessibility, /getDefaultDialerPackage/);
assert.match(accessibility, /clickTrustedTelephonyFirst/);
assert.doesNotMatch(accessibility, /TYPE_ACCESSIBILITY_OVERLAY/);
assert.doesNotMatch(accessibility, /PIN protégé/);

const service = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/RobotService.java', import.meta.url), 'utf8');
assert.match(service, /SDK_INT >= 34[\s\S]*FOREGROUND_SERVICE_TYPE_SPECIAL_USE/);
assert.match(service, /SDK_INT >= 29[\s\S]*FOREGROUND_SERVICE_TYPE_DATA_SYNC/);
assert.match(service, /catch \(RuntimeException primaryFailure\)[\s\S]*FOREGROUND_SERVICE_TYPE_DATA_SYNC/);
const readiness = service.slice(service.indexOf('private Readiness checkReadiness('),
  service.indexOf('private void disableUnsafeRobot('));
assert.doesNotMatch(readiness, /verifyCallRoute/);
assert.match(service, /DeviceLockState\.blocksUssd\(this\)/);
assert.ok(service.indexOf('DeviceLockState.blocksUssd(this)')
  < service.indexOf('SimCallManager.placeUssdCall(this, ussd, profileId)'));
assert.doesNotMatch(service, /prepareSystemUssdSurface/);
assert.doesNotMatch(service, /SYSTEM_USSD_SCREEN_WAKE_MS/);
assert.doesNotMatch(service, /InsecureKeyguardDismissActivity/);
assert.doesNotMatch(service, /SCREEN_BRIGHT_WAKE_LOCK|ACQUIRE_CAUSES_WAKEUP|disableKeyguard/);

const manifest = await readFile(new URL('../main/AndroidManifest.xml', import.meta.url), 'utf8');
assert.match(manifest, /foregroundServiceType="dataSync\|specialUse"/);

const gradleConfig = await readFile(new URL('../../build.gradle', import.meta.url), 'utf8');
assert.match(gradleConfig, /minSdk 23/);
assert.match(gradleConfig, /versionCode (?:51|52|53|54|55|58|60)/);
assert.match(gradleConfig, /versionName "(?:2\.7\.(?:0|1)|2\.8\.(?:0|1)|2\.9\.0|2\.9\.3|2\.9\.5)"/);
assert.match(gradleConfig, /release \{[\s\S]*signingConfig signingConfigs\.pilotDebug/);

const apiClient = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/ApiClient.java', import.meta.url), 'utf8');
assert.match(apiClient, /replace_device_id/);
assert.match(apiClient, /repair_sim_fingerprint/);
assert.match(apiClient, /replace_verified_same_sim_robot/);

const appConfig = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/AppConfig.java', import.meta.url), 'utf8');
assert.match(appConfig, /serverDeviceId/);

const html = await readFile(new URL('../main/assets/index.html', import.meta.url), 'utf8');
for (const moduleName of moduleNames) {
  assert.match(html, new RegExp('data-tab="' + moduleName + '"'));
  assert.match(html, new RegExp('data-tab-panel="' + moduleName + '"'));
}
assert.match(html, /PILOTAGE & RAPPORTS/);
assert.match(html, /ACTIVITÉ & SAV/);
assert.match(html, /DIAGNOSTIC RAPIDE/);
assert.match(css, /\.module-tabs\{position:fixed/);
assert.match(css, /\.module-tab-primary/);
assert.ok(activity.indexOf('MODIFIER LE PIN CAMTEL') < activity.indexOf('1. AUTORISATIONS'));
assert.match(activity, /setScrollbarFadingEnabled\(false\)/);
const unlockActivity = await readFile(new URL(
  '../main/java/com/profitloop/blueauto/SimpleKeyguardAssistActivity.java', import.meta.url), 'utf8');
assert.match(unlockActivity, /requestDismissKeyguard/);
assert.match(unlockActivity, /DeviceLockState\.isSecurelyLocked/);
assert.match(unlockActivity, /finishQuietly/);
assert.doesNotMatch(unlockActivity, /disableKeyguard/);
assert.match(activity, /openPinSettings/);

console.log('Android UI/runtime: verrou/PIN, dock actif, précontrôle de solde, confirmation finance, administration sensible et TEST_NUMBER OK');


// v2.6.7 complete-platform guards
const platformJs = readFileSync(new URL('../main/assets/platform-v267.js', import.meta.url), 'utf8');
assert.match(platformJs, /platform_snapshot/);
assert.match(platformJs, /operator_insights/);
assert.match(platformJs, /shadow_enroll/);
assert.match(platformJs, /mercenary_save/);
const messageParser = readFileSync(new URL('../main/java/com/profitloop/blueauto/BlueMessageParser.java', import.meta.url), 'utf8');
assert.match(messageParser, /Request is processed/);
assert.match(messageParser, /Current/);

const uiRuntime = readFileSync(new URL('../main/assets/app.js', import.meta.url), 'utf8');
assert.match(uiRuntime, /scheduleCommandPoll/);
assert.match(uiRuntime, /scheduleDashboardPoll/);
assert.match(uiRuntime, /60000/);
assert.match(uiRuntime, /visibilityState/);
assert.doesNotMatch(uiRuntime, /setInterval\(refresh,15000\)/);
assert.match(uiRuntime, /balance_reusable/);
assert.match(uiRuntime, /partageable sans nouvel USSD/);
assert.match(messageParser, /top-up service/);
const smsReceiver = readFileSync(new URL('../main/java/com/profitloop/blueauto/SmsReceiver.java', import.meta.url), 'utf8');
assert.match(smsReceiver, /targetOptional/);
assert.doesNotMatch(smsReceiver, /RobotService\.requestAudit\(context, profileId\)/);


const robotServiceV267 = readFileSync(new URL('../main/java/com/profitloop/blueauto/RobotService.java', import.meta.url), 'utf8');
const apiClientV267 = readFileSync(new URL('../main/java/com/profitloop/blueauto/ApiClient.java', import.meta.url), 'utf8');
assert.match(robotServiceV267, /maybeQueueNightlyNetworkAudit/);
assert.match(robotServiceV267, /startMinute = 2 \* 60/);
assert.match(robotServiceV267, /startMinute = 3 \* 60/);
assert.match(robotServiceV267, /startMinute = 4 \* 60/);
assert.match(robotServiceV267, /deterministicNightSlot/);
assert.match(robotServiceV267, /5 \* 60 \+ 15/);
assert.match(robotServiceV267, /result\.optBoolean\("complete", false\)/);
assert.match(robotServiceV267, /5 \* 60_000L/);
assert.match(apiClientV267, /network_balance_audit/);
assert.match(platformJs, /v267-audit/);
assert.match(platformJs, /network_balance_audit/);

console.log('Blue Magic v2.6.7 platform extension: UI/modules/message parser wired');
