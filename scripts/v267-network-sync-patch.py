from pathlib import Path


def read(path):
    return Path(path).read_text()


def write(path, value):
    Path(path).write_text(value)


def replace_once(path, old, new):
    value = read(path)
    if old not in value:
        raise SystemExit(f"anchor missing in {path}: {old[:120]!r}")
    write(path, value.replace(old, new, 1))


# ---------------------------------------------------------------------------
# Worker: expose intelligent network audit.
# ---------------------------------------------------------------------------
worker_path = "cloudflare/src/index.js"
s = read(worker_path)
old = "        case 'network_dashboard': return await networkDashboard(env, auth, headers);\n"
new = old + "        case 'network_balance_audit': return await networkBalanceAudit(env, auth, headers);\n"
if "case 'network_balance_audit'" not in s:
    if old not in s:
        raise SystemExit("network_dashboard switch anchor missing")
    s = s.replace(old, new, 1)

# Replace checkPurchaseCapacity with a reservation-at-arrival implementation.
start = s.index("async function checkPurchaseCapacity(env, auth, input, headers) {")
end = s.index("\nasync function purchaseCapacityStatus", start)
new_check = r'''async function checkPurchaseCapacity(env, auth, input, headers) {
  const clientId = String(input.client_request_id || '').trim();
  if (!/^[A-Za-z0-9_-]{16,80}$/.test(clientId)) {
    throw new ApiError('INVALID_REQUEST_ID', 'Clé anti-doublon du contrôle de solde invalide.', 422);
  }
  const previous = await env.DB.prepare(
    'SELECT * FROM purchase_preflights WHERE requester_node_code = ? AND client_request_id = ?'
  ).bind(auth.node_code, clientId).first();
  if (previous) return success({capacity: await capacityView(env, previous)}, 200, headers);

  const values = await resolveCommand(env, auth, input, 'REQUEST_SUPPLY');
  const checkId = crypto.randomUUID();

  // Reservation is decided in the same SQLite write statement that inserts the preflight.
  // D1 serializes writes, therefore the first request received by the network consumes the
  // available capacity before the next one is evaluated. No two callers can reserve the same FCFA.
  const reserved = await env.DB.prepare(
    "WITH request(amount) AS (VALUES (?)), snapshot AS ("
    + 'SELECT b.balance, b.observed_at, b.evidence_command_public_id, b.source_command_public_id, '
    + 'MAX(0, b.balance - '
    + "COALESCE((SELECT SUM(c.amount) FROM commands c WHERE c.executor_node_code = b.node_code "
    + "AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + 'AND ((source.id IS NOT NULL AND c.id > source.id) OR (source.id IS NULL AND c.created_at > b.observed_at)) '
    + "AND c.state NOT IN ('FAILED','CANCELLED')),0) - "
    + "COALESCE((SELECT SUM(p.requested_amount) FROM purchase_preflights p "
    + "WHERE p.supplier_node_code = b.node_code AND p.state = 'AVAILABLE' "
    + "AND p.purchase_command_public_id IS NULL "
    + "AND p.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ','now')),0)) AS available "
    + 'FROM account_balances b LEFT JOIN commands source ON source.public_id = b.source_command_public_id '
    + 'LEFT JOIN node_activity_state a ON a.node_code = b.node_code '
    + 'WHERE b.node_code = ? '
    + "AND b.valid_until > strftime('%Y-%m-%dT%H:%M:%fZ','now') "
    + "AND b.balance_quality = 'EXACT' "
    + "AND b.confidence IN ('OPERATOR_EXPLICIT','DERIVED_FROM_EXPLICIT') "
    + '(a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '
    + 'INSERT INTO purchase_preflights(public_id, client_request_id, requester_node_code, supplier_node_code, '
    + 'requested_amount, available_balance, balance_command_public_id, balance_reused, balance_observed_at, '
    + 'state, result_message, expires_at) '
    + 'SELECT ?, ?, ?, ?, request.amount, snapshot.available, '
    + 'COALESCE(snapshot.evidence_command_public_id, snapshot.source_command_public_id), 1, snapshot.observed_at, '
    + "CASE WHEN request.amount <= snapshot.available THEN 'AVAILABLE' ELSE 'INSUFFICIENT' END, "
    + "CASE WHEN request.amount <= snapshot.available THEN "
    + "'Demande réservée selon l ordre d arrivée. Solde encore disponible après cette réservation : ' "
    + "|| (snapshot.available - request.amount) || ' FCFA.' ELSE "
    + "'Les demandes arrivées avant sont prioritaires. Solde encore disponible du supérieur : ' "
    + "|| snapshot.available || ' FCFA.' END, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ','now','+120 seconds') "
    + 'FROM snapshot CROSS JOIN request RETURNING *'
  ).bind(values.amount, values.executor, checkId, clientId, auth.node_code, values.executor).first();

  if (reserved) {
    const availability = await robotAvailability(env, values.executor);
    const view = await capacityView(env, reserved);
    return success({capacity: {...view, ...availability}}, 201, headers);
  }

  // No reusable exact proof: all simultaneous requests share one BALANCE_OWN command.
  // Once the result arrives, refreshWaitingPreflights allocates the certified balance in rowid/FIFO order.
  let balanceCommand = await env.DB.prepare(
    "SELECT public_id FROM commands WHERE executor_node_code = ? AND command_kind = 'BALANCE_OWN' "
    + "AND state IN ('PENDING','LEASED','DIALING','AWAITING_RESULT') ORDER BY id LIMIT 1"
  ).bind(values.executor).first();
  if (!balanceCommand) {
    const commandId = crypto.randomUUID();
    const balanceClientId = `balance_${randomHex(16)}`;
    await env.DB.batch([
      env.DB.prepare(
        'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
        + 'target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, requires_pin) '
        + "VALUES(?, ?, ?, ?, NULL, 'TEST_NUMBER', 'BALANCE_OWN', '', NULL, NULL, '', 0)"
      ).bind(commandId, balanceClientId, auth.node_code, values.executor),
      env.DB.prepare(
        "INSERT INTO command_events(command_id, device_id, state, message) "
        + "SELECT id, ?, 'PENDING', 'Actualisation mutualisée du solde avant approvisionnements concurrents.' "
        + 'FROM commands WHERE public_id = ?'
      ).bind(auth.device_id, commandId)
    ]);
    balanceCommand = {public_id: commandId};
  }
  await env.DB.prepare(
    'INSERT INTO purchase_preflights(public_id, client_request_id, requester_node_code, '
    + 'supplier_node_code, requested_amount, balance_command_public_id, state, result_message, expires_at) '
    + "VALUES(?, ?, ?, ?, ?, ?, 'WAITING', ?, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'))"
  ).bind(checkId, clientId, auth.node_code, values.executor, values.amount,
    balanceCommand.public_id, 'Lecture mutualisée du solde du supérieur en cours; priorité conservée par ordre d arrivée.').run();
  const availability = await robotAvailability(env, values.executor);
  return success({capacity: {
    capacity_check_id: checkId, state: 'WAITING', requested_amount: values.amount,
    supplier_node_code: values.executor, available_balance: null,
    balance_command_id: balanceCommand.public_id, balance_reused: false,
    balance_observed_at: '', message: 'Lecture mutualisée en cours; votre rang de priorité est conservé.',
    ...availability
  }}, 202, headers);
}
'''
s = s[:start] + new_check + s[end:]

