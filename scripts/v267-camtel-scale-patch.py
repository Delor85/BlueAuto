from pathlib import Path

ROOT = Path('.')


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def replace_once(path, old, new):
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected one occurrence, found {count}: {old[:100]!r}')
    write(path, text.replace(old, new, 1))


def replace_between(path, start, end, replacement):
    text = read(path)
    a = text.find(start)
    if a < 0:
        raise SystemExit(f'{path}: start marker not found: {start!r}')
    b = text.find(end, a)
    if b < 0:
        raise SystemExit(f'{path}: end marker not found: {end!r}')
    write(path, text[:a] + replacement + text[b:])


# ---------------------------------------------------------------------------
# Canonical Camtel operator catalog (Worker/server side)
# ---------------------------------------------------------------------------
write('cloudflare/src/camtel-catalog.mjs', r'''export const CAMTEL_REGIONS = Object.freeze([
  {code: 'AD', name: 'Adamaoua'},
  {code: 'CE', name: 'Centre'},
  {code: 'ES', name: 'Est'},
  {code: 'EN', name: 'Extrême-Nord'},
  {code: 'LT', name: 'Littoral'},
  {code: 'NO', name: 'Nord'},
  {code: 'NW', name: 'Nord-Ouest'},
  {code: 'OU', name: 'Ouest'},
  {code: 'SU', name: 'Sud'},
  {code: 'SW', name: 'Sud-Ouest'}
]);

const REGION_CODES = new Set(CAMTEL_REGIONS.map(region => region.code));
const DAE_RE = /^([A-Z]{2})(\d{1,3})$/;
const DSM_LOCAL_RE = /^DSM([1-9]\d{0,2})$/;
const DSM_FULL_RE = /^DSM([1-9]\d{0,2})_([A-Z]{2}\d{1,3})$/;
const POS_LOCAL_RE = /^POS([1-9]\d{0,3})$/;
const POS_FULL_RE = /^POS([1-9]\d{0,3})_(DSM[1-9]\d{0,2}_[A-Z]{2}\d{1,3})$/;

export const CAMTEL_USSD = Object.freeze({
  testNumber: () => '*825*3*3#',
  distributionTransfer: (phone, amount) => `*550*2*${phone}*${amount}#`,
  retailTransfer: (phone, amount) => `*550*1*${phone}*${amount}#`,
  balanceOwn: pin => `*550*3*1*${pin}#`,
  historyLast5: pin => `*550*3*3*${pin}#`,
  transactionDetail: (transactionId, pin) => `*550*3*2*${transactionId}*${pin}#`,
  resetPinSelf: () => '*550*5*1#',
  modifyPin: (newPin, oldPin) => `*550*3*5*${newPin}*${newPin}*${oldPin}#`,
  balanceChild: (phone, pin) => `*550*5*2*${phone}*${pin}#`,
  freezeSelf: (phone, pin) => `*550*3*4*${phone}*${pin}#`,
  initChildPinReset: (phone, pin) => `*550*4*1*${phone}*${pin}#`,
  suspendChild: (phone, pin) => `*550*4*2*${phone}*${pin}#`,
  reactivateChild: (phone, pin) => `*550*4*3*${phone}*${pin}#`,
  freezeChild: (phone, pin) => `*550*5*3*${phone}*${pin}#`,
  reactivateFrozenChild: (phone, pin) => `*550*5*4*${phone}*${pin}#`
});

function regionCodeFromDae(dae) {
  const match = DAE_RE.exec(dae || '');
  return match && REGION_CODES.has(match[1]) && Number(match[2]) > 0 ? match[1] : '';
}

export function parseCamtelIdentity(value) {
  const node = String(value || '').trim().toUpperCase();
  let match = DAE_RE.exec(node);
  if (match && REGION_CODES.has(match[1]) && Number(match[2]) > 0) {
    return {ok: true, role: 'DAE', node_code: node, local_code: node,
      parent_node_code: '', dae_node_code: node, dsm_node_code: '', region_code: match[1]};
  }
  match = DSM_FULL_RE.exec(node);
  if (match) {
    const dae = match[2];
    const region = regionCodeFromDae(dae);
    if (region) return {ok: true, role: 'DSM', node_code: node, local_code: `DSM${match[1]}`,
      parent_node_code: dae, dae_node_code: dae, dsm_node_code: node, region_code: region};
  }
  match = POS_FULL_RE.exec(node);
  if (match) {
    const dsm = parseCamtelIdentity(match[2]);
    if (dsm.ok && dsm.role === 'DSM') return {ok: true, role: 'POS', node_code: node,
      local_code: `POS${match[1]}`, parent_node_code: dsm.node_code,
      dae_node_code: dsm.dae_node_code, dsm_node_code: dsm.node_code, region_code: dsm.region_code};
  }
  if (DSM_LOCAL_RE.test(node)) return {ok: true, role: 'DSM_LOCAL', node_code: node, local_code: node};
  if (POS_LOCAL_RE.test(node)) return {ok: true, role: 'POS_LOCAL', node_code: node, local_code: node};
  return {ok: false, error: 'INVALID_CAMTEL_IDENTITY'};
}

export function canonicalCamtelIdentity(value, expectedRole, parentCode = '') {
  const node = String(value || '').trim().toUpperCase();
  const role = String(expectedRole || '').trim().toUpperCase();
  const parent = String(parentCode || '').trim().toUpperCase();
  const parsed = parseCamtelIdentity(node);
  if (role === 'DAE') {
    return parsed.ok && parsed.role === 'DAE' ? parsed
      : {ok: false, error: 'INVALID_DAE_IDENTITY'};
  }
  if (role === 'DSM') {
    const parentIdentity = parseCamtelIdentity(parent);
    if (!parentIdentity.ok || parentIdentity.role !== 'DAE') {
      return {ok: false, error: 'INVALID_DAE_PARENT'};
    }
    if (parsed.ok && parsed.role === 'DSM') {
      return parsed.parent_node_code === parent ? parsed
        : {ok: false, error: 'NODE_PARENT_MISMATCH'};
    }
    const local = DSM_LOCAL_RE.exec(node);
    if (!local) return {ok: false, error: 'INVALID_DSM_IDENTITY'};
    return parseCamtelIdentity(`DSM${local[1]}_${parent}`);
  }
  if (role === 'POS') {
    const parentIdentity = parseCamtelIdentity(parent);
    if (!parentIdentity.ok || parentIdentity.role !== 'DSM') {
      return {ok: false, error: 'INVALID_DSM_PARENT'};
    }
    if (parsed.ok && parsed.role === 'POS') {
      return parsed.parent_node_code === parent ? parsed
        : {ok: false, error: 'NODE_PARENT_MISMATCH'};
    }
    const local = POS_LOCAL_RE.exec(node);
    if (!local) return {ok: false, error: 'INVALID_POS_IDENTITY'};
    return parseCamtelIdentity(`POS${local[1]}_${parent}`);
  }
  return {ok: false, error: 'INVALID_ROLE'};
}

export function publicCamtelCatalog() {
  return {
    catalog_version: '2026-08-v1',
    national_master_sim_name: 'SIM Nationale',
    regions: CAMTEL_REGIONS,
    identity: {
      dae: 'XXY (ex. OU3, CE04, LT10)',
      dsm: 'DSMZ_XXY (ex. DSM7_OU3)',
      pos: 'POSA_DSMZ_XXY (ex. POS16_DSM7_OU3)',
      short_alias_rule: 'DSMZ seulement dans son DAE; POSA seulement dans son DSM; accès direct DAE→PoS exige le nom complet.'
    },
    ussd_templates: {
      TEST_NUMBER: '*825*3*3#',
      DISTRIBUTION_TRANSFER: '*550*2*{phone}*{amount}#',
      RETAIL_TRANSFER: '*550*1*{phone}*{amount}#',
      BALANCE_OWN: '*550*3*1*{PIN_LOCAL}#',
      HISTORY_LAST5: '*550*3*3*{PIN_LOCAL}#',
      TRANSACTION_DETAIL: '*550*3*2*{transaction_id}*{PIN_LOCAL}#',
      RESET_PIN_SELF: '*550*5*1#',
      MODIFY_PIN_LOCAL: '*550*3*5*{new_pin}*{new_pin}*{old_pin}#',
      BALANCE_CHILD: '*550*5*2*{phone}*{PIN_LOCAL}#',
      FREEZE_SELF: '*550*3*4*{phone}*{PIN_LOCAL}#',
      INIT_CHILD_PIN_RESET: '*550*4*1*{phone}*{PIN_LOCAL}#',
      SUSPEND_CHILD: '*550*4*2*{phone}*{PIN_LOCAL}#',
      REACTIVATE_CHILD: '*550*4*3*{phone}*{PIN_LOCAL}#',
      FREEZE_CHILD: '*550*5*3*{phone}*{PIN_LOCAL}#',
      REACTIVATE_FROZEN_CHILD: '*550*5*4*{phone}*{PIN_LOCAL}#'
    }
  };
}
''')

