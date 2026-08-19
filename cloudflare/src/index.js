import {parseBlueMessage} from './blue-message.mjs';
import {CAMTEL_USSD, canonicalCamtelIdentity, parseCamtelIdentity, publicCamtelCatalog} from './camtel-catalog.mjs';

const API_VERSION = '2.9.3-cloudflare';
const ROBOT_LIVE_WINDOW_MINUTES = 15;
const BALANCE_EVIDENCE_TTL_SECONDS = 3600;
const REPORT_BALANCE_EVIDENCE_TTL_SECONDS = 14 * 3600;
const AUDIT_MAX_OUTSTANDING = 12;
const BALANCE_EVIDENCE_PRIORITY = Object.freeze({
  BALANCE_QUERY: 500,
  CHILD_BALANCE_QUERY: 500,
  HISTORY_RESULT: 450,
  FINANCIAL_RESULT: 400,
  TRANSACTION_DETAIL_RESULT: 300,
  ESTIMATED_TRANSFER: 100
});
const TERMINAL_STATES = new Set(['SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED', 'CANCELLED']);
const EVENT_STATES = new Set([
  'DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT',
  'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'
]);
const VALID_TRANSITIONS = {
  LEASED: new Set(['DIALING', 'FAILED']),
  DIALING: new Set(['AWAITING_PIN', 'AWAITING_RESULT', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED']),
  AWAITING_PIN: new Set(['PIN_SUBMITTED', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED']),
  PIN_SUBMITTED: new Set(['AWAITING_RESULT', 'SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED']),
  AWAITING_RESULT: new Set(['SUCCEEDED', 'FAILED', 'UNKNOWN', 'BLOCKED'])
};

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== '/api' && !url.pathname.startsWith('/api/')) {
      return env.ASSETS.fetch(request);
    }

    const headers = apiHeaders(request, env);
    if (request.method === 'OPTIONS') return new Response(null, {status: 204, headers});
    if (request.method !== 'POST' && request.method !== 'GET') {
      return failure('METHOD_NOT_ALLOWED', 'Méthode HTTP refusée.', 405, headers);
    }

    try {
      const action = (url.searchParams.get('action') || 'health').trim();
      const input = request.method === 'POST' ? await readJson(request) : {};
      if (action === 'health') {
        await env.DB.prepare('SELECT 1 AS online').first();
        return success({service: 'blue-magic-api', version: API_VERSION, database: 'online', capabilities: {commissions: true, commission_override: true, remote_results: true, force_sync: true, network_audit: true, owner_admin: true, super_admin: true, free_ops_cockpit: true, premium_for_all: true, hierarchical_rescue: true, simple_pilotage: true, dae_pro_free: true, region_national_ops_free: true, owner_mock_entitlement: true, accounting: true, tchoronko: true, event_balance: true, offline_sync: true, bir_relay: true, queue_reconciliation: true, lease_recovery: true, distribution_command_center: true, stockout_forecast: true, anomaly_detection: true, operator_incident_inference: true, reconciliation_center: true, effective_modes: ['REMOTE','ROBOT']}}, 200, headers);
      }
      if (action === 'pair_device') return await pairDevice(env, input, headers);

      const auth = await authenticate(request, env);
      switch (action) {
        case 'heartbeat': return await heartbeat(env, auth, input, headers);
        case 'force_sync': return await forceSyncRequest(env, auth, input, headers);
        case 'activate_robot': return await activateRobot(env, auth, input, headers);
        case 'update_device_mode': return await updateDeviceMode(env, auth, input, headers);
        case 'preview_command': return await previewCommand(env, auth, input, headers);
        case 'create_command': return await createCommand(env, auth, input, headers);
        case 'check_purchase_capacity': return await checkPurchaseCapacity(env, auth, input, headers);
        case 'purchase_capacity_status': return await purchaseCapacityStatus(env, auth, input, headers);
        case 'network_dashboard': return await networkDashboard(env, auth, headers);
        case 'network_balance_audit': return await networkBalanceAudit(env, auth, headers);
        case 'operator_catalog': return success({catalog: publicCamtelCatalog()}, 200, headers);
        case 'operator_insights': return await operatorInsights(env, auth, headers);
        case 'record_operator_message': return await recordOperatorMessageApi(env, auth, input, headers);
        case 'sync_local_events': return await syncLocalEvents(env, auth, input, headers);
        case 'relay_register': return await relayRegister(env, auth, input, headers);
        case 'relay_sync': return await relaySync(env, auth, input, headers);
        case 'platform_snapshot': return await platformSnapshot(env, auth, headers);
        case 'ops_cockpit': return await opsCockpit(env, auth, headers);
        case 'ops_assist': return await opsAssist(env, auth, input, headers);
        case 'ops_escalate': return await opsEscalate(env, auth, input, headers);
        case 'ops_resolve': return await opsResolve(env, auth, input, headers);
        case 'owner_ops_cockpit': return await ownerOpsCockpit(request, env, auth, headers);
        case 'owner_ops_resolve': return await ownerOpsResolve(request, env, auth, input, headers);
        case 'commission_policy': return await commissionPolicy(env, auth, headers);
        case 'commission_set_default': return await commissionSetDefault(env, auth, input, headers);
        case 'commission_set_child': return await commissionSetChild(env, auth, input, headers);
        case 'accounting_summary': return await accountingSummary(env, auth, input, headers);
        case 'transaction_ledger': return await transactionLedger(env, auth, input, headers);
        case 'owner_enroll': return await ownerEnroll(request, env, auth, input, headers);
        case 'owner_snapshot': return await ownerSnapshot(request, env, auth, headers);
        case 'owner_transactions': return await ownerTransactions(request, env, auth, input, headers);
        case 'owner_audit': return await ownerAudit(request, env, auth, input, headers);
        case 'owner_control': return await ownerControl(request, env, auth, input, headers);
        case 'owner_assist': return await ownerAssist(request, env, auth, input, headers);
        case 'owner_tchoronko_save': return await ownerTchoronkoSave(request, env, auth, input, headers);
        case 'device_control_poll': return await deviceControlPoll(env, auth, headers);
        case 'device_control_ack': return await deviceControlAck(env, auth, input, headers);
        case 'shadow_enroll': return await shadowEnroll(env, auth, input, headers);
        case 'debt_save': return await debtSave(env, auth, input, headers);
        case 'debt_list': return await debtList(env, auth, headers);
        case 'kyc_save': return await kycSave(env, auth, input, headers);
        case 'mercenary_save': return await mercenarySave(env, auth, input, headers);
        case 'mercenary_list': return await mercenaryList(env, auth, headers);
        case 'mercenary_sale': return await mercenarySale(env, auth, input, headers);
        case 'queue_snapshot': return await queueSnapshot(env, auth, headers);
        case 'recover_lease': return await recoverLease(env, auth, input, headers);
        case 'distribution_command_center': return await distributionCommandCenter(env, auth, headers);
        case 'reconciliation_center': return await reconciliationCenter(env, auth, headers);
        case 'owner_distribution_command_center': return await ownerDistributionCommandCenter(request, env, auth, headers);
        case 'lease_command': return await leaseCommand(env, auth, headers);
        case 'release_command': return await releaseCommand(env, auth, input, headers);
        case 'cancel_command': return await cancelCommand(env, auth, input, headers);
        case 'command_event': return await commandEvent(env, auth, input, headers);
        case 'command_status': return await commandStatus(env, auth, input, headers);
        default: throw new ApiError('UNKNOWN_ACTION', 'Action API inconnue.', 404);
      }
    } catch (error) {
      if (error instanceof ApiError) return failure(error.code, error.message, error.status, headers);
      console.error('BlueMagic API', error instanceof Error ? error.stack : String(error));
      return failure('INTERNAL_ERROR', 'Erreur interne du serveur.', 500, headers);
    }
  }
};

async function pairDevice(env, input, headers) {
  const expected = String(env.PAIRING_SECRET || '');
  const provided = String(input.pairing_secret || '');
  if (expected.length < 24 || !constantTimeEqual(expected, provided)) {
    throw new ApiError('PAIRING_DENIED', 'Secret d’appairage incorrect.', 403);
  }

  const requestedNode = nodeCode(input.node_code);
  const role = String(input.role || '').trim().toUpperCase();
  const mode = String(input.mode || '').trim().toUpperCase();
  const phoneNumber = phone(input.phone_number);
  const deviceName = cleanText(input.device_name || 'Android', 160);
  let parent = String(input.parent_node_code || '').trim().toUpperCase();
  if (!['DAE', 'DSM', 'POS'].includes(role)) throw new ApiError('INVALID_ROLE', 'Rôle invalide.', 422);
  if (!['REMOTE', 'ROBOT', 'HYBRID'].includes(mode)) throw new ApiError('INVALID_MODE', 'Mode invalide.', 422);

  // Existing installations remain repairable even if they predate the current Camtel grammar.
  // New identities, however, must use the official filiation XXY → DSMZ_XXY → POSA_DSMZ_XXY.
  const legacyExact = await env.DB.prepare(
    'SELECT node_code, role, phone_number, parent_node_code FROM nodes WHERE node_code = ? AND phone_number = ?'
  ).bind(requestedNode, phoneNumber).first();
  let node = '';
  let identity = null;
  if (legacyExact && legacyExact.role === role) {
    node = legacyExact.node_code;
    parent = String(legacyExact.parent_node_code || '');
    identity = parseCamtelIdentity(node);
  } else if (role === 'DAE') {
    parent = '';
    identity = canonicalCamtelIdentity(requestedNode, 'DAE', '');
    if (!identity.ok) throw identityApiError(identity.error);
    node = identity.node_code;
  } else {
    const suppliedIdentity = parseCamtelIdentity(requestedNode);
    if (!parent && suppliedIdentity.ok && suppliedIdentity.role === role) {
      parent = suppliedIdentity.parent_node_code;
    }
    if (!parent) {
      throw new ApiError('PARENT_REQUIRED',
        role === 'DSM' ? 'Indiquez le DAE supérieur (ex. OU3).'
          : 'Indiquez le DSM supérieur avec son nom complet (ex. DSM7_OU3).', 422);
    }
    const parentNode = await resolveParentNode(env, parent, role === 'DSM' ? 'DAE' : 'DSM');
    parent = parentNode.node_code;
    identity = canonicalCamtelIdentity(requestedNode, role, parent);
    if (!identity.ok) throw identityApiError(identity.error);
    node = identity.node_code;
  }

  const existing = await env.DB.prepare(
    'SELECT node_code, role, phone_number, parent_node_code FROM nodes WHERE node_code = ?'
  ).bind(node).first();
  if (existing) {
    const same = existing.role === role && existing.phone_number === phoneNumber
      && String(existing.parent_node_code || '') === parent;
    if (!same) throw new ApiError('NODE_IDENTITY_CONFLICT',
      'Cet identifiant Camtel existe avec une autre SIM, un autre rôle ou une autre filiation.', 409);
  } else {
    const phoneOwner = await env.DB.prepare('SELECT node_code FROM nodes WHERE phone_number = ?')
      .bind(phoneNumber).first();
    if (phoneOwner) throw new ApiError('PHONE_ALREADY_USED',
      `Cette SIM est déjà liée à ${phoneOwner.node_code}.`, 409);
    if (role !== 'DAE') {
      throw new ApiError('SUBORDINATE_APPROVAL_REQUIRED',
        role === 'DSM'
          ? 'Le DAE doit d’abord pré-enrôler et valider ce DSM.'
          : 'Le DSM doit d’abord pré-enrôler et valider ce PoS.', 409);
    }
    // Creation of a root DAE remains protected by the global super-admin pairing secret.
    await env.DB.prepare(
      'INSERT INTO nodes(node_code, role, phone_number, parent_node_code, default_commission_bps) VALUES(?, ?, ?, NULL, ?)'
    ).bind(node, role, phoneNumber, role === 'DAE' ? 1000 : role === 'DSM' ? 800 : 0).run();
  }

  // A first DSM/PoS activation must have been approved by its direct superior during the last 48 h.
  // Existing accounts with at least one device can still add/repair devices without a new approval.
  if (role !== 'DAE') {
    const paired = await env.DB.prepare(
      'SELECT 1 AS yes FROM devices WHERE node_code = ? LIMIT 1'
    ).bind(node).first();
    if (!paired) {
      const approval = await env.DB.prepare(
        "SELECT created_at FROM shadow_accounts WHERE node_code = ? "
        + "AND created_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-48 hours') LIMIT 1"
      ).bind(node).first();
      if (!approval) {
        throw new ApiError('SUBORDINATE_APPROVAL_EXPIRED',
          'La validation du supérieur est absente ou a plus de 48 h. Le supérieur doit la renouveler.', 409);
      }
    }
  }

  const repairFingerprint = String(input.repair_sim_fingerprint || '').trim().toLowerCase();
  const repairVerified = input.repair_sim_verified === true
    && /^[a-f0-9]{64}$/.test(repairFingerprint);
  const repairRobot = repairVerified && input.repair_robot_enabled === true
    && ['ROBOT', 'HYBRID'].includes(mode);
  const repairSlot = Number.isInteger(input.sim_slot) && input.sim_slot >= 0 && input.sim_slot <= 3
    ? input.sim_slot : null;

  const requestedReplacement = String(input.replace_device_id || '').trim();
  const explicitReplacement = requestedReplacement
    ? await env.DB.prepare(
      'SELECT device_id, node_code FROM devices WHERE device_id = ? LIMIT 1'
    ).bind(requestedReplacement).first()
    : null;
  const simReplacement = repairRobot
    ? await env.DB.prepare(
      'SELECT device_id, node_code FROM devices WHERE node_code = ? AND active = 1 '
      + 'AND sim_verified = 1 AND sim_fingerprint = ? '
      + 'ORDER BY robot_enabled DESC, last_seen_at DESC LIMIT 1'
    ).bind(node, repairFingerprint).first()
    : null;
  const replacement = simReplacement || explicitReplacement;
  if (replacement && replacement.node_code !== node) {
    throw new ApiError('DEVICE_IDENTITY_CONFLICT',
      'L’appareil à réparer appartient à un autre compte.', 409);
  }

  const deviceId = replacement ? replacement.device_id : crypto.randomUUID();
  const token = randomHex(32);
  const tokenHash = await sha256(token);
  if (replacement) {
    await env.DB.prepare(
      'UPDATE devices SET mode = ?, device_name = ?, token_hash = ?, active = 1, '
      + "robot_enabled = CASE WHEN ? = 'REMOTE' THEN 0 ELSE robot_enabled END, "
      + "last_seen_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE device_id = ?"
    ).bind(mode, deviceName, tokenHash, mode, deviceId).run();
  } else {
    await env.DB.prepare(
      'INSERT INTO devices(device_id, node_code, mode, device_name, token_hash, last_seen_at) '
      + "VALUES(?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
    ).bind(deviceId, node, mode, deviceName, tokenHash).run();
  }

  if (repairRobot) {
    await clearInvalidOrStaleSameSimOwners(env, node, deviceId, repairFingerprint);
    const liveConflict = await liveRobotOwner(env, node, deviceId);
    if (!liveConflict) {
      await env.DB.prepare(
        'UPDATE devices SET robot_enabled = 1, sim_verified = 1, sim_fingerprint = ?, sim_slot = ? '
        + 'WHERE device_id = ?'
      ).bind(repairFingerprint, repairSlot, deviceId).run();
    }
  }

  const official = parseCamtelIdentity(node);
  return success({
    device_id: deviceId, device_token: token, node_code: node,
    parent_node_code: parent, role, mode,
    region_code: official.ok ? official.region_code || '' : '',
    dae_node_code: official.ok ? official.dae_node_code || '' : '',
    dsm_node_code: official.ok ? official.dsm_node_code || '' : '',
    repaired_device: Boolean(replacement)
  }, replacement ? 200 : 201, headers);
}

async function authenticate(request, env) {
  const token = String(request.headers.get('X-Device-Token') || '').trim();
  if (!token) throw new ApiError('AUTH_REQUIRED', 'Jeton appareil requis.', 401);
  const auth = await env.DB.prepare(
    'SELECT d.device_id, d.node_code, d.mode, d.active AS device_active, '
    + 'd.robot_enabled, d.sim_verified, d.sim_fingerprint, d.sim_slot, d.last_seen_at, '
    + 'n.role, n.phone_number, n.parent_node_code, n.active AS node_active '
    + 'FROM devices d JOIN nodes n ON n.node_code = d.node_code '
    + 'WHERE d.token_hash = ? LIMIT 1'
  ).bind(await sha256(token)).first();
  if (!auth || !auth.device_active || !auth.node_active) {
    throw new ApiError('AUTH_INVALID', 'Appareil inconnu ou désactivé.', 401);
  }
  return auth;
}

async function heartbeat(env, auth, input, headers) {
  const simFingerprint = String(input.sim_fingerprint || '').trim().toLowerCase();
  const simVerified = input.sim_verified === true && /^[a-f0-9]{64}$/.test(simFingerprint);
  const wantsRobot = input.robot_enabled === true && simVerified
    && ['ROBOT', 'HYBRID'].includes(auth.mode);
  const claimsRobot = wantsRobot && input.claim_robot === true;
  const simSlot = Number.isInteger(input.sim_slot) && input.sim_slot >= 0 && input.sim_slot <= 3
    ? input.sim_slot : null;
  if (claimsRobot) {
    await claimRobotSlot(env, auth, input, simFingerprint, simSlot, false);
    return success({
      server_time: new Date().toISOString(), node_code: auth.node_code,
      robot_enabled: true, sim_verified: true, robot_claimed: true
    }, 200, headers);
  }

  // A periodic heartbeat preserves only the device already elected by the server. It can never
  // promote a Remote or evict the phone that currently owns the physical SIM route.
  const robotEnabled = wantsRobot && Boolean(auth.robot_enabled);
  await env.DB.prepare(
    "UPDATE devices SET last_seen_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), robot_enabled = ?, "
    + 'sim_verified = ?, sim_fingerprint = ?, sim_slot = ?, '
    + 'app_version = ?, android_version = ?, device_model = ?, offline_pending_events = ?, '
    + 'accessibility_enabled = ?, accessibility_connected = ?, battery_percent = ?, '
    + "last_telemetry_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE device_id = ?"
  ).bind(
    robotEnabled ? 1 : 0,
    simVerified ? 1 : 0,
    simVerified ? simFingerprint : '',
    simSlot,
    cleanText(input.app_version, 40),
    cleanText(input.android_version, 40),
    cleanText(input.device_model, 160),
    Math.max(0, Math.min(100000, Number(input.offline_pending_events || 0))),
    input.accessibility_enabled === true ? 1 : 0,
    input.accessibility_connected === true ? 1 : 0,
    input.battery_percent == null ? null : Math.max(0, Math.min(100, Number(input.battery_percent))),
    auth.device_id
  ).run();
  return success({
    server_time: new Date().toISOString(), node_code: auth.node_code,
    robot_enabled: robotEnabled, sim_verified: simVerified, robot_claimed: false
  }, 200, headers);
}

async function activateRobot(env, auth, input, headers) {
  const simFingerprint = String(input.sim_fingerprint || '').trim().toLowerCase();
  const simVerified = input.sim_verified === true && /^[a-f0-9]{64}$/.test(simFingerprint);
  if (!simVerified) {
    throw new ApiError('ROBOT_SIM_NOT_VERIFIED',
      'Installez et vérifiez d’abord la SIM officielle de ce compte sur ce téléphone.', 409);
  }
  const simSlot = Number.isInteger(input.sim_slot) && input.sim_slot >= 0 && input.sim_slot <= 3
    ? input.sim_slot : null;
  let replacedRobotCount = 0;
  if (input.replace_verified_same_sim_robot === true) {
    replacedRobotCount = await replaceVerifiedSameSimOwner(
      env, auth, input, simFingerprint, simSlot);
  } else {
    await claimRobotSlot(env, auth, input, simFingerprint, simSlot, true);
  }
  return success({
    mode: 'ROBOT', node_code: auth.node_code, robot_enabled: true,
    sim_verified: true, robot_claimed: true,
    replaced_verified_same_sim_robots: replacedRobotCount
  }, 200, headers);
}

async function replaceVerifiedSameSimOwner(env, auth, input, simFingerprint, simSlot) {
  // One SQLite statement transfers ownership and disables only owners carrying the exact same
  // verified SIM attestation. If another verified fingerprint owns the node, NOT EXISTS makes the
  // whole statement a no-op: the previous Robot therefore remains untouched.
  const result = await env.DB.prepare(
    "UPDATE devices SET robot_enabled = CASE WHEN device_id = ? THEN 1 ELSE 0 END, "
    + "mode = CASE WHEN device_id = ? THEN 'ROBOT' ELSE mode END, "
    + 'sim_verified = CASE WHEN device_id = ? THEN 1 ELSE sim_verified END, '
    + 'sim_fingerprint = CASE WHEN device_id = ? THEN ? ELSE sim_fingerprint END, '
    + 'sim_slot = CASE WHEN device_id = ? THEN ? ELSE sim_slot END, '
    + 'app_version = CASE WHEN device_id = ? THEN ? ELSE app_version END, '
    + 'android_version = CASE WHEN device_id = ? THEN ? ELSE android_version END, '
    + 'device_model = CASE WHEN device_id = ? THEN ? ELSE device_model END, '
    + "last_seen_at = CASE WHEN device_id = ? THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now') ELSE last_seen_at END "
    + 'WHERE node_code = ? AND active = 1 AND ('
    + 'device_id = ? OR (device_id <> ? AND robot_enabled = 1 '
    + 'AND sim_verified = 1 AND sim_fingerprint = ?)) '
    + 'AND NOT EXISTS (SELECT 1 FROM devices other WHERE other.node_code = ? '
    + 'AND other.device_id <> ? AND other.active = 1 AND other.robot_enabled = 1 '
    + 'AND other.sim_verified = 1 AND length(other.sim_fingerprint) = 64 '
    + 'AND other.sim_fingerprint <> ?)'
  ).bind(
    auth.device_id,
    auth.device_id,
    auth.device_id,
    auth.device_id, simFingerprint,
    auth.device_id, simSlot,
    auth.device_id, cleanText(input.app_version, 40),
    auth.device_id, cleanText(input.android_version, 40),
    auth.device_id, cleanText(input.device_model, 160),
    auth.device_id,
    auth.node_code,
    auth.device_id, auth.device_id, simFingerprint,
    auth.node_code, auth.device_id, simFingerprint
  ).run();
  const changed = Number(result.meta?.changes || 0);
  if (!changed) {
    throw new ApiError('ROBOT_ALREADY_ACTIVE',
      'Une autre SIM vérifiée possède encore ce Robot. Insérez la SIM officielle dans le slot '
      + 'choisi, vérifiez-la, puis recommencez.', 409);
  }
  return Math.max(0, changed - 1);
}

async function claimRobotSlot(env, auth, input, simFingerprint, simSlot, activateMode) {
  const targetMode = activateMode ? 'ROBOT' : auth.mode;
  if (!['ROBOT', 'HYBRID'].includes(targetMode)) {
    throw new ApiError('NOT_A_ROBOT', 'Passez d’abord ce compte en mode Robot.', 403);
  }
  await clearInvalidOrStaleSameSimOwners(env, auth.node_code, auth.device_id, simFingerprint);
  const result = await env.DB.prepare(
    "UPDATE devices SET mode = ?, robot_enabled = 1, sim_verified = 1, sim_fingerprint = ?, "
    + "sim_slot = ?, app_version = ?, android_version = ?, device_model = ?, "
    + "last_seen_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
    + 'WHERE device_id = ? AND NOT EXISTS ('
    + 'SELECT 1 FROM devices other WHERE other.node_code = ? AND other.device_id <> ? '
    + 'AND other.active = 1 AND other.robot_enabled = 1 '
    + 'AND other.sim_verified = 1 AND length(other.sim_fingerprint) = 64)'
  ).bind(
    targetMode, simFingerprint, simSlot,
    cleanText(input.app_version, 40), cleanText(input.android_version, 40),
    cleanText(input.device_model, 160), auth.device_id, auth.node_code, auth.device_id
  ).run();
  if (!result.meta?.changes) {
    throw new ApiError('ROBOT_ALREADY_ACTIVE',
      'La SIM de ce compte possède déjà un Robot actif sur un autre téléphone. '
      + 'Arrêtez d’abord cet ancien Robot, déplacez la SIM, vérifiez-la ici, puis recommencez.', 409);
  }
}

async function clearInvalidOrStaleSameSimOwners(env, nodeCodeValue, deviceId, simFingerprint) {
  await env.DB.prepare(
    "UPDATE devices SET robot_enabled = 0 WHERE node_code = ? AND device_id <> ? "
    + 'AND active = 1 AND robot_enabled = 1 AND ('
    + 'sim_verified <> 1 OR length(sim_fingerprint) <> 64 OR ('
    + 'sim_fingerprint = ? AND ('
    + "last_seen_at IS NULL OR last_seen_at < strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?))))"
  ).bind(nodeCodeValue, deviceId, simFingerprint,
    `-${ROBOT_LIVE_WINDOW_MINUTES} minutes`).run();
}

async function liveRobotOwner(env, nodeCodeValue, excludedDeviceId = '') {
  return env.DB.prepare(
    'SELECT device_id, app_version, android_version, last_seen_at FROM devices '
    + "WHERE node_code = ? AND device_id <> ? AND mode IN ('ROBOT', 'HYBRID') "
    + 'AND active = 1 AND robot_enabled = 1 AND sim_verified = 1 '
    + "AND length(sim_fingerprint) = 64 AND last_seen_at >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?) "
    + 'ORDER BY last_seen_at DESC LIMIT 1'
  ).bind(nodeCodeValue, excludedDeviceId,
    `-${ROBOT_LIVE_WINDOW_MINUTES} minutes`).first();
}

async function robotAvailability(env, nodeCodeValue) {
  const owner = await liveRobotOwner(env, nodeCodeValue);
  if (owner) {
    return {
      robot_ready: true,
      robot_status: 'ONLINE',
      robot_last_seen_at: owner.last_seen_at || '',
      robot_message: 'Le téléphone Robot détenteur de la SIM est connecté.'
    };
  }
  const configured = await env.DB.prepare(
    'SELECT last_seen_at FROM devices '
    + "WHERE node_code = ? AND mode IN ('ROBOT', 'HYBRID') AND active = 1 "
    + 'AND robot_enabled = 1 AND sim_verified = 1 AND length(sim_fingerprint) = 64 '
    + 'ORDER BY last_seen_at DESC LIMIT 1'
  ).bind(nodeCodeValue).first();
  return {
    robot_ready: false,
    robot_status: configured ? 'STALE' : 'OFFLINE',
    robot_last_seen_at: configured?.last_seen_at || '',
    robot_message: configured
      ? 'Le Robot enregistré ne communique plus. Ouvrez ce téléphone et redémarrez son Robot.'
      : 'Aucun téléphone Robot vérifié ne reçoit actuellement les commandes de cette SIM.'
  };
}

async function updateDeviceMode(env, auth, input, headers) {
  const mode = String(input.mode || '').trim().toUpperCase();
  if (!['REMOTE', 'ROBOT'].includes(mode)) {
    throw new ApiError('INVALID_MODE', 'Le mode doit être REMOTE ou ROBOT.', 422);
  }
  await env.DB.prepare(
    'UPDATE devices SET mode = ?, robot_enabled = CASE WHEN ? = \'REMOTE\' THEN 0 ELSE robot_enabled END, '
    + "last_seen_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE device_id = ?"
  ).bind(mode, mode, auth.device_id).run();
  return success({mode, node_code: auth.node_code}, 200, headers);
}

async function createCommand(env, auth, input, headers) {
  const requestType = String(input.request_type || '').trim().toUpperCase();
  const clientId = String(input.client_request_id || '').trim();
  if (!/^[A-Za-z0-9_-]{16,80}$/.test(clientId)) {
    throw new ApiError('INVALID_REQUEST_ID', 'Clé anti-doublon invalide.', 422);
  }
  const previous = await env.DB.prepare(
    'SELECT public_id, state, created_at, executor_node_code FROM commands '
    + 'WHERE requester_node_code = ? AND client_request_id = ?'
  ).bind(auth.node_code, clientId).first();
  if (previous) {
    try { await env.DB.prepare('INSERT INTO duplicate_request_audit(requester_node_code,existing_command_public_id,client_request_id,existing_state) VALUES(?,?,?,?)')
      .bind(auth.node_code,previous.public_id,clientId,previous.state).run(); } catch (ignored) {}
    const availability = await robotAvailability(env, previous.executor_node_code);
    return success({command: {...previous, ...availability}, duplicate: true}, 200, headers);
  }

  const values = await resolveCommand(env, auth, input, requestType);
  if (requestType === 'REQUEST_SUPPLY') {
    values.capacityCheckId = await requireAvailableCapacity(env, auth, input, values);
  }
  const expectedPreview = await previewFingerprint(values);
  const suppliedPreview = String(input.confirmation_fingerprint || '').trim().toLowerCase();
  if ((values.requiresPin || values.requiresConfirmation) && !/^[a-f0-9]{64}$/.test(suppliedPreview)) {
    throw new ApiError('CONFIRMATION_REQUIRED',
      'Affichez et confirmez d’abord le fournisseur, le bénéficiaire et le montant.', 409);
  }
  if (suppliedPreview && suppliedPreview !== expectedPreview) {
    throw new ApiError('CONFIRMATION_CHANGED',
      'Les numéros ou le montant ont changé depuis la confirmation. Recommencez sans composer.', 409);
  }
  const publicId = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  const insertCommand = values.capacityCheckId
    ? env.DB.prepare(
      'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
      + 'target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, '
      + 'requires_pin, capacity_check_id, requested_base_amount, commission_rate_bps, commission_amount) '
      + 'SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? '
      + 'WHERE EXISTS (SELECT 1 FROM purchase_preflights p '
      + 'JOIN account_balances b ON b.node_code = p.supplier_node_code '
      + 'LEFT JOIN commands source ON source.public_id = b.source_command_public_id '
      + 'WHERE p.public_id = ? AND p.requester_node_code = ? AND p.supplier_node_code = ? '
      + "AND p.requested_amount = ? AND p.state = 'AVAILABLE' "
      + "AND p.expires_at > strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
      + "AND b.valid_until > strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
      + "AND b.confidence IN ('OPERATOR_EXPLICIT','DERIVED_FROM_EXPLICIT') "
      + 'AND ? <= b.balance - COALESCE((SELECT SUM(reserved.amount) FROM commands reserved '
      + "WHERE reserved.executor_node_code = p.supplier_node_code "
      + "AND reserved.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
      + "AND ((source.id IS NOT NULL AND reserved.id > source.id) "
      + "OR (source.id IS NULL AND reserved.created_at > b.observed_at)) "
      + "AND reserved.state NOT IN ('FAILED','CANCELLED')), 0))"
    ).bind(
      publicId, clientId, auth.node_code, values.executor, values.targetNode,
      values.operation, values.commandKind || '', values.commandArgument || '', values.targetPhone,
      values.amount, values.ussd, values.requiresPin, values.capacityCheckId,
      values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0),
      values.capacityCheckId, auth.node_code, values.executor, values.amount, values.amount
    )
    : env.DB.prepare(
      'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
      + 'target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, '
      + 'requires_pin, capacity_check_id, requested_base_amount, commission_rate_bps, commission_amount) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(
      publicId, clientId, auth.node_code, values.executor, values.targetNode,
      values.operation, values.commandKind || '', values.commandArgument || '', values.targetPhone,
      values.amount, values.ussd, values.requiresPin, null,
      values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0)
    );
  let batchResults;
  try {
    batchResults = await env.DB.batch([
      insertCommand,
      env.DB.prepare(
        "INSERT INTO command_events(command_id, device_id, state, message) "
        + "SELECT id, ?, 'PENDING', 'Commande créée et contrôlée par le serveur.' "
        + 'FROM commands WHERE public_id = ?'
      ).bind(auth.device_id, publicId),
      ...(values.capacityCheckId ? [env.DB.prepare(
        "UPDATE purchase_preflights SET state = 'CONSUMED', purchase_command_public_id = ?, "
        + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
        + "WHERE public_id = ? AND state = 'AVAILABLE' "
        + 'AND EXISTS (SELECT 1 FROM commands WHERE public_id = ?)'
      ).bind(publicId, values.capacityCheckId, publicId)] : [])
    ]);
  } catch (error) {
    const duplicate = await env.DB.prepare(
      'SELECT public_id, state, created_at, executor_node_code FROM commands '
      + 'WHERE requester_node_code = ? AND client_request_id = ?'
    ).bind(auth.node_code, clientId).first();
    if (duplicate) {
      try { await env.DB.prepare('INSERT INTO duplicate_request_audit(requester_node_code,existing_command_public_id,client_request_id,existing_state) VALUES(?,?,?,?)')
        .bind(auth.node_code,duplicate.public_id,clientId,duplicate.state).run(); } catch (ignored) {}
      const availability = await robotAvailability(env, duplicate.executor_node_code);
      return success({command: {...duplicate, ...availability}, duplicate: true}, 200, headers);
    }
    throw error;
  }
  if (values.capacityCheckId && !batchResults[0].meta?.changes) {
    const current = await effectiveAvailableBalance(env, values.executor);
    const available = current?.available ?? 0;
    await env.DB.prepare(
      "UPDATE purchase_preflights SET state = 'INSUFFICIENT', available_balance = ?, "
      + "result_message = 'Le stock a diminué avant la création atomique de la commande.', "
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE public_id = ? "
      + "AND state = 'AVAILABLE'"
    ).bind(available, values.capacityCheckId).run();
    throw new ApiError('BALANCE_CHANGED',
      `Le stock disponible a changé : ${available} FCFA. Recommencez la commande.`, 409);
  }
  const availability = await robotAvailability(env, values.executor);
  return success({
    command: {
      public_id: publicId, state: 'PENDING', executor_node_code: values.executor,
      executor_phone: values.executorPhone, target_node_code: values.targetNode,
      target_phone: values.targetPhone,
      operation: values.commandKind || values.operation, amount: values.amount,
      requested_base_amount: values.requestedBaseAmount || values.amount,
      commission_rate_bps: Number(values.commissionRateBps || 0),
      commission_amount: Number(values.commissionAmount || 0),
      created_at: createdAt, updated_at: createdAt,
      ...availability
    },
    duplicate: false
  }, 201, headers);
}