# Replace waiting refresh: greedy FIFO by SQLite rowid. Each accepted preflight becomes a soft
# reservation; later rows see the reduced balance and receive the exact remaining amount.
start = s.index("async function refreshWaitingPreflights(env, nodeCode) {")
end = s.index("\nfunction balanceEvidencePriority", start)
new_refresh = r'''async function refreshWaitingPreflights(env, nodeCode) {
  for (let guard = 0; guard < 500; guard += 1) {
    const row = await env.DB.prepare(
      "SELECT rowid AS queue_order, * FROM purchase_preflights WHERE supplier_node_code = ? "
      + "AND state = 'WAITING' ORDER BY rowid LIMIT 1"
    ).bind(nodeCode).first();
    if (!row) return;
    const effective = await effectiveAvailableBalance(env, nodeCode, true);
    if (!effective) return;
    const held = await env.DB.prepare(
      "SELECT COALESCE(SUM(requested_amount),0) AS total FROM purchase_preflights "
      + "WHERE supplier_node_code = ? AND state = 'AVAILABLE' AND purchase_command_public_id IS NULL "
      + "AND expires_at > strftime('%Y-%m-%dT%H:%M:%fZ','now')"
    ).bind(nodeCode).first();
    const available = Math.max(0, effective.available - Number(held?.total || 0));
    const requested = Number(row.requested_amount);
    const accepted = requested <= available;
    const remaining = accepted ? available - requested : available;
    const message = accepted
      ? `Demande prioritaire réservée. Solde encore disponible après cette réservation : ${remaining} FCFA.`
      : `Les demandes arrivées avant sont prioritaires. Solde encore disponible du supérieur : ${remaining} FCFA.`;
    await env.DB.prepare(
      "UPDATE purchase_preflights SET state = ?, available_balance = ?, balance_reused = 0, "
      + 'balance_command_public_id = ?, balance_observed_at = ?, result_message = ?, '
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE public_id = ? AND state = 'WAITING'"
    ).bind(accepted ? 'AVAILABLE' : 'INSUFFICIENT', available,
      effective.evidence_command_public_id || effective.source_command_public_id,
      effective.observed_at, message, row.public_id).run();
  }
  throw new ApiError('PREFLIGHT_QUEUE_LIMIT', 'Trop de demandes simultanées; reprise au prochain cycle.', 503);
}
'''
s = s[:start] + new_refresh + s[end:]