# ---------------------------------------------------------------------------
# Worker: imports, constants and API action
# ---------------------------------------------------------------------------
replace_once('cloudflare/src/index.js',
"import {parseBlueMessage} from './blue-message.mjs';\n",
"import {parseBlueMessage} from './blue-message.mjs';\nimport {CAMTEL_USSD, canonicalCamtelIdentity, parseCamtelIdentity, publicCamtelCatalog} from './camtel-catalog.mjs';\n")
replace_once('cloudflare/src/index.js',
"const BALANCE_EVIDENCE_TTL_SECONDS = 3600;\n",
"const BALANCE_EVIDENCE_TTL_SECONDS = 3600;\nconst REPORT_BALANCE_EVIDENCE_TTL_SECONDS = 14 * 3600;\nconst AUDIT_MAX_OUTSTANDING = 12;\n")
replace_once('cloudflare/src/index.js',
"        case 'network_balance_audit': return await networkBalanceAudit(env, auth, headers);\n",
"        case 'network_balance_audit': return await networkBalanceAudit(env, auth, headers);\n        case 'operator_catalog': return success({catalog: publicCamtelCatalog()}, 200, headers);\n")

# ---------------------------------------------------------------------------
# Worker: strict Camtel identity + superior approval on first subordinate pair
# ---------------------------------------------------------------------------
replace_between('cloudflare/src/index.js', 'async function pairDevice(env, input, headers) {', '\nasync function authenticate(request, env) {', r'''async function pairDevice(env, input, headers) {
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
      'INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?, ?, ?, NULL)'
    ).bind(node, role, phoneNumber).run();
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
''')

# central identity helper used by direct child operations
replace_between('cloudflare/src/index.js', 'function canonicalChildCode(localCode, parentCode, expectedRole = \'\') {', '\nasync function resolveParentNode(env, reference, expectedRole) {', r'''function canonicalChildCode(localCode, parentCode, expectedRole = '') {
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
''')

