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
  const remoteCreated = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-remote-to-robot-01'
  }, posRemote.data.device_token);
  assert.equal(remoteCreated.data.command.robot_ready, true);
  assert.equal(remoteCreated.data.command.robot_status, 'ONLINE');
  const remoteRobotLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(remoteRobotLease.data.command.public_id, remoteCreated.data.command.public_id);
  await complete(remoteRobotLease.data.command, pos.data.device_token);

  const cancellable = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-cancel-pos-01'
  }, pos.data.device_token);
  const cancelled = await request('cancel_command', {
    command_id: cancellable.data.command.public_id
  }, pos.data.device_token);
  assert.equal(cancelled.data.cancelled, true);
  assert.equal(cancelled.data.command.state, 'CANCELLED');
  const cancelledStatus = await request('command_status', {
    command_id: cancellable.data.command.public_id
  }, pos.data.device_token);
  assert.equal(cancelledStatus.data.command.state, 'CANCELLED');

  const supplyDsmPreview = await request('preview_command', {
    request_type: 'SUPPLY_CHILD', target_node_code: 'DSM12', amount: '200'
  }, dae.data.device_token);
  const supplyDsm = await request('create_command', {
    request_type: 'SUPPLY_CHILD', target_node_code: 'DSM12', amount: '200',
    client_request_id: 'integration-alias-dsm-01',
    confirmation_fingerprint: supplyDsmPreview.data.preview.confirmation_fingerprint
  }, dae.data.device_token);
  assert.equal(supplyDsm.data.command.target_node_code, 'DSM12_CE04');

  const supplyPosPreview = await request('preview_command', {
    request_type: 'SUPPLY_CHILD', target_node_code: 'POS37', amount: '100'
  }, dsm.data.device_token);
  const supplyPos = await request('create_command', {
    request_type: 'SUPPLY_CHILD', target_node_code: 'POS37', amount: '100',
    client_request_id: 'integration-alias-pos-001',
    confirmation_fingerprint: supplyPosPreview.data.preview.confirmation_fingerprint
  }, dsm.data.device_token);
  assert.equal(supplyPos.data.command.target_node_code, 'POS37_DSM12_CE04');
  assert.match(supplyPos.data.command.created_at, /^\d{4}-\d{2}-\d{2}T/);

  const firstDaeLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(firstDaeLease.data.available, true);
  assert.equal(firstDaeLease.data.command.ussd_code, '*550*2*699000002*220#');
  assert.equal(firstDaeLease.data.command.executor_node_code, 'CE04');
  assert.equal(firstDaeLease.data.command.executor_phone, '699000001');
  assert.equal(firstDaeLease.data.command.integrity_version, 3);
  assert.match(firstDaeLease.data.command.integrity_digest, /^[a-f0-9]{64}$/);
  const released = await request('release_command', {
    command_id: firstDaeLease.data.command.public_id,
    lease_token: firstDaeLease.data.command.lease_token,
    reason: 'Écran sécurisé verrouillé pendant le test.'
  }, dae.data.device_token);
  assert.equal(released.data.released, true);
  assert.equal(released.data.command.state, 'PENDING');

  const resumedDaeLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(resumedDaeLease.data.command.public_id, firstDaeLease.data.command.public_id);
  await complete(resumedDaeLease.data.command, dae.data.device_token);

  const capacity = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '500',
    client_request_id: 'integration-capacity-available-01'
  }, dsm.data.device_token);
  assert.equal(capacity.data.capacity.state, 'WAITING');
  const capacityBalanceLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(capacityBalanceLease.data.command.command_kind, 'BALANCE_OWN');
  await complete(capacityBalanceLease.data.command, dae.data.device_token,
    'Your available balance is 1000 FCFA');
  const capacityReady = await request('purchase_capacity_status', {
    capacity_check_id: capacity.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  assert.equal(capacityReady.data.capacity.state, 'AVAILABLE');
  assert.equal(capacityReady.data.capacity.available_balance, 1000);
  assert.equal(capacityReady.data.capacity.base_amount, 500);
  assert.equal(capacityReady.data.capacity.commission_rate_bps, 1000);
  assert.equal(capacityReady.data.capacity.commission_amount, 50);
  assert.equal(capacityReady.data.capacity.requested_amount, 550);
  assert.equal(capacityReady.data.capacity.reservation_applied, false);

  const insufficient = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '1500',
    client_request_id: 'integration-capacity-insufficient-01'
  }, dsm.data.device_token);
  assert.equal(insufficient.data.capacity.state, 'INSUFFICIENT');
  assert.equal(insufficient.data.capacity.available_balance, 1000);
  assert.equal(insufficient.data.capacity.balance_reused, true);

  const supplyPreview = await request('preview_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500',
    capacity_check_id: capacity.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  assert.equal(supplyPreview.data.preview.executor_node_code, 'CE04');
  assert.equal(supplyPreview.data.preview.executor_phone, '699000001');
  assert.equal(supplyPreview.data.preview.target_node_code, 'DSM12_CE04');
  assert.equal(supplyPreview.data.preview.target_phone, '699000002');
  assert.equal(supplyPreview.data.preview.requested_base_amount, 500);
  assert.equal(supplyPreview.data.preview.commission_rate_bps, 1000);
  assert.equal(supplyPreview.data.preview.commission_amount, 50);
  assert.equal(supplyPreview.data.preview.amount, 550);
  assert.match(supplyPreview.data.preview.confirmation_fingerprint, /^[a-f0-9]{64}$/);

  const unconfirmed = await requestFailure('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-unconfirmed-01',
    capacity_check_id: capacity.data.capacity.capacity_check_id
  }, dsm.data.device_token, 409);
  assert.equal(unconfirmed.error.code, 'CONFIRMATION_REQUIRED');

  const created = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-test-0001',
    confirmation_fingerprint: supplyPreview.data.preview.confirmation_fingerprint,
    capacity_check_id: capacity.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  assert.equal(created.data.command.state, 'PENDING');

  const duplicate = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500', client_request_id: 'integration-test-0001'
  }, dsm.data.device_token);
  assert.equal(duplicate.data.duplicate, true);
  assert.equal(duplicate.data.command.public_id, created.data.command.public_id);

  const leased = await request('lease_command', {}, dae.data.device_token);
  assert.equal(leased.data.available, true);
  assert.equal(leased.data.command.ussd_code, '*550*2*699000002*550#');
  assert.equal(leased.data.command.requires_pin, true);

  for (const state of ['DIALING', 'AWAITING_PIN']) {
    const event = await request('command_event', {
      command_id: created.data.command.public_id,
      lease_token: leased.data.command.lease_token,
      state,
      message: `test ${state}`
    }, dae.data.device_token);
    assert.equal(event.data.command.state, state);
  }

  const parallelPos = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-parallel-pos-01'
  }, pos.data.device_token);
  const parallelPosLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(parallelPosLease.data.available, true);
  assert.equal(parallelPosLease.data.command.public_id, parallelPos.data.command.public_id);
  await complete(parallelPosLease.data.command, pos.data.device_token);

  for (const state of ['PIN_SUBMITTED', 'AWAITING_RESULT', 'SUCCEEDED']) {
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
  assert.equal(status.data.command.amount, 550);

  await db.prepare("DELETE FROM account_balances WHERE node_code = 'CE04'").run();
  const waitingCapacity = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '700',
    client_request_id: 'integration-capacity-live-ussd-01'
  }, dsmTwo.data.device_token);
  assert.equal(waitingCapacity.data.capacity.state, 'WAITING');
  const balanceLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(balanceLease.data.command.command_kind, 'BALANCE_OWN');
  assert.equal(balanceLease.data.command.ussd_code, '');
  assert.equal(balanceLease.data.command.requires_pin, false);
  for (const [state, message] of [
    ['DIALING', 'Consultation directe'],
    ['AWAITING_RESULT', 'Réponse Camtel attendue'],
    ['SUCCEEDED', 'Your available balance is 650 FCFA']
  ]) {
    await request('command_event', {
      command_id: balanceLease.data.command.public_id,
      lease_token: balanceLease.data.command.lease_token, state, message
    }, dae.data.device_token);
  }
  const checkedCapacity = await request('purchase_capacity_status', {
    capacity_check_id: waitingCapacity.data.capacity.capacity_check_id
  }, dsmTwo.data.device_token);
  assert.equal(checkedCapacity.data.capacity.state, 'INSUFFICIENT');
  assert.equal(checkedCapacity.data.capacity.available_balance, 650);
  assert.equal(checkedCapacity.data.capacity.reservation_applied, false);

  const dashboard = await request('network_dashboard', {}, dae.data.device_token);
  assert.equal(dashboard.data.nodes.some(node => node.node_code === 'CE04'
    && node.balance === 650), true);
  assert.equal(dashboard.data.nodes.some(node => node.device_kind === 'ANDROID'), true);

  // Une vue d'historique ne doit fournir un solde mutualisable que si le même écran Camtel
  // contient un libellé de solde actuel explicite. « Transfer Balance of 1 FCFA » n'en est pas un.
  const ambiguousHistory = await request('create_command', {
    request_type: 'LAST_TRANSACTIONS', client_request_id: 'integration-history-ambiguous-01'
  }, dae.data.device_token);
  const ambiguousHistoryLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(ambiguousHistoryLease.data.command.public_id, ambiguousHistory.data.command.public_id);
  await complete(ambiguousHistoryLease.data.command, dae.data.device_token,
    'Transfer Balance of 1FCFA to 621081275. Fee 0 FCFA.');
  const afterAmbiguousHistory = await request('network_dashboard', {}, dae.data.device_token);
  assert.equal(afterAmbiguousHistory.data.nodes.find(node => node.node_code === 'CE04').balance,
    650);

  const explicitHistory = await request('create_command', {
    request_type: 'LAST_TRANSACTIONS', client_request_id: 'integration-history-current-balance-01'
  }, dae.data.device_token);
  const explicitHistoryLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(explicitHistoryLease.data.command.public_id, explicitHistory.data.command.public_id);
  await complete(explicitHistoryLease.data.command, dae.data.device_token,
    '5 last transactions. Current balance is 1000 FCFA, fee 0 FCFA.');

  const exactHistoryMessage = 'Your mini statement is: '
    + 'ReceiptNumber:900001 CurrentBalance:880.00 FCFA AccountNo:500001 Details: Airtime Transfer to 699000002 - DSM12 Company Airtime Account 15/08/26 Airtime Transfer Dr 20.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed '
    + 'ReceiptNumber:900000 CurrentBalance:900.00 FCFA AccountNo:500001 Details: Airtime Transfer to 699000002 - DSM12 Company Airtime Account 15/08/26 Airtime Transfer Dr 10.00 FCFA CH0.00 FCFA CM0.00 FCFA Status:Completed';
  const liveHistory = await request('create_command', {
    request_type: 'LAST_TRANSACTIONS', client_request_id: 'integration-live-history-priority-01'
  }, dae.data.device_token);
  const liveHistoryLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(liveHistoryLease.data.command.public_id, liveHistory.data.command.public_id);
  await complete(liveHistoryLease.data.command, dae.data.device_token, exactHistoryMessage);
  let liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  let liveDae = liveDashboard.data.nodes.find(node => node.node_code === 'CE04');
  assert.equal(liveDae.balance, 880);
  assert.equal(liveDae.evidence_kind, 'HISTORY_RESULT');
  assert.equal(liveDae.balance_quality, 'EXACT');
  assert.equal(liveDae.balance_reusable, true);

  await request('record_operator_message', {
    message: 'Your Transfer Airtime to 699000002 - DSM12 has been successfully processed.Amount is 5.00 FCFA. Now your balance is 100.00 FCFA. TransactionID 000039365092, 07-07-2026 at 12:14:09.'
  }, dae.data.device_token);
  liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  liveDae = liveDashboard.data.nodes.find(node => node.node_code === 'CE04');
  assert.equal(liveDae.balance, 880);

  await request('record_operator_message', {
    message: 'Your available voucher stock is: 15.00 FCFA; Uncleared balance: 0.00 FCFA; Reserved balance: 0.00 FCFA; Current balance: 15.00 FCFA.'
  }, dae.data.device_token);
  liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'CE04').balance, 880);

  await request('record_operator_message', {
    message: 'Your Transfer Airtime to 699000002 - DSM12_CE04 has been successfully processed. Amount is 5.00 FCFA. TransactionID 000039300001 on 07-07-2026 at 01:00:00.'
  }, dae.data.device_token);
  const afterDelayedOld = await request('platform_snapshot', {}, dae.data.device_token);
  const delayedNode = afterDelayedOld.data.nodes.find(node => node.node_code === 'CE04');
  assert.notEqual(delayedNode.balance_report_state, 'RECHECK_REQUIRED');

  const childBalance = await request('create_command', {
    request_type: 'CHILD_BALANCE', target_node_code: 'DSM12_CE04',
    client_request_id: 'integration-child-balance-attribution-01'
  }, dae.data.device_token);
  const childBalanceLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(childBalanceLease.data.command.public_id, childBalance.data.command.public_id);
  await complete(childBalanceLease.data.command, dae.data.device_token,
    'Your available voucher stock is: 123.00 FCFA; Uncleared balance: 0.00 FCFA; Reserved balance: 0.00 FCFA; Current balance: 123.00 FCFA.');
  liveDashboard = await request('network_dashboard', {}, dae.data.device_token);
  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'CE04').balance, 880);
  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'DSM12_CE04').balance, 123);

  const sharedBalance = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '100',
    client_request_id: 'integration-shared-live-balance-01'
  }, dsm.data.device_token);
  assert.equal(sharedBalance.data.capacity.state, 'AVAILABLE');
  assert.equal(sharedBalance.data.capacity.balance_reused, true);
  assert.equal(sharedBalance.data.capacity.available_balance, 880);

  // Release the earlier demonstration preflight so the following test starts from 880 FCFA.
  await db.prepare("UPDATE purchase_preflights SET state='EXPIRED' WHERE public_id = ?")
    .bind(sharedBalance.data.capacity.capacity_check_id).run();

  // Quote-only concurrency: preflights never reserve or visually reduce stock. Both callers may
  // receive a valid quote; only the first CONFIRMED command reserves capacity atomically.
  const raceOne = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '700',
    client_request_id: 'integration-capacity-race-dsm1-01'
  }, dsm.data.device_token);
  const raceTwo = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '500',
    client_request_id: 'integration-capacity-race-dsm2-01'
  }, dsmTwo.data.device_token);
  assert.equal(raceOne.data.capacity.state, 'AVAILABLE');
  assert.equal(raceOne.data.capacity.available_balance, 880);
  assert.equal(raceOne.data.capacity.reservation_applied, false);
  assert.match(raceOne.data.capacity.message, /880 FCFA/);
  assert.equal(raceTwo.data.capacity.state, 'AVAILABLE');
  assert.equal(raceTwo.data.capacity.available_balance, 880);
  assert.equal(raceTwo.data.capacity.reservation_applied, false);
  assert.match(raceTwo.data.capacity.message, /880 FCFA/);
  const raceOnePreview = await request('preview_command', {
    request_type: 'REQUEST_SUPPLY', amount: '700',
    capacity_check_id: raceOne.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  const raceTwoPreview = await request('preview_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500',
    capacity_check_id: raceTwo.data.capacity.capacity_check_id
  }, dsmTwo.data.device_token);
  assert.equal(raceOnePreview.data.preview.amount, 770);
  assert.equal(raceTwoPreview.data.preview.amount, 550);
  const raceWinner = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '700',
    client_request_id: 'integration-capacity-race-create1',
    capacity_check_id: raceOne.data.capacity.capacity_check_id,
    confirmation_fingerprint: raceOnePreview.data.preview.confirmation_fingerprint
  }, dsm.data.device_token);
  assert.equal(raceWinner.data.command.amount, 770);
  const raceLoser = await requestFailure('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500',
    client_request_id: 'integration-capacity-race-create2',
    capacity_check_id: raceTwo.data.capacity.capacity_check_id,
    confirmation_fingerprint: raceTwoPreview.data.preview.confirmation_fingerprint
  }, dsmTwo.data.device_token, 409);
  assert.equal(raceLoser.error.code, 'BALANCE_CHANGED');
  const raceCancelled = await request('cancel_command', {
    command_id: raceWinner.data.command.public_id
  }, dsm.data.device_token);
  assert.equal(raceCancelled.data.cancelled, true);


  await db.prepare(
    "UPDATE account_balances SET valid_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-1 second') "
    + "WHERE node_code = 'CE04'"
  ).run();
  const expiredEvidence = await request('check_purchase_capacity', {
    request_type: 'REQUEST_SUPPLY', amount: '100',
    client_request_id: 'integration-capacity-expired-proof-01'
  }, dsm.data.device_token);
  assert.equal(expiredEvidence.data.capacity.state, 'WAITING');
  assert.equal(expiredEvidence.data.capacity.balance_reused, false);
  const refreshAfterExpiryLease = await request('lease_command', {}, dae.data.device_token);
  assert.equal(refreshAfterExpiryLease.data.command.command_kind, 'BALANCE_OWN');
  await complete(refreshAfterExpiryLease.data.command, dae.data.device_token,
    'Votre solde actuel est de 900 FCFA');
  const refreshedAfterExpiry = await request('purchase_capacity_status', {
    capacity_check_id: expiredEvidence.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  assert.equal(refreshedAfterExpiry.data.capacity.state, 'AVAILABLE');

  // Shared network audit: recent exact evidence is reused; stale descendants are queued bottom-up.
  await db.prepare("UPDATE purchase_preflights SET state='EXPIRED' WHERE supplier_node_code='CE04'").run();
  await db.prepare(
    "UPDATE account_balances SET observed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 hours'), "
    + "operator_event_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 hours'), "
    + "valid_until=strftime('%Y-%m-%dT%H:%M:%fZ','now','-14 hours') WHERE node_code='DSM12_CE04'"
  ).run();
  const networkAudit = await request('network_balance_audit', {}, dae.data.device_token);
  assert.equal(networkAudit.data.order, 'PRIORITY_THEN_BOTTOM_UP_POS_DSM_DAE');
  assert.equal(networkAudit.data.report_freshness_seconds, 14 * 3600);
  assert.equal(networkAudit.data.max_outstanding_per_scope, 12);
  assert.equal(networkAudit.data.reused >= 1, true);
  assert.equal(networkAudit.data.queued >= 1, true);
  const dsmAuditItem = networkAudit.data.details.find(item => item.node_code === 'DSM12_CE04');
  assert.equal(dsmAuditItem.action, 'QUEUED');
  assert.equal(dsmAuditItem.command_kind, 'BALANCE_OWN');
  const posAuditItem = networkAudit.data.details.find(item => item.node_code === 'POS37_DSM12_CE04');
  assert.ok(posAuditItem);
  await db.prepare("UPDATE commands SET state='CANCELLED' WHERE client_request_id LIKE 'audit_%' AND state='PENDING'").run();
  // DAE can route a PoS balance directly when the PoS/DSM Robot is unavailable; this is covered by
  // the same route planner and the CHILD_BALANCE command already validated above.

  const dsmLease = await request('lease_command', {}, dsm.data.device_token);
  assert.equal(dsmLease.data.available, true);
  assert.equal(dsmLease.data.command.ussd_code, '*550*2*699000003*108#');
  await complete(dsmLease.data.command, dsm.data.device_token);

  const queuedOne = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-queue-pos-01'
  }, pos.data.device_token);
  const queuedTwo = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-queue-pos-02'
  }, pos.data.device_token);
  const firstPosLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(firstPosLease.data.command.public_id, queuedOne.data.command.public_id);
  const blockedParallelLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(blockedParallelLease.data.available, false);
  assert.equal(blockedParallelLease.data.busy, true);
  await complete(firstPosLease.data.command, pos.data.device_token);
  const secondPosLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(secondPosLease.data.command.public_id, queuedTwo.data.command.public_id);
  await complete(secondPosLease.data.command, pos.data.device_token);

  const staleOne = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-stale-pos-01'
  }, pos.data.device_token);
  const staleTwo = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-stale-pos-02'
  }, pos.data.device_token);
  const staleLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(staleLease.data.command.public_id, staleOne.data.command.public_id);
  await request('command_event', {
    command_id: staleOne.data.command.public_id,
    lease_token: staleLease.data.command.lease_token,
    state: 'DIALING', message: 'simulation session interrompue'
  }, pos.data.device_token);
  await db.prepare(
    "UPDATE commands SET leased_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-1 second') WHERE public_id = ?"
  ).bind(staleOne.data.command.public_id).run();
  const afterStale = await request('lease_command', {}, pos.data.device_token);
  assert.equal(afterStale.data.available, true);
  assert.equal(afterStale.data.command.public_id, staleTwo.data.command.public_id);
  const staleStatus = await request('command_status', {
    command_id: staleOne.data.command.public_id
  }, pos.data.device_token);
  assert.equal(staleStatus.data.command.state, 'UNKNOWN');
  await complete(afterStale.data.command, pos.data.device_token);

  // A Remote cannot evict the active Robot by merely changing mode. At the exact moment of a
  // conflict, however, a second physical inspection of the same SIM may replace only the owner
  // carrying that identical attestation. A missing or different SIM never receives this right.
  const posReplacement = await pair({
    node_code: 'POS37', parent_node_code: 'DSM12_CE04', role: 'POS', mode: 'REMOTE',
    phone_number: '699000003', device_name: 'Nouveau téléphone POS'
  });
  const missingSim = await requestFailure('activate_robot', {
    ...robotPresence('', 1), sim_verified: false
  }, posReplacement.data.device_token, 409);
  assert.equal(missingSim.error.code, 'ROBOT_SIM_NOT_VERIFIED');
  const wrongSimReplacement = await requestFailure('activate_robot', {
    ...robotPresence('f'.repeat(64), 1), replace_verified_same_sim_robot: true
  }, posReplacement.data.device_token, 409);
  assert.equal(wrongSimReplacement.error.code, 'ROBOT_ALREADY_ACTIVE');
  const refusedReplacement = await requestFailure('activate_robot',
    robotPresence('c'.repeat(64), 1), posReplacement.data.device_token, 409);
  assert.equal(refusedReplacement.error.code, 'ROBOT_ALREADY_ACTIVE');
  assert.match(refusedReplacement.error.message, /Arrêtez d’abord cet ancien Robot/);
  await attest(pos.data.device_token, 'c'.repeat(64), 1, false, true);
  const electedCommand = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-elected-pos-01'
  }, pos.data.device_token);
  const originalPhoneLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(originalPhoneLease.data.command.public_id, electedCommand.data.command.public_id);
  await complete(originalPhoneLease.data.command, pos.data.device_token);

  const activatedReplacement = await request('activate_robot', {
    ...robotPresence('c'.repeat(64), 1), replace_verified_same_sim_robot: true
  }, posReplacement.data.device_token);
  assert.equal(activatedReplacement.data.robot_enabled, true);
  assert.equal(activatedReplacement.data.mode, 'ROBOT');
  assert.equal(activatedReplacement.data.replaced_verified_same_sim_robots, 1);
  await attest(pos.data.device_token, 'c'.repeat(64), 1, false, false);
  const transferredCommand = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-transferred-pos-01'
  }, pos.data.device_token);
  const formerPhoneLease = await request('lease_command', {}, pos.data.device_token);
  assert.equal(formerPhoneLease.data.available, false);
  assert.equal(formerPhoneLease.data.standby, true);
  const replacementLease = await request('lease_command', {}, posReplacement.data.device_token);
  assert.equal(replacementLease.data.command.public_id, transferredCommand.data.command.public_id);
  await complete(replacementLease.data.command, posReplacement.data.device_token);

  // Token repair reuses the exact device row. An invalid legacy owner cannot capture the SIM
  // queue, and the distinct REMOTE still creates an order leased only by the repaired ROBOT.
  const repairRobot = await pair({
    node_code: 'OU1', role: 'DAE', mode: 'ROBOT',
    phone_number: '699000011', device_name: 'Robot à réparer'
  });
  const repairRemote = await pair({
    node_code: 'OU1', role: 'DAE', mode: 'REMOTE',
    phone_number: '699000011', device_name: 'Remote de réparation'
  });
  await db.prepare(
    'UPDATE devices SET robot_enabled = 1, sim_verified = 0, sim_fingerprint = ? WHERE device_id = ?'
  ).bind('', repairRemote.data.device_id).run();
  await attest(repairRobot.data.device_token, 'd'.repeat(64), 0);

  const renewed = await pair({
    node_code: 'OU1', role: 'DAE', mode: 'ROBOT',
    phone_number: '699000011', device_name: 'Robot réparé',
    replace_device_id: repairRobot.data.device_id,
    repair_sim_verified: true, repair_sim_fingerprint: 'd'.repeat(64),
    repair_robot_enabled: true, sim_slot: 0
  });
  assert.equal(renewed.data.device_id, repairRobot.data.device_id);
  assert.equal(renewed.data.repaired_device, true);
  const rejectedOldToken = await requestFailure(
    'heartbeat', {}, repairRobot.data.device_token, 401);
  assert.equal(rejectedOldToken.error.code, 'AUTH_INVALID');

  const repairedRemoteCommand = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-repaired-remote-01'
  }, repairRemote.data.device_token);
  assert.equal(repairedRemoteCommand.data.command.robot_ready, true);
  const repairedLease = await request('lease_command', {}, renewed.data.device_token);
  assert.equal(repairedLease.data.command.public_id, repairedRemoteCommand.data.command.public_id);
  await complete(repairedLease.data.command, renewed.data.device_token);

  // A migrated Android profile may not know its old server device id. The verified SIM itself
  // must recover that exact Robot row immediately instead of creating a second queue owner.
  const legacyRobot = await pair({
    node_code: 'LT10', role: 'DAE', mode: 'ROBOT',
    phone_number: '699000012', device_name: 'Robot profil migré'
  });
  const legacyRemote = await pair({
    node_code: 'LT10', role: 'DAE', mode: 'REMOTE',
    phone_number: '699000012', device_name: 'Remote profil migré'
  });
  await attest(legacyRobot.data.device_token, 'e'.repeat(64), 0);
  const legacyRenewed = await pair({
    node_code: 'LT10', role: 'DAE', mode: 'ROBOT',
    phone_number: '699000012', device_name: 'Robot migré réparé',
    repair_sim_verified: true, repair_sim_fingerprint: 'e'.repeat(64),
    repair_robot_enabled: true, sim_slot: 0
  });
  assert.equal(legacyRenewed.data.device_id, legacyRobot.data.device_id);
  assert.equal(legacyRenewed.data.repaired_device, true);
  const legacyOldToken = await requestFailure('heartbeat', {}, legacyRobot.data.device_token, 401);
  assert.equal(legacyOldToken.error.code, 'AUTH_INVALID');
  const legacyRemoteCommand = await request('create_command', {
    request_type: 'TEST_NUMBER', client_request_id: 'integration-legacy-remote-01'
  }, legacyRemote.data.device_token);
  assert.equal(legacyRemoteCommand.data.command.robot_status, 'ONLINE');
  const legacyLease = await request('lease_command', {}, legacyRenewed.data.device_token);
  assert.equal(legacyLease.data.command.public_id, legacyRemoteCommand.data.command.public_id);
  await complete(legacyLease.data.command, legacyRenewed.data.device_token);

  console.log('Cloudflare integration: Remote/Robot, FIFO, solde frais, concurrence atomique et états complets OK');
} finally {
  await mf.dispose();
}