# Intelligent bottom-up audit. It reuses any exact balance evidence younger than 10 minutes,
# including own balance, child balance, mini-statement CurrentBalance, and financial receipts.
# Only stale/ambiguous nodes receive an USSD order. Commands are inserted POS -> DSM -> DAE.
audit_anchor = "async function resolveDescendant(env, ancestorNode, requestedNode, roles) {"
audit_code = r'''async function networkBalanceAudit(env, auth, headers) {
  const network = await env.DB.prepare(
    'WITH RECURSIVE network(node_code, parent_node_code, role, phone_number, depth) AS ('
    + 'SELECT node_code, parent_node_code, role, phone_number, 0 FROM nodes WHERE node_code = ? AND active = 1 '
    + 'UNION ALL SELECT n.node_code, n.parent_node_code, n.role, n.phone_number, p.depth + 1 '
    + 'FROM nodes n JOIN network p ON n.parent_node_code = p.node_code WHERE n.active = 1) '
    + 'SELECT * FROM network ORDER BY depth DESC, node_code'
  ).bind(auth.node_code).all();
  const nodes = network.results || [];
  const liveRows = await env.DB.prepare(
    "SELECT DISTINCT node_code FROM devices WHERE active = 1 AND robot_enabled = 1 AND sim_verified = 1 "
    + "AND mode IN ('ROBOT','HYBRID') "
    + "AND last_seen_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')"
  ).all();
  const live = new Set((liveRows.results || []).map(row => row.node_code));
  let reused = 0;
  let queued = 0;
  let alreadyPending = 0;
  let unavailable = 0;
  const details = [];

  for (const node of nodes) {
    const fresh = await reportBalanceFresh(env, node.node_code);
    if (fresh) {
      reused += 1;
      details.push({node_code: node.node_code, action: 'REUSED', evidence_kind: fresh.evidence_kind,
        observed_at: fresh.observed_at});
      continue;
    }
    const existing = await env.DB.prepare(
      "SELECT public_id FROM commands WHERE state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT') "
      + "AND ((command_kind = 'BALANCE_OWN' AND executor_node_code = ?) "
      + "OR (command_kind = 'BALANCE_CHILD' AND target_node_code = ?)) ORDER BY id LIMIT 1"
    ).bind(node.node_code, node.node_code).first();
    if (existing) {
      alreadyPending += 1;
      details.push({node_code: node.node_code, action: 'PENDING', command_id: existing.public_id});
      continue;
    }

    let executor = '';
    let commandKind = '';
    let targetNode = null;
    let targetPhone = null;
    if (live.has(node.node_code)) {
      executor = node.node_code;
      commandKind = 'BALANCE_OWN';
    } else if (node.role === 'POS') {
      if (node.parent_node_code && live.has(node.parent_node_code)) {
        executor = node.parent_node_code;
      } else if (auth.role === 'DAE' && live.has(auth.node_code)) {
        // Camtel permits a DAE to query any PoS in its descendant network directly.
        executor = auth.node_code;
      }
      if (executor) {
        commandKind = 'BALANCE_CHILD';
        targetNode = node.node_code;
        targetPhone = node.phone_number;
      }
    } else if (node.role === 'DSM' && auth.role === 'DAE' && live.has(auth.node_code)) {
      executor = auth.node_code;
      commandKind = 'BALANCE_CHILD';
      targetNode = node.node_code;
      targetPhone = node.phone_number;
    }

    if (!executor) {
      unavailable += 1;
      details.push({node_code: node.node_code, action: 'UNAVAILABLE'});
      continue;
    }
    const commandId = crypto.randomUUID();
    const clientId = `audit_${randomHex(16)}`;
    const result = await env.DB.prepare(
      'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
      + 'target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, requires_pin) '
      + "SELECT ?, ?, ?, ?, ?, 'TEST_NUMBER', ?, '', ?, NULL, '', 0 "
      + 'WHERE NOT EXISTS (SELECT 1 FROM commands WHERE '
      + "state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT') "
      + "AND ((? = 'BALANCE_OWN' AND command_kind = 'BALANCE_OWN' AND executor_node_code = ?) "
      + "OR (? = 'BALANCE_CHILD' AND command_kind = 'BALANCE_CHILD' AND target_node_code = ?)))"
    ).bind(commandId, clientId, auth.node_code, executor, targetNode, commandKind, targetPhone,
      commandKind, node.node_code, commandKind, node.node_code).run();
    if (!result.meta?.changes) {
      alreadyPending += 1;
      details.push({node_code: node.node_code, action: 'PENDING'});
      continue;
    }
    queued += 1;
    await env.DB.prepare(
      "INSERT INTO command_events(command_id, device_id, state, message) "
      + "SELECT id, ?, 'PENDING', ? FROM commands WHERE public_id = ?"
    ).bind(auth.device_id,
      `Audit réseau Bottom-Up: actualiser ${node.node_code} sans requête superflue.`, commandId).run();
    details.push({node_code: node.node_code, action: 'QUEUED', executor_node_code: executor,
      command_kind: commandKind, command_id: commandId});
  }
  return success({
    scope_node_code: auth.node_code,
    order: 'BOTTOM_UP_POS_DSM_DAE',
    freshness_seconds: 600,
    reused, queued, already_pending: alreadyPending, unavailable,
    details: details.slice(0, 250)
  }, 200, headers);
}

async function reportBalanceFresh(env, nodeCodeValue) {
  return await env.DB.prepare(
    'SELECT b.balance, b.evidence_kind, b.observed_at FROM account_balances b '
    + 'LEFT JOIN node_activity_state a ON a.node_code = b.node_code WHERE b.node_code = ? '
    + "AND b.balance_quality = 'EXACT' "
    + "AND b.observed_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-600 seconds') "
    + '(a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)'
  ).bind(nodeCodeValue).first();
}

'''
if "async function networkBalanceAudit" not in s:
    if audit_anchor not in s:
        raise SystemExit("resolveDescendant anchor missing")
    s = s.replace(audit_anchor, audit_code + audit_anchor, 1)