# ---------------------------------------------------------------------------
# Worker: finance proof chronology must compare operator time, not delayed receipt time
# ---------------------------------------------------------------------------
replace_once('cloudflare/src/index.js',
"    'SELECT b.balance, b.observed_at, b.valid_until, b.confidence, b.balance_quality, b.evidence_kind, b.evidence_priority, '\n    + 'b.source_command_public_id, b.evidence_command_public_id, c.id AS source_command_id '\n",
"    'SELECT b.balance, b.observed_at, b.operator_event_at, b.valid_until, b.confidence, b.balance_quality, b.evidence_kind, b.evidence_priority, '\n    + 'b.source_command_public_id, b.evidence_command_public_id, c.id AS source_command_id '\n")
replace_once('cloudflare/src/index.js',
"    if (activity?.last_unbalanced_activity_at\n        && Date.parse(activity.last_unbalanced_activity_at) > Date.parse(snapshot.observed_at || '')) return null;\n",
"    const evidenceAt = snapshot.operator_event_at || snapshot.observed_at || '';\n    if (activity?.last_unbalanced_activity_at\n        && Date.parse(activity.last_unbalanced_activity_at) > Date.parse(evidenceAt)) return null;\n")

# ---------------------------------------------------------------------------
# Worker: scale-aware report audit - 14h idle evidence, small bounded batches, priority + Bottom-Up
# ---------------------------------------------------------------------------
replace_between('cloudflare/src/index.js', 'async function networkBalanceAudit(env, auth, headers) {', '\nasync function resolveDescendant(env, ancestorNode, requestedNode, roles) {', r'''async function networkBalanceAudit(env, auth, headers) {
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
''')

# ---------------------------------------------------------------------------
# Worker: DAE short DSM allowed, direct DAE→PoS requires full identity
# ---------------------------------------------------------------------------
old_child_balance = r'''  if (requestType === 'CHILD_BALANCE') {
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
'''
new_child_balance = r'''  if (requestType === 'CHILD_BALANCE') {
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
'''
replace_once('cloudflare/src/index.js', old_child_balance, new_child_balance)

# ---------------------------------------------------------------------------
# Worker: centralize USSD templates
# ---------------------------------------------------------------------------
for old, new in [
    ("ussd: `*550*2*${auth.phone_number}*${value}#`", "ussd: CAMTEL_USSD.distributionTransfer(auth.phone_number, value)"),
    ("operation: 'DISTRIBUTION_TRANSFER', ussd: `*550*2*${child.phone_number}*${value}#`, requiresPin: 1", "operation: 'DISTRIBUTION_TRANSFER', ussd: CAMTEL_USSD.distributionTransfer(child.phone_number, value), requiresPin: 1"),
    ("operation: 'RETAIL_TRANSFER', ussd: `*550*1*${targetPhone}*${value}#`, requiresPin: 1", "operation: 'RETAIL_TRANSFER', ussd: CAMTEL_USSD.retailTransfer(targetPhone, value), requiresPin: 1"),
    ("operation: 'TEST_NUMBER', ussd: '*825*3*3#', requiresPin: 0", "operation: 'TEST_NUMBER', ussd: CAMTEL_USSD.testNumber(), requiresPin: 0"),
    (".bind(publicId,clientId,auth.node_code,pos.node_code,null,targetPhone,value,`*550*1*${targetPhone}*${value}#`,mercenaryId,auth.node_code,debit)", ".bind(publicId,clientId,auth.node_code,pos.node_code,null,targetPhone,value,CAMTEL_USSD.retailTransfer(targetPhone,value),mercenaryId,auth.node_code,debit)")
]:
    replace_once('cloudflare/src/index.js', old, new)

# ---------------------------------------------------------------------------
# Worker: operator phone ↔ canonical identity and chronological activity state
# ---------------------------------------------------------------------------
replace_between('cloudflare/src/index.js', 'async function recordParsedOperatorMessage(env, nodeCodeValue, message, publicId, command, commandState) {', '\nfunction publicOperatorMessage(parsed) {', r'''async function recordParsedOperatorMessage(env, nodeCodeValue, message, publicId, command, commandState) {
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
''')
replace_once('cloudflare/src/index.js',
"    commission_amount: parsed.commission_amount, tax_amount: parsed.tax_amount\n",
"    commission_amount: parsed.commission_amount, tax_amount: parsed.tax_amount,\n    identity_conflict: parsed.identity_conflict || ''\n")

# ---------------------------------------------------------------------------
# Worker: live report generated at display time, explicit state instead of frozen numeric snapshot
# ---------------------------------------------------------------------------
replace_between('cloudflare/src/index.js', 'async function platformSnapshot(env, auth, headers) {', '\nasync function shadowEnroll(env, auth, input, headers) {', r'''async function platformSnapshot(env, auth, headers) {
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
''')

# Pre-enrolment is now the authoritative direct-superior approval and canonicalizes aliases.
replace_between('cloudflare/src/index.js', 'async function shadowEnroll(env, auth, input, headers) {', '\nasync function debtSave(env, auth, input, headers) {', r'''async function shadowEnroll(env, auth, input, headers) {
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
    await env.DB.prepare('INSERT INTO nodes(node_code, role, phone_number, parent_node_code) VALUES(?,?,?,?)')
      .bind(desired, childRole, p, auth.node_code).run();
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
''')

