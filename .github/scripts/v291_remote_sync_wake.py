from pathlib import Path


def replace_once(path, old, new, label):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if text.count(old)!=1: raise SystemExit(f'{label}: expected 1 anchor, got {text.count(old)}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

# Worker: complete advertised force_sync capability with a same-node, non-financial wake queue.
replace_once('cloudflare/src/index.js',
"const API_VERSION = '2.9.0-cloudflare';",
"const API_VERSION = '2.9.1-cloudflare';",
'worker version')
replace_once('cloudflare/src/index.js',
"        case 'heartbeat': return await heartbeat(env, auth, input, headers);\n",
"        case 'heartbeat': return await heartbeat(env, auth, input, headers);\n        case 'force_sync': return await forceSyncRequest(env, auth, input, headers);\n",
'force_sync route')
anchor="""async function ownerAssist(request, env, auth, input, headers) {
"""
insert="""async function forceSyncRequest(env, auth, input, headers) {
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

"""+anchor
replace_once('cloudflare/src/index.js',anchor,insert,'force_sync function')
lease_anchor="""  if (!auth.robot_enabled) {
    return success({
      available: false, standby: true,
      reason: 'Cette SIM est actuellement revendiquée par un autre téléphone Robot.'
    }, 200, headers);
  }

"""
lease_insert=lease_anchor+"""  // Non-financial Remote wake piggybacks on the Robot's existing lease poll.
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

"""
replace_once('cloudflare/src/index.js',lease_anchor,lease_insert,'lease wake consumption')

# Android API client: safe control-plane request only.
api_anchor="""    JSONObject leaseCommand() throws Exception {
        return postControl("lease_command", new JSONObject(), true);
    }

"""
api_insert=api_anchor+"""    JSONObject requestForceSync(String reason) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("reason", reason == null ? "REMOTE_SYNC_STALE" : trim(reason, 80));
        return postControl("force_sync", payload, true);
    }

"""
replace_once('app/src/main/java/com/profitloop/blueauto/ApiClient.java',api_anchor,api_insert,'ApiClient force sync')

# Remote bridge: wake locally, then ask only its own same-node Robot through the server.
main_anchor="""        @JavascriptInterface
        public void kickSynchronization() {
            // Silent, non-financial control-plane wake used by the field self-healing layer.
            // It never creates a command and never dials USSD.
            RobotService.forceSync(MainActivity.this);
        }
"""
main_insert="""        @JavascriptInterface
        public void kickSynchronization() {
            // Silent, non-financial control-plane wake used by the field self-healing layer.
            // It never creates a command and never dials USSD.
            RobotService.forceSync(MainActivity.this);
            final String profileId = AppConfig.profileId(MainActivity.this);
            if (profileId == null || profileId.isEmpty() || !AppConfig.isRemoteMode(MainActivity.this, profileId)) return;
            new Thread(() -> {
                try {
                    ApiClient.forProfile(MainActivity.this, profileId).requestForceSync("REMOTE_SYNC_STALE");
                } catch (Exception ignored) {
                    // Local recovery remains active; older Worker/migration stages stay compatible.
                }
            }, "bir-remote-sync-wake").start();
        }
"""
replace_once('app/src/main/java/com/profitloop/blueauto/MainActivity.java',main_anchor,main_insert,'bridge remote wake')

# Robot: consume force_sync flag returned by the existing lease poll and perform local recovery.
robot_anchor="""                    JSONObject lease = api.leaseCommand();
                    clearProfileApiFailure(profileId);
                    if (lease.optBoolean("available", false)) {
"""
robot_insert="""                    JSONObject lease = api.leaseCommand();
                    clearProfileApiFailure(profileId);
                    if (lease.optBoolean("force_sync", false)) {
                        apiRetryAtByProfile.remove(profileId);
                        lastHeartbeatByProfile.remove(profileId);
                        OfflineSyncManager.syncSome(this, 25);
                        retryDueFinalReports(8);
                        try {
                            api.heartbeat(false);
                            lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                        } catch (Exception ignored) {}
                        updateNotification(robotSummary("Auto-Réveil distant reçu — synchronisation reprise"));
                        nextDelay = 500L;
                        continue;
                    }
                    if (lease.optBoolean("available", false)) {
"""
replace_once('app/src/main/java/com/profitloop/blueauto/RobotService.java',robot_anchor,robot_insert,'Robot wake consume')

print('BIR v2.9.1 same-node remote sync wake patch applied')