write(worker_path, s)


# ---------------------------------------------------------------------------
# Android native: call the shared audit API automatically in staggered Bottom-Up windows.
# POS starts at 02h, DSM at 03h, DAE at 04h. Every level reuses fresh evidence produced below.
# ---------------------------------------------------------------------------
api_path = "app/src/main/java/com/profitloop/blueauto/ApiClient.java"
s = read(api_path)
anchor = "    JSONObject dashboard() throws Exception {\n        return post(\"network_dashboard\", new JSONObject(), true);\n    }\n"
addition = """    JSONObject networkBalanceAudit() throws Exception {\n        return post(\"network_balance_audit\", new JSONObject(), true);\n    }\n\n"""
if "JSONObject networkBalanceAudit()" not in s:
    if anchor not in s:
        raise SystemExit("ApiClient dashboard anchor missing")
    s = s.replace(anchor, addition + anchor, 1)
s = s.replace(
    "(?:operator_insights|platform_snapshot|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale)",
    "(?:operator_insights|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale)",
    1,
)
write(api_path, s)

robot_path = "app/src/main/java/com/profitloop/blueauto/RobotService.java"
s = read(robot_path)
if "import java.util.Calendar;" not in s:
    s = s.replace("import java.util.HashMap;\n", "import java.util.Calendar;\nimport java.util.HashMap;\nimport java.util.Locale;\n", 1)