# Dashboard finance validity must use operator chronology rather than server receipt chronology.
replace_once('cloudflare/src/index.js',
"      const unbalancedAfterEvidence = Boolean(row.last_unbalanced_activity_at && row.observed_at\n        && Date.parse(row.last_unbalanced_activity_at) > Date.parse(row.observed_at));\n",
"      const evidenceAt = row.operator_event_at || row.observed_at || '';\n      const unbalancedAfterEvidence = Boolean(row.last_unbalanced_activity_at && evidenceAt\n        && Date.parse(row.last_unbalanced_activity_at) > Date.parse(evidenceAt));\n")

# ---------------------------------------------------------------------------
# Parser tests: official Camtel names in messages remain intact
# ---------------------------------------------------------------------------
replace_once('cloudflare/test/blue-message-intelligence.mjs',
"assert.equal(parsed.source_phone, '620451087');\n",
"assert.equal(parsed.source_phone, '620451087');\nassert.equal(parsed.source_node, 'DSM7_OU3');\n")
replace_once('cloudflare/test/blue-message-intelligence.mjs',
"assert.equal(parsed.target_phone, '621081275');\n",
"assert.equal(parsed.target_phone, '621081275');\nassert.equal(parsed.target_node, 'POS16_DSM7_OU3');\n")

write('cloudflare/test/camtel-catalog.mjs', r'''import assert from 'node:assert/strict';
import {CAMTEL_REGIONS, canonicalCamtelIdentity, parseCamtelIdentity, publicCamtelCatalog} from '../src/camtel-catalog.mjs';

assert.equal(CAMTEL_REGIONS.length, 10);
assert.deepEqual(CAMTEL_REGIONS.map(item => item.code), ['AD','CE','ES','EN','LT','NO','NW','OU','SU','SW']);
let id = parseCamtelIdentity('CE04');
assert.equal(id.ok, true);
assert.equal(id.role, 'DAE');
assert.equal(id.region_code, 'CE');
id = canonicalCamtelIdentity('DSM12', 'DSM', 'CE04');
assert.equal(id.node_code, 'DSM12_CE04');
assert.equal(id.parent_node_code, 'CE04');
id = canonicalCamtelIdentity('POS37', 'POS', 'DSM12_CE04');
assert.equal(id.node_code, 'POS37_DSM12_CE04');
assert.equal(id.dae_node_code, 'CE04');
assert.equal(id.region_code, 'CE');
assert.equal(canonicalCamtelIdentity('POS37_DSM12_CE04', 'POS', 'DSM12_CE04').ok, true);
assert.equal(canonicalCamtelIdentity('POS37_DSM12_CE04', 'POS', 'DSM9_CE04').ok, false);
const catalog = publicCamtelCatalog();
assert.equal(catalog.national_master_sim_name, 'SIM Nationale');
assert.match(catalog.identity.pos, /POSA_DSMZ_XXY/);
console.log('Camtel catalog: hierarchy, regions and aliases OK');
''')
replace_once('cloudflare/package.json',
'"check": "node --check src/index.js && node --check src/blue-message.mjs && node test/blue-message-intelligence.mjs && node test/integration.mjs"',
'"check": "node --check src/index.js && node --check src/blue-message.mjs && node --check src/camtel-catalog.mjs && node test/camtel-catalog.mjs && node test/blue-message-intelligence.mjs && node test/integration.mjs"')

# ---------------------------------------------------------------------------
# Integration fixtures now use real Camtel topology and superior pre-approval
# ---------------------------------------------------------------------------
path = 'cloudflare/test/integration.mjs'
text = read(path)
for old, new in [
    ('POS5_DSM-TEST_DAE-TEST', 'POS37_DSM12_CE04'),
    ('DSM-TEST_DAE-TEST', 'DSM12_CE04'),
    ('DAE-TEST', 'CE04'),
    ('DSM-TEST', 'DSM12'),
    ('POS5', 'POS37'),
    ('DAE-REPAIR', 'OU1'),
    ('DAE-LEGACY', 'LT10')
]:
    text = text.replace(old, new)
write(path, text)
replace_once(path,
"  const dsm = await pair({\n    node_code: 'DSM12', parent_node_code: 'CE04', role: 'DSM', mode: 'ROBOT',\n    phone_number: '699000002', device_name: 'Télécommande test'\n  });\n",
r'''  const unapprovedDsm = await rawRequest('pair_device', {
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
''')
replace_once(path,
"  const dsmTwo = await pair({\n    node_code: 'DSM2', parent_node_code: 'CE04', role: 'DSM', mode: 'REMOTE',\n",
"  await request('shadow_enroll', {node_code: 'DSM2', phone_number: '699000004'}, dae.data.device_token);\n  const dsmTwo = await pair({\n    node_code: 'DSM2', parent_node_code: 'CE04', role: 'DSM', mode: 'REMOTE',\n")
replace_once(path,
"  const pos = await pair({\n    node_code: 'POS37', parent_node_code: 'DSM12', role: 'POS', mode: 'ROBOT',\n",
"  await request('shadow_enroll', {node_code: 'POS37', phone_number: '699000003'}, dsm.data.device_token);\n  const pos = await pair({\n    node_code: 'POS37', parent_node_code: 'DSM12_CE04', role: 'POS', mode: 'ROBOT',\n")
# Any later pair/repair of that POS must use the full DSM parent to avoid global ambiguity.
text = read(path).replace("parent_node_code: 'DSM12', role: 'POS'", "parent_node_code: 'DSM12_CE04', role: 'POS'")
write(path, text)

