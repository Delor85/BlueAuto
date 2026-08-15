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
  for (const migration of ['0001_initial.sql', '0002_robot_sim_attestation.sql',
    '0003_balance_preflight_and_modules.sql', '0004_blue_message_intelligence_and_modules.sql',
    '0005_commission_policies_and_financial_quotes.sql']) {
    const schema = await readFile(new URL(`../migrations/${migration}`, import.meta.url), 'utf8');
    for (const statement of schema.split(';').map(value => value.trim()).filter(Boolean)) {
      await db.prepare(statement).run();
    }
  }

  const health = await request('health');
  assert.equal(health.ok, true);
  assert.equal(health.data.database, 'online');

  const dae = await pair({
    node_code: 'CE04', role: 'DAE', mode: 'ROBOT',
    phone_number: '699000001', device_name: 'Robot test'
  });
  const daeRemote = await request('update_device_mode', {mode: 'REMOTE'}, dae.data.device_token);
  assert.equal(daeRemote.data.mode, 'REMOTE');
  const daeRobot = await request('update_device_mode', {mode: 'ROBOT'}, dae.data.device_token);
  assert.equal(daeRobot.data.mode, 'ROBOT');
  await attest(dae.data.device_token, 'a'.repeat(64), 0);
  const unapprovedDsm = await rawRequest('pair_device', {
    node_code: 'DSM12', parent_node_code: 'CE04', role: 'DSM', mode: 'ROBOT',
    phone_number: '699000002', device_name: 'DSM sans validation', pairing_secret: PAIRING_SECRET
  }, '');
  assert.equal(unapprovedDsm.status, 409);
  assert.equal(unapprovedDsm.body.error.code, 'SUBORDINATE_APPROVAL_REQUIRED');
  const approvedDsm = await request('shadow_enroll', {
    node_code: 'DSM12', phone_number: '699000002', display_name: 'DSM 12', zone: 'Centre'
  }, dae.data.device_token);
  assert.equal(approvedDsm.data.shadow.node_code, 'DSM12_CE04');
  const dsm = await pair({
    node_code: 'DSM12', parent_node_code: 'CE04', role: 'DSM', mode: 'ROBOT',
    phone_number: '699000002', device_name: 'Télécommande test'
  });
  assert.equal(dsm.data.node_code, 'DSM12_CE04');
  await attest(dsm.data.device_token, 'b'.repeat(64), 0);

  await request('shadow_enroll', {node_code: 'DSM2', phone_number: '699000004'}, dae.data.device_token);
  const dsmTwo = await pair({
    node_code: 'DSM2', parent_node_code: 'CE04', role: 'DSM', mode: 'REMOTE',
    phone_number: '699000004', device_name: 'Deuxième DSM légitime'
  });
  assert.equal(dsmTwo.data.node_code, 'DSM2_CE04');

  await request('shadow_enroll', {node_code: 'POS37', phone_number: '699000003'}, dsm.data.device_token);
  const pos = await pair({
    node_code: 'POS37', parent_node_code: 'DSM12_CE04', role: 'POS', mode: 'ROBOT',
    phone_number: '699000003', device_name: 'Second Robot test'
  });
  assert.equal(pos.data.node_code, 'POS37_DSM12_CE04');
  await attest(pos.data.device_token, 'c'.repeat(64), 1);
  const shortPosFromDae = await requestFailure('create_command', {
    request_type: 'CHILD_BALANCE', target_node_code: 'POS37',
    client_request_id: 'integration-dae-short-pos-refused-01'
  }, dae.data.device_token, 422);
  assert.equal(shortPosFromDae.error.code, 'POS_FULL_NAME_REQUIRED');

  // Real field topology: a distinct REMOTE creates the order and the phone that owns the
  // verified SIM leases it. This must not rely on one token acting as both devices.
  const posRemote = await pair({
    node_code: 'POS37', parent_node_code: 'DSM12_CE04', role: 'POS', mode: 'REMOTE',
    phone_number: '699000003', device_name: 'Télécommande POS distincte'
  });

  await testCommandLifecycle(posRemote.data.device_token, pos.data.device_token, {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-request-0001'
  });

  await testCommandLifecycle(posRemote.data.device_token, pos.data.device_token, {
    request_type: 'CHECK_BALANCE', client_request_id: 'integration-balance-0001'
  }, {resultText: 'Your balance is 75,000 FCFA', expectedKind: 'BALANCE_OWN'});

  const dsmBalance = await request('create_command', {
    request_type: 'CHECK_BALANCE', client_request_id: 'integration-balance-dsm-0001'
  }, dsm.data.device_token);
  assert.equal(dsmBalance.data.command.executor_node_code, 'DSM12_CE04');
  let dsmLeased = await request('lease_command', {}, dsm.data.device_token);
  assert.equal(dsmLeased.data.available, true);
  assert.equal(dsmLeased.data.command.public_id, dsmBalance.data.command.public_id);
  assert.equal(dsmLeased.data.command.ussd_code, '');
  await event(dsm.data.device_token, dsmBalance.data.command.public_id, 'DIALING');
  await event(dsm.data.device_token, dsmBalance.data.command.public_id, 'AWAITING_RESULT');
  await recordOperator(dsm.data.device_token, {
    command_public_id: dsmBalance.data.command.public_id,
    channel: 'USSD', raw_message: 'Your balance is 50000 FCFA'
  });
  await event(dsm.data.device_token, dsmBalance.data.command.public_id, 'SUCCEEDED', '', '');

  // Purchase preflight reuses the supplier's fresh exact balance rather than spending another USSD.
  const capacity = await request('check_purchase_capacity', {
    requested_amount: 1000, client_request_id: 'integration-capacity-0001'
  }, posRemote.data.device_token);
  assert.equal(capacity.data.capacity.state, 'AVAILABLE');
  assert.equal(capacity.data.capacity.balance_reused, true);

  const preview = await request('preview_command', {
    request_type: 'REQUEST_SUPPLY', requested_amount: 1000,
    client_request_id: 'integration-purchase-preview-0001',
    capacity_check_id: capacity.data.capacity.capacity_check_id
  }, posRemote.data.device_token);
  assert.equal(preview.data.preview.executor_node_code, 'DSM12_CE04');
  assert.equal(preview.data.preview.target_node_code, 'POS37_DSM12_CE04');
  assert.equal(preview.data.preview.requested_base_amount, 1000);
  assert.equal(preview.data.preview.commission_rate_bps, 800);
  assert.equal(preview.data.preview.commission_amount, 80);
  assert.equal(preview.data.preview.amount, 1080);

  const purchase = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', requested_amount: 1000,
    client_request_id: 'integration-purchase-0001',
    capacity_check_id: capacity.data.capacity.capacity_check_id,
    confirmation_fingerprint: preview.data.preview.confirmation_fingerprint
  }, posRemote.data.device_token);
  assert.equal(purchase.data.command.amount, 1080);
  assert.equal(purchase.data.command.requested_base_amount, 1000);
  assert.equal(purchase.data.command.commission_amount, 80);

  // A DSM can customize one PoS without changing its default rate.
  const customized = await request('commission_set_child', {
    child_node_code: 'POS37', rate_bps: 900
  }, dsm.data.device_token);
  assert.equal(customized.data.default_rate_bps, 800);
  assert.equal(customized.data.children.find(row => row.node_code === 'POS37_DSM12_CE04').effective_rate_bps, 900);

  const details = await request('create_command', {
    request_type: 'TRANSACTION_DETAILS', command_argument: '000040529208',
    client_request_id: 'integration-detail-0001'
  }, posRemote.data.device_token);
  assert.equal(details.data.command.operation, 'TRANSACTION_DETAIL');

  // Recreate a fresh POS balance proof for report/audit tests.
  const posFreshBalance = await request('create_command', {
    request_type: 'CHECK_BALANCE', client_request_id: 'integration-balance-pos-fresh-0001'
  }, posRemote.data.device_token);
  const posFreshLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(posFreshLease.data.available, true);
  assert.equal(posFreshLease.data.command.public_id, posFreshBalance.data.command.public_id);
  await event(pos.data.device_token, posFreshBalance.data.command.public_id, 'DIALING');
  await event(pos.data.device_token, posFreshBalance.data.command.public_id, 'AWAITING_RESULT');
  await recordOperator(pos.data.device_token, {
    command_public_id: posFreshBalance.data.command.public_id,
    channel: 'USSD', raw_message: 'Your balance is 92000 FCFA'
  });
  await event(pos.data.device_token, posFreshBalance.data.command.public_id, 'SUCCEEDED', '', '');

  // A delayed older financial receipt must never invalidate a newer exact balance.
  await recordOperator(pos.data.device_token, {
    channel: 'SMS', raw_message: 'You 699123456 received 10.00 FCFA of top-up. TransactionID is 000039377114. 14-08-2026 at 16:00:00'
  });
  const dashboardAfterOldSms = await request('network_dashboard', {}, posRemote.data.device_token);
  assert.equal(dashboardAfterOldSms.data.nodes[0].balance, 92000);
  assert.equal(dashboardAfterOldSms.data.nodes[0].balance_quality, 'EXACT');

  const audit = await request('network_balance_audit', {}, dae.data.device_token);
  assert.equal(audit.data.order, 'PRIORITY_THEN_BOTTOM_UP_POS_DSM_DAE');
  assert.equal(audit.data.report_freshness_seconds, 14 * 3600);
  assert.equal(audit.data.finance_freshness_seconds, 3600);

  console.log('Cloudflare integration: Remote/Robot, FIFO, solde frais, concurrence atomique et états complets OK');
} finally {
  await mf.dispose();
}

