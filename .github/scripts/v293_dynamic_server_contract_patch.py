from pathlib import Path

p=Path('cloudflare/test/integration.mjs')
s=p.read_text(encoding='utf-8')

anchor="""  const leased = await request('lease_command', {}, dae.data.device_token);\n  assert.equal(leased.data.available, true);\n  assert.equal(leased.data.command.ussd_code, '*550*2*699000002*550#');\n  assert.equal(leased.data.command.requires_pin, true);\n\n"""
insert=anchor+"""  // v2.9.3: Remote and Robot must observe the same active queue, and a lost local\n  // LEASED copy may be recovered only by the same device without incrementing the command.\n  const queueSnapshot = await request('queue_snapshot', {}, dae.data.device_token);\n  assert.equal(queueSnapshot.data.active_count >= 1, true);\n  assert.equal(queueSnapshot.data.commands.some(row => row.public_id === created.data.command.public_id\n    && row.state === 'LEASED'), true);\n  const recoveredLease = await request('recover_lease', {\n    command_id: created.data.command.public_id\n  }, dae.data.device_token);\n  assert.equal(recoveredLease.data.recovered, true);\n  assert.equal(recoveredLease.data.verify_only, false);\n  assert.equal(recoveredLease.data.command.public_id, created.data.command.public_id);\n  assert.notEqual(recoveredLease.data.command.lease_token, leased.data.command.lease_token);\n  leased.data.command.lease_token = recoveredLease.data.command.lease_token;\n\n"""
if anchor not in s:
    raise SystemExit('lease recovery insertion anchor missing')
s=s.replace(anchor,insert,1)

anchor="""  for (const state of ['DIALING', 'AWAITING_PIN']) {\n    const event = await request('command_event', {\n      command_id: created.data.command.public_id,\n      lease_token: leased.data.command.lease_token,\n      state,\n      message: `test ${state}`\n    }, dae.data.device_token);\n    assert.equal(event.data.command.state, state);\n  }\n\n"""
insert=anchor+"""  // Once the irreversible DIALING fence has been crossed, recovery is observation only.\n  const verifyOnlyRecovery = await request('recover_lease', {\n    command_id: created.data.command.public_id\n  }, dae.data.device_token);\n  assert.equal(verifyOnlyRecovery.data.recovered, false);\n  assert.equal(verifyOnlyRecovery.data.verify_only, true);\n  assert.equal(verifyOnlyRecovery.data.state, 'AWAITING_PIN');\n\n"""
if anchor not in s:
    raise SystemExit('verify-only insertion anchor missing')
s=s.replace(anchor,insert,1)

anchor="""  assert.equal(status.data.command.state, 'SUCCEEDED');\n  assert.equal(status.data.command.amount, 550);\n\n"""
insert=anchor+"""  const commandCenter = await request('distribution_command_center', {}, dae.data.device_token);\n  assert.equal(commandCenter.data.summary.nodes >= 3, true);\n  assert.equal(Array.isArray(commandCenter.data.nodes), true);\n  assert.equal(Array.isArray(commandCenter.data.anomalies), true);\n  assert.equal(typeof commandCenter.data.service_signal.code, 'string');\n  assert.equal(commandCenter.data.nodes.some(row => row.node_code === 'CE04'), true);\n  assert.equal(commandCenter.data.nodes.some(row => row.node_code === 'DSM12_CE04'), true);\n  assert.equal(commandCenter.data.nodes.some(row => row.node_code === 'POS37_DSM12_CE04'), true);\n\n  const reconciliationCenter = await request('reconciliation_center', {}, dsm.data.device_token);\n  assert.equal(typeof reconciliationCenter.data.summary.matched, 'number');\n  assert.equal(typeof reconciliationCenter.data.summary.bir_only, 'number');\n  assert.equal(Array.isArray(reconciliationCenter.data.transactions), true);\n  assert.equal(Array.isArray(reconciliationCenter.data.blue_only), true);\n\n"""
if anchor not in s:
    raise SystemExit('command center insertion anchor missing')
s=s.replace(anchor,insert,1)

p.write_text(s,encoding='utf-8')
print('Dynamic v2.9.3 server recovery/Command Center integration checks injected')