# DAE direct POS requires full name while DSM may use short POS alias.
anchor = "  assert.equal(pos.data.node_code, 'POS37_DSM12_CE04');\n  await attest(pos.data.device_token, 'c'.repeat(64), 1);\n"
replace_once(path, anchor, anchor + r'''  const shortPosFromDae = await requestFailure('create_command', {
    request_type: 'CHILD_BALANCE', target_node_code: 'POS37',
    client_request_id: 'integration-dae-short-pos-refused-01'
  }, dae.data.device_token, 422);
  assert.equal(shortPosFromDae.error.code, 'POS_FULL_NAME_REQUIRED');
''')
# A 20-minute balance is deliberately still valid for the morning report; use >14h to exercise stale audit.
replace_once(path,
"    \"UPDATE account_balances SET observed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','-20 minutes'), \"\n    + \"valid_until=strftime('%Y-%m-%dT%H:%M:%fZ','now','+40 minutes') WHERE node_code='DSM12_CE04'\"\n",
"    \"UPDATE account_balances SET observed_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 hours'), \"\n    + \"operator_event_at=strftime('%Y-%m-%dT%H:%M:%fZ','now','-15 hours'), \"\n    + \"valid_until=strftime('%Y-%m-%dT%H:%M:%fZ','now','-14 hours') WHERE node_code='DSM12_CE04'\"\n")
replace_once(path,
"  assert.equal(networkAudit.data.order, 'BOTTOM_UP_POS_DSM_DAE');\n",
"  assert.equal(networkAudit.data.order, 'PRIORITY_THEN_BOTTOM_UP_POS_DSM_DAE');\n  assert.equal(networkAudit.data.report_freshness_seconds, 14 * 3600);\n  assert.equal(networkAudit.data.max_outstanding_per_scope, 12);\n")

# Late older unbalanced message must not invalidate a newer exact proof.
marker = "  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'CE04').balance, 880);\n\n  const childBalance = await request('create_command', {\n"
replace_once(path, marker, "  assert.equal(liveDashboard.data.nodes.find(node => node.node_code === 'CE04').balance, 880);\n\n" + r'''  await request('record_operator_message', {
    message: 'Your Transfer Airtime to 699000002 - DSM12_CE04 has been successfully processed. Amount is 5.00 FCFA. TransactionID 000039300001 on 07-07-2026 at 01:00:00.'
  }, dae.data.device_token);
  const afterDelayedOld = await request('platform_snapshot', {}, dae.data.device_token);
  const delayedNode = afterDelayedOld.data.nodes.find(node => node.node_code === 'CE04');
  assert.notEqual(delayedNode.balance_report_state, 'RECHECK_REQUIRED');

  const childBalance = await request('create_command', {
''')

# ---------------------------------------------------------------------------
# Android: deterministic staggered nightly planning and bounded retry
# ---------------------------------------------------------------------------
replace_between('app/src/main/java/com/profitloop/blueauto/RobotService.java',
'    private void maybeQueueNightlyNetworkAudit(String profileId, ApiClient api) {',
'\n    private boolean retryOneDueFinalReport() {', r'''    private void maybeQueueNightlyNetworkAudit(String profileId, ApiClient api) {
        String role = AppConfig.role(this, profileId).toUpperCase(Locale.ROOT);
        int startMinute;
        int spanMinutes;
        if ("POS".equals(role)) { startMinute = 2 * 60; spanMinutes = 60; }
        else if ("DSM".equals(role)) { startMinute = 3 * 60; spanMinutes = 60; }
        else if ("DAE".equals(role)) { startMinute = 4 * 60; spanMinutes = 60; }
        else return;

        Calendar now = Calendar.getInstance();
        int minuteOfDay = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE);
        if (minuteOfDay >= 7 * 60) return;
        String dayKey = String.format(Locale.US, "%04d-%03d",
                now.get(Calendar.YEAR), now.get(Calendar.DAY_OF_YEAR));
        String node = AppConfig.nodeCode(this, profileId);
        int slot = deterministicNightSlot(node + "|" + dayKey + "|PRIMARY", spanMinutes);
        int dueMinute = startMinute + slot;
        android.content.SharedPreferences prefs =
                getSharedPreferences("blue_magic_night_audit", MODE_PRIVATE);
        String primaryKey = profileId + "_" + role + "_primary";
        String finalKey = profileId + "_" + role + "_final";
        String retryKey = profileId + "_" + role + "_retry_at";
        long retryAt = prefs.getLong(retryKey, 0L);
        if (System.currentTimeMillis() < retryAt) return;

        String phase = "";
        if (minuteOfDay >= dueMinute && !dayKey.equals(prefs.getString(primaryKey, ""))) {
            phase = "PRIMARY";
        } else if ("DAE".equals(role)) {
            // A small second DAE sweep before 06:00 catches post-audit activity without waking
            // every PoS a second time. Reports themselves remain live and never freeze at this hour.
            int finalDue = 5 * 60 + 15
                    + deterministicNightSlot(node + "|" + dayKey + "|FINAL", 40);
            if (minuteOfDay >= finalDue && !dayKey.equals(prefs.getString(finalKey, ""))) {
                phase = "FINAL";
            }
        }
        if (phase.isEmpty()) return;

        try {
            JSONObject result = api.networkBalanceAudit();
            boolean complete = result.optBoolean("complete", false);
            android.content.SharedPreferences.Editor edit = prefs.edit();
            if (complete) {
                edit.putString("FINAL".equals(phase) ? finalKey : primaryKey, dayKey)
                        .remove(retryKey).apply();
            } else {
                edit.putLong(retryKey, System.currentTimeMillis() + 5 * 60_000L).apply();
            }
            updateNotification(robotSummary("Audit " + phase.toLowerCase(Locale.ROOT) + " " + role + " : "
                    + result.optInt("queued", 0) + " requête(s), "
                    + result.optInt("reused", 0) + " preuve(s), "
                    + result.optInt("deferred", 0) + " différée(s)"));
        } catch (Exception ignored) {
            prefs.edit().putLong(retryKey, System.currentTimeMillis() + 5 * 60_000L).apply();
        }
    }

    private static int deterministicNightSlot(String key, int spanMinutes) {
        int hash = key == null ? 0 : key.hashCode();
        if (hash == Integer.MIN_VALUE) hash = 0;
        return Math.abs(hash) % Math.max(1, spanMinutes);
    }
''')

