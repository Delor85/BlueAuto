import assert from 'node:assert/strict';
import {randomBytes} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {Miniflare} from 'miniflare';

const PAIRING_SECRET = randomBytes(32).toString('hex');
const mf = new Miniflare({
  modules: true,
  scriptPath: new URL('../src/index.js', import.meta.url).pathname,
  compatibilityDate: '2026-08-07',
  d1Databases: ['DB'],
  bindings: {PAIRING_SECRET, ALLOWED_ORIGIN: ''}
});

try {
  const db = await mf.getD1Database('DB');
  const schema = await readFile(new URL('../migrations/0001_initial.sql', import.meta.url), 'utf8');
  for (const statement of schema.split(';').map(value => value.trim()).filter(Boolean)) {
    await db.prepare(statement).run();
  }

  const health = await request('health');
  assert.equal(health.ok, true);
  assert.equal(health.data.database, 'online');

  const dae = await pair({
    node_code: 'DAE-TEST', role: 'DAE', mode: 'ROBOT',
    phone_number: '699000001', device_name: 'Robot test'
  });
  const dsm = await pair({
    node_code: 'DSM-TEST', parent_node_code: 'DAE-TEST', role: 'DSM', mode: 'ROBOT',
    phone_number: '699000002', device_name: 'Télécommande test'
  });
  assert.equal(dsm.data.node_code, 'DSM-TEST_DAE-TEST');

  const pos = await pair({
    node_code: 'POS5', parent_node_code: 'DSM-TEST', role: 'POS', mode: 'ROBOT',
    phone_number: '699000003', device_name: 'Second Robot test'
  });
  assert.equal(pos.data.node_code, 'POS5_DSM-TEST_DAE-TEST');

  const supplyDsm = await request('create_command', {
    request_type: 'SUPPLY_CHILD', target_node_code: 'DSM-TEST', amount: '200',
    client_request_id: 'integration-alias-dsm-01'
  }, dae.data.device_token);
  assert.equal(supplyDsm.data.command.target_node_code, 'DSM-TEST_DAE-TEST');

  const supplyPos = await request('create_command', {
    request_type: 'SUPPLY_CHILD', target_node_code: 'POS5', amount: '100',
    client_request_id: 'integration-alias-pos-001'
  }, dsm.data.device_token);
  assert.equal(supplyPos.data.command.target_node_code, 'POS5_DSM-TEST_DAE-TEST');
  assert.match(supplyPos.data.command.created_at, /^\d{4}-\d{2}-\d{2}T/);

  const created = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-test-0001'
  }, dsm.data.device_token);
  assert.equal(created.data.command.state, 'PENDING');

  const duplicate = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-test-0001'
  }, dsm.data.device_token);
  assert.equal(duplicate.data.duplicate, true);
  assert.equal(duplicate.data.command.public_id, created.data.command.public_id);

  const firstDaeLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(firstDaeLease.data.available, true);
  assert.equal(firstDaeLease.data.command.ussd_code, '*550*2*699000002*200#');
  await complete(firstDaeLease.data.command, dae.data.device_token);

  const leased = await request('lease_command', {}, dae.data.device_token);
  assert.equal(leased.data.available, true);
  assert.equal(leased.data.command.ussd_code, '*550*2*699000002*500#');
  assert.equal(leased.data.command.requires_pin, true);

  for (const state of ['DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT', 'SUCCEEDED']) {
    const event = await request('command_event', {
      command_id: created.data.command.public_id,
      lease_token: leased.data.command.lease_token,
      state,
      message: `test ${state}`
    }, dae.data.device_token);
    assert.equal(event.data.command.state, state);
  }

  const status = await request('command_status', {
    command_id: created.data.command.public_id
  }, dsm.data.device_token);
  assert.equal(status.data.command.state, 'SUCCEEDED');
  assert.equal(status.data.command.amount, 500);

  const dsmLease = await request('lease_command', {}, dsm.data.device_token);
  assert.equal(dsmLease.data.available, true);
  assert.equal(dsmLease.data.command.ussd_code, '*550*2*699000003*100#');
  await complete(dsmLease.data.command, dsm.data.device_token);

  console.log('Cloudflare integration: hierarchy aliases, timestamps, two Robots, idempotency and full state flow OK');
} finally {
  await mf.dispose();
}

async function pair(payload) {
  return request('pair_device', {...payload, pairing_secret: PAIRING_SECRET});
}

async function complete(command, token) {
  for (const state of ['DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT', 'SUCCEEDED']) {
    const event = await request('command_event', {
      command_id: command.public_id,
      lease_token: command.lease_token,
      state,
      message: `test ${state}`
    }, token);
    assert.equal(event.data.command.state, state);
  }
}

async function request(action, payload = {}, token = '') {
  const headers = {'Content-Type': 'application/json'};
  if (token) headers['X-Device-Token'] = token;
  const response = await mf.dispatchFetch(`http://blue-magic.test/api?action=${action}`, {
    method: 'POST', headers, body: JSON.stringify(payload)
  });
  const body = await response.json();
  assert.equal(response.status < 400, true, JSON.stringify(body));
  assert.equal(body.ok, true, JSON.stringify(body));
  return body;
}
