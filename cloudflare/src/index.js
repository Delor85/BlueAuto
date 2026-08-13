const API_VERSION = '2.6.4-cloudflare';
const ROBOT_LIVE_WINDOW_MINUTES = 15;
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
  await claimRobotSlot(env, auth, input, simFingerprint, simSlot, true);
  return success({
    mode: 'ROBOT', node_code: auth.node_code, robot_enabled: true,
    sim_verified: true, robot_claimed: true
  }, 200, headers);
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
  const expectedPreview = await previewFingerprint(values);
  const suppliedPreview = String(input.confirmation_fingerprint || '').trim().toLowerCase();
  if (values.requiresPin && !/^[a-f0-9]{64}$/.test(suppliedPreview)) {
    throw new ApiError('CONFIRMATION_REQUIRED',
      'Affichez et confirmez d’abord le fournisseur, le bénéficiaire et le montant.', 409);
  }
  if (suppliedPreview && suppliedPreview !== expectedPreview) {
    throw new ApiError('CONFIRMATION_CHANGED',
      'Les numéros ou le montant ont changé depuis la confirmation. Recommencez sans composer.', 409);
  }
  const publicId = crypto.randomUUID();
  const createdAt = new Date().toISOString();
  try {
    await env.DB.batch([
      env.DB.prepare(
        'INSERT INTO commands(public_id, client_request_id, requester_node_code, executor_node_code, '
        + 'target_node_code, operation, target_phone, amount, ussd_code, requires_pin) '
        + 'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
      ).bind(
        publicId, clientId, auth.node_code, values.executor, values.targetNode,
        values.operation, values.targetPhone, values.amount, values.ussd, values.requiresPin
      ),
      env.DB.prepare(
        "INSERT INTO command_events(command_id, device_id, state, message) "
        + "SELECT id, ?, 'PENDING', 'Commande créée et contrôlée par le serveur.' "
        + 'FROM commands WHERE public_id = ?'
      ).bind(auth.device_id, publicId)
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
  const availability = await robotAvailability(env, values.executor);
  return success({
    command: {
      public_id: publicId, state: 'PENDING', executor_node_code: values.executor,
      executor_phone: values.executorPhone, target_node_code: values.targetNode,
      target_phone: values.targetPhone,
      operation: values.operation, amount: values.amount,
      created_at: createdAt, updated_at: createdAt,
      ...availability
    },
    duplicate: false
  }, 201, headers);
}

async function previewCommand(env, auth, input, headers) {
  const requestType = String(input.request_type || '').trim().toUpperCase();
  const values = await resolveCommand(env, auth, input, requestType);
  const availability = await robotAvailability(env, values.executor);
  return success({preview: {
    request_type: requestType,
    executor_node_code: values.executor,
    executor_phone: values.executorPhone,
    target_node_code: values.targetNode,
    target_phone: values.targetPhone,
    amount: values.amount,
    operation: values.operation,
    requires_pin: Boolean(values.requiresPin),
    confirmation_fingerprint: await previewFingerprint(values),
    ...availability
  }}, 200, headers);
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
    + "target_node_code, operation, target_phone, amount, ussd_code, requires_pin"
  ).bind(await sha256(leaseToken), auth.node_code).first();
  if (!command) return success({available: false}, 200, headers);

  await env.DB.prepare(
    "INSERT INTO command_events(command_id, device_id, state, message) VALUES(?, ?, 'LEASED', 'Commande réservée au Robot.')"
  ).bind(command.id, auth.device_id).run();
  command.executor_phone = auth.phone_number;
  command.integrity_version = 2;
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
  return success({command: {public_id: publicId, state: nextState}, already_terminal: false}, 200, headers);
}

async function commandStatus(env, auth, input, headers) {
  const publicId = String(input.command_id || '').trim();
  const command = await env.DB.prepare(
    'SELECT public_id, requester_node_code, executor_node_code, target_node_code, operation, target_phone, '
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
  return Object.fromEntries(keys.filter(key => key in command).map(key => [key, command[key]]));
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
    command.target_node_code || '', command.operation || '', command.target_phone || '',
    command.amount == null ? '' : String(command.amount), command.ussd_code || '',
    command.requires_pin ? '1' : '0'
  ];
  return sha256(parts.filter(value => value !== null).join('|'));
}

async function previewFingerprint(values) {
  return sha256([
    values.executor || '', values.executorPhone || '', values.targetNode || '',
    values.targetPhone || '', values.amount == null ? '' : String(values.amount),
    values.operation || '', values.ussd || '', values.requiresPin ? '1' : '0'
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