# ---------------------------------------------------------------------------
# Android: central USSD registry
# ---------------------------------------------------------------------------
write('app/src/main/java/com/profitloop/blueauto/CamtelUssdCatalog.java', r'''package com.profitloop.blueauto;

/**
 * Référentiel unique des commandes USSD Blue/Camtel exécutées par l'APK.
 * Si Camtel change un code, modifier ce fichier et son miroir public
 * cloudflare/src/camtel-catalog.mjs dans le même lot de version.
 * Aucun PIN réel n'est stocké ici.
 */
final class CamtelUssdCatalog {
    private CamtelUssdCatalog() {}

    static String testNumber() { return "*825*3*3#"; }
    static String distributionTransfer(String phone, String amount) { return "*550*2*" + phone + "*" + amount + "#"; }
    static String retailTransfer(String phone, String amount) { return "*550*1*" + phone + "*" + amount + "#"; }
    static String balanceOwn(String pin) { return "*550*3*1*" + pin + "#"; }
    static String historyLast5(String pin) { return "*550*3*3*" + pin + "#"; }
    static String transactionDetail(String id, String pin) { return "*550*3*2*" + id + "*" + pin + "#"; }
    static String resetPinSelf() { return "*550*5*1#"; }
    static String modifyPin(String newPin, String oldPin) { return "*550*3*5*" + newPin + "*" + newPin + "*" + oldPin + "#"; }
    static String balanceChild(String phone, String pin) { return "*550*5*2*" + phone + "*" + pin + "#"; }
    static String freezeSelf(String phone, String pin) { return "*550*3*4*" + phone + "*" + pin + "#"; }
    static String initChildPinReset(String phone, String pin) { return "*550*4*1*" + phone + "*" + pin + "#"; }
    static String suspendChild(String phone, String pin) { return "*550*4*2*" + phone + "*" + pin + "#"; }
    static String reactivateChild(String phone, String pin) { return "*550*4*3*" + phone + "*" + pin + "#"; }
    static String freezeChild(String phone, String pin) { return "*550*5*3*" + phone + "*" + pin + "#"; }
    static String reactivateFrozenChild(String phone, String pin) { return "*550*5*4*" + phone + "*" + pin + "#"; }
}
''')

for old, new in [
    ('built = "*550*2*" + phone + "*" + amount + "#";', 'built = CamtelUssdCatalog.distributionTransfer(phone, amount);'),
    ('built = "*550*1*" + phone + "*" + amount + "#";', 'built = CamtelUssdCatalog.retailTransfer(phone, amount);'),
    ('built = "*825*3*3#";', 'built = CamtelUssdCatalog.testNumber();'),
    ('built = "*550*3*1*" + localPin + "#";', 'built = CamtelUssdCatalog.balanceOwn(localPin);'),
    ('built = "*550*3*3*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.historyLast5(localPin(context, profileId));'),
    ('built = "*550*5*1#";', 'built = CamtelUssdCatalog.resetPinSelf();'),
    ('built = "*550*3*5*" + newPin + "*" + newPin + "*" + oldPin + "#";', 'built = CamtelUssdCatalog.modifyPin(newPin, oldPin);'),
    ('built = "*550*3*2*" + argument + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.transactionDetail(argument, localPin(context, profileId));'),
    ('built = "*550*5*2*" + phone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.balanceChild(phone, localPin(context, profileId));'),
    ('built = "*550*3*4*" + configuredPhone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.freezeSelf(configuredPhone, localPin(context, profileId));'),
    ('built = "*550*4*1*" + phone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.initChildPinReset(phone, localPin(context, profileId));'),
    ('built = "*550*4*2*" + phone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.suspendChild(phone, localPin(context, profileId));'),
    ('built = "*550*4*3*" + phone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.reactivateChild(phone, localPin(context, profileId));'),
    ('built = "*550*5*3*" + phone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.freezeChild(phone, localPin(context, profileId));'),
    ('built = "*550*5*4*" + phone + "*" + localPin(context, profileId) + "#";', 'built = CamtelUssdCatalog.reactivateFrozenChild(phone, localPin(context, profileId));')
]:
    replace_once('app/src/main/java/com/profitloop/blueauto/UssdCommandFactory.java', old, new)