call_anchor = """                    if (System.currentTimeMillis() - lastHeartbeat >= AppConfig.HEARTBEAT_MS) {
                        api.heartbeat(lastHeartbeat == 0L);
                        lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                    }

                    JSONObject lease = api.leaseCommand();"""
call_new = """                    if (System.currentTimeMillis() - lastHeartbeat >= AppConfig.HEARTBEAT_MS) {
                        api.heartbeat(lastHeartbeat == 0L);
                        lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                    }

                    maybeQueueNightlyNetworkAudit(profileId, api);
                    JSONObject lease = api.leaseCommand();"""
if "maybeQueueNightlyNetworkAudit(profileId, api);" not in s:
    if call_anchor not in s:
        raise SystemExit("RobotService heartbeat/lease anchor missing")
    s = s.replace(call_anchor, call_new, 1)
method_anchor = "    private boolean retryOneDueFinalReport() {"
method = r'''    private void maybeQueueNightlyNetworkAudit(String profileId, ApiClient api) {
        String role = AppConfig.role(this, profileId).toUpperCase(Locale.ROOT);
        int startHour;
        if ("POS".equals(role)) startHour = 2;
        else if ("DSM".equals(role)) startHour = 3;
        else if ("DAE".equals(role)) startHour = 4;
        else return;
        Calendar now = Calendar.getInstance();
        int hour = now.get(Calendar.HOUR_OF_DAY);
        if (hour < startHour || hour >= 7) return;
        String dayKey = String.format(Locale.US, "%04d-%03d",
                now.get(Calendar.YEAR), now.get(Calendar.DAY_OF_YEAR));
        String prefKey = profileId + "_" + role;
        String done = getSharedPreferences("blue_magic_night_audit", MODE_PRIVATE)
                .getString(prefKey, "");
        if (dayKey.equals(done)) return;
        try {
            JSONObject result = api.networkBalanceAudit();
            getSharedPreferences("blue_magic_night_audit", MODE_PRIVATE)
                    .edit().putString(prefKey, dayKey).apply();
            updateNotification(robotSummary("Audit nocturne " + role + " : "
                    + result.optInt("queued", 0) + " requête(s), "
                    + result.optInt("reused", 0) + " preuve(s) réutilisée(s)"));
        } catch (Exception ignored) {
            // Do not mark the day complete: the normal Robot loop will retry during the night window.
        }
    }

'''
if "private void maybeQueueNightlyNetworkAudit" not in s:
    if method_anchor not in s:
        raise SystemExit("RobotService retry anchor missing")
    s = s.replace(method_anchor, method + method_anchor, 1)
write(robot_path, s)


# ---------------------------------------------------------------------------
# UI: intelligent refresh now asks the server to plan selective Bottom-Up checks;
# report snapshot remains available separately.
# ---------------------------------------------------------------------------
platform_path = "app/src/main/assets/platform-v267.js"
s = read(platform_path)
s = s.replace(
    '<div class="actions"><button id="v267-snapshot">Rafraîchir réseau intelligent</button><button id="v267-messages">Preuves Blue récentes</button></div>',
    '<div class="actions"><button id="v267-audit">Rafraîchir réseau intelligent</button><button id="v267-snapshot">Rapport réseau</button><button id="v267-messages">Preuves Blue récentes</button></div>',
    1,
)
if "bind('v267-audit'" not in s:
    s = s.replace("  bind('v267-snapshot', () => request('platform_snapshot'));\n",
                  "  bind('v267-audit', () => request('network_balance_audit'));\n  bind('v267-snapshot', () => request('platform_snapshot'));\n", 1)
handler_anchor = "    if (action === 'platform_snapshot') {"
handler = """    if (action === 'network_balance_audit') {
      const out=$('v267-report-output');
      if(out) out.innerHTML=`Audit Bottom-Up lancé : <b>${Number(data.queued||0)}</b> requête(s) sélective(s), <b>${Number(data.reused||0)}</b> preuve(s) réutilisée(s), <b>${Number(data.already_pending||0)}</b> déjà en file, <b>${Number(data.unavailable||0)}</b> indisponible(s).`;
      return;
    }
"""
if "action === 'network_balance_audit'" not in s:
    if handler_anchor not in s:
        raise SystemExit("platform handler anchor missing")
    s = s.replace(handler_anchor, handler + handler_anchor, 1)