async function previewCommand(env, auth, input, headers) {
  const requestType = String(input.request_type || '').trim().toUpperCase();
  const values = await resolveCommand(env, auth, input, requestType);
  if (requestType === 'REQUEST_SUPPLY') {
    values.capacityCheckId = await requireAvailableCapacity(env, auth, input, values);
  }
  const availability = await robotAvailability(env, values.executor);
  return success({preview: {
    request_type: requestType,
    executor_node_code: values.executor,
    executor_phone: values.executorPhone,
    target_node_code: values.targetNode,
    target_phone: values.targetPhone,
    amount: values.amount,
    requested_base_amount: values.requestedBaseAmount || values.amount,
    commission_rate_bps: Number(values.commissionRateBps || 0),
    commission_amount: Number(values.commissionAmount || 0),
    commission_source: values.commissionSource || '',
    operation: values.commandKind || values.operation,
    requires_pin: Boolean(values.requiresPin),
    dangerous: Boolean(values.requiresConfirmation),
    operation_label: values.operationLabel || '',
    capacity_check_id: values.capacityCheckId || '',
    confirmation_fingerprint: await previewFingerprint(values),
    ...availability
  }}, 200, headers);
}

async function checkPurchaseCapacity(env, auth, input, headers) {
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

  // This step certifies/quotes capacity only. It must NOT reserve or visually deduct stock.
  // The atomic reservation happens only when createCommand inserts the confirmed financial command.
  const reserved = await env.DB.prepare(
    "WITH request(amount) AS (VALUES (?)), snapshot AS ("
    + 'SELECT b.balance, b.observed_at, b.evidence_command_public_id, b.source_command_public_id, '
    + 'MAX(0, b.balance - '
    + "COALESCE((SELECT SUM(c.amount) FROM commands c WHERE c.executor_node_code = b.node_code "
    + "AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + 'AND ((source.id IS NOT NULL AND c.id > source.id) OR (source.id IS NULL AND c.created_at > b.observed_at)) '
    + "AND c.state NOT IN ('FAILED','CANCELLED')),0)) AS available "
    + 'FROM account_balances b LEFT JOIN commands source ON source.public_id = b.source_command_public_id '
    + 'LEFT JOIN node_activity_state a ON a.node_code = b.node_code '
    + 'WHERE b.node_code = ? '
    + "AND b.valid_until > strftime('%Y-%m-%dT%H:%M:%fZ','now') "
    + "AND b.balance_quality = 'EXACT' "
    + "AND b.confidence IN ('OPERATOR_EXPLICIT','DERIVED_FROM_EXPLICIT') "
    + 'AND (a.last_unbalanced_activity_at IS NULL OR a.last_unbalanced_activity_at <= b.observed_at)) '
    + 'INSERT INTO purchase_preflights(public_id, client_request_id, requester_node_code, supplier_node_code, '
    + 'requested_amount, base_amount, commission_rate_bps, commission_amount, available_balance, balance_command_public_id, balance_reused, balance_observed_at, '
    + 'state, result_message, expires_at) '
    + 'SELECT ?, ?, ?, ?, request.amount, ?, ?, ?, snapshot.available, '
    + 'COALESCE(snapshot.evidence_command_public_id, snapshot.source_command_public_id), 1, snapshot.observed_at, '
    + "CASE WHEN request.amount <= snapshot.available THEN 'AVAILABLE' ELSE 'INSUFFICIENT' END, "
    + "CASE WHEN request.amount <= snapshot.available THEN "
    + "'Montant disponible au contrôle. Aucune réservation avant confirmation. Disponible : ' "
    + "|| CAST(snapshot.available AS INTEGER) || ' FCFA.' ELSE "
    + "'Montant insuffisant au contrôle. Disponible du supérieur : ' "
    + "|| CAST(snapshot.available AS INTEGER) || ' FCFA.' END, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ','now','+120 seconds') "
    + 'FROM snapshot CROSS JOIN request RETURNING *'
  ).bind(values.amount, values.executor, checkId, clientId, auth.node_code, values.executor,
    values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0)).first();

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
    + 'supplier_node_code, requested_amount, base_amount, commission_rate_bps, commission_amount, balance_command_public_id, state, result_message, expires_at) '
    + "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, 'WAITING', ?, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'))"
  ).bind(checkId, clientId, auth.node_code, values.executor, values.amount,
    values.requestedBaseAmount || values.amount, Number(values.commissionRateBps || 0), Number(values.commissionAmount || 0),
    balanceCommand.public_id, 'Lecture mutualisée du solde du supérieur en cours; priorité conservée par ordre d arrivée.').run();
  const availability = await robotAvailability(env, values.executor);
  return success({capacity: {
    capacity_check_id: checkId, state: 'WAITING', requested_amount: values.amount,
    base_amount: values.requestedBaseAmount || values.amount, commission_rate_bps: Number(values.commissionRateBps || 0),
    commission_amount: Number(values.commissionAmount || 0),
    supplier_node_code: values.executor, available_balance: null,
    balance_command_id: balanceCommand.public_id, balance_reused: false,
    balance_observed_at: '', message: 'Lecture mutualisée en cours; votre rang de priorité est conservé.',
    ...availability
  }}, 202, headers);
}

async function purchaseCapacityStatus(env, auth, input, headers) {
  const checkId = String(input.capacity_check_id || '').trim();
  const row = await env.DB.prepare(
    'SELECT * FROM purchase_preflights WHERE public_id = ? AND requester_node_code = ?'
  ).bind(checkId, auth.node_code).first();
  if (!row) throw new ApiError('CAPACITY_CHECK_NOT_FOUND', 'Contrôle de solde introuvable.', 404);
  return success({capacity: await capacityView(env, row)}, 200, headers);
}

async function requireAvailableCapacity(env, auth, input, values) {
  const checkId = String(input.capacity_check_id || '').trim();
  if (!checkId) {
    throw new ApiError('BALANCE_CHECK_REQUIRED',
      'Vérifiez d’abord le solde disponible du supérieur.', 409);
  }
  const row = await env.DB.prepare(
    'SELECT * FROM purchase_preflights WHERE public_id = ? AND requester_node_code = ? '
    + 'AND supplier_node_code = ? AND requested_amount = ?'
  ).bind(checkId, auth.node_code, values.executor, values.amount).first();
  if (!row) throw new ApiError('BALANCE_CHECK_CHANGED',
    'Le montant ou le fournisseur a changé depuis le contrôle de solde.', 409);
  const view = await capacityView(env, row);
  if (view.state === 'INSUFFICIENT') {
    throw new ApiError('BALANCE_INSUFFICIENT',
      `Montant indisponible. Solde actuellement utilisable : ${view.available_balance} FCFA.`, 409);
  }
  if (view.state !== 'AVAILABLE') {
    throw new ApiError('BALANCE_CHECK_NOT_READY',
      'La lecture du solde du supérieur n’est pas encore disponible.', 409);
  }
  return checkId;
}

async function capacityView(env, row) {
  let state = row.state;
  if (['WAITING', 'AVAILABLE'].includes(state)
      && Date.parse(row.expires_at || '') <= Date.now()) {
    state = 'EXPIRED';
    await env.DB.prepare(
      "UPDATE purchase_preflights SET state = 'EXPIRED', result_message = ?, "
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE public_id = ? "
      + "AND state IN ('WAITING','AVAILABLE')"
    ).bind('Le contrôle de solde a expiré; relancez la demande.', row.public_id).run();
  }
  return {
    capacity_check_id: row.public_id,
    state,
    requested_amount: Number(row.requested_amount),
    base_amount: Number(row.base_amount || row.requested_amount),
    commission_rate_bps: Number(row.commission_rate_bps || 0),
    commission_amount: Number(row.commission_amount || 0),
    maximum_base_amount: maxBaseForTotal(Number(row.available_balance || 0), Number(row.commission_rate_bps || 0)),
    available_balance: row.available_balance == null ? null : Number(row.available_balance),
    supplier_node_code: row.supplier_node_code,
    balance_command_id: row.balance_command_public_id || '',
    balance_reused: Boolean(row.balance_reused),
    balance_observed_at: row.balance_observed_at || '',
    reservation_applied: false,
    message: state === 'EXPIRED' ? 'Le contrôle de solde a expiré; relancez la demande.'
      : row.result_message || '',
    expires_at: row.expires_at || ''
  };
}

async function effectiveAvailableBalance(env, node, requireReusable = false) {
  const snapshot = await env.DB.prepare(
    'SELECT b.balance, b.observed_at, b.operator_event_at, b.valid_until, b.confidence, b.balance_quality, b.evidence_kind, b.evidence_priority, '
    + 'b.source_command_public_id, b.evidence_command_public_id, c.id AS source_command_id '
    + 'FROM account_balances b '
    + 'LEFT JOIN commands c ON c.public_id = b.source_command_public_id WHERE b.node_code = ?'
  ).bind(node).first();
  if (!snapshot) return null;
  if (requireReusable && (Date.parse(snapshot.valid_until || '') <= Date.now()
      || snapshot.balance_quality !== 'EXACT'
      || !['OPERATOR_EXPLICIT', 'DERIVED_FROM_EXPLICIT'].includes(snapshot.confidence))) return null;
  if (requireReusable) {
    const activity = await env.DB.prepare(
      'SELECT last_unbalanced_activity_at FROM node_activity_state WHERE node_code = ?'
    ).bind(node).first();
    const evidenceAt = snapshot.operator_event_at || snapshot.observed_at || '';
    if (activity?.last_unbalanced_activity_at
        && Date.parse(activity.last_unbalanced_activity_at) > Date.parse(evidenceAt)) return null;
  }
  const reserved = await env.DB.prepare(
    "SELECT COALESCE(SUM(amount), 0) AS total FROM commands WHERE executor_node_code = ? "
    + "AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + 'AND ((? IS NOT NULL AND id > ?) OR (? IS NULL AND created_at > ?)) '
    + "AND state NOT IN ('FAILED','CANCELLED')"
  ).bind(node, snapshot.source_command_id, snapshot.source_command_id,
    snapshot.source_command_id, snapshot.observed_at).first();
  return {available: Math.max(0, Number(snapshot.balance) - Number(reserved?.total || 0)),
    observed_at: snapshot.observed_at, valid_until: snapshot.valid_until,
    confidence: snapshot.confidence,
    source_command_public_id: snapshot.source_command_public_id,
    evidence_command_public_id: snapshot.evidence_command_public_id};
}

async function networkBalanceAudit(env, auth, headers) {
  const network = await env.DB.prepare(
    'WITH RECURSIVE network(node_code, parent_node_code, role, phone_number, depth) AS ('
    + 'SELECT node_code, parent_node_code, role, phone_number, 0 FROM nodes WHERE node_code = ? AND active = 1 '
    + 'UNION ALL SELECT n.node_code, n.parent_node_code, n.role, n.phone_number, p.depth + 1 '
    + 'FROM nodes n JOIN network p ON n.parent_node_code = p.node_code WHERE n.active = 1) '
    + 'SELECT * FROM network'
  ).bind(auth.node_code).all();
  const nodes = network.results || [];
  const liveRows = await env.DB.prepare(
    "SELECT DISTINCT node_code FROM devices WHERE active = 1 AND robot_enabled = 1 AND sim_verified = 1 "
    + "AND mode IN ('ROBOT','HYBRID') "
    + "AND last_seen_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes')"
  ).all();
  const live = new Set((liveRows.results || []).map(row => row.node_code));
  const candidates = [];
  let reused = 0;
  const details = [];
  for (const node of nodes) {
    const status = await reportBalanceStatus(env, node.node_code);
    if (status.reusable) {
      reused += 1;
      details.push({node_code: node.node_code, action: 'REUSED', priority: status.priority,
        evidence_kind: status.evidence_kind, evidence_at: status.evidence_at,
        observed_at: status.observed_at});
    } else {
      candidates.push({...node, audit_status: status});
    }
  }
  candidates.sort((left, right) => {
    const priority = left.audit_status.priority_rank - right.audit_status.priority_rank;
    if (priority) return priority;
    const depth = Number(right.depth || 0) - Number(left.depth || 0);
    return depth || String(left.node_code).localeCompare(String(right.node_code));
  });

  const outstandingRow = await env.DB.prepare(
    "SELECT COUNT(*) AS total FROM commands WHERE requester_node_code = ? "
    + "AND client_request_id LIKE 'audit_%' "
    + "AND state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT')"
  ).bind(auth.node_code).first();
  let budget = Math.max(0, AUDIT_MAX_OUTSTANDING - Number(outstandingRow?.total || 0));
  let queued = 0;
  let alreadyPending = 0;
  let unavailable = 0;
  let deferred = 0;

  for (const node of candidates) {
    const existing = await env.DB.prepare(
      "SELECT public_id FROM commands WHERE state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT') "
      + "AND ((command_kind = 'BALANCE_OWN' AND executor_node_code = ?) "
      + "OR (command_kind = 'BALANCE_CHILD' AND target_node_code = ?)) ORDER BY id LIMIT 1"
    ).bind(node.node_code, node.node_code).first();
    if (existing) {
      alreadyPending += 1;
      details.push({node_code: node.node_code, action: 'PENDING', priority: node.audit_status.priority,
        command_id: existing.public_id});
      continue;
    }
    if (budget <= 0) {
      deferred += 1;
      details.push({node_code: node.node_code, action: 'DEFERRED', priority: node.audit_status.priority});
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
      details.push({node_code: node.node_code, action: 'UNAVAILABLE', priority: node.audit_status.priority});
      continue;
    }
    const executorOutstanding = await env.DB.prepare(
      "SELECT COUNT(*) AS total FROM commands WHERE executor_node_code = ? "
      + "AND client_request_id LIKE 'audit_%' "
      + "AND state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT')"
    ).bind(executor).first();
    if (Number(executorOutstanding?.total || 0) >= AUDIT_MAX_OUTSTANDING) {
      deferred += 1;
      details.push({node_code: node.node_code, action: 'DEFERRED', priority: node.audit_status.priority,
        executor_node_code: executor});
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
      details.push({node_code: node.node_code, action: 'PENDING', priority: node.audit_status.priority});
      continue;
    }
    budget -= 1;
    queued += 1;
    await env.DB.prepare(
      "INSERT INTO command_events(command_id, device_id, state, message) "
      + "SELECT id, ?, 'PENDING', ? FROM commands WHERE public_id = ?"
    ).bind(auth.device_id,
      `Audit ${node.audit_status.priority} Bottom-Up: actualiser ${node.node_code} sans requête superflue.`, commandId).run();
    details.push({node_code: node.node_code, action: 'QUEUED', priority: node.audit_status.priority,
      executor_node_code: executor, command_kind: commandKind, command_id: commandId});
  }

  const identity = parseCamtelIdentity(auth.node_code);
  return success({
    scope_node_code: auth.node_code,
    region_code: identity.ok ? identity.region_code || '' : '',
    dae_node_code: identity.ok ? identity.dae_node_code || '' : '',
    order: 'PRIORITY_THEN_BOTTOM_UP_POS_DSM_DAE',
    report_freshness_seconds: REPORT_BALANCE_EVIDENCE_TTL_SECONDS,
    finance_freshness_seconds: BALANCE_EVIDENCE_TTL_SECONDS,
    max_outstanding_per_scope: AUDIT_MAX_OUTSTANDING,
    reused, queued, already_pending: alreadyPending, unavailable, deferred,
    complete: deferred === 0,
    details: details.slice(0, 500)
  }, 200, headers);
}