# Pairing UI: official examples and store canonical parent returned by Worker.
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
'EditText nodeCode = field("Code local (ex. SU2, DSM7 ou POS5)", "", false);',
'EditText nodeCode = field("Identifiant Camtel (ex. OU3, DSM7 ou POS16)", "", false);')
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
'EditText parent = field("Code nœud supérieur (vide pour un DAE)", "", false);',
'EditText parent = field("Supérieur : OU3 pour DSM / DSM7_OU3 pour PoS", "", false);')
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
'                    String canonicalNode = data.optString("node_code", node);\n                    if (token.isEmpty()) throw new IllegalStateException("Jeton appareil absent.");',
'                    String canonicalNode = data.optString("node_code", node);\n                    String canonicalParent = data.optString("parent_node_code", parentNode);\n                    if (token.isEmpty()) throw new IllegalStateException("Jeton appareil absent.");')
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',
'                    AppConfig.savePairing(this, deviceId, token, canonicalNode, sim, parentNode,\n',
'                    AppConfig.savePairing(this, deviceId, token, canonicalNode, sim, canonicalParent,\n')

# Operator catalog is read-only through the native bridge.
replace_once('app/src/main/java/com/profitloop/blueauto/ApiClient.java',
'(?:operator_insights|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale)',
'(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale)')

# Platform UI: explain live report state, superior validation and catalog.
replace_once('app/src/main/assets/platform-v267.js',
'<div class="actions"><button id="v267-audit">Rafraîchir réseau intelligent</button><button id="v267-snapshot">Rapport réseau</button><button id="v267-messages">Preuves Blue récentes</button></div>',
'<div class="actions"><button id="v267-audit">Rafraîchir réseau intelligent</button><button id="v267-snapshot">Rapport réseau vivant</button><button id="v267-messages">Preuves Blue récentes</button><button id="v267-catalog">Référentiel Camtel</button></div>')
replace_once('app/src/main/assets/platform-v267.js',
'<section class="card v267-extra"><h3>📟 Pré-enrôlement Tchoronko / Compte fantôme</h3>',
'<section class="card v267-extra"><h3>📟 Validation / pré-enrôlement enfant</h3><p class="small">Le DAE valide ses DSM; le DSM valide ses PoS. La validation initiale est valable 48 h. Un code court est accepté seulement dans sa branche.</p>')
replace_once('app/src/main/assets/platform-v267.js',
"  bind('v267-messages', () => request('operator_insights'));\n",
"  bind('v267-messages', () => request('operator_insights'));\n  bind('v267-catalog', () => request('operator_catalog'));\n")
replace_once('app/src/main/assets/platform-v267.js',
"Audit Bottom-Up lancé : <b>${Number(data.queued||0)}</b> requête(s) sélective(s), <b>${Number(data.reused||0)}</b> preuve(s) réutilisée(s), <b>${Number(data.already_pending||0)}</b> déjà en file, <b>${Number(data.unavailable||0)}</b> indisponible(s).",
"Audit ${esc(data.region_code||'')} / ${esc(data.dae_node_code||data.scope_node_code||'')} : <b>${Number(data.queued||0)}</b> requête(s), <b>${Number(data.reused||0)}</b> preuve(s), <b>${Number(data.deferred||0)}</b> différée(s), <b>${Number(data.unavailable||0)}</b> indisponible(s). Finance 1 h; rapport inactif jusqu’à ${Math.round(Number(data.report_freshness_seconds||0)/3600)} h sans mouvement ultérieur.")
old_snapshot = r'''      const nodes=data.nodes||[]; const dry=nodes.filter(n => n.balance != null && Number(n.balance)<7500);
      const dormant=nodes.filter(n => n.last_activity_at && Date.now()-Date.parse(n.last_activity_at)>48*3600e3);
      const coaching=dormant.slice(0,8).map(n=>`🟠 ${esc(n.node_code)} — Bonjour, votre activité Blue semble ralentie. Solde connu : ${money(n.balance)}. Besoin d'aide pour relancer les ventes ?`);
      $('v267-report-output').innerHTML=`Flotte: <b>${nodes.length}</b> · Zones sèches: <b>${dry.length}</b> · Hibernation >48h: <b>${dormant.length}</b><br>`+
        dry.slice(0,12).map(n=>`🔴 ${esc(n.node_code)} — ${money(n.balance)}`).join('<br>') +
        (coaching.length?'<hr><b>Scripts CRM suggérés</b><br>'+coaching.join('<br>'):'');
'''
new_snapshot = r'''      const nodes=data.nodes||[]; const dry=nodes.filter(n => n.balance != null && Number(n.balance)<7500);
      const dormant=nodes.filter(n => n.last_activity_at && Date.now()-Date.parse(n.last_activity_at)>48*3600e3);
      const recheck=nodes.filter(n => n.balance_report_state==='RECHECK_REQUIRED');
      const certified=nodes.filter(n => n.balance_report_state==='CERTIFIED');
      const coaching=dormant.slice(0,8).map(n=>`🟠 ${esc(n.node_code)} — Bonjour, votre activité Blue semble ralentie. Solde connu : ${money(n.balance)}. Besoin d'aide pour relancer les ventes ?`);
      $('v267-report-output').innerHTML=`Rapport vivant au <b>${esc(data.generated_at||'')}</b> · Flotte: <b>${nodes.length}</b> · Certifiés: <b>${certified.length}</b> · À revérifier: <b>${recheck.length}</b> · Zones sèches: <b>${dry.length}</b><br>`+
        recheck.slice(0,12).map(n=>`⚠ ${esc(n.node_code)} — mouvement après dernière preuve ${esc(n.evidence_at||'inconnue')}`).join('<br>')+
        (recheck.length?'<hr>':'')+dry.slice(0,12).map(n=>`🔴 ${esc(n.node_code)} — ${money(n.balance)} · ${esc(n.balance_report_state||'UNKNOWN')}`).join('<br>') +
        (coaching.length?'<hr><b>Scripts CRM suggérés</b><br>'+coaching.join('<br>'):'');
'''
replace_once('app/src/main/assets/platform-v267.js', old_snapshot, new_snapshot)
replace_once('app/src/main/assets/platform-v267.js',
"    } else if (action === 'operator_insights') {\n",
r'''    } else if (action === 'operator_catalog') {
      const c=data.catalog||{}, regions=c.regions||[], out=$('v267-report-output');
      if(out) out.innerHTML=`<b>Référentiel Camtel ${esc(c.catalog_version||'')}</b> · Master : ${esc(c.national_master_sim_name||'')}<br>`+
        regions.map(r=>`${esc(r.code)}=${esc(r.name)}`).join(' · ')+`<br>${esc(c.identity?.dae||'')}<br>${esc(c.identity?.dsm||'')}<br>${esc(c.identity?.pos||'')}<br>${esc(c.identity?.short_alias_rule||'')}`;
    } else if (action === 'operator_insights') {
''')