async function pair(payload) {
  return request('pair_device', {...payload, pairing_secret: PAIRING_SECRET});
}

async function attest(token, fingerprint, simSlot, claimRobot = true, expectedEnabled = true) {
  const heartbeat = await request('heartbeat', {
    ...robotPresence(fingerprint, simSlot), robot_enabled: true, claim_robot: claimRobot
  }, token);
  assert.equal(heartbeat.data.robot_enabled, expectedEnabled);
  assert.equal(heartbeat.data.sim_verified, true);
}

async function disableRobot(token, fingerprint, simSlot) {
  const heartbeat = await request('heartbeat', {
    ...robotPresence(fingerprint, simSlot), robot_enabled: false, claim_robot: false
  }, token);
  assert.equal(heartbeat.data.robot_enabled, false);
}

function robotPresence(fingerprint, simSlot) {
  return {
    sim_verified: Boolean(fingerprint), sim_fingerprint: fingerprint, sim_slot: simSlot,
    app_version: 'integration', android_version: 'test', device_model: 'Miniflare'
  };
}

async function complete(command, token, successMessage = 'test SUCCEEDED') {
  const states = command.requires_pin
    ? ['DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT', 'SUCCEEDED']
    : ['DIALING', 'AWAITING_RESULT', 'SUCCEEDED'];
  for (const state of states) {
    const event = await request('command_event', {
      command_id: command.public_id,
      lease_token: command.lease_token,
      state,
      message: state === 'SUCCEEDED' ? successMessage : `test ${state}`
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

async function requestFailure(action, payload, token, expectedStatus) {
  const headers = {'Content-Type': 'application/json', 'X-Device-Token': token};
  const response = await mf.dispatchFetch(`http://blue-magic.test/api?action=${action}`, {
    method: 'POST', headers, body: JSON.stringify(payload)
  });
  const body = await response.json();
  assert.equal(response.status, expectedStatus, JSON.stringify(body));
  assert.equal(body.ok, false, JSON.stringify(body));
  return body;
}

async function rawRequest(action, payload, token) {
  const response = await mf.dispatchFetch(`http://blue-magic.test/api?action=${action}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Device-Token': token},
    body: JSON.stringify(payload)
  });
  return {status: response.status, body: await response.json()};
}