async function pair(data) {
  return request('pair_device', {...data, pairing_secret: PAIRING_SECRET});
}

async function attest(token, fingerprint, slot) {
  return request('activate_robot', {sim_fingerprint: fingerprint, sim_slot: slot}, token);
}

async function testCommandLifecycle(remoteToken, robotToken, payload, options = {}) {
  const created = await request('create_command', payload, remoteToken);
  assert.equal(created.data.command.state, 'PENDING');
  const leased = await request('lease_command', {}, robotToken);
  assert.equal(leased.data.available, true);
  assert.equal(leased.data.command.public_id, created.data.command.public_id);
  await event(robotToken, created.data.command.public_id, 'DIALING');
  if (leased.data.command.requires_pin) await event(robotToken, created.data.command.public_id, 'AWAITING_PIN');
  else await event(robotToken, created.data.command.public_id, 'AWAITING_RESULT');
  if (options.resultText) {
    await recordOperator(robotToken, {
      command_public_id: created.data.command.public_id,
      channel: 'USSD', raw_message: options.resultText
    });
  }
  await event(robotToken, created.data.command.public_id, 'SUCCEEDED', '', '');
  const final = await request('command_status', {public_id: created.data.command.public_id}, remoteToken);
  assert.equal(final.data.command.state, 'SUCCEEDED');
}

async function event(token, publicId, state, message = '', transactionId = '') {
  return request('command_event', {
    public_id: publicId, state, message, transaction_id: transactionId
  }, token);
}

async function recordOperator(token, input) {
  return request('record_operator_message', input, token);
}

async function requestFailure(action, input, token, expectedStatus) {
  const result = await rawRequest(action, input, token);
  assert.equal(result.status, expectedStatus, JSON.stringify(result.body));
  assert.equal(result.body.ok, false);
  return result.body;
}

async function request(action, input = {}, token = '') {
  const result = await rawRequest(action, input, token);
  assert.equal(result.status >= 200 && result.status < 300, true, JSON.stringify(result.body));
  assert.equal(result.body.ok, true, JSON.stringify(result.body));
  return result.body;
}

async function rawRequest(action, input = {}, token = '') {
  const headers = {'content-type': 'application/json'};
  if (token) headers.authorization = `Bearer ${token}`;
  const response = await mf.dispatchFetch(`https://unit.test/api?action=${action}`, {
    method: 'POST', headers, body: JSON.stringify(input)
  });
  return {status: response.status, body: await response.json()};
}