async function reportBalanceStatus(env, nodeCodeValue) {
  const row = await env.DB.prepare(
    'SELECT b.balance, b.evidence_kind, b.balance_quality, b.observed_at, b.operator_event_at, '
    + 'a.last_financial_activity_at, a.last_unbalanced_activity_at '
    + 'FROM account_balances b LEFT JOIN node_activity_state a ON a.node_code=b.node_code '
    + 'WHERE b.node_code=?'
  ).bind(nodeCodeValue).first();
  if (!row) return {reusable: false, priority: 'P1_BLIND', priority_rank: 1,
    evidence_kind: '', observed_at: '', evidence_at: ''};
  const evidenceAt = row.operator_event_at || row.observed_at || '';
  const unbalanced = Boolean(row.last_unbalanced_activity_at && evidenceAt
    && Date.parse(row.last_unbalanced_activity_at) > Date.parse(evidenceAt));
  if (unbalanced || row.balance_quality === 'NEEDS_RECHECK') {
    return {...row, reusable: false, priority: 'P0_RECHECK', priority_rank: 0,
      evidence_at: evidenceAt};
  }
  if (row.balance_quality !== 'EXACT') {
    return {...row, reusable: false, priority: 'P1_BLIND', priority_rank: 1,
      evidence_at: evidenceAt};
  }
  const ageMs = evidenceAt ? Date.now() - Date.parse(evidenceAt) : Number.POSITIVE_INFINITY;
  if (ageMs <= REPORT_BALANCE_EVIDENCE_TTL_SECONDS * 1000) {
    return {...row, reusable: true, priority: 'P2_RECENT', priority_rank: 2,
      evidence_at: evidenceAt};
  }
  const activeRecently = row.last_financial_activity_at
    && Date.now() - Date.parse(row.last_financial_activity_at) <= 48 * 3600 * 1000;
  return {...row, reusable: false,
    priority: activeRecently ? 'P2_ACTIVE_STALE' : 'P3_DORMANT_STALE',
    priority_rank: activeRecently ? 2 : 3, evidence_at: evidenceAt};
}

async function resolveDescendant(env, ancestorNode, requestedNode, roles) {
  const target = String(requestedNode || '').trim().toUpperCase();
  if (!target) return null;
  const row = await env.DB.prepare(
    'WITH RECURSIVE subtree(node_code) AS (SELECT ? UNION ALL '
    + 'SELECT n.node_code FROM nodes n JOIN subtree s ON n.parent_node_code = s.node_code WHERE n.active = 1) '
    + 'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code FROM subtree s '
    + 'JOIN nodes n ON n.node_code = s.node_code WHERE n.node_code = ? AND n.node_code <> ? LIMIT 1'
  ).bind(ancestorNode, target, ancestorNode).first();
  return row && roles.includes(row.role) ? row : null;
}

async function resolveCommand(env, auth, input, requestType) {
  const requester = auth.node_code;
  if (requestType === 'REQUEST_SUPPLY') {
    if (!['DSM', 'POS'].includes(auth.role) || !auth.parent_node_code) {
      throw new ApiError('REQUEST_NOT_ALLOWED', 'Ce compte ne peut pas demander une recharge supérieure.', 403);
    }
    const value = amount(input.amount);
    const parent = await env.DB.prepare(
      'SELECT node_code, phone_number FROM nodes WHERE node_code = ? AND active = 1'
    ).bind(auth.parent_node_code).first();
    if (!parent) {
      throw new ApiError('PARENT_NOT_FOUND', 'Le fournisseur supérieur actif est introuvable.', 422);
    }
    const policy = await commissionRateFor(env, parent.node_code, requester);
    const quote = commissionQuote(value, policy.rate_bps);
    return {
      executor: parent.node_code, executorPhone: parent.phone_number,
      targetNode: requester, targetPhone: auth.phone_number,
      amount: quote.total_amount, requestedBaseAmount: value,
      commissionRateBps: policy.rate_bps, commissionAmount: quote.commission_amount,
      commissionSource: policy.source, operation: 'DISTRIBUTION_TRANSFER',
      ussd: CAMTEL_USSD.distributionTransfer(auth.phone_number, quote.total_amount), requiresPin: 1
    };
  }
  if (requestType === 'SUPPLY_CHILD') {
    if (!['DAE', 'DSM'].includes(auth.role)) {
      throw new ApiError('REQUEST_NOT_ALLOWED', 'Seul un DAE ou DSM peut approvisionner un enfant.', 403);
    }
    const childRole = auth.role === 'DAE' ? 'DSM' : 'POS';
    const child = await resolveDirectChild(env, requester, input.target_node_code, childRole);
    if (!child) throw new ApiError('CHILD_NOT_FOUND', 'Ce compte n’est pas un enfant direct actif.', 422);
    const value = amount(input.amount);
    let policy = await commissionRateFor(env, requester, child.node_code);
    if (input.commission_rate_bps !== undefined && input.commission_rate_bps !== null && String(input.commission_rate_bps) !== '') {
      const oneOffRate = Number(input.commission_rate_bps);
      if (!Number.isInteger(oneOffRate) || oneOffRate < 0 || oneOffRate > 5000) {
        throw new ApiError('INVALID_COMMISSION_RATE', 'Le taux de commission de cet envoi doit être compris entre 0 et 50 %.', 422);
      }
      policy = {rate_bps: oneOffRate, source: 'TRANSACTION_OVERRIDE'};
    }
    const quote = commissionQuote(value, policy.rate_bps);
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: child.node_code, targetPhone: child.phone_number, amount: quote.total_amount,
      requestedBaseAmount: value, commissionRateBps: policy.rate_bps,
      commissionAmount: quote.commission_amount, commissionSource: policy.source,
      operation: 'DISTRIBUTION_TRANSFER',
      ussd: CAMTEL_USSD.distributionTransfer(child.phone_number, quote.total_amount), requiresPin: 1
    };
  }
  if (requestType === 'RETAIL_SALE') {
    if (auth.role !== 'POS') throw new ApiError('REQUEST_NOT_ALLOWED', 'Vente détail réservée aux PoS.', 403);
    const targetPhone = phone(input.target_phone);
    const value = amount(input.amount);
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: null, targetPhone, amount: value,
      operation: 'RETAIL_TRANSFER', ussd: CAMTEL_USSD.retailTransfer(targetPhone, value), requiresPin: 1
    };
  }
  if (requestType === 'TEST_NUMBER') {
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: null, targetPhone: null, amount: null,
      operation: 'TEST_NUMBER', ussd: CAMTEL_USSD.testNumber(), requiresPin: 0
    };
  }
  if (requestType === 'CHECK_BALANCE' || requestType === 'LAST_TRANSACTIONS') {
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: null, targetPhone: null, amount: null,
      operation: 'TEST_NUMBER',
      commandKind: requestType === 'CHECK_BALANCE' ? 'BALANCE_OWN' : 'HISTORY_LAST5',
      commandArgument: '', ussd: '', requiresPin: 0
    };
  }
  if (requestType === 'RESET_PIN_SELF' || requestType === 'MODIFY_PIN_LOCAL') {
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: requester, targetPhone: auth.phone_number, amount: null,
      operation: 'TEST_NUMBER', commandKind: 'TRANSACTION_DETAIL',
      commandArgument: requestType === 'RESET_PIN_SELF' ? 'BM_RESET_PIN_SELF' : 'BM_MODIFY_PIN_LOCAL',
      ussd: '', requiresPin: 0, requiresConfirmation: 0,
      operationLabel: requestType === 'RESET_PIN_SELF' ? 'Demander le reset PIN' : 'Modifier le PIN Camtel localement'
    };
  }
  if (requestType === 'TRANSACTION_DETAILS') {
    const transactionId = String(input.transaction_id || '').trim();
    if (!/^[A-Za-z0-9_-]{6,64}$/.test(transactionId)) {
      throw new ApiError('INVALID_TRANSACTION_ID', 'Identifiant de transaction invalide.', 422);
    }
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: null, targetPhone: null, amount: null,
      operation: 'TEST_NUMBER', commandKind: 'TRANSACTION_DETAIL',
      commandArgument: transactionId, ussd: '', requiresPin: 0
    };
  }
  if (requestType === 'CHILD_BALANCE') {
    if (!['DAE', 'DSM'].includes(auth.role)) {
      throw new ApiError('REQUEST_NOT_ALLOWED', 'Ce rôle ne supervise aucun solde enfant.', 403);
    }
    const reference = nodeCode(input.target_node_code);
    let child;
    if (auth.role === 'DAE') {
      if (/^POS[1-9]\d{0,3}$/.test(reference)) {
        throw new ApiError('POS_FULL_NAME_REQUIRED',
          'Un DAE doit désigner directement un PoS par son nom complet, ex. POS16_DSM7_OU3.', 422);
      }
      if (/^DSM[1-9]\d{0,2}$/.test(reference)) {
        child = await resolveDirectChild(env, requester, reference, 'DSM');
      } else {
        child = await resolveDescendant(env, requester, reference, ['DSM', 'POS']);
      }
    } else {
      child = await resolveDirectChild(env, requester, reference, 'POS');
    }
    if (!child) throw new ApiError('CHILD_NOT_FOUND', 'Ce compte n’est pas dans la flotte supervisée active.', 422);
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: child.node_code, targetPhone: child.phone_number, amount: null,
      operation: 'TEST_NUMBER', commandKind: 'BALANCE_CHILD', commandArgument: '',
      ussd: '', requiresPin: 0
    };
  }
  const childAdminKinds = {
    INIT_CHILD_PIN_RESET: ['INIT_CHILD_PIN_RESET', 'Initier la réinitialisation du PIN enfant'],
    SUSPEND_CHILD: ['SUSPEND_CHILD', 'Suspendre l’enfant'],
    REACTIVATE_CHILD: ['REACTIVATE_CHILD', 'Réactiver l’enfant suspendu'],
    FREEZE_CHILD: ['FREEZE_CHILD', 'Geler la SIM enfant'],
    REACTIVATE_FROZEN_CHILD: ['REACTIVATE_FROZEN_CHILD', 'Réactiver la SIM enfant gelée']
  };
  if (requestType in childAdminKinds) {
    if (!['DAE', 'DSM'].includes(auth.role)) {
      throw new ApiError('REQUEST_NOT_ALLOWED', 'Ce rôle ne gère aucun compte enfant.', 403);
    }
    const childRole = auth.role === 'DAE' ? 'DSM' : 'POS';
    const child = await resolveDirectChild(env, requester, input.target_node_code, childRole);
    if (!child) throw new ApiError('CHILD_NOT_FOUND', 'Ce compte n’est pas un enfant direct actif.', 422);
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: child.node_code, targetPhone: child.phone_number, amount: null,
      operation: 'TEST_NUMBER', commandKind: childAdminKinds[requestType][0],
      commandArgument: '', ussd: '', requiresPin: 0, requiresConfirmation: 1,
      operationLabel: childAdminKinds[requestType][1]
    };
  }
  if (requestType === 'FREEZE_SELF') {
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: requester, targetPhone: auth.phone_number, amount: null,
      operation: 'TEST_NUMBER', commandKind: 'FREEZE_SELF', commandArgument: '',
      ussd: '', requiresPin: 0, requiresConfirmation: 1,
      operationLabel: 'Geler ma propre SIM en cas de vol ou perte'
    };
  }
  throw new ApiError('INVALID_REQUEST_TYPE', 'Type de commande inconnu.', 422);
}


async function queueSnapshot(env, auth, headers) {
  const rows = await env.DB.prepare(
    "SELECT public_id,requester_node_code,executor_node_code,target_node_code,operation,command_kind,target_phone,amount,requested_base_amount,commission_rate_bps,commission_amount,state,result_message,operator_transaction_id,created_at,started_at,completed_at,updated_at "
    + "FROM commands WHERE requester_node_code=? OR executor_node_code=? OR target_node_code=? "
    + "ORDER BY CASE WHEN state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT') THEN 0 ELSE 1 END,id DESC LIMIT 80"
  ).bind(auth.node_code,auth.node_code,auth.node_code).all();
  const commands=(rows.results||[]).map(commandView);
  const active=commands.filter(c=>!TERMINAL_STATES.has(c.state));
  const pending=active.filter(c=>c.state==='PENDING');
  let oldest=0;
  for(const row of active){const age=row.created_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.created_at))/1000)):0;if(age>oldest)oldest=age;}
  return success({node_code:auth.node_code,generated_at:new Date().toISOString(),server_time_ms:Date.now(),pending_count:pending.length,active_count:active.length,oldest_pending_age_seconds:oldest,commands},200,headers);
}

async function recoverLease(env, auth, input, headers) {
  const publicId=String(input.command_id||'').trim();
  if(!publicId)throw new ApiError('COMMAND_REQUIRED','Commande à récupérer requise.',422);
  const current=await env.DB.prepare(
    'SELECT * FROM commands WHERE public_id=? AND executor_node_code=?'
  ).bind(publicId,auth.node_code).first();
  if(!current)throw new ApiError('COMMAND_NOT_FOUND','Commande introuvable pour ce Robot.',404);
  if(current.state!=='LEASED'){
    const verifyOnly=['DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT'].includes(current.state);
    return success({recovered:false,verify_only:verifyOnly,state:current.state,command:commandView(current)},200,headers);
  }
  if(!current.leased_by_device_id || current.leased_by_device_id!==auth.device_id){
    return success({recovered:false,verify_only:false,state:current.state,reason:'LEASE_OWNED_BY_ANOTHER_DEVICE'},200,headers);
  }
  const leaseToken=randomHex(24),hash=await sha256(leaseToken);
  const command=await env.DB.prepare(
    "UPDATE commands SET lease_token_hash=?,leased_until=strftime('%Y-%m-%dT%H:%M:%fZ','now','+120 seconds'),last_recovery_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
    + "WHERE id=? AND state='LEASED' AND leased_by_device_id=? RETURNING *"
  ).bind(hash,current.id,auth.device_id).first();
  if(!command)throw new ApiError('COMMAND_RACE','La commande a changé pendant la récupération.',409);
  await env.DB.prepare("INSERT INTO command_events(command_id,device_id,state,message) VALUES(?,?,'LEASED','Lease restauré sur le même appareil après perte de la copie locale; aucune recomposition préalable.')")
    .bind(command.id,auth.device_id).run();
  command.executor_phone=auth.phone_number;command.integrity_version=3;
  const integrityDigest=await commandDigest(command);
  return success({recovered:true,verify_only:false,command:{
    public_id:command.public_id,lease_token:leaseToken,requester_node_code:command.requester_node_code,
    executor_node_code:command.executor_node_code,executor_phone:command.executor_phone,
    target_node_code:command.target_node_code,operation:command.operation,command_kind:command.command_kind||'',
    command_argument:command.command_argument||'',target_phone:command.target_phone,amount:command.amount,
    requested_base_amount:command.requested_base_amount,commission_rate_bps:Number(command.commission_rate_bps||0),
    commission_amount:Number(command.commission_amount||0),ussd_code:command.ussd_code,requires_pin:Boolean(command.requires_pin),
    integrity_version:3,integrity_digest:integrityDigest
  }},200,headers);
}

function commandCenterRow(row){
  const balance=row.balance==null?null:Number(row.balance),out7=Number(row.outflow_7d||0),daily=out7/7;
  const daysCover=balance==null||daily<=0?null:Math.round((balance/daily)*10)/10;
  const terminal24=Number(row.success_24h||0)+Number(row.bad_24h||0);
  const failRate=terminal24?Math.round(Number(row.bad_24h||0)*1000/terminal24)/10:0;
  const balanceAge=row.balance_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.balance_at))/1000)):null;
  const robotAge=row.robot_last_seen_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.robot_last_seen_at))/1000)):null;
  const queueAge=row.oldest_queue_at?Math.max(0,Math.floor((Date.now()-Date.parse(row.oldest_queue_at))/1000)):0;
  const anomalies=[];
  if(daysCover!=null&&daysCover<1)anomalies.push({code:'STOCKOUT_RISK',severity:'CRITICAL',message:'Couverture estimée inférieure à 1 jour.'});
  else if(daysCover!=null&&daysCover<3)anomalies.push({code:'STOCKOUT_RISK',severity:'WARN',message:'Couverture estimée inférieure à 3 jours.'});
  if(queueAge>900)anomalies.push({code:'QUEUE_STALE',severity:queueAge>3600?'CRITICAL':'WARN',message:'Commande active trop ancienne.'});
  if(terminal24>=5&&failRate>=20)anomalies.push({code:'FAILURE_SPIKE',severity:failRate>=50?'CRITICAL':'WARN',message:`Taux d'échec/à vérifier ${failRate} % sur 24 h.`});
  if(Number(row.duplicate_24h||0)>=3)anomalies.push({code:'DUPLICATE_SPIKE',severity:'WARN',message:`${Number(row.duplicate_24h)} tentative(s) anti-doublon sur 24 h.`});
  if(balanceAge==null||balanceAge>6*3600)anomalies.push({code:'BALANCE_STALE',severity:'INFO',message:'Preuve de solde ancienne ou absente.'});
  if(row.robot_enabled&&robotAge!=null&&robotAge>15*60)anomalies.push({code:'ROBOT_STALE',severity:'CRITICAL',message:'Robot déclaré actif mais télémétrie ancienne.'});
  if(row.robot_enabled&&row.accessibility_enabled&&!row.accessibility_connected)anomalies.push({code:'ACCESSIBILITY_DISCONNECTED',severity:'WARN',message:'Accessibilité autorisée mais service Android non connecté.'});
  return {...row,balance,outflow_7d:out7,daily_outflow_estimate:Math.round(daily*100)/100,days_cover:daysCover,stockout:daysCover==null?'UNKNOWN':daysCover<1?'CRITICAL':daysCover<3?'WATCH':'COMFORTABLE',failure_rate_24h:failRate,balance_age_seconds:balanceAge,robot_age_seconds:robotAge,oldest_queue_age_seconds:queueAge,anomalies};
}

async function distributionCommandCenterCore(env, rootNode, national=false) {
  const nodeSql=national
    ? "SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.default_commission_bps,n.inbound_commission_bps FROM nodes n WHERE n.active=1"
    : "WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree t ON n.parent_node_code=t.node_code WHERE n.active=1) SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.default_commission_bps,n.inbound_commission_bps FROM nodes n JOIN tree t ON t.node_code=n.node_code WHERE n.active=1";
  const nodes=national?(await env.DB.prepare(nodeSql).all()).results||[]:(await env.DB.prepare(nodeSql).bind(rootNode).all()).results||[];
  const output=[];
  for(const n of nodes){
    const balance=await env.DB.prepare('SELECT balance,balance_quality,evidence_kind,COALESCE(operator_event_at,observed_at) AS balance_at,last_transaction_id FROM account_balances WHERE node_code=?').bind(n.node_code).first();
    const flow=await env.DB.prepare("SELECT COALESCE(SUM(CASE WHEN state='SUCCEEDED' AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') THEN amount ELSE 0 END),0) outflow_7d,COALESCE(SUM(CASE WHEN created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') AND state='SUCCEEDED' THEN 1 ELSE 0 END),0) success_24h,COALESCE(SUM(CASE WHEN created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') AND state IN ('FAILED','UNKNOWN','BLOCKED') THEN 1 ELSE 0 END),0) bad_24h FROM commands WHERE executor_node_code=? AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").bind(n.node_code).first();
    const queue=await env.DB.prepare("SELECT COUNT(*) queue_count,MIN(created_at) oldest_queue_at FROM commands WHERE executor_node_code=? AND state IN ('PENDING','LEASED','DIALING','AWAITING_PIN','PIN_SUBMITTED','AWAITING_RESULT')").bind(n.node_code).first();
    const dev=await env.DB.prepare("SELECT robot_enabled,accessibility_enabled,accessibility_connected,offline_pending_events,battery_percent,last_seen_at AS robot_last_seen_at,app_version,android_version,device_name FROM devices WHERE node_code=? AND active=1 ORDER BY robot_enabled DESC,last_seen_at DESC LIMIT 1").bind(n.node_code).first();
    const dup=await env.DB.prepare("SELECT COUNT(*) total FROM duplicate_request_audit WHERE requester_node_code=? AND observed_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours')").bind(n.node_code).first();
    output.push(commandCenterRow({...n,...(balance||{}),...(flow||{}),...(queue||{}),...(dev||{}),duplicate_24h:Number(dup?.total||0)}));
  }
  const anomalies=[];for(const n of output)for(const a of n.anomalies||[])anomalies.push({...a,node_code:n.node_code,role:n.role});
  const recent=national
    ? await env.DB.prepare("SELECT COUNT(*) total,COUNT(DISTINCT CASE WHEN state IN ('FAILED','UNKNOWN','BLOCKED') THEN executor_node_code END) bad_nodes,SUM(CASE WHEN state IN ('FAILED','UNKNOWN','BLOCKED') THEN 1 ELSE 0 END) bad FROM commands WHERE updated_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes') AND state IN ('SUCCEEDED','FAILED','UNKNOWN','BLOCKED')").first()
    : await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree t ON n.parent_node_code=t.node_code WHERE n.active=1) SELECT COUNT(*) total,COUNT(DISTINCT CASE WHEN c.state IN ('FAILED','UNKNOWN','BLOCKED') THEN c.executor_node_code END) bad_nodes,SUM(CASE WHEN c.state IN ('FAILED','UNKNOWN','BLOCKED') THEN 1 ELSE 0 END) bad FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.updated_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 minutes') AND c.state IN ('SUCCEEDED','FAILED','UNKNOWN','BLOCKED')").bind(rootNode).first();
  const bad=Number(recent?.bad||0),total=Number(recent?.total||0),badNodes=Number(recent?.bad_nodes||0),ratio=total?bad/total:0;
  const serviceSignal=badNodes>=3&&total>=5&&ratio>=0.35
    ? {code:'PROBABLE_OPERATOR_INCIDENT',severity:'CRITICAL',message:'Des échecs ou états à vérifier sont corrélés sur plusieurs nœuds. Suspendre les répétitions inutiles et vérifier le service Blue.'}
    : badNodes===1&&bad>0?{code:'NODE_SPECIFIC_ANOMALY',severity:'WARN',message:'Le signal récent semble concentré sur un seul nœud/appareil.'}
    : {code:'SERVICE_STABLE',severity:'OK',message:'Aucun incident transversal significatif détecté dans les données B.I.R. récentes.'};
  const flows=national
    ? await env.DB.prepare("SELECT operation,COUNT(*) count,COALESCE(SUM(amount),0) amount FROM commands WHERE state='SUCCEEDED' AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') GROUP BY operation").all()
    : await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree t ON n.parent_node_code=t.node_code WHERE n.active=1) SELECT c.operation,COUNT(*) count,COALESCE(SUM(c.amount),0) amount FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.state='SUCCEEDED' AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') AND c.created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') GROUP BY c.operation").bind(rootNode).all();
  const critical=anomalies.filter(a=>a.severity==='CRITICAL').length,warn=anomalies.filter(a=>a.severity==='WARN').length;
  return {generated_at:new Date().toISOString(),scope:national?'NATIONAL':rootNode,summary:{nodes:output.length,critical,warn,stockout_critical:output.filter(n=>n.stockout==='CRITICAL').length,stockout_watch:output.filter(n=>n.stockout==='WATCH').length},service_signal:serviceSignal,flows_7d:flows.results||[],nodes:output,anomalies:anomalies.slice(0,500)};
}

