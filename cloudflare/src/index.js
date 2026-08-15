import {parseBlueMessage} from './blue-message.mjs';

const API_VERSION = '2.6.7-cloudflare';
const ROBOT_LIVE_WINDOW_MINUTES = 15;
const BALANCE_EVIDENCE_TTL_SECONDS = 3600;
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
        return success({service: 'blue-magic-api', version: API_VERSION, database: 'online'}, 200, headers);
      }
      if (action === 'pair_device') return await pairDevice(env, input, headers);

      const auth = await authenticate(request, env);
      switch (action) {
        case 'heartbeat': return await heartbeat(env, auth, input, headers);
        case 'activate_robot': return await activateRobot(env, auth, input, headers);
        case 'update_device_mode': return await updateDeviceMode(env, auth, input, headers);
        case 'preview_command': return await previewCommand(env, auth, input, headers);
        case 'create_command': return await createCommand(env, auth, input, headers);
        case 'check_purchase_capacity': return await checkPurchaseCapacity(env, auth, input, headers);
        case 'purchase_capacity_status': return await purchaseCapacityStatus(env, auth, input, headers);
        case 'network_dashboard': return await networkDashboard(env, auth, headers);
        case 'operator_insights': return await operatorInsights(env, auth, headers);
        case 'record_operator_message': return await recordOperatorMessageApi(env, auth, input, headers);
        case 'platform_snapshot': return await platformSnapshot(env, auth, headers);
        case 'shadow_enroll': return await shadowEnroll(env, auth, input, headers);
        case 'debt_save': return await debtSave(env, auth, input, headers);
        case 'debt_list': return await debtList(env, auth, headers);
        case 'kyc_save': return await kycSave(env, auth, input, headers);
        case 'mercenary_save': return await mercenarySave(env, auth, input, headers);
        case 'mercenary_list': return await mercenaryList(env, auth, headers);
        case 'mercenary_sale': return await mercenarySale(env, auth, input, headers);
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
  if (role === 'DAE') parent = '';
  if (role !== 'DAE' && !parent) throw new ApiError('PARENT_REQUIRED', 'Le supérieur est obligatoire.', 422);
  if (parent) {
    const parentNode = await resolveParentNode(env, parent, role === 'DSM' ? 'DAE' : 'DSM');
    parent = parentNode.node_code;
  }

  let node = requestedNode;
  const requestedExisting = await env.DB.prepare(
    'SELECT node_code, parent_node_code FROM nodes WHERE node_code = ?'
  ).bind(requestedNode).first();
  if (role !== 'DAE' && (!requestedExisting
      || String(requestedExisting.parent_node_code || '') !== parent)) {
    node = canonicalChildCode(requestedNode, parent, role);
  }

  const existing = await env.DB.prepare(
    'SELECT node_code, role, phone_number, parent_node_code FROM nodes WHERE node_code = ?'
  ).bind(node).first();
  if (existing) {
    const same = existing.role === role && existing.phone_number === phoneNumber
      && String(existing.parent_node_code || '') === parent;
    if (!same) throw new ApiError('NODE_IDENTITY_CONFLICT', 'Ce nœud existe avec une autre identité.', 409);
  } else {
    const phoneOwner = await env.DB.prepare('SELECT node_code FROM nodes WHERE phone_number = ?')
      .bind(phoneNumber).first();
    if (phoneOwner) throw new ApiError('PHONE_ALREADY_USED', 'Ce numéro appartient déjà à un autre nœud.', 409);
    await env.DB.prepare(
      'INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?, ?, ?, ?)'
    ).bind(node, role, phoneNumber, parent || null).run();
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
  // Prefer the row that already owns this verified physical SIM. This repairs profiles created
  // by older versions that remembered a newer duplicate row while the queue stayed on the old one.
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

  // A token renewal must not leave a phantom Robot behind. Ownership may follow the repaired
  // installation only when this phone proves the same physical SIM and the previous owner has
  // stopped heartbeating. A Remote without that SIM can never take ownership here.
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

  return success({
    device_id: deviceId, device_token: token, node_code: node, role, mode,
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
    + 'app_version = ?, android_version = ?, device_model = ? WHERE device_id = ?'
  ).bind(
    robotEnabled ? 1 : 0,
    simVerified ? 1 : 0,
    simVerified ? simFingerprint : '',
    simSlot,
    cleanText(input.app_version, 40),
    cleanText(input.android_version, 40),
    cleanText(input.device_model, 160),
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
      + 'requires_pin, capacity_check_id) '
      + 'SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? '
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
      values.capacityCheckId, auth.node_code, values.executor, values.amount, values.amount
    )
    : env.DB.prepare(
      'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
      + 'target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, '
      + 'requires_pin, capacity_check_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(
      publicId, clientId, auth.node_code, values.executor, values.targetNode,
      values.operation, values.commandKind || '', values.commandArgument || '', values.targetPhone,
      values.amount, values.ussd, values.requiresPin, null
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
  // Le cahier impose de mutualiser les ressources fiables. Une preuve Camtel explicite reste
  // réutilisable une heure tant qu’aucune activité non rapprochée n’est observée; les débits/réservations connus sont déduits avant toute décision.
  const reusable = await effectiveAvailableBalance(env, values.executor, true);
  if (reusable) {
    const state = values.amount <= reusable.available ? 'AVAILABLE' : 'INSUFFICIENT';
    const message = state === 'AVAILABLE'
      ? 'Une preuve Camtel de moins d’une heure, sans activité non rapprochée, couvre le montant; aucun USSD supplémentaire.'
      : 'Le montant demandé dépasse la preuve récente du solde disponible du supérieur.';
    await env.DB.prepare(
      'INSERT INTO purchase_preflights(public_id, client_request_id, requester_node_code, '
      + 'supplier_node_code, requested_amount, available_balance, balance_command_public_id, '
      + 'balance_reused, balance_observed_at, state, result_message, expires_at) '
      + "VALUES(?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, "
      + "strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'))"
    ).bind(checkId, clientId, auth.node_code, values.executor, values.amount,
      reusable.available, reusable.evidence_command_public_id || reusable.source_command_public_id,
      reusable.observed_at, state, message).run();
    const availability = await robotAvailability(env, values.executor);
    return success({capacity: {
      capacity_check_id: checkId, state, requested_amount: values.amount,
      supplier_node_code: values.executor, available_balance: reusable.available,
      balance_command_id: reusable.evidence_command_public_id || reusable.source_command_public_id || '',
      balance_reused: true, balance_observed_at: reusable.observed_at, message,
      ...availability
    }}, 201, headers);
  }

  // Sans preuve encore valide, une seule consultation BALANCE_OWN est partagée entre toutes les
  // demandes concurrentes du même fournisseur.
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
        + "SELECT id, ?, 'PENDING', 'Actualisation du solde demandée avant un approvisionnement.' "
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
    balanceCommand.public_id, 'Lecture USSD du solde du supérieur en cours.').run();
  const availability = await robotAvailability(env, values.executor);
  return success({capacity: {
    capacity_check_id: checkId, state: 'WAITING', requested_amount: values.amount,
    supplier_node_code: values.executor, available_balance: null,
    balance_command_id: balanceCommand.public_id, balance_reused: false,
    balance_observed_at: '', ...availability
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
    available_balance: row.available_balance == null ? null : Number(row.available_balance),
    supplier_node_code: row.supplier_node_code,
    balance_command_id: row.balance_command_public_id || '',
    balance_reused: Boolean(row.balance_reused),
    balance_observed_at: row.balance_observed_at || '',
    message: state === 'EXPIRED' ? 'Le contrôle de solde a expiré; relancez la demande.'
      : row.result_message || '',
    expires_at: row.expires_at || ''
  };
}

async function effectiveAvailableBalance(env, node, requireReusable = false) {
  const snapshot = await env.DB.prepare(
    'SELECT b.balance, b.observed_at, b.valid_until, b.confidence, b.balance_quality, b.evidence_kind, b.evidence_priority, '
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
    if (activity?.last_unbalanced_activity_at
        && Date.parse(activity.last_unbalanced_activity_at) > Date.parse(snapshot.observed_at || '')) return null;
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
    return {
      executor: parent.node_code, executorPhone: parent.phone_number,
      targetNode: requester, targetPhone: auth.phone_number,
      amount: value, operation: 'DISTRIBUTION_TRANSFER',
      ussd: `*550*2*${auth.phone_number}*${value}#`, requiresPin: 1
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
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: child.node_code, targetPhone: child.phone_number, amount: value,
      operation: 'DISTRIBUTION_TRANSFER', ussd: `*550*2*${child.phone_number}*${value}#`, requiresPin: 1
    };
  }
  if (requestType === 'RETAIL_SALE') {
    if (auth.role !== 'POS') throw new ApiError('REQUEST_NOT_ALLOWED', 'Vente détail réservée aux PoS.', 403);
    const targetPhone = phone(input.target_phone);
    const value = amount(input.amount);
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: null, targetPhone, amount: value,
      operation: 'RETAIL_TRANSFER', ussd: `*550*1*${targetPhone}*${value}#`, requiresPin: 1
    };
  }
  if (requestType === 'TEST_NUMBER') {
    return {
      executor: requester, executorPhone: auth.phone_number,
      targetNode: null, targetPhone: null, amount: null,
      operation: 'TEST_NUMBER', ussd: '*825*3*3#', requiresPin: 0
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
    let child;
    if (auth.role === 'DAE') {
      child = await resolveDescendant(env, requester, input.target_node_code, ['DSM', 'POS']);
    } else {
      child = await resolveDirectChild(env, requester, input.target_node_code, 'POS');
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

  await env.DB.prepare(
    "UPDATE commands SET state = CASE "
    + "WHEN state = 'LEASED' AND attempt < max_attempts THEN 'PENDING' "
    + "WHEN state = 'LEASED' THEN 'FAILED' ELSE 'UNKNOWN' END, "
    + "result_message = CASE "
    + "WHEN state = 'LEASED' AND attempt < max_attempts THEN 'Lease expiré avant composition.' "
    + "WHEN state = 'LEASED' THEN 'Robot indisponible après plusieurs leases.' "
    + "ELSE 'Session USSD expirée après composition; vérification manuelle requise.' END, "
    + 'lease_token_hash = NULL, leased_until = NULL, '
    + "completed_at = CASE WHEN state <> 'LEASED' OR attempt >= max_attempts "
    + "THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now') ELSE completed_at END, "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
    + "WHERE executor_node_code = ? "
    + "AND state IN ('LEASED', 'DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT') "
    + "AND leased_until < strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
  ).bind(auth.node_code).run();

  const active = await env.DB.prepare(
    "SELECT public_id, state FROM commands WHERE executor_node_code = ? "
    + "AND state IN ('LEASED', 'DIALING', 'AWAITING_PIN', 'PIN_SUBMITTED', 'AWAITING_RESULT') "
    + 'ORDER BY id LIMIT 1'
  ).bind(auth.node_code).first();
  if (active) {
    return success({available: false, busy: true, active_command: active}, 200, headers);
  }

  const leaseToken = randomHex(24);
  const command = await env.DB.prepare(
    "UPDATE commands SET state = 'LEASED', attempt = attempt + 1, lease_token_hash = ?, "
    + "leased_until = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+120 seconds'), "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
    + "WHERE id = (SELECT id FROM commands WHERE executor_node_code = ? AND state = 'PENDING' ORDER BY id LIMIT 1) "
    + "AND state = 'PENDING' RETURNING id, public_id, requester_node_code, executor_node_code, "
    + "target_node_code, operation, command_kind, command_argument, target_phone, amount, ussd_code, requires_pin"
  ).bind(await sha256(leaseToken), auth.node_code).first();
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
    'SELECT id, state, executor_node_code, lease_token_hash FROM commands WHERE public_id = ?'
  ).bind(publicId).first();
  if (!command || command.executor_node_code !== auth.node_code) {
    throw new ApiError('COMMAND_NOT_FOUND', 'Commande introuvable pour ce Robot.', 404);
  }
  if (command.state !== 'LEASED') {
    return success({command: {public_id: publicId, state: command.state}, released: false}, 200, headers);
  }
  if (!command.lease_token_hash || command.lease_token_hash !== await sha256(leaseToken)) {
    throw new ApiError('LEASE_INVALID', 'Lease invalide ou expiré.', 409);
  }
  const reason = cleanText(input.reason || 'Exécution différée par le Robot.', 500);
  const results = await env.DB.batch([
    env.DB.prepare(
      "UPDATE commands SET state = 'PENDING', attempt = CASE WHEN attempt > 0 THEN attempt - 1 ELSE 0 END, "
      + 'lease_token_hash = NULL, leased_until = NULL, result_message = ?, '
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
      + 'leased_until = CASE WHEN ? = 1 THEN NULL ELSE leased_until END, '
      + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
      + 'WHERE id = ? AND state = ?'
    ).bind(nextState, message, operatorId, nextState, terminal ? 1 : 0, terminal ? 1 : 0, command.id, command.state),
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
  const effective = await effectiveAvailableBalance(env, nodeCode, true);
  if (!effective) return;
  await env.DB.prepare(
    "UPDATE purchase_preflights SET state = CASE WHEN requested_amount <= ? "
    + "THEN 'AVAILABLE' ELSE 'INSUFFICIENT' END, available_balance = ?, balance_reused = 0, "
    + 'balance_command_public_id = ?, balance_observed_at = ?, '
    + "result_message = CASE WHEN requested_amount <= ? "
    + "THEN 'Le solde Camtel certifié couvre le montant demandé.' "
    + "ELSE 'Le montant demandé dépasse le solde disponible du supérieur.' END, "
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') "
    + "WHERE supplier_node_code = ? AND state = 'WAITING'"
  ).bind(effective.available, effective.available,
    effective.evidence_command_public_id || effective.source_command_public_id,
    effective.observed_at, effective.available, nodeCode).run();
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
    await env.DB.prepare(
      'INSERT OR IGNORE INTO operator_messages(command_public_id, node_code, message_kind, status, '
      + 'receipt_number, source_phone, source_node_code, target_phone, target_node_code, amount, '
      + 'current_balance, account_no, transaction_date, debit_credit, charge_amount, commission_amount, '
      + 'tax_amount, raw_message) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    ).bind(publicId, nodeCodeValue, 'MINI_STATEMENT_ENTRY', entry.status || 'INFO',
      entry.receipt_number || null, entry.source_phone || '', entry.source_node || '',
      entry.target_phone || '', entry.target_node || '', entry.debit_credit_amount,
      entry.current_balance, entry.account_no || '', entry.transaction_date || '',
      entry.debit_credit || '', entry.charge_amount, entry.commission_amount, entry.tax_amount,
      cleanText(entry.raw_message, 1800)).run();
  }

  const passiveFinancial = !command && ['TRANSFER_RECEIVED','TRANSFER_SENT','RETAIL_TOPUP_RECEIVED','RETAIL_TOPUP_SENT'].includes(parsed.kind)
    && parsed.status === 'SUCCEEDED';
  const financial = (command && ['DISTRIBUTION_TRANSFER', 'RETAIL_TRANSFER'].includes(command.operation)
    && ['SUCCEEDED', 'UNKNOWN'].includes(commandState)) || passiveFinancial;
  const unbalanced = financial && parsed.current_balance == null;
  await env.DB.prepare(
    'INSERT INTO node_activity_state(node_code, last_activity_at, last_financial_activity_at, '
    + 'last_unbalanced_activity_at, last_operator_message_at, last_transaction_id, transaction_counter) '
    + "VALUES(?, strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
    + "CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%fZ','now') ELSE NULL END, "
    + "CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%fZ','now') ELSE NULL END, "
    + "strftime('%Y-%m-%dT%H:%M:%fZ','now'), ?, CASE WHEN ? THEN 1 ELSE 0 END) "
    + 'ON CONFLICT(node_code) DO UPDATE SET '
    + "last_activity_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
    + "last_financial_activity_at = CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%fZ','now') ELSE last_financial_activity_at END, "
    + "last_unbalanced_activity_at = CASE WHEN ? THEN strftime('%Y-%m-%dT%H:%M:%fZ','now') "
    + 'WHEN ? IS NOT NULL THEN NULL ELSE last_unbalanced_activity_at END, '
    + "last_operator_message_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'), "
    + 'last_transaction_id = CASE WHEN length(?) > 0 THEN ? ELSE last_transaction_id END, '
    + 'transaction_counter = transaction_counter + CASE WHEN ? THEN 1 ELSE 0 END, '
    + "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  ).bind(nodeCodeValue, financial ? 1 : 0, unbalanced ? 1 : 0, tx || '', financial ? 1 : 0,
    financial ? 1 : 0, unbalanced ? 1 : 0, parsed.current_balance,
    tx || '', tx || '', financial ? 1 : 0).run();
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
    commission_amount: parsed.commission_amount, tax_amount: parsed.tax_amount
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
    + 's.terminal_type, s.display_name, s.zone, a.last_activity_at, a.last_financial_activity_at '
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
  return success({nodes: nodes.results || [], debts: debts.results || [], mercenary}, 200, headers);
}

async function shadowEnroll(env, auth, input, headers) {
  if (!['DAE','DSM'].includes(auth.role)) throw new ApiError('REQUEST_NOT_ALLOWED', 'Seul un DAE/DSM peut pré-enrôler un enfant.', 403);
  const childRole = auth.role === 'DAE' ? 'DSM' : 'POS';
  const desired = nodeCode(input.node_code);
  const p = phone(input.phone_number);
  const displayName = cleanText(input.display_name, 120);
  const zone = cleanText(input.zone, 120);
  const existing = await env.DB.prepare('SELECT node_code, role, phone_number, parent_node_code FROM nodes WHERE node_code=? OR phone_number=? LIMIT 1')
    .bind(desired, p).first();
  if (existing && (existing.node_code !== desired || existing.phone_number !== p || existing.role !== childRole
      || String(existing.parent_node_code || '') !== auth.node_code)) {
    throw new ApiError('IDENTITY_CONFLICT', 'Ce numéro ou identifiant appartient déjà à une autre identité.', 409);
  }
  if (!existing) {
    await env.DB.prepare('INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?,?,?,?)')
      .bind(desired, childRole, p, auth.node_code).run();
  }
  await env.DB.prepare(
    "INSERT INTO shadow_accounts(node_code, created_by_node_code, terminal_type, display_name, zone) "
    + "VALUES(?, ?, 'TCHORONKO_SHADOW', ?, ?) ON CONFLICT(node_code) DO UPDATE SET "
    + "display_name=excluded.display_name, zone=excluded.zone, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
  ).bind(desired, auth.node_code, displayName, zone).run();
  return success({shadow:{node_code:desired, role:childRole, phone_number:p, terminal_type:'TCHORONKO_SHADOW'}}, 201, headers);
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
    ).bind(publicId,clientId,auth.node_code,pos.node_code,null,targetPhone,value,`*550*1*${targetPhone}*${value}#`,mercenaryId,auth.node_code,debit),
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
    + 'SELECT n.node_code, n.role, n.phone_number, n.parent_node_code, '
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
      const unbalancedAfterEvidence = Boolean(row.last_unbalanced_activity_at && row.observed_at
        && Date.parse(row.last_unbalanced_activity_at) > Date.parse(row.observed_at));
      const reusable = balance != null && row.balance_quality === 'EXACT'
        && Date.parse(row.valid_until || '') > Date.now() && !unbalancedAfterEvidence;
      return {...row, balance, reserved_amount: reserved,
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
  const local = nodeCode(localCode);
  if (expectedRole && !local.startsWith(expectedRole)) {
    throw new ApiError('INVALID_NODE_ROLE', `Le code doit commencer par ${expectedRole}.`, 422);
  }
  const suffix = `_${parentCode}`;
  if (local.endsWith(suffix)) return local;
  if (local.includes('_')) {
    throw new ApiError('NODE_PARENT_MISMATCH',
      'Le nom complet fourni appartient à une autre arborescence.', 422);
  }
  return nodeCode(`${local}${suffix}`);
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