# ---------------------------------------------------------------------------
# Documentation: one explicit place to change operator grammar/codes
# ---------------------------------------------------------------------------
write('docs/CAMTEL_OPERATOR_CATALOG.md', '''# Blue Magic — Référentiel opérateur Camtel / Blue\n\nVersion applicative : **2.6.7**. Ce document décrit le référentiel actif. Il ne contient aucun PIN, secret d’appairage ni donnée de signature.\n\n## Identités canoniques\n\n- DAE : `XXY`, par exemple `OU3`, `CE04`, `LT10`. `XX` est l’abréviation régionale et `Y` le rang du DAE dans la région.\n- DSM : `DSMZ_XXY`, par exemple `DSM7_OU3`. Dans l’arborescence du DAE `OU3`, le raccourci `DSM7` est accepté; la base conserve toujours `DSM7_OU3`.\n- PoS : `POSA_DSMZ_XXY`, par exemple `POS16_DSM7_OU3`. Dans l’arborescence du DSM `DSM7_OU3`, le raccourci `POS16` est accepté; la base conserve toujours le nom complet.\n- Accès direct DAE vers un PoS : nom complet obligatoire, car plusieurs DSM peuvent chacun posséder un `POS5`.\n- `node_code` est globalement unique et le numéro SIM est globalement unique. Les messages Blue/Camtel sont rapprochés du nœud canonique par numéro SIM quand celui-ci est connu.\n\n## Régions\n\n`AD` Adamaoua · `CE` Centre · `ES` Est · `EN` Extrême-Nord · `LT` Littoral · `NO` Nord · `NW` Nord-Ouest · `OU` Ouest · `SU` Sud · `SW` Sud-Ouest.\n\n## Validation de création\n\nLe DAE pré-enrôle/valide ses DSM et le DSM pré-enrôle/valide ses PoS. La première activation doit intervenir dans les 48 heures de cette validation. La création d’un DAE racine reste protégée par le mécanisme super-admin d’appairage. Un rôle ne peut pré-enrôler que le niveau immédiatement inférieur.\n\n## Où modifier si Camtel change les noms ou les codes\n\n1. `cloudflare/src/camtel-catalog.mjs` : régions, grammaire canonique, filiation et catalogue public des commandes.\n2. `app/src/main/java/com/profitloop/blueauto/CamtelUssdCatalog.java` : commandes réellement composées par Android.\n3. Mettre à jour les tests `cloudflare/test/camtel-catalog.mjs`, `cloudflare/test/blue-message-intelligence.mjs` et les contrats Android avant tout déploiement.\n\nLe Worker reste l’autorité pour la filiation. L’APK ne devine jamais l’identité à partir d’un montant de solde anonyme : une réponse `BALANCE_CHILD` est attribuée au `target_node_code` complet déjà connu de la commande.\n\n## Audit nocturne\n\nLa fraîcheur financière reste limitée à 1 heure. Pour le rapport du matin, une preuve EXACTE peut être réutilisée jusqu’à 14 heures si aucun mouvement financier non rapproché n’est postérieur à la preuve. Les audits sont répartis de façon déterministe : PoS à partir de 02:00, DSM à partir de 03:00, DAE à partir de 04:00, puis un petit balayage final DAE avant 06:00. Le Worker limite chaque vague à de petits lots et traite d’abord les comptes `P0_RECHECK`, puis aveugles/actifs, puis dormants.\n\nLe rapport est **vivant** : il est recalculé au moment de l’ouverture. Une transaction postérieure à l’audit avec `CurrentBalance` remplace la preuve; sans `CurrentBalance`, le compte passe à `RECHECK_REQUIRED`.\n''')

# ---------------------------------------------------------------------------
# Safety assertions: no migration edit / no production workflow mutation
# ---------------------------------------------------------------------------
if not (ROOT / 'cloudflare/migrations/0004_blue_message_intelligence_and_modules.sql').exists():
    raise SystemExit('0004 missing')
if (ROOT / 'cloudflare/migrations/0005_blue_message_intelligence_and_modules.sql').exists():
    raise SystemExit('0005 must not exist')

print('v2.6.7 Camtel hierarchy + scale patch applied')