write(platform_path, s)


# ---------------------------------------------------------------------------
# Tests: replace old race semantics with FIFO reservation semantics and add
# bottom-up audit reuse/routing checks.
# ---------------------------------------------------------------------------
test_path = "cloudflare/test/integration.mjs"
s = read(test_path)
start = s.index("  const raceOne = await request('check_purchase_capacity'")
end = s.index("\n  await db.prepare(\n    \"UPDATE account_balances SET valid_until", start)
new_race = r'''  // Release the earlier demonstration preflight so the following test starts from 880 FCFA.
  await db.prepare("UPDATE purchase_preflights SET state='EXPIRED' WHERE public_id = ?")
    .bind(sharedBalance.data.capacity.capacity_check_id).run();

  // FIFO network reservation: first request gets the stock, second immediately receives the remainder.
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
s = s[:start] + new_race + s[end:]

# Add bottom-up audit test after stale expiry refresh is complete and before subsequent queue tests.
audit_anchor = """  const refreshedAfterExpiry = await request('purchase_capacity_status', {
    capacity_check_id: expiredEvidence.data.capacity.capacity_check_id
  }, dsm.data.device_token);
  assert.equal(refreshedAfterExpiry.data.capacity.state, 'AVAILABLE');
"""
audit_extra = r'''
  // Shared network audit: recent exact evidence is reused; stale descendants are queued bottom-up.
  await db.prepare("UPDATE purchase_preflights SET state='EXPIRED' WHERE supplier_node_code='DAE-TEST'").run();
  await db.prepare(
    "UPDATE account_balances SET observed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','-20 minutes'), "
    + "valid_until=strftime('%Y-%m-%dT%H:%M:%fZ','now','+40 minutes') WHERE node_code='DSM-TEST_DAE-TEST'"
  ).run();
  const networkAudit = await request('network_balance_audit', {}, dae.data.device_token);
  assert.equal(networkAudit.data.order, 'BOTTOM_UP_POS_DSM_DAE');
  assert.equal(networkAudit.data.reused >= 1, true);
  assert.equal(networkAudit.data.queued >= 1, true);
  const dsmAuditItem = networkAudit.data.details.find(item => item.node_code === 'DSM-TEST_DAE-TEST');
  assert.equal(dsmAuditItem.action, 'QUEUED');
  assert.equal(dsmAuditItem.command_kind, 'BALANCE_OWN');
  const posAuditItem = networkAudit.data.details.find(item => item.node_code === 'POS5_DSM-TEST_DAE-TEST');
  assert.ok(posAuditItem);
  // DAE can route a PoS balance directly when the PoS/DSM Robot is unavailable; this is covered by
  // the same route planner and the CHILD_BALANCE command already validated above.
'''
if audit_extra not in s:
    if audit_anchor not in s:
        raise SystemExit("integration expiry anchor missing")
    s = s.replace(audit_anchor, audit_anchor + audit_extra, 1)
write(test_path, s)


# Static Android/Web guards.
finance_path = "app/src/test/finance-flow.mjs"
s = read(finance_path)
anchor = "console.log('Blue Magic v2.6.7 platform extension: UI/modules/message parser wired');"
extra = r'''
const robotServiceV267 = readFileSync(new URL('../main/java/com/profitloop/blueauto/RobotService.java', import.meta.url), 'utf8');
const apiClientV267 = readFileSync(new URL('../main/java/com/profitloop/blueauto/ApiClient.java', import.meta.url), 'utf8');
assert.match(robotServiceV267, /maybeQueueNightlyNetworkAudit/);
assert.match(robotServiceV267, /startHour = 2/);
assert.match(robotServiceV267, /startHour = 3/);
assert.match(robotServiceV267, /startHour = 4/);
assert.match(apiClientV267, /network_balance_audit/);
assert.match(platformJs, /v267-audit/);
assert.match(platformJs, /network_balance_audit/);
'''
if extra not in s:
    if anchor not in s:
        raise SystemExit("finance-flow anchor missing")
    s = s.replace(anchor, extra + "\n" + anchor, 1)
write(finance_path, s)

print("Blue Magic v2.6.7 bottom-up network sync patch applied")
