from pathlib import Path

# Applied after v268_followup_patch.py inside CI working tree.
p = Path('cloudflare/src/index.js')
s = p.read_text()
old = """    + \"|| CAST((snapshot.available - request.amount) AS INTEGER) || ' FCFA.' ELSE \""""
new = """    + \"|| CAST(snapshot.available AS INTEGER) || ' FCFA.' ELSE \""""
if old not in s:
    raise SystemExit('quote-only available message anchor missing')
s = s.replace(old, new, 1)
p.write_text(s)

p = Path('cloudflare/test/integration.mjs')
s = p.read_text()
old = '''  // FIFO network reservation: first request gets the stock, second immediately receives the remainder.
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
  assert.match(raceOne.data.capacity.message, /180 FCFA/);
  assert.equal(raceTwo.data.capacity.state, 'INSUFFICIENT');
  assert.equal(raceTwo.data.capacity.available_balance, 180);
  assert.match(raceTwo.data.capacity.message, /180 FCFA/);
  const raceTwoPreview = await requestFailure('preview_command', {
    request_type: 'REQUEST_SUPPLY', amount: '500',
    capacity_check_id: raceTwo.data.capacity.capacity_check_id
  }, dsmTwo.data.device_token, 409);
  assert.equal(raceTwoPreview.error.code, 'BALANCE_INSUFFICIENT');
  const raceOnePreview = await request('preview_command', {
    request_type: 'REQUEST_SUPPLY', amount: '700',
    capacity_check_id: raceOne.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  const raceWinner = await request('create_command', {
    request_type: 'REQUEST_SUPPLY', amount: '700',
    client_request_id: 'integration-capacity-race-create1',
    capacity_check_id: raceOne.data.capacity.capacity_check_id,
    confirmation_fingerprint: raceOnePreview.data.preview.confirmation_fingerprint
  }, dsm.data.device_token);
  const raceCancelled = await request('cancel_command', {
    command_id: raceWinner.data.command.public_id
  }, dsm.data.device_token);
  assert.equal(raceCancelled.data.cancelled, true);
'''
new = '''  // Quote-only concurrency: preflights never reserve or visually reduce stock. Both callers may
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
'''
if old not in s:
    raise SystemExit('legacy FIFO reservation block missing')
s = s.replace(old, new, 1)
p.write_text(s)