async function distributionCommandCenter(env, auth, headers){return success(await distributionCommandCenterCore(env,auth.node_code,false),200,headers);}
async function ownerDistributionCommandCenter(request,env,auth,headers){const owner=await authenticateOwnerAny(request,env,auth);const data=await distributionCommandCenterCore(env,auth.node_code,true);await adminAudit(env,owner.entitlement_id,'DISTRIBUTION_COMMAND_CENTER',null,auth.device_id,{nodes:data.summary.nodes},'READ');return success(data,200,headers);}

async function reconciliationCenter(env,auth,headers){
  const commands=await env.DB.prepare("SELECT c.public_id,c.state,c.operation,c.amount,c.operator_transaction_id,c.created_at,c.completed_at,om.transaction_id,om.receipt_number,om.status AS operator_status,om.current_balance FROM commands c LEFT JOIN operator_messages om ON om.command_public_id=c.public_id WHERE (c.requester_node_code=? OR c.executor_node_code=? OR c.target_node_code=?) AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') ORDER BY c.id DESC LIMIT 300").bind(auth.node_code,auth.node_code,auth.node_code).all();
  const blueOnly=await env.DB.prepare("SELECT transaction_id,receipt_number,status,amount,current_balance,transaction_date,transaction_time,created_at FROM operator_messages WHERE node_code=? AND message_kind IN ('TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT') AND command_public_id IS NULL ORDER BY id DESC LIMIT 100").bind(auth.node_code).all();
  const evidence=await env.DB.prepare("SELECT COUNT(*) total,SUM(CASE WHEN accepted=1 THEN 1 ELSE 0 END) accepted,SUM(CASE WHEN accepted=0 THEN 1 ELSE 0 END) rejected FROM balance_evidence_log WHERE node_code=?").bind(auth.node_code).first();
  let matched=0,mismatch=0,birOnly=0;const rows=[];
  for(const r of commands.results||[]){let state='MATCHED',reason='Commande et preuve opérateur reliées.';if(!r.transaction_id&&!r.receipt_number){state='BIR_ONLY';reason='Commande financière sans preuve opérateur liée.';birOnly++;}else if(r.state==='SUCCEEDED'&&String(r.operator_status||'').toUpperCase()==='FAILED'){state='MISMATCH';reason='B.I.R. et preuve opérateur portent des états incompatibles.';mismatch++;}else matched++;rows.push({...r,reconciliation_state:state,reconciliation_reason:reason});}
  const imported=await env.DB.prepare("SELECT match_state,COUNT(*) total FROM reconciliation_rows GROUP BY match_state").all();
  return success({generated_at:new Date().toISOString(),node_code:auth.node_code,summary:{matched,mismatch,bir_only:birOnly,blue_only:(blueOnly.results||[]).length,balance_evidence_total:Number(evidence?.total||0),balance_evidence_accepted:Number(evidence?.accepted||0),balance_evidence_rejected:Number(evidence?.rejected||0)},transactions:rows,blue_only:blueOnly.results||[],imported_reconciliation:imported.results||[]},200,headers);
}

async function leaseCommand(env, auth, headers) {
  if (!['ROBOT', 'HYBRID'].includes(auth.mode)) {
    throw new ApiError('NOT_A_ROBOT', 'Cet appareil n’est pas autorisé à louer des commandes.', 403);
  }
  if (!auth.sim_verified || !/^[a-f0-9]{64}$/.test(auth.sim_fingerprint || '')) {
    throw new ApiError('ROBOT_SIM_NOT_VERIFIED',
      'Ce Robot doit confirmer la présence et l’identité de sa SIM avant de louer une commande.', 409);
  }
  if (!auth.robot_enabled) {
    return success({
      available: false, standby: true,
      reason: 'Cette SIM est actuellement revendiquée par un autre téléphone Robot.'
    }, 200, headers);
  }

  // Non-financial Remote wake piggybacks on the Robot's existing lease poll.
  // It never creates a command and is consumed only by the active Robot of the same node.
  try {
    await env.DB.prepare("UPDATE sync_wake_requests SET state='EXPIRED' WHERE node_code=? AND state='PENDING' AND created_at<strftime('%Y-%m-%dT%H:%M:%fZ','now','-10 minutes')")
      .bind(auth.node_code).run();
    const wake = await env.DB.prepare("UPDATE sync_wake_requests SET state='CONSUMED',consumed_by_device_id=?,consumed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=(SELECT id FROM sync_wake_requests WHERE node_code=? AND state='PENDING' ORDER BY id LIMIT 1) AND state='PENDING' RETURNING id,reason,created_at")
      .bind(auth.device_id,auth.node_code).first();
    if (wake) return success({available:false,force_sync:true,wake_id:wake.id,wake_reason:wake.reason,requested_at:wake.created_at},200,headers);
  } catch (error) {
    // A 2.9.1 client remains compatible during staged rollout before migration 0009.
    if (!String(error?.message || error).includes('sync_wake_requests')) throw error;
  }

  await env.DB.prepare(
    "UPDATE commands SET state = CASE "
    + "WHEN state = 'LEASED' AND attempt < max_attempts THEN 'PENDING' "
    + "WHEN state = 'LEASED' THEN 'FAILED' ELSE 'UNKNOWN' END, "
    + "result_message = CASE "
    + "WHEN state = 'LEASED' AND attempt < max_attempts THEN 'Lease expiré avant composition.' "
    + "WHEN state = 'LEASED' THEN 'Robot indisponible après plusieurs leases.' "
    + "ELSE 'Session USSD expirée après composition; vérification manuelle requise.' END, "
    + 'lease_token_hash = NULL, leased_until = NULL, leased_by_device_id = NULL, '
    + "completed_at = CASE WHEN state <> 'LEASED' OR attempt >= max_attempts "
    + "THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now') ELSE completed_at END, "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
    + "WHERE executor_node_code = ? "
    + "AND state IN ('LEASED', 'DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT') "
    + "AND leased_until < strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
  ).bind(auth.node_code).run();

  const active = await env.DB.prepare(
    "SELECT public_id, state, leased_by_device_id, leased_until, updated_at FROM commands WHERE executor_node_code = ? "
    + "AND state IN ('LEASED', 'DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT') "
    + 'ORDER BY id LIMIT 1'
  ).bind(auth.node_code).first();
  if (active) {
    return success({available: false, busy: true, active_command: active}, 200, headers);
  }

  const leaseToken = randomHex(24);
  const command = await env.DB.prepare(
    "UPDATE commands SET state = 'LEASED', attempt = attempt + 1, lease_token_hash = ?, leased_by_device_id = ?, "
    + "leased_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'), "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
    + "WHERE id = (SELECT id FROM commands WHERE executor_node_code = ? AND state = 'PENDING' ORDER BY id LIMIT 1) "
    + "AND state = 'PENDING' RETURNING id, public_id, requester_node_code, executor_node_code, "
    + "target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, requires_pin"
  ).bind(await sha256(leaseToken), auth.device_id, auth.node_code).first();
  if (!command) return success({available: false}, 200, headers);

  await env.DB.prepare(
    "INSERT INTO command_events(command_id, device_id, state, message) VALUES(?, ?, 'LEASED', 'Commande réservée au Robot.')"
  ).bind(command.id, auth.device_id).run();
  command.executor_phone = auth.phone_number;
  command.integrity_version = 3;
  const integrityDigest = await commandDigest(command);
  return success({
    available: true,
    command: {
      public_id: command.public_id,
      lease_token: leaseToken,
      requester_node_code: command.requester_node_code,
      executor_node_code: command.executor_node_code,
      executor_phone: command.executor_phone,
      target_node_code: command.target_node_code,
      operation: command.operation,
      command_kind: command.command_kind || '',
      command_argument: command.command_argument || '',
      target_phone: command.target_phone,
      amount: command.amount,
      ussd_code: command.ussd_code,
      requires_pin: Boolean(command.requires_pin),
      integrity_version: command.integrity_version,
      integrity_digest: integrityDigest
    }
  }, 200, headers);
}

async function releaseCommand(env, auth, input, headers) {
  const publicId = String(input.command_id || '').trim();
  const leaseToken = String(input.lease_token || '').trim();
  const command = await env.DB.prepare(
    'SELECT id, state, executor_node_code, lease_token_hash, leased_by_device_id FROM commands WHERE public_id = ?'
  ).bind(publicId).first();
  if (!command || command.executor_node_code !== auth.node_code) {
    throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable pour ce Robot.', 404);
  }
  if (command.state !== 'LEASED') {
    return success({command: {public_id: publicId, state: command.state}, released: false}, 200, headers);
  }
  if (command.leased_by_device_id && command.leased_by_device_id !== auth.device_id) {
    throw new ApiError('LEASE_OWNER_MISMATCH', 'Ce lease appartient à un autre appareil Robot.', 409);
  }
  if (!command.lease_token_hash || command.lease_token_hash !== await sha256(leaseToken)) {
    throw new ApiError('LEASE_INVALID', 'Lease invalide ou expiré.', 409);
  }
  const reason = cleanText(input.reason || 'Exécution différée par le Robot.', 500);
  const results = await env.DB.batch([
    env.DB.prepare(
      "UPDATE commands SET state = 'PENDING', attempt = CASE WHEN attempt > 0 THEN attempt - 1 ELSE 0 END, "
      + 'lease_token_hash = NULL, leased_until = NULL, leased_by_device_id = NULL, result_message = ?, '
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ? AND state = 'LEASED'"
    ).bind(reason, command.id),
    env.DB.prepare(
      "INSERT INTO command_events(command_id, device_id, state, message) VALUES(?, ?, 'RELEASED', ?)"
    ).bind(command.id, auth.device_id, reason)
  ]);
  if (!results[0].meta?.changes) throw new ApiError('COMMAND_RACE', 'La commande a changé.', 409);
  return success({command: {public_id: publicId, state: 'PENDING'}, released: true}, 200, headers);
}

async function cancelCommand(env, auth, input, headers) {
  const publicId = String(input.command_id || '').trim();
  const command = await env.DB.prepare(
    'SELECT id, public_id, state, requester_node_code, executor_node_code FROM commands WHERE public_id = ?'
  ).bind(publicId).first();
  if (!command || (command.requester_node_code !== auth.node_code
      && command.executor_node_code !== auth.node_code)) {
    throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable pour ce compte.', 404);
  }
  if (TERMINAL_STATES.has(command.state)) {
    return success({command: {public_id: publicId, state: command.state}, cancelled: false}, 200, headers);
  }
  if (command.state !== 'PENDING') {
    throw new ApiError('CANCEL_TOO_LATE',
      'La composition a peut-être commencé. Utilisez la libération locale et vérifiez la transaction.', 409);
  }
  const message = 'Commande annulée volontairement avant sa réservation par un Robot.';
  const results = await env.DB.batch([
    env.DB.prepare(
      "UPDATE commands SET state = 'CANCELLED', result_message = ?, "
      + "completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = ? AND state = 'PENDING'"
    ).bind(message, command.id),
    env.DB.prepare(
      "INSERT INTO command_events(command_id, device_id, state, message) VALUES(?, ?, 'CANCELLED', ?)"
    ).bind(command.id, auth.device_id, message)
  ]);
  if (!results[0].meta?.changes) throw new ApiError('COMMAND_RACE', 'La commande a changé.', 409);
  return success({
    command: {public_id: publicId, state: 'CANCELLED', result_message: message}, cancelled: true
  }, 200, headers);
}

async function commandEvent(env, auth, input, headers) {
  const publicId = String(input.command_id || '').trim();
  const leaseToken = String(input.lease_token || '').trim();
  const nextState = String(input.state || '').trim().toUpperCase();
  if (!EVENT_STATES.has(nextState)) throw new ApiError('INVALID_STATE', 'État de commande invalide.', 422);

  const command = await env.DB.prepare('SELECT * FROM commands WHERE public_id = ?').bind(publicId).first();
  if (!command || command.executor_node_code !== auth.node_code) {
    throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable pour ce Robot.', 404);
  }
  if (!command.lease_token_hash || command.lease_token_hash !== await sha256(leaseToken)) {
    throw new ApiError('LEASE_INVALID', 'Lease invalide ou expiré.', 409);
  }
  if (TERMINAL_STATES.has(command.state)) {
    return success({command: commandView(command), already_terminal: true}, 200, headers);
  }
  if (!VALID_TRANSITIONS[command.state]?.has(nextState)) {
    throw new ApiError('INVALID_TRANSITION', `Transition ${command.state} vers ${nextState} refusée.`, 409);
  }

  const message = cleanText(input.message, 2000);
  const suppliedOperatorId = String(input.operator_transaction_id || '').trim();
  const operatorId = /^[A-Za-z0-9_-]{6,64}$/.test(suppliedOperatorId) ? suppliedOperatorId : null;
  const terminal = TERMINAL_STATES.has(nextState);
  const results = await env.DB.batch([
    env.DB.prepare(
      'UPDATE commands SET state = ?, result_message = ?, operator_transaction_id = ?, '
      + "started_at = CASE WHEN ? = 'DIALING' AND started_at IS NULL THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now') ELSE started_at END, "
      + "completed_at = CASE WHEN ? = 1 THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now') ELSE completed_at END, "
      + 'leased_until = CASE WHEN ? = 1 THEN NULL ELSE leased_until END, leased_by_device_id = CASE WHEN ? = 1 THEN NULL ELSE leased_by_device_id END, '
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
      + 'WHERE id = ? AND state = ?'
    ).bind(nextState, message, operatorId, nextState, terminal ? 1 : 0, terminal ? 1 : 0, terminal ? 1 : 0, command.id, command.state),
    env.DB.prepare(
      'INSERT INTO command_events(command_id, device_id, state, message) VALUES(?, ?, ?, ?)'
    ).bind(command.id, auth.device_id, nextState, message)
  ]);
  if (!results[0].meta?.changes) throw new ApiError('COMMAND_RACE', 'La commande a changé; relisez son état.', 409);
  if (terminal) await applyTerminalEffects(env, command, nextState, message, publicId);
  if (message) await recordParsedOperatorMessage(env, auth.node_code, message, publicId, command, nextState);
  return success({command: {public_id: publicId, state: nextState}, already_terminal: false}, 200, headers);
}

async function commandStatus(env, auth, input, headers) {
  const publicId = String(input.command_id || '').trim();
  const command = await env.DB.prepare(
    'SELECT public_id, requester_node_code, executor_node_code, target_node_code, operation, command_kind, target_phone, '
    + 'amount, state, result_message, operator_transaction_id, created_at, started_at, completed_at, updated_at '
    + 'FROM commands WHERE public_id = ? AND (requester_node_code = ? OR executor_node_code = ?)'
  ).bind(publicId, auth.node_code, auth.node_code).first();
  if (!command) throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable.', 404);
  return success({command: commandView(command)}, 200, headers);
}

function commandView(command) {
  const keys = [
    'public_id', 'requester_node_code', 'executor_node_code', 'target_node_code', 'operation',
    'target_phone', 'amount', 'state', 'result_message', 'operator_transaction_id', 'created_at',
    'started_at', 'completed_at', 'updated_at'
  ];
  const view = Object.fromEntries(keys.filter(key => key in command).map(key => [key, command[key]]));
  if (command.command_kind) view.operation = command.command_kind;
  return view;
}

