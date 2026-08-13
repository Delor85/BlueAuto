import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const elements = new Map();
const ids = [
  'nativeBadge', 'browserNotice', 'nodeCode', 'nodeMeta', 'robotState', 'fatalNotice',
  'actionNotice', 'roleNotice', 'requestSupplyCard', 'supplyChildCard', 'retailCard',
  'requestSupplyAmount', 'childNode', 'childAmount', 'retailPhone', 'retailAmount',
  'refreshCommands', 'commandList', 'toast', 'serverHealthStatus', 'metricCommandCount',
  'metricSuccessCount', 'metricPendingCount', 'metricLastDuration', 'metricSuccessRate',
  'metricFinanceCount', 'reportActivityTitle', 'reportActivityDetail', 'fleetNodeStatus',
  'fleetSimStatus', 'configRobotStatus', 'supportStatus'
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
const actions = ['request-supply', 'supply-child', 'retail-sale', 'test-number']
  .map(action => Object.assign(element(action), {action, tagName: 'BUTTON'}));
const moduleNames = ['reports', 'flux', 'fleet', 'config', 'support'];
const tabButtons = moduleNames.map(tab => Object.assign(element(tab), {tab, tagName: 'BUTTON'}));
const tabPanels = moduleNames.map(panel => Object.assign(element(panel), {panel}));
const nativeActions = ['accounts', 'verify-sim', 'permissions', 'pin', 'manage', 'start-robot',
  'server-health', 'go-test'].map(action => Object.assign(element(action), {
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
    startRobot() {}, checkServerHealth() {}
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

assert.match(tabButtons.find(item => item.tab === 'flux').className, /active/);
assert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen');
tabButtons.find(item => item.tab === 'reports').onclick();
assert.match(tabButtons.find(item => item.tab === 'reports').className, /active/);
assert.equal(tabPanels.find(item => item.panel === 'reports').className, 'module-screen');
assert.equal(tabPanels.find(item => item.panel === 'flux').className, 'module-screen hidden');
assert.equal(localStorage.getItem('blue_magic_active_module'), 'reports');

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
window.BlueMagicNative.onCommandCreated({command: {public_id: 'command-123456789', state: 'PENDING'}});
assert.equal(actions.every(item => !item.disabled), true);

confirmResult = false;
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
assert.match(accessibility, /fieldContainsPin\(target\.field, pin\) \|\| actionAccepted/);
assert.doesNotMatch(accessibility, /actionAccepted && attempt >= MAX_PIN_WRITE_ATTEMPTS/);
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
assert.ok(service.indexOf('prepareSystemUssdSurface(needsWakeSettle)')
  < service.indexOf('SimCallManager.placeUssdCall(this, ussd, profileId)'));
assert.match(service, /SYSTEM_USSD_SCREEN_WAKE_MS = 45_000L/);
assert.doesNotMatch(service, /"PIN_SUBMITTED"\.equals\(state\)\) releaseCommandScreenWakeLock/);

const manifest = await readFile(new URL('../main/AndroidManifest.xml', import.meta.url), 'utf8');
assert.match(manifest, /foregroundServiceType="dataSync\|specialUse"/);

const gradleConfig = await readFile(new URL('../../build.gradle', import.meta.url), 'utf8');
assert.match(gradleConfig, /minSdk 23/);
assert.match(gradleConfig, /versionCode 46/);
assert.match(gradleConfig, /versionName "2\.6\.6"/);

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
assert.match(html, /ONGLET 1 — GRAPHES & RAPPORTS/);
assert.match(html, /ONGLET 5 — SAV & DIAGNOSTIC/);
assert.match(css, /\.module-tabs\{position:fixed/);
assert.match(css, /\.module-tab-primary/);
assert.ok(activity.indexOf('MODIFIER LE PIN CAMTEL') < activity.indexOf('1. AUTORISATIONS'));
assert.match(activity, /setScrollbarFadingEnabled\(false\)/);
assert.match(activity, /requestDismissKeyguard/);
assert.match(activity, /openPinSettings/);

console.log('Android UI/runtime: dock, PIN access, simple-lock wake flow, finance confirmation and TEST_NUMBER OK');
