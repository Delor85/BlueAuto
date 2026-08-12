import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';

const elements = new Map();
const ids = [
  'nativeBadge', 'browserNotice', 'nodeCode', 'nodeMeta', 'robotState', 'fatalNotice',
  'actionNotice', 'roleNotice', 'requestSupplyCard', 'supplyChildCard', 'retailCard',
  'requestSupplyAmount', 'childNode', 'childAmount', 'retailPhone', 'retailAmount',
  'refreshCommands', 'commandList', 'toast'
];

function element(id = '') {
  return {
    id, className: '', textContent: '', innerHTML: '', value: '', disabled: false,
    tagName: id.includes('Amount') || id.includes('Phone') ? 'INPUT' : 'DIV',
    getAttribute(name) { return name === 'data-action' ? this.action : ''; }
  };
}

for (const id of ids) elements.set(id, element(id));
const actions = ['request-supply', 'supply-child', 'retail-sale', 'test-number']
  .map(action => Object.assign(element(action), {action, tagName: 'BUTTON'}));
const bridgeCalls = [];
let confirmResult = true;
let confirmationText = '';

const document = {
  readyState: 'complete', activeElement: null,
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, element(id));
    return elements.get(id);
  },
  querySelectorAll(selector) {
    if (selector === 'button[data-action]') return actions;
    return [];
  },
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
    getCommandStatus() {}, cancelCommand() {}, setFormEditing() {}
  },
  confirm(message) { confirmationText = message; return confirmResult; },
  setTimeout() {}, setInterval() {}
};
const localStorage = {
  values: new Map(),
  getItem(key) { return this.values.get(key) || null; },
  setItem(key, value) { this.values.set(key, value); }
};

const script = await readFile(new URL('../main/assets/app.js', import.meta.url), 'utf8');
vm.runInNewContext(script, {window, document, localStorage, Date, Math, JSON, String, Object, isNaN});

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
  confirmation_fingerprint: 'f'.repeat(64)
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

console.log('Android finance UI: Android 6 colors, preview, confirm, cancel and TEST_NUMBER flow OK');
