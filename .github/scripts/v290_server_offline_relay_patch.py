from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'cloudflare/src/index.js'
s=p.read_text(encoding='utf-8')

def once(old,new,label):
    global s
    if s.count(old)!=1: raise SystemExit(f'v290 server anchor {label}: expected 1 got {s.count(old)}')
    s=s.replace(old,new,1)

once("const API_VERSION = '2.8.0-cloudflare';","const API_VERSION = '2.9.0-cloudflare';",'version')
once("event_balance: true}}, 200, headers);","event_balance: true, offline_sync: true, bir_relay: true, effective_modes: ['REMOTE','ROBOT']}}, 200, headers);",'capabilities')
once("        case 'record_operator_message': return await recordOperatorMessageApi(env, auth, input, headers);",
     "        case 'record_operator_message': return await recordOperatorMessageApi(env, auth, input, headers);\n        case 'sync_local_events': return await syncLocalEvents(env, auth, input, headers);\n        case 'relay_register': return await relayRegister(env, auth, input, headers);\n        case 'relay_sync': return await relaySync(env, auth, input, headers);",'routes')

# Keep legacy HYBRID accepted server-side only for safe upgrades of old installed builds.
# The v2.9 Android UI exposes/effectively uses only REMOTE and ROBOT.

append=r'''

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
'''

if 'async function syncLocalEvents(env, auth, input, headers)' not in s:
    s += append
p.write_text(s,encoding='utf-8')
print('BIR v2.9 server offline/Relay source patch applied')
