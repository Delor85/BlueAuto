import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Miniflare} from 'miniflare';

const PAIRING_SECRET = 'integration-pairing-secret-123456';
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
    node_code: 'DSM-TEST', parent_node_code: 'DAE-TEST', role: 'DSM', mode: 'REMOTE',
    phone_number: '699000002', device_name: 'Télécommande test'
  });

  const created = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-test-0001'
  }, dsm.data.device_token);
  assert.equal(created.data.command.state, 'PENDING');

  const duplicate = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-test-0001'
  }, dsm.data.device_token);
  assert.equal(duplicate.data.duplicate, true);
  assert.equal(duplicate.data.command.public_id, created.data.command.public_id);

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
  console.log('Cloudflare integration: health, pairing, idempotency, lease and full state flow OK');
} finally {
  await mf.dispose();
}

async function pair(payload) {
  return request('pair_device', {...payload, pairing_secret: PAIRING_SECRET});
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
