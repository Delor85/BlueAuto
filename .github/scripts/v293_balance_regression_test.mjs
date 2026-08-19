import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const store = new Map();
globalThis.localStorage = {
  getItem(key) { return store.has(key) ? store.get(key) : null; },
  setItem(key, value) { store.set(key, String(value)); },
  removeItem(key) { store.delete(key); }
};
globalThis.document = {
  readyState: 'complete',
  getElementById() { return null; },
  addEventListener() {}
};
globalThis.window = globalThis;
globalThis.setTimeout = (fn) => { fn(); return 1; };

globalThis.AndroidBridge = {
  getConfiguration() {
    return JSON.stringify({profile_id:'DSM1_SU1', node_code:'DSM1_SU1'});
  },
  getCertifiedBalance() {
    return JSON.stringify({
      balance: 82,
      transaction_id: '000040632407',
      receipt_number: '',
      operator_event_at: '2026-08-19T09:48:11.000Z',
      observed_at: '2026-08-19T09:52:31.000Z',
      operator_event_at_ms: Date.parse('2026-08-19T09:48:11.000Z'),
      captured_at_ms: Date.parse('2026-08-19T09:52:31.000Z'),
      chronology_ms: Date.parse('2026-08-19T09:48:11.000Z')
    });
  }
};

const profile='DSM1_SU1';
const proofKey='bir_balance_guard_v271_'+profile;
const journalKey='bir_transaction_journal_v271_'+profile;

// Reproduce the field regression: an older WebView proof says 81, while the newest native
// Blue proof says 82; the command journal records the SAME 1 FCFA transaction later locally.
localStorage.setItem(proofKey, JSON.stringify({
  balance:81, ts:Date.parse('2026-08-19T09:47:00.000Z'), last_transaction_id:'older-proof'
}));
localStorage.setItem(journalKey, JSON.stringify([{
  id:'c341b94d-fe78-446f-8acc-0cb8b8106573',
  state:'SUCCEEDED', op:'RETAIL_SALE', amount:1,
  tx:'000040632407',
  at:'2026-08-19T09:52:31.000Z'
}]));

const source=fs.readFileSync('app/src/main/assets/balance-engine-v280.js','utf8');
vm.runInThisContext(source,{filename:'balance-engine-v280.js'});
let state=globalThis.BIREventBalanceV280.recompute();
assert.equal(state.balance,82,'same Blue transaction must not be applied twice');
assert.equal(state.movements,0,'same transaction must be recognized as evidence, not later movement');
assert.equal(state.last_transaction_id,'000040632407');

// A genuinely different transaction after the proof must still be counted.
localStorage.setItem(journalKey, JSON.stringify([
  {
    id:'c341b94d-fe78-446f-8acc-0cb8b8106573', state:'SUCCEEDED', op:'RETAIL_SALE', amount:1,
    tx:'000040632407', at:'2026-08-19T09:52:31.000Z'
  },
  {
    id:'another-command', state:'SUCCEEDED', op:'RETAIL_SALE', amount:1,
    tx:'000040632408', operator_at:'2026-08-19T09:53:31.000Z', at:'2026-08-19T09:53:40.000Z'
  }
]));
state=globalThis.BIREventBalanceV280.recompute();
assert.equal(state.balance,81,'a distinct later successful transfer must reduce the certified balance once');
assert.equal(state.movements,1);

console.log('B.I.R. v2.9.3 balance regression locked: certified 82 stays 82 for same tx; later different 1 FCFA tx becomes 81 exactly once.');