async function applyTerminalEffects(env, command, state, message, publicId) {
  await applyMercenaryTerminal(env, publicId, state);
  if (state === 'SUCCEEDED' && command.operation === 'DISTRIBUTION_TRANSFER'
      && command.target_node_code && Number.isInteger(Number(command.commission_rate_bps))) {
    const inbound = Math.max(0, Math.min(5000, Number(command.commission_rate_bps || 0)));
    await env.DB.prepare('UPDATE nodes SET inbound_commission_bps=? WHERE node_code=?')
      .bind(inbound, command.target_node_code).run();
  }
  const explicitEvidence = state === 'SUCCEEDED' ? explicitBalanceEvidence(command, message) : null;
  if (explicitEvidence) {
    await saveObservedBalance(env, explicitEvidence.nodeCode, explicitEvidence.value, publicId,
      explicitEvidence.kind, {
        operatorEventAt: operatorEventAt(explicitEvidence.parsed) || new Date().toISOString(),
        transactionId: explicitEvidence.parsed.transaction_id || explicitEvidence.parsed.receipt_number || '',
        passive: false
      });
    await refreshWaitingPreflights(env, explicitEvidence.nodeCode);
    return;
  }
  if (command.command_kind === 'BALANCE_OWN') {
    await env.DB.prepare(
      "UPDATE purchase_preflights SET state = 'FAILED', result_message = ?, "
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
      + "WHERE balance_command_public_id = ? AND state = 'WAITING'"
    ).bind(state === 'SUCCEEDED'
      ? 'Le message Camtel a été reçu, mais aucun solde actuel explicite n’a pu être certifié.'
      : `La consultation du solde a échoué (${state}).`, publicId).run();
    return;
  }
  if (state === 'SUCCEEDED'
      && ['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)
      && Number(command.amount) > 0) {
    const value = Number(command.amount);
    const statements = [env.DB.prepare(
      "UPDATE account_balances SET balance = MAX(0, balance - ?), source = 'ESTIMATED_TRANSFER', "
      + "evidence_kind = 'ESTIMATED_TRANSFER', confidence = 'DERIVED_FROM_EXPLICIT', "
      + "evidence_priority = 100, balance_quality = 'ESTIMATED', operator_event_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
      + 'source_command_public_id = ?, '
      + "valid_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE node_code = ?"
    ).bind(value, publicId, command.executor_node_code)];
    if (command.target_node_code) {
      statements.push(env.DB.prepare(
        "UPDATE account_balances SET balance = balance + ?, source = 'ESTIMATED_TRANSFER', "
        + "evidence_kind = 'ESTIMATED_TRANSFER', confidence = 'DERIVED_FROM_EXPLICIT', "
        + 'source_command_public_id = ?, '
        + "valid_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
        + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE node_code = ?"
      ).bind(value, publicId, command.target_node_code));
    }
    await env.DB.batch(statements);
  }
}

function explicitBalanceEvidence(command, message) {
  const parsed = parseBlueMessage(message);
  const value = parsed.current_balance;
  if (value == null) return null;
  if (command.command_kind === 'BALANCE_CHILD' && command.target_node_code) {
    return {nodeCode: command.target_node_code, value, kind: 'CHILD_BALANCE_QUERY', parsed};
  }
  const kinds = {
    BALANCE_OWN: 'BALANCE_QUERY',
    HISTORY_LAST5: 'HISTORY_RESULT',
    TRANSACTION_DETAIL: 'TRANSACTION_DETAIL_RESULT'
  };
  if (kinds[command.command_kind]) {
    return {nodeCode: command.executor_node_code, value, kind: kinds[command.command_kind], parsed};
  }
  if (['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)) {
    return {nodeCode: command.executor_node_code, value, kind: 'FINANCIAL_RESULT', parsed};
  }
  return null;
}

async function refreshWaitingPreflights(env, nodeCode) {
  for (let guard = 0; guard < 500; guard += 1) {
    const row = await env.DB.prepare(
      "SELECT rowid AS queue_order, * FROM purchase_preflights WHERE supplier_node_code = ? "
      + "AND state = 'WAITING' ORDER BY rowid LIMIT 1"
    ).bind(nodeCode).first();
    if (!row) return;
    const effective = await effectiveAvailableBalance(env, nodeCode, true);
    if (!effective) return;
    const available = Math.max(0, effective.available);
    const requested = Number(row.requested_amount);
    const accepted = requested <= available;
    const remaining = accepted ? available - requested : available;
    const message = accepted
      ? `Montant disponible au contrôle : ${available} FCFA. Aucune réservation avant confirmation.`
      : `Montant insuffisant au contrôle. Solde disponible du supérieur : ${available} FCFA.`;
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

function balanceEvidencePriority(kind) {
  return Number(BALANCE_EVIDENCE_PRIORITY[kind] || 0);
}

function operatorEventAt(parsed) {
  const date = String(parsed?.transaction_date || '').trim();
  const time = String(parsed?.transaction_time || '').trim();
  if (!date || !time) return '';
  const dm = /^(\d{2})[-/](\d{2})[-/](\d{2,4})$/.exec(date);
  const tm = /^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?$/i.exec(time);
  if (!dm || !tm) return '';
  let year = Number(dm[3]);
  if (year < 100) year += 2000;
  let hour = Number(tm[1]);
  const ampm = String(tm[4] || '').toUpperCase();
  if (ampm === 'PM' && hour < 12) hour += 12;
  if (ampm === 'AM' && hour === 12) hour = 0;
  // CAMTEL/Blue timestamps are Cameroon local time (UTC+1, no DST).
  const value = new Date(Date.UTC(year, Number(dm[2]) - 1, Number(dm[1]), hour - 1,
    Number(tm[2]), Number(tm[3] || 0)));
  return Number.isNaN(value.getTime()) ? '' : value.toISOString();
}

async function saveObservedBalance(env, nodeCode, value, publicId, evidenceKind, metadata = {}) {
  const priority = balanceEvidencePriority(evidenceKind);
  const incomingEventAt = cleanText(metadata.operatorEventAt, 64)
    || (metadata.passive ? '' : new Date().toISOString());
  const transactionId = cleanText(metadata.transactionId, 80);
  const current = await env.DB.prepare(
    'SELECT balance, evidence_kind, evidence_priority, operator_event_at, observed_at, balance_quality '
    + 'FROM account_balances WHERE node_code = ?'
  ).bind(nodeCode).first();
  let accepted = true;
  let reason = current ? 'NEWER_OR_STRONGER_EVIDENCE' : 'FIRST_EXPLICIT_EVIDENCE';
  if (current) {
    const currentAt = String(current.operator_event_at || current.observed_at || '');
    const incomingMs = incomingEventAt ? Date.parse(incomingEventAt) : NaN;
    const currentMs = currentAt ? Date.parse(currentAt) : NaN;
    if (Number.isFinite(incomingMs) && Number.isFinite(currentMs) && incomingMs < currentMs) {
      accepted = false;
      reason = 'STALE_OPERATOR_EVENT';
    } else if (Number.isFinite(incomingMs) && Number.isFinite(currentMs)
        && incomingMs === currentMs && priority < Number(current.evidence_priority || 0)) {
      accepted = false;
      reason = 'LOWER_PRIORITY_SAME_EVENT';
    } else if (!incomingEventAt && metadata.passive && current.balance_quality === 'EXACT') {
      accepted = false;
      reason = 'PASSIVE_EVENT_WITHOUT_SAFE_CHRONOLOGY';
    }
  }
  await env.DB.prepare(
    'INSERT INTO balance_evidence_log(node_code, command_public_id, balance, evidence_kind, '
    + 'evidence_priority, balance_quality, operator_event_at, transaction_id, accepted, decision_reason) '
    + 'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(nodeCode, publicId || null, value, evidenceKind, priority, 'EXACT',
    incomingEventAt || null, transactionId, accepted ? 1 : 0, reason).run();
  if (!accepted) return {accepted: false, reason};
  await env.DB.prepare(
    'INSERT INTO account_balances(node_code, balance, source, evidence_kind, confidence, '
    + 'source_command_public_id, evidence_command_public_id, observed_at, valid_until, '
    + 'evidence_priority, operator_event_at, balance_quality, last_transaction_id) '
    + "VALUES(?, ?, 'USSD', ?, 'OPERATOR_EXPLICIT', ?, ?, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now'), "
    + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+' || ? || ' seconds'), ?, ?, 'EXACT', ?) "
    + 'ON CONFLICT(node_code) DO UPDATE SET balance = excluded.balance, source = excluded.source, '
    + 'evidence_kind = excluded.evidence_kind, confidence = excluded.confidence, '
    + 'source_command_public_id = excluded.source_command_public_id, '
    + 'evidence_command_public_id = excluded.evidence_command_public_id, '
    + 'observed_at = excluded.observed_at, valid_until = excluded.valid_until, '
    + 'evidence_priority = excluded.evidence_priority, operator_event_at = excluded.operator_event_at, '
    + "balance_quality = 'EXACT', last_transaction_id = excluded.last_transaction_id, "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
  ).bind(nodeCode, value, evidenceKind, publicId || null, publicId || null,
    BALANCE_EVIDENCE_TTL_SECONDS, priority, incomingEventAt || null, transactionId).run();
  return {accepted: true, reason};
}

function parseBalanceFcfa(message) {
  return parseBlueMessage(message).current_balance;
}

async function recordOperatorMessageApi(env, auth, input, headers) {
  const message = cleanText(input.message, 2000);
  if (!message) throw new ApiError('MESSAGE_REQUIRED', 'Message Blue/Camtel requis.', 422);
  const parsed = await recordParsedOperatorMessage(env, auth.node_code, message, null, null, 'PASSIVE');
  // Generic balance messages are deliberately not promoted passively: Camtel uses the same wording
  // for a child balance. Command context is mandatory to distinguish own vs child balance safely.
  const passiveFinancialKinds = new Set(['TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT']);
  const promotable = parsed.kind === 'MINI_STATEMENT' || passiveFinancialKinds.has(parsed.kind);
  if (promotable && parsed.current_balance != null) {
    const kind = parsed.kind === 'MINI_STATEMENT' ? 'HISTORY_RESULT' : 'FINANCIAL_RESULT';
    const result = await saveObservedBalance(env, auth.node_code, parsed.current_balance, null, kind, {
      operatorEventAt: operatorEventAt(parsed),
      transactionId: parsed.transaction_id || parsed.receipt_number || '',
      passive: true
    });
    if (result.accepted) await refreshWaitingPreflights(env, auth.node_code);
  }
  return success({operator_message: publicOperatorMessage(parsed)}, 201, headers);
}

async function recordParsedOperatorMessage(env, nodeCodeValue, message, publicId, command, commandState) {
  const parsed = parseBlueMessage(message);
  const tx = parsed.transaction_id || null;
  let identityConflict = '';
  if (parsed.source_phone) {
    const owner = await env.DB.prepare('SELECT node_code FROM nodes WHERE phone_number=? LIMIT 1')
      .bind(parsed.source_phone).first();
    if (owner) {
      if (parsed.source_node && parsed.source_node.toUpperCase() !== owner.node_code) {
        identityConflict += `SOURCE_LABEL:${parsed.source_node}->${owner.node_code}`;
      }
      parsed.source_node = owner.node_code;
    }
  }
  if (parsed.target_phone) {
    const owner = await env.DB.prepare('SELECT node_code FROM nodes WHERE phone_number=? LIMIT 1')
      .bind(parsed.target_phone).first();
    if (owner) {
      if (parsed.target_node && parsed.target_node.toUpperCase() !== owner.node_code) {
        identityConflict += `${identityConflict ? ';' : ''}TARGET_LABEL:${parsed.target_node}->${owner.node_code}`;
      }
      parsed.target_node = owner.node_code;
    }
  }
  parsed.identity_conflict = identityConflict;

  await env.DB.prepare(
    'INSERT OR IGNORE INTO operator_messages(command_public_id, node_code, message_kind, status, transaction_id, '
    + 'receipt_number, source_phone, source_node_code, target_phone, target_node_code, amount, current_balance, '
    + 'account_no, transaction_date, transaction_time, debit_credit, charge_amount, commission_amount, tax_amount, raw_message) '
    + 'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
  ).bind(publicId, nodeCodeValue, parsed.kind, parsed.status, tx, parsed.receipt_number,
    parsed.source_phone, parsed.source_node, parsed.target_phone, parsed.target_node,
    parsed.amount_fcfa, parsed.current_balance, parsed.account_no, parsed.transaction_date,
    parsed.transaction_time, parsed.debit_credit, parsed.charge_amount, parsed.commission_amount,
    parsed.tax_amount, cleanText(parsed.raw_message, 1800)).run();

  for (const entry of (parsed.mini_statement_entries || []).slice(0, 5)) {
    let sourceNode = entry.source_node || '';
    let targetNode = entry.target_node || '';
    if (entry.source_phone) {
      const owner = await env.DB.prepare('SELECT node_code FROM nodes WHERE phone_number=? LIMIT 1')
        .bind(entry.source_phone).first();
      if (owner) sourceNode = owner.node_code;
    }
    if (entry.target_phone) {
      const owner = await env.DB.prepare('SELECT node_code FROM nodes WHERE phone_number=? LIMIT 1')
        .bind(entry.target_phone).first();
      if (owner) targetNode = owner.node_code;
    }
    await env.DB.prepare(
      'INSERT OR IGNORE INTO operator_messages(command_public_id, node_code, message_kind, status, '
      + 'receipt_number, source_phone, source_node_code, target_phone, target_node_code, amount, '
      + 'current_balance, account_no, transaction_date, debit_credit, charge_amount, commission_amount, '
      + 'tax_amount, raw_message) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(publicId, nodeCodeValue, 'MINI_STATEMENT_ENTRY', entry.status || 'INFO',
      entry.receipt_number || null, entry.source_phone || '', sourceNode,
      entry.target_phone || '', targetNode, entry.debit_credit_amount,
      entry.current_balance, entry.account_no || '', entry.transaction_date || '',
      entry.debit_credit || '', entry.charge_amount, entry.commission_amount, entry.tax_amount,
      cleanText(entry.raw_message, 1800)).run();
  }

  const passiveFinancial = !command
    && ['TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT'].includes(parsed.kind)
    && parsed.status === 'SUCCEEDED';
  const financial = (command && ['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)
    && ['SUCCEEDED', 'UNKNOWN'].includes(commandState)) || passiveFinancial;
  const unbalanced = financial && parsed.current_balance == null;
  const eventAt = operatorEventAt(parsed) || new Date().toISOString();
  const receivedAt = new Date().toISOString();
  const current = await env.DB.prepare('SELECT * FROM node_activity_state WHERE node_code=?')
    .bind(nodeCodeValue).first();
  const maxIso = (left, right) => !left ? right : (!right ? left : (left >= right ? left : right));
  const lastActivityAt = maxIso(current?.last_activity_at || '', eventAt);
  const lastFinancialAt = financial
    ? maxIso(current?.last_financial_activity_at || '', eventAt)
    : (current?.last_financial_activity_at || null);
  let lastUnbalancedAt = current?.last_unbalanced_activity_at || null;
  if (financial && unbalanced) {
    lastUnbalancedAt = maxIso(lastUnbalancedAt || '', eventAt) || null;
  } else if (financial && parsed.current_balance != null && lastUnbalancedAt
      && Date.parse(eventAt) >= Date.parse(lastUnbalancedAt)) {
    lastUnbalancedAt = null;
  }
  const counter = Number(current?.transaction_counter || 0) + (financial ? 1 : 0);
  await env.DB.prepare(
    'INSERT INTO node_activity_state(node_code,last_activity_at,last_financial_activity_at,'
    + 'last_unbalanced_activity_at,last_operator_message_at,last_transaction_id,transaction_counter) '
    + 'VALUES(?,?,?,?,?,?,?) ON CONFLICT(node_code) DO UPDATE SET '
    + 'last_activity_at=excluded.last_activity_at, last_financial_activity_at=excluded.last_financial_activity_at, '
    + 'last_unbalanced_activity_at=excluded.last_unbalanced_activity_at, '
    + 'last_operator_message_at=excluded.last_operator_message_at, '
    + 'last_transaction_id=excluded.last_transaction_id, transaction_counter=excluded.transaction_counter, '
    + "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  ).bind(nodeCodeValue, lastActivityAt, lastFinancialAt, lastUnbalancedAt, receivedAt,
    tx || current?.last_transaction_id || '', counter).run();
  return parsed;
}

function publicOperatorMessage(parsed) {
  return {
    kind: parsed.kind, status: parsed.status, transaction_id: parsed.transaction_id || '',
    receipt_number: parsed.receipt_number || '', source_phone: parsed.source_phone || '',
    source_node: parsed.source_node || '', target_phone: parsed.target_phone || '',
    target_node: parsed.target_node || '', amount_fcfa: parsed.amount_fcfa,
    current_balance: parsed.current_balance, account_no: parsed.account_no || '',
    transaction_date: parsed.transaction_date || '', transaction_time: parsed.transaction_time || '',
    debit_credit: parsed.debit_credit || '', charge_amount: parsed.charge_amount,
    commission_amount: parsed.commission_amount, tax_amount: parsed.tax_amount,
    identity_conflict: parsed.identity_conflict || ''
  };
}

async function operatorInsights(env, auth, headers) {
  const rows = await env.DB.prepare(
    'WITH RECURSIVE network(node_code) AS (SELECT ? UNION ALL '
    + 'SELECT n.node_code FROM nodes n JOIN network p ON n.parent_node_code = p.node_code WHERE n.active = 1) '
    + 'SELECT m.node_code, m.message_kind, m.status, m.transaction_id, m.receipt_number, '
    + 'm.source_phone, m.source_node_code, m.target_phone, m.target_node_code, m.amount, m.current_balance, '
    + 'm.account_no, m.transaction_date, m.transaction_time, m.debit_credit, m.created_at '
    + 'FROM operator_messages m JOIN network n ON n.node_code = m.node_code ORDER BY m.id DESC LIMIT 100'
  ).bind(auth.node_code).all();
  return success({messages: rows.results || []}, 200, headers);
}

async function platformSnapshot(env, auth, headers) {
  const nodes = await env.DB.prepare(
    'WITH RECURSIVE network(node_code) AS (SELECT ? UNION ALL '
    + 'SELECT n.node_code FROM nodes n JOIN network p ON n.parent_node_code = p.node_code WHERE n.active = 1) '
    + 'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, b.balance, b.observed_at, '
    + 'b.operator_event_at, b.evidence_kind, b.balance_quality, b.valid_until, '
    + 's.terminal_type, s.display_name, s.zone, a.last_activity_at, a.last_financial_activity_at, '
    + 'a.last_unbalanced_activity_at '
    + 'FROM network x JOIN nodes n ON n.node_code=x.node_code '
    + 'LEFT JOIN account_balances b ON b.node_code=n.node_code '
    + 'LEFT JOIN shadow_accounts s ON s.node_code=n.node_code '
    + 'LEFT JOIN node_activity_state a ON a.node_code=n.node_code ORDER BY n.role,n.node_code'
  ).bind(auth.node_code).all();
  const debts = await env.DB.prepare(
    "SELECT id, debtor_node_code, amount_advanced, amount_repaid, due_date, note, state, updated_at "
    + "FROM debts WHERE owner_node_code = ? AND state <> 'CANCELLED' ORDER BY id DESC LIMIT 100"
  ).bind(auth.node_code).all();
  let mercenary = {count: 0, virtual_balance: 0, commission_balance: 0};
  if (auth.role === 'DAE') {
    const row = await env.DB.prepare(
      'SELECT COUNT(*) AS count, COALESCE(SUM(virtual_balance),0) AS virtual_balance, '
      + 'COALESCE(SUM(commission_balance),0) AS commission_balance FROM mercenary_accounts '
      + 'WHERE owner_dae_node_code = ? AND active=1'
    ).bind(auth.node_code).first();
    if (row) mercenary = row;
  }
  const now = Date.now();
  const publicNodes = (nodes.results || []).map(row => {
    const balance = row.balance == null ? null : Number(row.balance);
    const evidenceAt = row.operator_event_at || row.observed_at || '';
    const unbalancedAfterEvidence = Boolean(row.last_unbalanced_activity_at && evidenceAt
      && Date.parse(row.last_unbalanced_activity_at) > Date.parse(evidenceAt));
    let reportState = 'UNKNOWN';
    if (balance != null) {
      if (unbalancedAfterEvidence || row.balance_quality === 'NEEDS_RECHECK') reportState = 'RECHECK_REQUIRED';
      else if (row.balance_quality === 'ESTIMATED') reportState = 'ESTIMATED';
      else if (row.balance_quality === 'EXACT' && evidenceAt
          && now - Date.parse(evidenceAt) <= REPORT_BALANCE_EVIDENCE_TTL_SECONDS * 1000) reportState = 'CERTIFIED';
      else if (row.balance_quality === 'EXACT') reportState = 'KNOWN_IDLE_OLD';
    }
    return {...row, balance, evidence_at: evidenceAt, balance_report_state: reportState,
      report_reusable: reportState === 'CERTIFIED'};
  });
  const reportSummary = publicNodes.reduce((acc, node) => {
    acc[node.balance_report_state] = (acc[node.balance_report_state] || 0) + 1;
    return acc;
  }, {});
  const identity = parseCamtelIdentity(auth.node_code);
  return success({generated_at: new Date().toISOString(),
    scope_node_code: auth.node_code,
    region_code: identity.ok ? identity.region_code || '' : '',
    dae_node_code: identity.ok ? identity.dae_node_code || '' : '',
    report_freshness_seconds: REPORT_BALANCE_EVIDENCE_TTL_SECONDS,
    nodes: publicNodes, report_summary: reportSummary,
    debts: debts.results || [], mercenary}, 200, headers);
}

async function cockpitRows(env, scopeNode) {
  const rows = await env.DB.prepare(
    "WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) " +
    "SELECT n.node_code,n.role,n.parent_node_code,n.default_commission_bps,b.balance,b.balance_quality,b.observed_at, " +
    "d.device_id,d.robot_enabled,d.sim_verified,d.offline_pending_events,d.accessibility_enabled,d.accessibility_connected,d.battery_percent,d.last_seen_at,d.last_telemetry_at " +
    "FROM tree t JOIN nodes n ON n.node_code=t.node_code LEFT JOIN account_balances b ON b.node_code=n.node_code " +
    "LEFT JOIN devices d ON d.device_id=(SELECT d2.device_id FROM devices d2 WHERE d2.node_code=n.node_code AND d2.active=1 ORDER BY d2.robot_enabled DESC,d2.last_seen_at DESC LIMIT 1) ORDER BY n.role,n.node_code")
    .bind(scopeNode).all();
  return rows.results || [];
}
function healthView(row) {
  const last = row.last_telemetry_at || row.last_seen_at || '';
  const age = last ? Math.max(0, Date.now()-Date.parse(last)) : Infinity;
  const stale = age > 15*60*1000;
  let severity='OK', message='Robot prêt';
  if (!row.device_id) {severity='CRITICAL';message='Aucun appareil actif connu';}
  else if (stale) {severity='HOT';message='Nœud silencieux : dernier état connu ancien';}
  else if (row.robot_enabled && (!row.sim_verified || !row.accessibility_enabled || !row.accessibility_connected)) {severity='WARN';message='Robot à vérifier : SIM ou Accessibilité';}
  else if (row.battery_percent != null && Number(row.battery_percent) < 15) {severity='WARN';message='Batterie faible';}
  return {severity,message,telemetry_freshness: stale ? 'DERNIER ÉTAT CONNU — '+last : 'CONFIRMÉ SERVEUR — '+last,
    robot_enabled:Boolean(row.robot_enabled),sim_verified:Boolean(row.sim_verified),accessibility_enabled:Boolean(row.accessibility_enabled),
    accessibility_connected:Boolean(row.accessibility_connected),battery_percent:row.battery_percent == null ? null:Number(row.battery_percent),
    offline_pending_events_last_reported:Number(row.offline_pending_events||0),telemetry_stale:stale};
}
async function openEscalationsFor(env, auth) {
  let assigned = auth.role === 'POS' ? auth.node_code : auth.node_code;
  const rows = await env.DB.prepare("SELECT * FROM ops_escalations WHERE state='OPEN' AND (assigned_to=? OR raised_by_node_code=? OR target_node_code=?) ORDER BY CASE severity WHEN 'CRITICAL' THEN 4 WHEN 'HOT' THEN 3 WHEN 'WARN' THEN 2 ELSE 1 END DESC,created_at DESC LIMIT 100")
    .bind(assigned,auth.node_code,auth.node_code).all();
  return (rows.results||[]).map(x=>({...x,can_resolve:x.assigned_to===auth.node_code,routing_label:'Assigné à '+x.assigned_to}));
}
async function continuitySummary(env, scopeNode) {
  const events = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT received_via,COUNT(*) AS c FROM offline_events e JOIN tree t ON t.node_code=e.source_node_code WHERE e.received_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') GROUP BY received_via").bind(scopeNode).all();
  const pending = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT COALESCE(SUM(d.offline_pending_events),0) AS pending FROM devices d JOIN tree t ON t.node_code=d.node_code WHERE d.active=1").bind(scopeNode).first();
  let direct=0,relay=0; for (const row of events.results||[]) {if(row.received_via==='BIR_RELAY')relay+=Number(row.c||0);else direct+=Number(row.c||0);}
  const total=direct+relay, pendingReported=Number(pending?.pending||0), denominator=total+pendingReported;
  return {direct,relay,total,pending_reported:pendingReported,window_hours:24,rate:denominator?Math.round(total*1000/denominator)/10:null};
}
async function forecastSummary(env, scopeNode) {
  const row = await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT COALESCE(SUM(CASE WHEN c.state='SUCCEEDED' AND c.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') THEN c.amount ELSE 0 END),0) AS outflow FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").bind(scopeNode).first();
  const b = await env.DB.prepare('SELECT balance FROM account_balances WHERE node_code=?').bind(scopeNode).first();
  const daily=Number(row?.outflow||0)/7, balance=b?.balance==null?null:Number(b.balance), days=balance==null||daily<=0?null:Math.round(balance/daily*10)/10;
  return {days_cover:days,message:days==null?'Données insuffisantes':days<1?'Rupture probable : approvisionnement urgent':days<3?'Stock à surveiller':'Couverture de stock confortable'};
}
async function opsCockpit(env, auth, headers) {
  const all = await cockpitRows(env,auth.node_code), health=all.map(r=>({...r,...healthView(r)}));
  const escalations=await openEscalationsFor(env,auth), continuity=await continuitySummary(env,auth.node_code), forecast=await forecastSummary(env,auth.node_code);
  let nodes=[];
  if(auth.role==='POS') nodes=health.filter(x=>x.node_code===auth.node_code).map(x=>({...x,can_escalate:true,action_hint:'Si un blocage persiste, signalez-le à votre DSM.'}));
  else if(auth.role==='DSM') nodes=health.filter(x=>x.node_code===auth.node_code||x.parent_node_code===auth.node_code).map(x=>({...x,can_escalate:x.role==='POS',action_hint:x.role==='POS'?'Ce PoS relève directement de vous. Traitez-le ici; escaladez seulement si nécessaire.':'Votre compte DSM.'}));
  else if(auth.role==='DAE') {
    const dsms=health.filter(x=>x.parent_node_code===auth.node_code&&x.role==='DSM');
    nodes=dsms.map(d=>{const children=health.filter(x=>x.parent_node_code===d.node_code&&x.role==='POS');const hot=children.filter(x=>['HOT','CRITICAL'].includes(x.severity)).length;return {...d,pos_count:children.length,pos_attention:hot,can_escalate:false,action_hint:hot?`${hot} PoS à suivre par ${d.node_code}; intervenez via votre DSM si le cas est escaladé.`:'Ce DSM gère ses PoS; aucune intervention DAE requise.'};});
    const escalatedPos=new Set(escalations.filter(e=>e.assigned_to===auth.node_code).map(e=>e.target_node_code));
    for(const pos of health.filter(x=>x.role==='POS'&&escalatedPos.has(x.node_code))) nodes.push({...pos,can_escalate:false,action_hint:'Détail visible car le DSM a demandé votre secours.'});
  }
  const healthy=health.filter(x=>x.robot_enabled&&!x.telemetry_stale&&x.severity==='OK').length, robots=health.filter(x=>x.device_id).length;
  const severities=health.map(x=>x.severity).concat(escalations.map(x=>x.severity)); const rank={OK:1,INFO:1,WARN:2,HOT:3,CRITICAL:4}; let max='OK'; for(const x of severities)if((rank[x]||1)>(rank[max]||1))max=x;
  const tx=await env.DB.prepare("WITH RECURSIVE tree(node_code) AS (SELECT ? UNION ALL SELECT n.node_code FROM nodes n JOIN tree p ON n.parent_node_code=p.node_code WHERE n.active=1) SELECT COUNT(*) AS c,COALESCE(SUM(commission_amount),0) AS commission FROM commands c JOIN tree t ON t.node_code=c.executor_node_code WHERE c.created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days') AND c.state='SUCCEEDED'").bind(auth.node_code).first();
  return success({generated_at:new Date().toISOString(),scope_role:auth.role,scope_node_code:auth.node_code,nodes,escalations,
    summary:{healthy_robots:healthy,robot_count:robots,sync_rate_percent:continuity.rate,sync_confirmed_events:continuity.total,pending_events_last_reported:continuity.pending_reported,sync_window_hours:continuity.window_hours,max_severity:max,next_action:escalations.length?`Traitez d’abord ${escalations[0].target_node_code} — ${escalations[0].severity}.`:(max==='HOT'||max==='CRITICAL'?'Un nœud silencieux ou critique demande votre attention.':'Rien d’urgent. Continuez normalement.'),continuity_source:'SERVER_CONFIRMED_ONLY'},
    forecast,audit:{proof_count:continuity.total,direct_events:continuity.direct,relay_events:continuity.relay},commission:{last7d_commission:Number(tx?.commission||0)},rescue:{attention_count:health.filter(x=>x.severity!=='OK').length+escalations.length}},200,headers);
}

async function queueOpsSyncWake(env, targetNode, requestedByDeviceId, reason) {
  await env.DB.prepare("UPDATE sync_wake_requests SET state='EXPIRED' WHERE node_code=? AND state='PENDING' AND created_at<strftime('%Y-%m-%dT%H:%M:%fZ','now','-10 minutes')")
    .bind(targetNode).run();
  const robot = await env.DB.prepare("SELECT device_id,last_seen_at FROM devices WHERE node_code=? AND active=1 AND robot_enabled=1 AND sim_verified=1 AND mode IN ('ROBOT','HYBRID') ORDER BY last_seen_at DESC LIMIT 1")
    .bind(targetNode).first();
  if (!robot) return {queued:false,node_code:targetNode,reason:'NO_ACTIVE_ROBOT'};
  const pending = await env.DB.prepare("SELECT id,created_at FROM sync_wake_requests WHERE node_code=? AND state='PENDING' ORDER BY id DESC LIMIT 1")
    .bind(targetNode).first();
  if (pending) return {queued:true,duplicate_safe:true,wake_id:pending.id,node_code:targetNode,robot_device_id:robot.device_id};
  const result = await env.DB.prepare("INSERT INTO sync_wake_requests(node_code,requested_by_device_id,reason) VALUES(?,?,?)")
    .bind(targetNode,requestedByDeviceId,cleanText(reason||'OPS_ASSIST_SYNC',80)||'OPS_ASSIST_SYNC').run();
  return {queued:true,duplicate_safe:false,wake_id:Number(result.meta?.last_row_id||0),node_code:targetNode,robot_device_id:robot.device_id};
}

async function opsAssist(env, auth, input, headers) {
  rejectSensitiveRemotePayload(input || {});
  const action = String(input.action || 'WAKE_SYNC').trim().toUpperCase();
  if (action !== 'WAKE_SYNC') throw new ApiError('OPS_ASSIST_ACTION_INVALID','Seule la réparation de synchronisation non financière est autorisée ici.',422);
  const target = nodeCode(input.target_node_code || auth.node_code);
  let relation = '';
  if (auth.role === 'POS') {
    if (target !== auth.node_code) throw new ApiError('OPS_ASSIST_SCOPE','Un PoS ne répare que son propre compte.',403);
    relation = 'SELF';
  } else if (auth.role === 'DSM') {
    const child = await resolveDirectChild(env, auth.node_code, target, 'POS');
    if (!child) throw new ApiError('OPS_ASSIST_SCOPE','Le DSM aide uniquement un PoS direct.',403);
    relation = 'DSM_TO_DIRECT_POS';
  } else if (auth.role === 'DAE') {
    const dsm = await resolveDirectChild(env, auth.node_code, target, 'DSM');
    if (dsm) {
      relation = 'DAE_TO_DIRECT_DSM';
    } else {
      const escalated = await env.DB.prepare(
        "SELECT e.target_node_code,n.parent_node_code FROM ops_escalations e " +
        "JOIN nodes n ON n.node_code=e.target_node_code JOIN nodes p ON p.node_code=n.parent_node_code " +
        "WHERE e.state='OPEN' AND e.assigned_to=? AND e.target_node_code=? " +
        "AND e.severity IN ('HOT','CRITICAL') AND n.role='POS' AND p.role='DSM' AND p.parent_node_code=? LIMIT 1")
        .bind(auth.node_code,target,auth.node_code).first();
      if (!escalated) throw new ApiError('OPS_ASSIST_SCOPE','Le DAE aide ses DSM; un PoS exige une escalade HOT/CRITICAL du DSM.',403);
      relation = 'DAE_EXCEPTION_ESCALATED_POS';
    }
  } else {
    throw new ApiError('OPS_ASSIST_SCOPE','Rôle non autorisé pour cette aide.',403);
  }
  const queued = await queueOpsSyncWake(env,target,auth.device_id,input.reason||'PILOTAGE_V292');
  return success({...queued,assist_relation:relation,non_financial:true},queued.queued?202:200,headers);
}

async function opsEscalate(env, auth, input, headers) {
  const target=nodeCode(input.target_node_code||auth.node_code), severity=String(input.severity||'WARN').toUpperCase();
  if(!['INFO','WARN','HOT','CRITICAL'].includes(severity))throw new ApiError('ESCALATION_SEVERITY_INVALID','Sévérité invalide.',422);
  let assigned='';
  if(auth.role==='POS') {if(target!==auth.node_code)throw new ApiError('ESCALATION_SCOPE','Un PoS ne signale que son propre problème.',403);assigned=auth.parent_node_code;}
  else if(auth.role==='DSM') {const child=await resolveDirectChild(env,auth.node_code,target,'POS');if(!child)throw new ApiError('ESCALATION_SCOPE','Le DSM ne peut escalader qu’un de ses PoS directs.',403);assigned=auth.parent_node_code;}
  else if(auth.role==='DAE') {const child=await resolveDirectChild(env,auth.node_code,target,'DSM');if(!child)throw new ApiError('ESCALATION_SCOPE','Le DAE ne peut escalader qu’un DSM direct.',403);assigned='ADMIN';}
  else throw new ApiError('ESCALATION_SCOPE','Rôle non autorisé.',403);
  const publicId=crypto.randomUUID();await env.DB.prepare('INSERT INTO ops_escalations(public_id,raised_by_node_code,target_node_code,assigned_to,severity,kind,message) VALUES(?,?,?,?,?,?,?)')
    .bind(publicId,auth.node_code,target,assigned,severity,cleanText(input.kind||'ASSISTANCE',80),cleanText(input.message,600)).run();
  return success({public_id:publicId,target_node_code:target,assigned_to:assigned,severity,state:'OPEN'},201,headers);
}
async function opsResolve(env, auth, input, headers) {
  const id=String(input.escalation_id||'').trim();const row=await env.DB.prepare("SELECT * FROM ops_escalations WHERE public_id=? AND state='OPEN'").bind(id).first();
  if(!row)throw new ApiError('ESCALATION_NOT_FOUND','Escalade introuvable.',404);if(row.assigned_to!==auth.node_code)throw new ApiError('ESCALATION_NOT_ASSIGNED','Seul le niveau actuellement responsable peut clôturer ce cas.',403);
  await env.DB.prepare("UPDATE ops_escalations SET state='RESOLVED',resolved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE public_id=?").bind(id).run();return success({public_id:id,state:'RESOLVED'},200,headers);
}
async function ownerOpsCockpit(request, env, auth, headers) {
  const owner=await authenticateOwnerAny(request,env,auth);const nodes=(await env.DB.prepare("SELECT n.node_code,n.role,n.parent_node_code,d.robot_enabled,d.sim_verified,d.offline_pending_events,d.accessibility_enabled,d.accessibility_connected,d.battery_percent,d.last_seen_at,d.last_telemetry_at FROM nodes n LEFT JOIN devices d ON d.device_id=(SELECT d2.device_id FROM devices d2 WHERE d2.node_code=n.node_code AND d2.active=1 ORDER BY d2.robot_enabled DESC,d2.last_seen_at DESC LIMIT 1) WHERE n.active=1 ORDER BY n.role,n.node_code").all()).results||[];
  const health=nodes.map(r=>({...r,...healthView(r)})), dae=health.filter(x=>x.role==='DAE').map(d=>{const desc=health.filter(x=>x.node_code===d.node_code||x.parent_node_code===d.node_code||health.some(m=>m.role==='DSM'&&m.parent_node_code===d.node_code&&x.parent_node_code===m.node_code));return {node_code:d.node_code,label:d.node_code,severity:desc.some(x=>x.severity==='CRITICAL')?'CRITICAL':desc.some(x=>x.severity==='HOT')?'HOT':desc.some(x=>x.severity==='WARN')?'WARN':'OK',action_hint:`${desc.length} nœud(s) dans ce réseau DAE. Les PoS restent gérés par leurs DSM.`,scope_note:'Vue région/nationale agrégée',can_escalate:false};});
  const open=await env.DB.prepare("SELECT * FROM ops_escalations WHERE state='OPEN' AND assigned_to='ADMIN' ORDER BY created_at DESC LIMIT 200").all();
  const continuity=await env.DB.prepare("SELECT received_via,COUNT(*) AS c FROM offline_events WHERE received_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-24 hours') GROUP BY received_via").all();
  let direct=0,relay=0;for(const x of continuity.results||[]){if(x.received_via==='BIR_RELAY')relay+=Number(x.c||0);else direct+=Number(x.c||0);}
  const pendingRow=await env.DB.prepare("SELECT COALESCE(SUM(offline_pending_events),0) AS pending FROM devices WHERE active=1").first();
  const pendingReported=Number(pendingRow?.pending||0), confirmed=direct+relay, continuityDenominator=confirmed+pendingReported;
  const syncRate=continuityDenominator?Math.round(confirmed*1000/continuityDenominator)/10:null;
  const tx=await env.DB.prepare("SELECT COALESCE(SUM(commission_amount),0) AS commission FROM commands WHERE state='SUCCEEDED' AND created_at>=strftime('%Y-%m-%dT%H:%M:%fZ','now','-7 days')").first();const alerts=health.filter(x=>x.severity!=='OK');
  await adminAudit(env,owner.entitlement_id,'OWNER_OPS_COCKPIT',null,auth.device_id,{nodes:nodes.length,alerts:alerts.length},'READ');
  return success({generated_at:new Date().toISOString(),scope_role:owner.kind,groups:dae,escalations:(open.results||[]).map(x=>({...x,can_resolve:true,routing_label:'Escalade DAE → ADMIN'})),summary:{healthy_robots:health.filter(x=>x.robot_enabled&&!x.telemetry_stale&&x.severity==='OK').length,robot_count:health.filter(x=>x.device_id).length,sync_rate_percent:syncRate,sync_confirmed_events:confirmed,pending_events_last_reported:pendingReported,sync_window_hours:24,max_severity:alerts.some(x=>x.severity==='CRITICAL')?'CRITICAL':alerts.some(x=>x.severity==='HOT')?'HOT':alerts.length?'WARN':'OK',next_action:(open.results||[]).length?`${(open.results||[]).length} escalade(s) DAE à examiner.`:alerts.length?`${alerts.length} nœud(s) à surveiller; laissez DSM/DAE traiter leur périmètre.`:'Rien d’urgent au niveau national.',continuity_source:'SERVER_CONFIRMED_ONLY'},forecast:{days_cover:null,message:'Prévision détaillée disponible par DAE'},audit:{proof_count:direct+relay,direct_events:direct,relay_events:relay},commission:{last7d_commission:Number(tx?.commission||0)},rescue:{attention_count:alerts.length+(open.results||[]).length}},200,headers);
}

async function ownerOpsResolve(request, env, auth, input, headers) {
  const owner=await authenticateOwnerAny(request,env,auth);
  const id=String(input.escalation_id||'').trim();
  if(!id)throw new ApiError('ESCALATION_ID_REQUIRED','Identifiant d’escalade requis.',422);
  const row=await env.DB.prepare("SELECT * FROM ops_escalations WHERE public_id=? AND state='OPEN' AND assigned_to='ADMIN'").bind(id).first();
  if(!row)throw new ApiError('ESCALATION_NOT_FOUND','Escalade ADMIN introuvable ou déjà clôturée.',404);
  await env.DB.prepare("UPDATE ops_escalations SET state='RESOLVED',resolved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE public_id=? AND state='OPEN' AND assigned_to='ADMIN'").bind(id).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_OPS_RESOLVE',row.target_node_code,auth.device_id,{escalation_id:id,raised_by_node_code:row.raised_by_node_code,severity:row.severity},'ACCEPTED');
  return success({public_id:id,state:'RESOLVED',target_node_code:row.target_node_code},200,headers);
}


async function shadowEnroll(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) {
    throw new ApiError('REQUEST_NOT_ALLOWED', 'Seul un DAE/DSM peut valider un enfant direct.', 403);
  }
  const childRole = auth.role === 'DAE' ? 'DSM' : 'POS';
  const identity = canonicalCamtelIdentity(input.node_code, childRole, auth.node_code);
  if (!identity.ok) throw identityApiError(identity.error);
  const desired = identity.node_code;
  const p = phone(input.phone_number);
  const displayName = cleanText(input.display_name, 120);
  const zone = cleanText(input.zone, 120);
  const existing = await env.DB.prepare(
    'SELECT node_code, role, phone_number, parent_node_code FROM nodes WHERE node_code=? OR phone_number=? LIMIT 1'
  ).bind(desired, p).first();
  if (existing && (existing.node_code !== desired || existing.phone_number !== p || existing.role !== childRole
      || String(existing.parent_node_code || '') !== auth.node_code)) {
    throw new ApiError('IDENTITY_CONFLICT',
      'Ce numéro ou identifiant appartient déjà à une autre identité Camtel.', 409);
  }
  if (!existing) {
    await env.DB.prepare('INSERT INTO nodes(node_code, role, phone_number, parent_node_code, default_commission_bps) VALUES(?,?,?,?,?)')
      .bind(desired, childRole, p, auth.node_code, childRole === 'DSM' ? 800 : 0).run();
  }
  await env.DB.prepare(
    "INSERT INTO shadow_accounts(node_code, created_by_node_code, terminal_type, display_name, zone) "
    + "VALUES(?, ?, 'TCHORONKO_SHADOW', ?, ?) ON CONFLICT(node_code) DO UPDATE SET "
    + "created_by_node_code=excluded.created_by_node_code, display_name=excluded.display_name, "
    + "zone=excluded.zone, created_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
    + "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  ).bind(desired, auth.node_code, displayName, zone).run();
  return success({shadow:{node_code:desired, local_code:identity.local_code,
    role:childRole, phone_number:p, parent_node_code:auth.node_code,
    region_code:identity.region_code, approval_valid_hours:48,
    terminal_type:'TCHORONKO_SHADOW'}}, 201, headers);
}

async function debtSave(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) throw new ApiError('REQUEST_NOT_ALLOWED', 'Ce rôle ne gère pas de créances enfant.', 403);
  const debtor = await resolveDescendant(env, auth.node_code, input.debtor_node_code, auth.role === 'DAE' ? ['DSM','POS'] : ['POS']);
  if (!debtor) throw new ApiError('DEBTOR_NOT_FOUND', 'Débiteur absent de votre flotte.', 422);
  const advanced = amount(input.amount_advanced);
  const repaid = input.amount_repaid == null || input.amount_repaid === '' ? 0 : Math.max(0, Number(input.amount_repaid));
  if (!Number.isInteger(repaid) || repaid > advanced) throw new ApiError('INVALID_REPAID', 'Remboursement invalide.', 422);
  const id = Number(input.id || 0);
  if (id > 0) {
    await env.DB.prepare(
      "UPDATE debts SET amount_advanced=?, amount_repaid=?, due_date=?, note=?, state=?, "
      + "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND owner_node_code=? AND debtor_node_code=?"
    ).bind(advanced, repaid, cleanText(input.due_date, 40) || null, cleanText(input.note, 300),
      repaid >= advanced ? 'PAID' : 'OPEN', id, auth.node_code, debtor.node_code).run();
  } else {
    await env.DB.prepare('INSERT INTO debts(owner_node_code, debtor_node_code, amount_advanced, amount_repaid, due_date, note, state) VALUES(?,?,?,?,?,?,?)')
      .bind(auth.node_code, debtor.node_code, advanced, repaid, cleanText(input.due_date, 40) || null,
        cleanText(input.note, 300), repaid >= advanced ? 'PAID' : 'OPEN').run();
  }
  return await debtList(env, auth, headers);
}

async function debtList(env, auth, headers) {
  const rows = await env.DB.prepare(
    "SELECT id, debtor_node_code, amount_advanced, amount_repaid, "
    + '(amount_advanced-amount_repaid) AS remaining, due_date, note, state, updated_at '
    + "FROM debts WHERE owner_node_code=? AND state<>'CANCELLED' ORDER BY id DESC LIMIT 200"
  ).bind(auth.node_code).all();
  return success({debts: rows.results || []}, 200, headers);
}

async function kycSave(env, auth, input, headers) {
  const lat = input.latitude === '' || input.latitude == null ? null : Number(input.latitude);
  const lon = input.longitude === '' || input.longitude == null ? null : Number(input.longitude);
  if (lat != null && (!Number.isFinite(lat) || lat < -90 || lat > 90)) throw new ApiError('INVALID_LATITUDE','Latitude invalide.',422);
  if (lon != null && (!Number.isFinite(lon) || lon < -180 || lon > 180)) throw new ApiError('INVALID_LONGITUDE','Longitude invalide.',422);
  await env.DB.prepare(
    'INSERT INTO kyc_profiles(node_code,legal_name,id_document_number,document_reference,latitude,longitude,zone) '
    + 'VALUES(?,?,?,?,?,?,?) ON CONFLICT(node_code) DO UPDATE SET legal_name=excluded.legal_name, '
    + 'id_document_number=excluded.id_document_number, document_reference=excluded.document_reference, '
    + 'latitude=excluded.latitude, longitude=excluded.longitude, zone=excluded.zone, '
    + "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  ).bind(auth.node_code, cleanText(input.legal_name,160), cleanText(input.id_document_number,100),
    cleanText(input.document_reference,200), lat, lon, cleanText(input.zone,120)).run();
  const row = await env.DB.prepare('SELECT * FROM kyc_profiles WHERE node_code=?').bind(auth.node_code).first();
  return success({kyc:row},200,headers);
}

async function commissionRateFor(env, parentNodeCode, childNodeCode) {
  const override = await env.DB.prepare(
    'SELECT rate_bps FROM commission_overrides WHERE parent_node_code=? AND child_node_code=?'
  ).bind(parentNodeCode, childNodeCode).first();
  if (override) return {rate_bps: Number(override.rate_bps), source: 'CHILD_OVERRIDE'};
  const parent = await env.DB.prepare('SELECT default_commission_bps FROM nodes WHERE node_code=?')
    .bind(parentNodeCode).first();
  return {rate_bps: Number(parent?.default_commission_bps || 0), source: 'PARENT_DEFAULT'};
}

function commissionQuote(baseAmount, rateBps) {
  const base = Number(baseAmount || 0);
  const rate = Number(rateBps || 0);
  const commission = Math.floor(base * rate / 10000);
  return {base_amount: base, rate_bps: rate, commission_amount: commission,
    total_amount: base + commission};
}

function maxBaseForTotal(totalAmount, rateBps) {
  const total = Math.max(0, Math.floor(Number(totalAmount || 0)));
  const rate = Math.max(0, Math.floor(Number(rateBps || 0)));
  let base = Math.floor(total * 10000 / (10000 + rate));
  while (base > 0 && commissionQuote(base, rate).total_amount > total) base -= 1;
  while (commissionQuote(base + 1, rate).total_amount <= total) base += 1;
  return base;
}

async function commissionPolicy(env, auth, headers) {
  if (!['DAE','DSM'].includes(auth.role)) {
    return success({node_code: auth.node_code, role: auth.role, default_rate_bps: 0, children: []}, 200, headers);
  }
  const childRole = auth.role === 'DAE' ? 'DSM' : 'POS';
  const parent = await env.DB.prepare('SELECT default_commission_bps FROM nodes WHERE node_code=?')
    .bind(auth.node_code).first();
  const children = await env.DB.prepare(
    'SELECT n.node_code,n.phone_number,o.rate_bps AS override_rate_bps FROM nodes n '
    + 'LEFT JOIN commission_overrides o ON o.parent_node_code=? AND o.child_node_code=n.node_code '
    + 'WHERE n.parent_node_code=? AND n.role=? AND n.active=1 ORDER BY n.node_code'
  ).bind(auth.node_code, auth.node_code, childRole).all();
  return success({node_code:auth.node_code, role:auth.role,
    default_rate_bps:Number(parent?.default_commission_bps || 0),
    children:(children.results||[]).map(row=>({...row,
      effective_rate_bps: row.override_rate_bps == null ? Number(parent?.default_commission_bps || 0) : Number(row.override_rate_bps),
      source: row.override_rate_bps == null ? 'PARENT_DEFAULT' : 'CHILD_OVERRIDE'}))},200,headers);
}

async function commissionSetDefault(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) throw new ApiError('REQUEST_NOT_ALLOWED','Seul un DAE ou DSM définit un taux enfant.',403);
  const rate = Number(input.rate_bps);
  if (!Number.isInteger(rate) || rate < 0 || rate > 5000) throw new ApiError('INVALID_COMMISSION_RATE','Taux invalide.',422);
  await env.DB.prepare('UPDATE nodes SET default_commission_bps=? WHERE node_code=?')
    .bind(rate,auth.node_code).run();
  return commissionPolicy(env,auth,headers);
}

async function commissionSetChild(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) throw new ApiError('REQUEST_NOT_ALLOWED','Seul un DAE ou DSM personnalise un taux enfant.',403);
  const childRole=auth.role==='DAE'?'DSM':'POS';
  const child=await resolveDirectChild(env,auth.node_code,input.child_node_code,childRole);
  if(!child) throw new ApiError('CHILD_NOT_FOUND','Enfant direct introuvable.',422);
  if (input.use_default === true) {
    await env.DB.prepare('DELETE FROM commission_overrides WHERE parent_node_code=? AND child_node_code=?')
      .bind(auth.node_code,child.node_code).run();
  } else {
    const rate=Number(input.rate_bps);
    if(!Number.isInteger(rate)||rate<0||rate>5000) throw new ApiError('INVALID_COMMISSION_RATE','Taux invalide.',422);
    await env.DB.prepare(
      "INSERT INTO commission_overrides(parent_node_code,child_node_code,rate_bps,updated_by_node_code) VALUES(?,?,?,?) "
      + "ON CONFLICT(parent_node_code,child_node_code) DO UPDATE SET rate_bps=excluded.rate_bps,updated_by_node_code=excluded.updated_by_node_code,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
    ).bind(auth.node_code,child.node_code,rate,auth.node_code).run();
  }
  return commissionPolicy(env,auth,headers);
}

async function mercenarySave(env, auth, input, headers) {
  if (auth.role !== 'DAE') throw new ApiError('REQUEST_NOT_ALLOWED','Hub Mercenaires réservé au DAE.',403);
  const p = phone(input.phone_number);
  const name = cleanText(input.display_name,120);
  if (!name) throw new ApiError('NAME_REQUIRED','Nom du mercenaire requis.',422);
  const posCode = String(input.dedicated_pos_node_code || '').trim().toUpperCase();
  let pos = null;
  if (posCode) {
    pos = await resolveDescendant(env, auth.node_code, posCode, ['POS']);
    if (!pos) throw new ApiError('POS_NOT_FOUND','La SIM PoS centrale doit appartenir à votre flotte.',422);
  }
  const deposit = input.deposit_amount == null || input.deposit_amount === '' ? 0 : Number(input.deposit_amount);
  if (!Number.isInteger(deposit) || deposit < 0) throw new ApiError('INVALID_DEPOSIT','Dépôt virtuel invalide.',422);
  let row = await env.DB.prepare('SELECT * FROM mercenary_accounts WHERE owner_dae_node_code=? AND phone_number=?').bind(auth.node_code,p).first();
  if (!row) {
    const result = await env.DB.prepare('INSERT INTO mercenary_accounts(owner_dae_node_code,display_name,phone_number,dedicated_pos_node_code,virtual_balance) VALUES(?,?,?,?,?)')
      .bind(auth.node_code,name,p,pos?.node_code || null,deposit).run();
    row = await env.DB.prepare('SELECT * FROM mercenary_accounts WHERE id=?').bind(result.meta.last_row_id).first();
    if (deposit > 0) await env.DB.prepare("INSERT INTO mercenary_ledger(mercenary_id,kind,amount,note) VALUES(?,'DEPOSIT',?,'Dépôt initial')").bind(row.id,deposit).run();
  } else {
    await env.DB.prepare(
      "UPDATE mercenary_accounts SET display_name=?, dedicated_pos_node_code=?, virtual_balance=virtual_balance+?, "
      + "updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND owner_dae_node_code=?"
    ).bind(name,pos?.node_code || row.dedicated_pos_node_code || null,deposit,row.id,auth.node_code).run();
    if (deposit > 0) await env.DB.prepare("INSERT INTO mercenary_ledger(mercenary_id,kind,amount,note) VALUES(?,'DEPOSIT',?,'Dépôt complémentaire')").bind(row.id,deposit).run();
    row = await env.DB.prepare('SELECT * FROM mercenary_accounts WHERE id=?').bind(row.id).first();
  }
  return success({mercenary:row},201,headers);
}

async function mercenaryList(env, auth, headers) {
  if (auth.role !== 'DAE') throw new ApiError('REQUEST_NOT_ALLOWED','Hub Mercenaires réservé au DAE.',403);
  const rows = await env.DB.prepare('SELECT * FROM mercenary_accounts WHERE owner_dae_node_code=? ORDER BY id DESC').bind(auth.node_code).all();
  return success({mercenaries:rows.results || []},200,headers);
}

async function mercenarySale(env, auth, input, headers) {
  if (auth.role !== 'DAE') throw new ApiError('REQUEST_NOT_ALLOWED','Hub Mercenaires réservé au DAE.',403);
  const mercenaryId = Number(input.mercenary_id || 0);
  const targetPhone = phone(input.client_phone);
  const value = amount(input.amount);
  const clientId = String(input.client_request_id || '').trim();
  if (!/^[A-Za-z0-9_-]{16,80}$/.test(clientId)) throw new ApiError('INVALID_REQUEST_ID','Clé anti-doublon invalide.',422);
  if (input.confirmed !== true) throw new ApiError('CONFIRMATION_REQUIRED','Confirmez le mercenaire, le client et le montant.',409);
  const account = await env.DB.prepare('SELECT * FROM mercenary_accounts WHERE id=? AND owner_dae_node_code=? AND active=1').bind(mercenaryId,auth.node_code).first();
  if (!account || !account.dedicated_pos_node_code) throw new ApiError('MERCENARY_NOT_READY','Compte ou SIM PoS centrale non configuré.',409);
  const pos = await resolveDescendant(env, auth.node_code, account.dedicated_pos_node_code, ['POS']);
  if (!pos) throw new ApiError('POS_NOT_FOUND','SIM PoS centrale absente de votre flotte.',409);
  const commission = Math.floor(value * 75 / 1000);
  const debit = value - commission;
  if (Number(account.virtual_balance) < debit) throw new ApiError('VIRTUAL_BALANCE_INSUFFICIENT',`Solde virtuel disponible : ${account.virtual_balance} FCFA.`,409);
  const physical = await effectiveAvailableBalance(env, pos.node_code, true);
  if (!physical) throw new ApiError('PHYSICAL_BALANCE_REQUIRED','Le solde de la SIM PoS centrale doit être rafraîchi avant cette vente.',409);
  if (physical.available < value) throw new ApiError('PHYSICAL_BALANCE_INSUFFICIENT',`Stock PoS disponible : ${physical.available} FCFA.`,409);
  const duplicate = await env.DB.prepare('SELECT public_id,state FROM commands WHERE requester_node_code=? AND client_request_id=?').bind(auth.node_code,clientId).first();
  if (duplicate) return success({command:duplicate,duplicate:true},200,headers);
  const publicId = crypto.randomUUID();
  const statements = [
    env.DB.prepare(
      'INSERT INTO commands(public_id,client_request_id,requester_node_code,executor_node_code,target_node_code,operation,target_phone,amount,ussd_code,requires_pin) '
      + "SELECT ?,?,?,?,?, 'RETAIL_TRANSFER',?,?,?,1 WHERE EXISTS(SELECT 1 FROM mercenary_accounts WHERE id=? AND owner_dae_node_code=? AND active=1 AND virtual_balance>=?)"
    ).bind(publicId,clientId,auth.node_code,pos.node_code,null,targetPhone,value,CAMTEL_USSD.retailTransfer(targetPhone,value),mercenaryId,auth.node_code,debit),
    env.DB.prepare("INSERT INTO command_events(command_id,device_id,state,message) SELECT id,?,'PENDING','Vente Mercenaire confirmée.' FROM commands WHERE public_id=?").bind(auth.device_id,publicId),
    env.DB.prepare("UPDATE mercenary_accounts SET virtual_balance=virtual_balance-?, commission_balance=commission_balance+?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND EXISTS(SELECT 1 FROM commands WHERE public_id=?)").bind(debit,commission,mercenaryId,publicId),
    env.DB.prepare("INSERT INTO mercenary_sales(mercenary_id,command_public_id,client_phone,amount,debit_amount,commission_amount) SELECT ?,?,?,?,?,? WHERE EXISTS(SELECT 1 FROM commands WHERE public_id=?)").bind(mercenaryId,publicId,targetPhone,value,debit,commission,publicId),
    env.DB.prepare("INSERT INTO mercenary_ledger(mercenary_id,kind,amount,command_public_id,note) SELECT ?,'SALE_DEBIT',?,?,? WHERE EXISTS(SELECT 1 FROM commands WHERE public_id=?)").bind(mercenaryId,debit,publicId,'Débit net après commission 7,5 %',publicId),
    env.DB.prepare("INSERT INTO mercenary_ledger(mercenary_id,kind,amount,command_public_id,note) SELECT ?,'COMMISSION',?,?,? WHERE EXISTS(SELECT 1 FROM commands WHERE public_id=?)").bind(mercenaryId,commission,publicId,'Commission 7,5 %',publicId)
  ];
  const results = await env.DB.batch(statements);
  if (!results[0].meta?.changes) throw new ApiError('MERCENARY_RACE','Le solde virtuel a changé; recommencez.',409);
  return success({command:{public_id:publicId,state:'PENDING',executor_node_code:pos.node_code,target_phone:targetPhone,amount:value},commission_fcfa:commission,debit_fcfa:debit,duplicate:false},201,headers);
}

async function applyMercenaryTerminal(env, publicId, state) {
  const sale = await env.DB.prepare('SELECT * FROM mercenary_sales WHERE command_public_id=?').bind(publicId).first();
  if (!sale) return;
  if (state === 'SUCCEEDED') {
    await env.DB.prepare("UPDATE mercenary_sales SET state='SUCCEEDED',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?").bind(sale.id).run();
    return;
  }
  if (['FAILED','CANCELLED','BLOCKED'].includes(state) && !['REFUNDED','SUCCEEDED'].includes(sale.state)) {
    await env.DB.batch([
      env.DB.prepare("UPDATE mercenary_accounts SET virtual_balance=virtual_balance+?, commission_balance=MAX(0,commission_balance-?),updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?").bind(sale.debit_amount,sale.commission_amount,sale.mercenary_id),
      env.DB.prepare("UPDATE mercenary_sales SET state='REFUNDED',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?").bind(sale.id),
      env.DB.prepare("INSERT INTO mercenary_ledger(mercenary_id,kind,amount,command_public_id,note) VALUES(?,'REFUND',?,?,'Commande non exécutée; solde virtuel restauré')").bind(sale.mercenary_id,sale.debit_amount,publicId)
    ]);
  } else if (state === 'UNKNOWN') {
    await env.DB.prepare("UPDATE mercenary_sales SET state='VERIFY',updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?").bind(sale.id).run();
  }
}


async function networkDashboard(env, auth, headers) {
  const nodes = await env.DB.prepare(
    'WITH RECURSIVE network(node_code) AS (SELECT ? UNION ALL '
    + 'SELECT n.node_code FROM nodes n JOIN network p ON n.parent_node_code = p.node_code '
    + 'WHERE n.active = 1) '
    + 'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, n.default_commission_bps, n.inbound_commission_bps, '
    + 'b.balance, b.source AS balance_source, b.evidence_kind, b.confidence, b.observed_at, b.valid_until, '
    + 'b.evidence_priority, b.operator_event_at, b.balance_quality, b.last_transaction_id, '
    + 'a.last_financial_activity_at, a.last_unbalanced_activity_at, '
    + "COALESCE((SELECT SUM(r.amount) FROM commands r LEFT JOIN commands src ON src.public_id = b.source_command_public_id "
    + "WHERE r.executor_node_code = n.node_code AND r.operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + "AND ((src.id IS NOT NULL AND r.id > src.id) OR (src.id IS NULL AND r.created_at > b.observed_at)) "
    + "AND r.state NOT IN ('FAILED','CANCELLED')),0) AS reserved_amount, "
    + '(SELECT MAX(c.updated_at) FROM commands c WHERE c.requester_node_code = n.node_code '
    + 'OR c.executor_node_code = n.node_code OR c.target_node_code = n.node_code) AS last_activity_at, '
    + '(SELECT COUNT(*) FROM devices d WHERE d.node_code = n.node_code AND d.active = 1) AS android_devices '
    + 'FROM network x JOIN nodes n ON n.node_code = x.node_code '
    + 'LEFT JOIN account_balances b ON b.node_code = n.node_code '
    + 'LEFT JOIN node_activity_state a ON a.node_code = n.node_code ORDER BY n.role, n.node_code'
  ).bind(auth.node_code).all();
  const summary = await env.DB.prepare(
    'WITH RECURSIVE network(node_code) AS (SELECT ? UNION ALL '
    + 'SELECT n.node_code FROM nodes n JOIN network p ON n.parent_node_code = p.node_code '
    + 'WHERE n.active = 1) '
    + "SELECT COUNT(*) AS command_count, "
    + "SUM(CASE WHEN state = 'SUCCEEDED' THEN 1 ELSE 0 END) AS success_count, "
    + "SUM(CASE WHEN state NOT IN ('SUCCEEDED','FAILED','UNKNOWN','BLOCKED','CANCELLED') THEN 1 ELSE 0 END) AS pending_count, "
    + "SUM(CASE WHEN state = 'SUCCEEDED' AND operation IN ('DISTRIBUTION_TRANSFER','RETAIL_TRANSFER') "
    + "THEN amount ELSE 0 END) AS successful_volume "
    + 'FROM commands WHERE requester_node_code IN (SELECT node_code FROM network)'
  ).bind(auth.node_code).first();
  return success({
    generated_at: new Date().toISOString(), root_node_code: auth.node_code,
    nodes: nodes.results.map(row => {
      const balance = row.balance == null ? null : Number(row.balance);
      const reserved = Number(row.reserved_amount || 0);
      const evidenceAt = row.operator_event_at || row.observed_at || '';
      const unbalancedAfterEvidence = Boolean(row.last_unbalanced_activity_at && evidenceAt
        && Date.parse(row.last_unbalanced_activity_at) > Date.parse(evidenceAt));
      const reusable = balance != null && row.balance_quality === 'EXACT'
        && Date.parse(row.valid_until || '') > Date.now() && !unbalancedAfterEvidence;
      const defaultRate = Number(row.default_commission_bps || 0);
      const inboundRate = Number(row.inbound_commission_bps || (row.role === 'DAE' ? 1000 : row.role === 'DSM' ? 900 : row.role === 'POS' ? 800 : 0));
      const baseEquivalent = balance == null ? null : maxBaseForTotal(balance, inboundRate);
      return {...row, balance, default_commission_bps: defaultRate, inbound_commission_bps: inboundRate, reserved_amount: reserved,
        commission_base_balance: baseEquivalent,
        commission_component_balance: balance == null ? null : balance - baseEquivalent,
        available_balance: balance == null ? null : Math.max(0, balance - reserved),
        balance_reusable: reusable,
        balance_age_seconds: row.observed_at
          ? Math.max(0, Math.floor((Date.now() - Date.parse(row.observed_at)) / 1000)) : null,
        android_devices: Number(row.android_devices || 0),
        device_kind: Number(row.android_devices || 0) > 0 ? 'ANDROID' : 'NON_ENREGISTRE'};
    }),
    summary: {
      command_count: Number(summary?.command_count || 0),
      success_count: Number(summary?.success_count || 0),
      pending_count: Number(summary?.pending_count || 0),
      successful_volume: Number(summary?.successful_volume || 0)
    }
  }, 200, headers);
}

async function readJson(request) {
  const text = await request.text();
  if (!text.trim()) return {};
  if (text.length > 16_384) throw new ApiError('BODY_TOO_LARGE', 'Requête trop volumineuse.', 413);
  try {
    const value = JSON.parse(text);
    if (!value || Array.isArray(value) || typeof value !== 'object') throw new Error('not-object');
    return value;
  } catch (_) {
    throw new ApiError('INVALID_JSON', 'Corps JSON invalide.', 400);
  }
}

function nodeCode(value) {
  const node = String(value || '').trim().toUpperCase();
  if (!/^[A-Z0-9\/_-]{3,64}$/.test(node)) throw new ApiError('INVALID_NODE', 'Code nœud invalide.', 422);
  return node;
}

function canonicalChildCode(localCode, parentCode, expectedRole = '') {
  const result = canonicalCamtelIdentity(localCode, expectedRole, parentCode);
  if (!result.ok) throw identityApiError(result.error);
  return result.node_code;
}

function identityApiError(code) {
  const messages = {
    INVALID_DAE_IDENTITY: 'Identifiant DAE invalide. Format attendu : XXY, ex. OU3, CE04 ou LT10.',
    INVALID_DAE_PARENT: 'Le supérieur DSM doit être un DAE officiel, ex. OU3.',
    INVALID_DSM_IDENTITY: 'Identifiant DSM invalide. Utilisez DSM7 dans son DAE ou DSM7_OU3 au format complet.',
    INVALID_DSM_PARENT: 'Le supérieur PoS doit être un DSM complet, ex. DSM7_OU3.',
    INVALID_POS_IDENTITY: 'Identifiant PoS invalide. Utilisez POS16 dans son DSM ou POS16_DSM7_OU3 au format complet.',
    NODE_PARENT_MISMATCH: 'Le nom complet fourni appartient à une autre filiation Camtel.'
  };
  return new ApiError(code || 'INVALID_CAMTEL_IDENTITY',
    messages[code] || 'Identité Camtel invalide.', 422);
}

async function resolveParentNode(env, reference, expectedRole) {
  const value = nodeCode(reference);
  const exact = await env.DB.prepare(
    'SELECT node_code, role FROM nodes WHERE node_code = ? AND active = 1'
  ).bind(value).first();
  if (exact) {
    if (exact.role !== expectedRole) {
      throw new ApiError('INVALID_PARENT_ROLE', `Le supérieur doit être de type ${expectedRole}.`, 422);
    }
    return exact;
  }
  const candidates = await env.DB.prepare(
    'SELECT node_code, role FROM nodes WHERE role = ? AND active = 1 '
    + 'AND node_code LIKE ? ORDER BY node_code LIMIT 2'
  ).bind(expectedRole, `${value}_%`).all();
  if (candidates.results.length === 1) return candidates.results[0];
  if (candidates.results.length > 1) {
    throw new ApiError('PARENT_AMBIGUOUS',
      'Ce code supérieur abrégé existe dans plusieurs arborescences; saisissez son nom complet.', 422);
  }
  throw new ApiError('PARENT_NOT_FOUND', 'Nœud supérieur introuvable.', 422);
}

async function resolveDirectChild(env, parentCode, reference, expectedRole) {
  const value = nodeCode(reference);
  const exact = await env.DB.prepare(
    'SELECT node_code, phone_number FROM nodes '
    + 'WHERE node_code = ? AND parent_node_code = ? AND role = ? AND active = 1'
  ).bind(value, parentCode, expectedRole).first();
  if (exact) return exact;
  const canonical = canonicalChildCode(value, parentCode, expectedRole);
  return env.DB.prepare(
    'SELECT node_code, phone_number FROM nodes '
    + 'WHERE node_code = ? AND parent_node_code = ? AND role = ? AND active = 1'
  ).bind(canonical, parentCode, expectedRole).first();
}

async function commandDigest(command) {
  const parts = [
    command.public_id || '', command.requester_node_code || '', command.executor_node_code || '',
    command.integrity_version >= 2 ? command.executor_phone || '' : null,
    command.target_node_code || '', command.operation || '',
    command.integrity_version >= 3 ? command.command_kind || '' : null,
    command.integrity_version >= 3 ? command.command_argument || '' : null,
    command.target_phone || '',
    command.amount == null ? '' : String(command.amount), command.ussd_code || '',
    command.requires_pin ? '1' : '0'
  ];
  return sha256(parts.filter(value => value !== null).join('|'));
}

async function previewFingerprint(values) {
  return sha256([
    values.executor || '', values.executorPhone || '', values.targetNode || '',
    values.targetPhone || '', values.amount == null ? '' : String(values.amount),
    values.operation || '', values.commandKind || '', values.commandArgument || '', values.ussd || '',
    values.requestedBaseAmount || '', values.commissionRateBps || '', values.commissionAmount || '',
    values.requiresPin ? '1' : '0', values.requiresConfirmation ? '1' : '0',
    values.capacityCheckId || ''
  ].join('|'));
}

function phone(value) {
  const normalized = String(value || '').replace(/\D/g, '');
  if (!/^\d{9}$/.test(normalized)) throw new ApiError('INVALID_PHONE', 'Le numéro doit contenir 9 chiffres.', 422);
  return normalized;
}

function amount(value) {
  const text = String(value ?? '').trim();
  if (!/^[1-9]\d{0,8}$/.test(text)) throw new ApiError('INVALID_AMOUNT', 'Montant entier invalide.', 422);
  const number = Number(text);
  if (!Number.isSafeInteger(number) || number < 1 || number > 50_000_000) {
    throw new ApiError('INVALID_AMOUNT', 'Montant hors limites.', 422);
  }
  return number;
}

function cleanText(value, max) {
  return String(value || '').trim().slice(0, max);
}

async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function randomHex(byteCount) {
  const bytes = new Uint8Array(byteCount);
  crypto.getRandomValues(bytes);
  return [...bytes].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

function constantTimeEqual(left, right) {
  const a = new TextEncoder().encode(left);
  const b = new TextEncoder().encode(right);
  let different = a.length ^ b.length;
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    different |= (a[index % a.length] || 0) ^ (b[index % b.length] || 0);
  }
  return different === 0;
}

function apiHeaders(request, env) {
  const headers = new Headers({
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store, max-age=0',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()'
  });
  const origin = request.headers.get('Origin') || '';
  const allowed = String(env.ALLOWED_ORIGIN || '').trim();
  if (origin && allowed && origin === allowed) {
    headers.set('Access-Control-Allow-Origin', allowed);
    headers.set('Vary', 'Origin');
    headers.set('Access-Control-Allow-Headers', 'Content-Type, X-Device-Token, X-BlueMagic-Client');
    headers.set('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
  }
  return headers;
}

function success(data, status, headers) {
  return new Response(JSON.stringify({ok: true, data}), {status, headers});
}

function failure(code, message, status, headers) {
  return new Response(JSON.stringify({ok: false, error: {code, message}}), {status, headers});
}

class ApiError extends Error {
  constructor(code, message, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}


// ---- B.I.R. v2.8 source-only owner/admin + accounting layer -----------------
async function ownerEnroll(request, env, auth, input, headers) {
  const kind = String(input.kind || '').trim().toUpperCase();
  if (!['OWNER_ADMIN','MOCK_OWNER','SUPER_ADMIN'].includes(kind)) throw new ApiError('OWNER_KIND_INVALID','Entitlement propriétaire invalide.',422);
  const expected = String(kind === 'MOCK_OWNER' ? env.MOCK_OWNER_SECRET || '' : env.OWNER_ADMIN_SECRET || '');
  const provided = String(input.owner_code || '');
  if (expected.length < 32) throw new ApiError('OWNER_CAPABILITY_DISABLED','Entitlement propriétaire non activé sur ce serveur.',503);
  if (!constantTimeEqual(expected, provided)) throw new ApiError('OWNER_ENROLL_DENIED','Code propriétaire incorrect.',403);
  if (kind === 'SUPER_ADMIN') {
    const admin = await env.DB.prepare("SELECT entitlement_id FROM owner_entitlements WHERE kind='OWNER_ADMIN' AND bound_device_id=? AND active=1 LIMIT 1").bind(auth.device_id).first();
    if (!admin) throw new ApiError('SUPER_ADMIN_REQUIRES_ADMIN','Activez d’abord ADMIN sur ce même appareil.',403);
    const existingSuper = await env.DB.prepare("SELECT entitlement_id,bound_device_id FROM owner_entitlements WHERE kind='SUPER_ADMIN' AND active=1 LIMIT 1").first();
    if (existingSuper && existingSuper.bound_device_id !== auth.device_id) throw new ApiError('SUPER_ADMIN_ALREADY_ASSIGNED','Le SUPER-ADMIN unique est déjà lié à un autre appareil.',409);
  }

  const token = randomHex(32), tokenHash = await sha256(token), entitlementId = crypto.randomUUID();
  const existing = await env.DB.prepare('SELECT entitlement_id FROM owner_entitlements WHERE kind=? AND bound_device_id=? LIMIT 1').bind(kind,auth.device_id).first();
  if (existing) {
    await env.DB.prepare("UPDATE owner_entitlements SET token_hash=?, active=1, last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE entitlement_id=?")
      .bind(tokenHash,existing.entitlement_id).run();
    await adminAudit(env, existing.entitlement_id, 'OWNER_REENROLL', auth.node_code, auth.device_id, {kind}, 'ACCEPTED');
    return success({entitlement_id:existing.entitlement_id,owner_token:token,kind},200,headers);
  }
  await env.DB.prepare('INSERT INTO owner_entitlements(entitlement_id,kind,bound_device_id,token_hash,last_seen_at) VALUES(?,?,?,?,?)')
    .bind(entitlementId,kind,auth.device_id,tokenHash,new Date().toISOString()).run();
  await adminAudit(env, entitlementId, 'OWNER_ENROLL', auth.node_code, auth.device_id, {kind}, 'ACCEPTED');
  return success({entitlement_id:entitlementId,owner_token:token,kind},201,headers);
}

async function authenticateOwner(request, env, auth, requiredKind='OWNER_ADMIN') {
  const token = String(request.headers.get('X-Owner-Token') || '').trim();
  if (!token) throw new ApiError('OWNER_AUTH_REQUIRED','Jeton propriétaire requis.',401);
  const row = await env.DB.prepare('SELECT entitlement_id,kind,bound_device_id,active FROM owner_entitlements WHERE token_hash=? LIMIT 1')
    .bind(await sha256(token)).first();
  if (!row || !row.active || row.bound_device_id !== auth.device_id || (requiredKind && row.kind !== requiredKind)) {
    throw new ApiError('OWNER_AUTH_INVALID','Entitlement propriétaire invalide pour cet appareil.',403);
  }
  await env.DB.prepare("UPDATE owner_entitlements SET last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE entitlement_id=?")
    .bind(row.entitlement_id).run();
  return row;
}

async function authenticateOwnerAny(request, env, auth, kinds=['OWNER_ADMIN','SUPER_ADMIN']) {
  const token = String(request.headers.get('X-Owner-Token') || '').trim();
  if (!token) throw new ApiError('OWNER_AUTH_REQUIRED','Jeton propriétaire requis.',401);
  const row = await env.DB.prepare('SELECT entitlement_id,kind,bound_device_id,active FROM owner_entitlements WHERE token_hash=? LIMIT 1')
    .bind(await sha256(token)).first();
  if (!row || !row.active || row.bound_device_id !== auth.device_id || !kinds.includes(row.kind))
    throw new ApiError('OWNER_AUTH_INVALID','Entitlement propriétaire invalide pour cet appareil.',403);
  await env.DB.prepare("UPDATE owner_entitlements SET last_seen_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE entitlement_id=?").bind(row.entitlement_id).run();
  return row;
}
function rejectSensitiveRemotePayload(input) {
  const raw = JSON.stringify(input || {}).toLowerCase();
  if (/\"[^\"]*(?:pin|password|secret|token)[^\"]*\"\s*:/.test(raw))
    throw new ApiError('REMOTE_SECRET_FORBIDDEN','Aucun PIN, mot de passe, secret ou jeton ne peut être transmis par une action distante.',422);
}

async function adminAudit(env, entitlementId, action, targetNode, targetDevice, payload, outcome='ACCEPTED') {
  const safePayload = JSON.stringify(payload || {}).slice(0,2000);
  await env.DB.prepare('INSERT INTO admin_audit_log(entitlement_id,action,target_node_code,target_device_id,payload_json,outcome) VALUES(?,?,?,?,?,?)')
    .bind(entitlementId || null,String(action||'').slice(0,80),targetNode || null,targetDevice || null,safePayload,String(outcome||'ACCEPTED').slice(0,40)).run();
}

function periodSql(period) {
  const p = String(period || 'day').toLowerCase();
  if (p === 'week') return '-7 days';
  if (p === 'month') return '-1 month';
  if (p === 'quarter') return '-3 months';
  if (p === 'year') return '-1 year';
  return '-1 day';
}

async function accountingSummary(env, auth, input, headers) {
  const since = periodSql(input.period);
  const rows = await env.DB.prepare(
    "SELECT operation,state,requester_node_code,executor_node_code,target_node_code,amount,requested_base_amount,commission_amount " +
    "FROM commands WHERE (requester_node_code=? OR executor_node_code=? OR target_node_code=?) " +
    "AND created_at >= strftime('%Y-%m-%dT%H:%M:%fZ','now',?) ORDER BY id DESC LIMIT 5000")
    .bind(auth.node_code,auth.node_code,auth.node_code,since).all();
  let purchase_count=0,purchase_amount=0,sale_count=0,sale_amount=0,commission_amount=0,success_count=0,failed_count=0;
  for (const row of rows.results || []) {
    if (row.state === 'SUCCEEDED') success_count += 1; else if (TERMINAL_STATES.has(row.state)) failed_count += 1;
    if (row.state !== 'SUCCEEDED') continue;
    const base = Number(row.requested_base_amount || row.amount || 0);
    if (row.operation === 'RETAIL_TRANSFER' && row.executor_node_code === auth.node_code) { sale_count += 1; sale_amount += base; }
    else if (row.operation === 'DISTRIBUTION_TRANSFER') {
      if (row.target_node_code === auth.node_code) { purchase_count += 1; purchase_amount += base; }
      else if (row.executor_node_code === auth.node_code) { sale_count += 1; sale_amount += base; }
    }
    commission_amount += Number(row.commission_amount || 0);
  }
  return success({period:String(input.period||'day'),purchase_count,purchase_amount,sale_count,sale_amount,commission_amount,net_flow:sale_amount-purchase_amount,success_count,failed_count,source:'SERVER'},200,headers);
}

async function transactionLedger(env, auth, input, headers) {
  const limit = Math.max(1,Math.min(1000,Number(input.limit||300)));
  const rows = await env.DB.prepare(
    'SELECT public_id,requester_node_code,executor_node_code,target_node_code,operation,target_phone,amount,requested_base_amount,commission_rate_bps,commission_amount,state,operator_transaction_id,created_at,completed_at,updated_at FROM commands ' +
    'WHERE requester_node_code=? OR executor_node_code=? OR target_node_code=? ORDER BY id DESC LIMIT ?')
    .bind(auth.node_code,auth.node_code,auth.node_code,limit).all();
  return success({transactions:rows.results||[]},200,headers);
}

async function ownerSnapshot(request, env, auth, headers) {
  const owner = await authenticateOwnerAny(request,env,auth);
  const nodes = await env.DB.prepare(
    'SELECT n.node_code,n.role,n.phone_number,n.parent_node_code,n.active,n.created_at,n.default_commission_bps,b.balance,b.balance_quality,b.evidence_kind,b.observed_at,b.operator_event_at,s.terminal_type,s.display_name,s.zone ' +
    'FROM nodes n LEFT JOIN account_balances b ON b.node_code=n.node_code LEFT JOIN shadow_accounts s ON s.node_code=n.node_code ORDER BY n.role,n.node_code').all();
  const devices = await env.DB.prepare('SELECT device_id,node_code,mode,device_name,active,robot_enabled,sim_verified,sim_slot,app_version,android_version,last_seen_at,created_at FROM devices ORDER BY node_code,last_seen_at DESC').all();
  const alerts=[];
  for (const d of devices.results||[]) {
    if (!d.active) alerts.push({code:'DEVICE_DISABLED',node_code:d.node_code,device_id:d.device_id,message:'Appareil désactivé.'});
    else if (d.robot_enabled && !d.sim_verified) alerts.push({code:'ROBOT_SIM_UNVERIFIED',node_code:d.node_code,device_id:d.device_id,message:'Robot actif sans preuve SIM valide.'});
    else if (d.robot_enabled && (!d.last_seen_at || Date.now()-Date.parse(d.last_seen_at)>15*60*1000)) alerts.push({code:'ROBOT_OFFLINE',node_code:d.node_code,device_id:d.device_id,message:'Robot annoncé actif mais hors ligne.'});
  }
  await adminAudit(env,owner.entitlement_id,'OWNER_SNAPSHOT',null,auth.device_id,{nodes:(nodes.results||[]).length,devices:(devices.results||[]).length},'READ');
  return success({generated_at:new Date().toISOString(),nodes:nodes.results||[],devices:devices.results||[],alerts},200,headers);
}

async function ownerTransactions(request, env, auth, input, headers) {
  const owner = await authenticateOwnerAny(request,env,auth);
  const limit = Math.max(1,Math.min(2000,Number(input.limit||500)));
  const rows = await env.DB.prepare('SELECT public_id,requester_node_code,executor_node_code,target_node_code,operation,target_phone,amount,requested_base_amount,commission_rate_bps,commission_amount,state,operator_transaction_id,created_at,completed_at,updated_at FROM commands ORDER BY id DESC LIMIT ?').bind(limit).all();
  await adminAudit(env,owner.entitlement_id,'OWNER_TRANSACTIONS',null,auth.device_id,{limit},'READ');
  return success({transactions:rows.results||[]},200,headers);
}

async function ownerAudit(request, env, auth, input, headers) {
  const owner = await authenticateOwnerAny(request,env,auth);
  const limit = Math.max(1,Math.min(1000,Number(input.limit||300)));
  const rows = await env.DB.prepare('SELECT id,entitlement_id,action,target_node_code,target_device_id,outcome,created_at FROM admin_audit_log ORDER BY id DESC LIMIT ?').bind(limit).all();
  await adminAudit(env,owner.entitlement_id,'OWNER_AUDIT_READ',null,auth.device_id,{limit},'READ');
  return success({audit:rows.results||[]},200,headers);
}

async function ownerControl(request, env, auth, input, headers) {
  rejectSensitiveRemotePayload(input);
  const owner = await authenticateOwner(request,env,auth,'SUPER_ADMIN');
  const action = String(input.action||'').trim().toUpperCase();
  if (!['START_ROBOT','STOP_ROBOT','SET_REMOTE','SET_ROBOT','SYNC_NOW','CANCEL_PENDING'].includes(action)) throw new ApiError('ADMIN_ACTION_INVALID','Action de contrôle invalide.',422);
  let deviceId=String(input.target_device_id||'').trim(), node=String(input.target_node_code||'').trim().toUpperCase(), target=null;
  if (deviceId) target=await env.DB.prepare('SELECT device_id,node_code FROM devices WHERE device_id=? LIMIT 1').bind(deviceId).first();
  else if (node) target=await env.DB.prepare('SELECT device_id,node_code FROM devices WHERE node_code=? AND active=1 ORDER BY robot_enabled DESC,last_seen_at DESC LIMIT 1').bind(node).first();
  if (!target) throw new ApiError('ADMIN_TARGET_NOT_FOUND','Appareil cible introuvable.',404);
  await env.DB.prepare('INSERT INTO device_control_actions(target_device_id,target_node_code,action,payload_json,requested_by_entitlement_id) VALUES(?,?,?,?,?)')
    .bind(target.device_id,target.node_code,action,JSON.stringify(input.payload||{}).slice(0,1200),owner.entitlement_id).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_CONTROL_'+action,target.node_code,target.device_id,{queued:true},'QUEUED');
  return success({queued:true,action,target_device_id:target.device_id,target_node_code:target.node_code},202,headers);
}

async function forceSyncRequest(env, auth, input, headers) {
  rejectSensitiveRemotePayload(input || {});
  if (auth.mode !== 'REMOTE') {
    throw new ApiError('FORCE_SYNC_REMOTE_ONLY','Le réveil distant est réservé au profil Remote du même compte.',403);
  }
  await env.DB.prepare("UPDATE sync_wake_requests SET state='EXPIRED' WHERE node_code=? AND state='PENDING' AND created_at<strftime('%Y-%m-%dT%H:%M:%fZ','now','-10 minutes')")
    .bind(auth.node_code).run();
  const robot = await env.DB.prepare("SELECT device_id,last_seen_at FROM devices WHERE node_code=? AND active=1 AND robot_enabled=1 AND sim_verified=1 AND mode IN ('ROBOT','HYBRID') ORDER BY last_seen_at DESC LIMIT 1")
    .bind(auth.node_code).first();
  if (!robot) return success({queued:false,node_code:auth.node_code,reason:'NO_ACTIVE_ROBOT'},200,headers);
  const pending = await env.DB.prepare("SELECT id,created_at FROM sync_wake_requests WHERE node_code=? AND state='PENDING' ORDER BY id DESC LIMIT 1")
    .bind(auth.node_code).first();
  if (pending) return success({queued:true,duplicate_safe:true,wake_id:pending.id,node_code:auth.node_code,robot_device_id:robot.device_id},200,headers);
  const reason = cleanText(input?.reason || 'REMOTE_SYNC_STALE',80) || 'REMOTE_SYNC_STALE';
  const result = await env.DB.prepare("INSERT INTO sync_wake_requests(node_code,requested_by_device_id,reason) VALUES(?,?,?)")
    .bind(auth.node_code,auth.device_id,reason).run();
  return success({queued:true,duplicate_safe:false,wake_id:Number(result.meta?.last_row_id||0),node_code:auth.node_code,robot_device_id:robot.device_id},202,headers);
}

async function ownerAssist(request, env, auth, input, headers) {
  rejectSensitiveRemotePayload(input);
  const owner = await authenticateOwnerAny(request,env,auth);
  const node = nodeCode(input.target_node_code), requestType=String(input.request_type||'').trim().toUpperCase();
  const exists=await env.DB.prepare('SELECT node_code FROM nodes WHERE node_code=? LIMIT 1').bind(node).first();
  if(!exists) throw new ApiError('ADMIN_TARGET_NOT_FOUND','Utilisateur cible introuvable.',404);
  if(!requestType) throw new ApiError('ADMIN_ASSIST_INVALID','Type de commande absent.',422);
  await env.DB.prepare('INSERT INTO admin_assist_requests(target_node_code,request_type,payload_json,requires_user_confirmation,requested_by_entitlement_id) VALUES(?,?,?,?,?)')
    .bind(node,requestType,JSON.stringify(input.payload||{}).slice(0,1800),1,owner.entitlement_id).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_ASSIST',node,null,{request_type:requestType},'PENDING_USER_CONFIRMATION');
  return success({queued:true,target_node_code:node,request_type:requestType,requires_user_confirmation:true},202,headers);
}

async function ownerTchoronkoSave(request, env, auth, input, headers) {
  rejectSensitiveRemotePayload(input);
  const owner = await authenticateOwner(request,env,auth,'SUPER_ADMIN');
  const role = String(input.role||'').trim().toUpperCase();
  if (!['DSM','POS'].includes(role)) throw new ApiError('TCHORONKO_ROLE_INVALID','Un Tchoronko doit être DSM ou POS.',422);
  const node = nodeCode(input.node_code), parent = nodeCode(input.parent_node_code);
  const phone = String(input.phone_number||'').replace(/\D/g,'');
  if (!/^6\d{8}$/.test(phone)) throw new ApiError('PHONE_INVALID','Numéro Blue Tchoronko invalide.',422);
  const parentRow = await env.DB.prepare('SELECT node_code,role FROM nodes WHERE node_code=? AND active=1 LIMIT 1').bind(parent).first();
  const requiredParent = role === 'DSM' ? 'DAE' : 'DSM';
  if (!parentRow || parentRow.role !== requiredParent) throw new ApiError('TCHORONKO_PARENT_INVALID',`Un ${role} doit dépendre directement d'un ${requiredParent}.`,422);
  const existing = await env.DB.prepare('SELECT node_code,role,parent_node_code FROM nodes WHERE node_code=? LIMIT 1').bind(node).first();
  if (existing && existing.role !== role) throw new ApiError('TCHORONKO_ROLE_CONFLICT','Ce code existe déjà avec un autre rôle.',409);
  if (existing) {
    await env.DB.prepare('UPDATE nodes SET phone_number=?,parent_node_code=?,active=1 WHERE node_code=?').bind(phone,parent,node).run();
  } else {
    await env.DB.prepare('INSERT INTO nodes(node_code,role,phone_number,parent_node_code,active) VALUES(?,?,?,?,1)').bind(node,role,phone,parent).run();
  }
  await env.DB.prepare(`INSERT INTO shadow_accounts(node_code,terminal_type,display_name,zone,notes,updated_at)
      VALUES(?,?,?,?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))
      ON CONFLICT(node_code) DO UPDATE SET terminal_type=excluded.terminal_type,display_name=excluded.display_name,zone=excluded.zone,notes=excluded.notes,updated_at=excluded.updated_at`)
    .bind(node,'TCHORONKO_SHADOW',cleanText(input.display_name||node,120),cleanText(input.zone||'',120),cleanText(input.notes||'',500)).run();
  await adminAudit(env,owner.entitlement_id,'OWNER_TCHORONKO_SAVE',node,null,{role,parent_node_code:parent,phone_number:phone},'ACCEPTED');
  return success({saved:true,node_code:node,role,parent_node_code:parent,terminal_type:'TCHORONKO_SHADOW'},200,headers);
}

async function deviceControlPoll(env, auth, headers) {
  let actions=[];
  try {
    const rows=await env.DB.prepare("SELECT id,action,payload_json,created_at FROM device_control_actions WHERE target_device_id=? AND state='PENDING' ORDER BY id ASC LIMIT 20").bind(auth.device_id).all();
    actions=rows.results||[];
  } catch (error) {
    // Migration 0006 not applied yet: explicit capability signal instead of a generic 500.
    throw new ApiError('ADMIN_CONTROL_NOT_ENABLED','Contrôle administrateur non activé sur cette base.',503);
  }
  return success({actions},200,headers);
}

async function deviceControlAck(env, auth, input, headers) {
  const id=Number(input.action_id||0); if(!Number.isInteger(id)||id<=0) throw new ApiError('ADMIN_ACTION_INVALID','Identifiant de contrôle invalide.',422);
  const row=await env.DB.prepare('SELECT requested_by_entitlement_id,target_node_code,action FROM device_control_actions WHERE id=? AND target_device_id=? LIMIT 1').bind(id,auth.device_id).first();
  if(!row) throw new ApiError('ADMIN_ACTION_NOT_FOUND','Commande de contrôle introuvable.',404);
  const ok=input.success===true;
  await env.DB.prepare("UPDATE device_control_actions SET state=?,acknowledged_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'),result_message=? WHERE id=?")
    .bind(ok?'ACKNOWLEDGED':'FAILED',cleanText(input.message||'',500),id).run();
  await adminAudit(env,row.requested_by_entitlement_id,'DEVICE_CONTROL_ACK_'+row.action,row.target_node_code,auth.device_id,{action_id:id},ok?'ACKNOWLEDGED':'FAILED');
  return success({acknowledged:true,id,state:ok?'ACKNOWLEDGED':'FAILED'},200,headers);
}


async function syncLocalEvents(env, auth, input, headers) {
  const events = Array.isArray(input.events) ? input.events : [];
  if (events.length > 100) throw new ApiError('OFFLINE_BATCH_TOO_LARGE', 'Lot hors connexion trop volumineux.', 422);
  const accepted = [];
  for (const event of events) {
    if (!event || typeof event !== 'object') continue;
    const eventId = String(event.event_id || '').trim();
    if (!/^evt_[A-Za-z0-9]{16,80}$/.test(eventId)) continue;
    const kind = cleanText(event.kind || 'EVENT', 80);
    const commandPublicId = cleanText(event.command_id || '', 128) || null;
    const payload = event.payload && typeof event.payload === 'object' ? event.payload : {};
    const payloadJson = JSON.stringify(payload);
    if (payloadJson.length > 12000) continue;
    const createdAt = Number.isFinite(Number(event.created_at)) ? Math.max(0, Math.floor(Number(event.created_at))) : 0;
    const inserted = await env.DB.prepare(
      "INSERT OR IGNORE INTO offline_events(event_id, source_device_id, source_node_code, command_public_id, kind, payload_json, source_created_at, received_via, relay_hops) VALUES(?, ?, ?, ?, ?, ?, ?, 'DIRECT', 0)"
    ).bind(eventId, auth.device_id, auth.node_code, commandPublicId, kind, payloadJson, createdAt).run();
    if (inserted.meta?.changes) {
      await consumeOfflineEvent(env, auth.device_id, auth.node_code, commandPublicId, kind, payload);
    }
    accepted.push(eventId);
  }
  return success({accepted_event_ids: accepted, duplicate_safe: true}, 200, headers);
}

async function relayRegister(env, auth, input, headers) {
  const publicKey = String(input.public_key || '').trim();
  const fingerprint = String(input.fingerprint || '').trim().toLowerCase();
  if (publicKey.length < 100 || publicKey.length > 5000 || !/^[a-f0-9]{64}$/.test(fingerprint)) {
    throw new ApiError('RELAY_IDENTITY_INVALID', 'Identité B.I.R. Relay invalide.', 422);
  }
  if ((await sha256(publicKey)) !== fingerprint) {
    throw new ApiError('RELAY_FINGERPRINT_INVALID', 'Empreinte B.I.R. Relay incohérente.', 422);
  }
  await env.DB.prepare(
    "INSERT INTO relay_identities(device_id,node_code,public_key_b64,fingerprint_sha256,active) VALUES(?,?,?,?,1) "
    + "ON CONFLICT(device_id) DO UPDATE SET node_code=excluded.node_code, public_key_b64=excluded.public_key_b64, fingerprint_sha256=excluded.fingerprint_sha256, active=1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  ).bind(auth.device_id, auth.node_code, publicKey, fingerprint).run();
  return success({registered: true, fingerprint}, 200, headers);
}

async function relaySync(env, auth, input, headers) {
  const event = input && typeof input === 'object' ? input : {};
  if (String(event.protocol || '') !== 'BIR_RELAY_EVENT_V1') throw new ApiError('RELAY_PROTOCOL_INVALID', 'Protocole Relay invalide.', 422);
  const eventId = String(event.event_id || '').trim();
  const sourceDevice = String(event.source_device_id || '').trim();
  const sourceNode = String(event.source_node_code || '').trim().toUpperCase();
  const fingerprint = String(event.relay_fingerprint || '').trim().toLowerCase();
  const publicKey = String(event.relay_public_key || '').trim();
  const signature = String(event.relay_signature || '').trim();
  const hops = Math.max(0, Math.floor(Number(event.relay_hops || 0)));
  if (!/^evt_[A-Za-z0-9]{16,80}$/.test(eventId) || !sourceDevice || !sourceNode || hops > 3) {
    throw new ApiError('RELAY_ENVELOPE_INVALID', 'Enveloppe Relay invalide.', 422);
  }
  const identity = await env.DB.prepare(
    'SELECT r.device_id,r.node_code,r.public_key_b64,r.fingerprint_sha256,d.active FROM relay_identities r JOIN devices d ON d.device_id=r.device_id WHERE r.device_id=? AND r.active=1 LIMIT 1'
  ).bind(sourceDevice).first();
  if (!identity || !identity.active || identity.node_code !== sourceNode || identity.fingerprint_sha256 !== fingerprint || identity.public_key_b64 !== publicKey) {
    throw new ApiError('RELAY_SOURCE_UNTRUSTED', 'Source Relay inconnue ou révoquée.', 403);
  }
  if (!(await verifyRelaySignature(event, publicKey, signature))) {
    throw new ApiError('RELAY_SIGNATURE_INVALID', 'Signature Relay invalide.', 403);
  }
  const kind = cleanText(event.kind || 'EVENT', 80);
  const commandPublicId = cleanText(event.command_id || '', 128) || null;
  const payload = event.payload && typeof event.payload === 'object' ? event.payload : {};
  const payloadJson = JSON.stringify(payload);
  if (payloadJson.length > 12000) throw new ApiError('RELAY_PAYLOAD_TOO_LARGE', 'Événement Relay trop volumineux.', 422);
  const createdAt = Number.isFinite(Number(event.created_at)) ? Math.max(0, Math.floor(Number(event.created_at))) : 0;
  const inserted = await env.DB.prepare(
    "INSERT OR IGNORE INTO offline_events(event_id,source_device_id,source_node_code,command_public_id,kind,payload_json,source_created_at,received_via,relay_fingerprint_sha256,relay_hops) VALUES(?,?,?,?,?,?,?,'BIR_RELAY',?,?)"
  ).bind(eventId, sourceDevice, sourceNode, commandPublicId, kind, payloadJson, createdAt, fingerprint, hops).run();
  if (inserted.meta?.changes) await consumeOfflineEvent(env, sourceDevice, sourceNode, commandPublicId, kind, payload);
  return success({accepted: Boolean(inserted.meta?.changes), duplicate: !inserted.meta?.changes, event_id: eventId, courier_device_id: auth.device_id}, 200, headers);
}

async function consumeOfflineEvent(env, sourceDevice, sourceNode, commandPublicId, kind, payload) {
  const message = cleanText(payload?.result_message || payload?.message || '', 2000);
  if (kind === 'LOCAL_COMMAND_RESULT' && commandPublicId) {
    const command = await env.DB.prepare('SELECT * FROM commands WHERE public_id=? LIMIT 1').bind(commandPublicId).first();
    if (command && command.executor_node_code === sourceNode && !TERMINAL_STATES.has(command.state)) {
      const next = String(payload?.state || '').trim().toUpperCase();
      if (TERMINAL_STATES.has(next)) {
        const tx = cleanText(payload?.operator_transaction_id || '', 128) || null;
        const result = await env.DB.prepare(
          "UPDATE commands SET state=?, result_message=?, operator_transaction_id=COALESCE(?,operator_transaction_id), lease_token_hash=NULL, leased_until=NULL, completed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND state NOT IN ('SUCCEEDED','FAILED','UNKNOWN','BLOCKED','CANCELLED')"
        ).bind(next, message, tx, command.id).run();
        if (result.meta?.changes) {
          await env.DB.prepare('INSERT INTO command_events(command_id,device_id,state,message) VALUES(?,?,?,?)')
            .bind(command.id, sourceDevice, next, `B.I.R. offline/Relay reconciliation — ${message}`.slice(0,2000)).run();
          await applyTerminalEffects(env, command, next, message, commandPublicId);
          if (message) await recordParsedOperatorMessage(env, sourceNode, message, commandPublicId, command, next);
          return;
        }
      }
    }
  }
  if (message) await recordParsedOperatorMessage(env, sourceNode, message, null, null, 'OFFLINE_SYNC');
}

async function verifyRelaySignature(event, publicKeyB64, signatureB64) {
  try {
    const canonical = relayCanonical(event);
    const keyBytes = base64Bytes(publicKeyB64);
    const signature = base64Bytes(signatureB64);
    const key = await crypto.subtle.importKey('spki', keyBytes, {name:'RSASSA-PKCS1-v1_5', hash:'SHA-256'}, false, ['verify']);
    return await crypto.subtle.verify({name:'RSASSA-PKCS1-v1_5'}, key, signature, new TextEncoder().encode(canonical));
  } catch (_) { return false; }
}

function relayCanonical(event) {
  const payload = event?.payload && typeof event.payload === 'object' ? event.payload : {};
  return `${String(event.event_id||'')}|${String(event.source_device_id||'')}|${String(event.source_node_code||'')}|${Math.max(0,Math.floor(Number(event.created_at||0)))}|${String(event.kind||'')}|${JSON.stringify(payload)}`;
}

function base64Bytes(value) {
  const binary = atob(String(value || ''));
  const bytes = new Uint8Array(binary.length);
  for (let i=0;i<binary.length;i+=1) bytes[i]=binary.charCodeAt(i);
  return bytes;
}
