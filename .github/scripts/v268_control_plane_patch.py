from pathlib import Path


def read(path): return Path(path).read_text()
def write(path, text): Path(path).write_text(text)
def one(text, old, new, label):
    if old not in text:
        raise SystemExit('missing patch anchor: ' + label)
    return text.replace(old, new, 1)

# -----------------------------------------------------------------------------
# ApiClient: keep conservative finance/event timeouts, use shorter retry-safe
# control-plane timeouts for polling. Always disconnect even on exceptions.
# -----------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/ApiClient.java'
s=read(p)
s=one(s,
'''    JSONObject heartbeat(boolean claimRobot) throws Exception {
        String targetProfile = profileIdOverride.isEmpty()
                ? AppConfig.profileId(context) : profileIdOverride;
        SimIdentityManager.Verification sim = SimIdentityManager.verify(context, targetProfile);
        boolean locallyEnabled = AppConfig.robotEnabled(context, targetProfile);
        JSONObject payload = new JSONObject();
        payload.put("app_version", "2.6.8");
        payload.put("android_version", Build.VERSION.RELEASE);
        payload.put("device_model", Build.MANUFACTURER + " " + Build.MODEL);
        payload.put("robot_enabled", locallyEnabled && sim.valid);
        payload.put("claim_robot", claimRobot && locallyEnabled && sim.valid);
        payload.put("sim_verified", sim.valid);
        payload.put("sim_fingerprint", sim.attestation());
        payload.put("sim_slot", Math.max(0, AppConfig.simSlot(context, targetProfile)));
        return post("heartbeat", payload, true);
    }

    JSONObject leaseCommand() throws Exception {
        return post("lease_command", new JSONObject(), true);
    }''',
'''    JSONObject heartbeat(boolean claimRobot) throws Exception {
        String targetProfile = profileIdOverride.isEmpty()
                ? AppConfig.profileId(context) : profileIdOverride;
        SimIdentityManager.Verification sim = SimIdentityManager.verify(context, targetProfile);
        boolean locallyEnabled = AppConfig.robotEnabled(context, targetProfile);
        JSONObject payload = new JSONObject();
        payload.put("app_version", "2.6.8");
        payload.put("android_version", Build.VERSION.RELEASE);
        payload.put("device_model", Build.MANUFACTURER + " " + Build.MODEL);
        payload.put("robot_enabled", locallyEnabled && sim.valid);
        payload.put("claim_robot", claimRobot && locallyEnabled && sim.valid);
        payload.put("sim_verified", sim.valid);
        payload.put("sim_fingerprint", sim.attestation());
        payload.put("sim_slot", Math.max(0, AppConfig.simSlot(context, targetProfile)));
        return postControl("heartbeat", payload, true);
    }

    JSONObject leaseCommand() throws Exception {
        return postControl("lease_command", new JSONObject(), true);
    }''', 'heartbeat and lease fast control plane')

s=s.replace('''    JSONObject dashboard() throws Exception {
        return post("network_dashboard", new JSONObject(), true);
    }

    JSONObject commandStatus(String publicId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("command_id", publicId);
        return post("command_status", payload, true);
    }''',
'''    JSONObject dashboard() throws Exception {
        return postControl("network_dashboard", new JSONObject(), true);
    }

    JSONObject commandStatus(String publicId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("command_id", publicId);
        return postControl("command_status", payload, true);
    }''',1)

s=one(s,
'''    private JSONObject post(String action, JSONObject payload, boolean authenticated) throws Exception {
        return post(action, payload, authenticated, true);
    }

    private JSONObject post(String action, JSONObject payload, boolean authenticated,
                            boolean allowAuthenticationRepair) throws Exception {''',
'''    private JSONObject post(String action, JSONObject payload, boolean authenticated) throws Exception {
        return post(action, payload, authenticated, true, 12_000, 18_000);
    }

    private JSONObject postControl(String action, JSONObject payload, boolean authenticated) throws Exception {
        // Retry-safe control-plane calls never dial USSD or mutate financial stock. Shorter timeouts
        // prevent one weak profile/network route from starving the other SIM queues on this phone.
        return post(action, payload, authenticated, true, 7_000, 10_000);
    }

    private JSONObject post(String action, JSONObject payload, boolean authenticated,
                            boolean allowAuthenticationRepair) throws Exception {
        return post(action, payload, authenticated, allowAuthenticationRepair, 12_000, 18_000);
    }

    private JSONObject post(String action, JSONObject payload, boolean authenticated,
                            boolean allowAuthenticationRepair, int connectTimeoutMs,
                            int readTimeoutMs) throws Exception {''', 'post overloads')

s=s.replace('''        connection.setConnectTimeout(12_000);
        connection.setReadTimeout(18_000);
        connection.setRequestMethod("POST");''',
'''        connection.setConnectTimeout(connectTimeoutMs);
        connection.setReadTimeout(readTimeoutMs);
        connection.setUseCaches(false);
        connection.setRequestMethod("POST");''',1)

old='''        connection.setDoOutput(true);
        byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
        connection.setFixedLengthStreamingMode(body.length);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body);
        }

        int status = connection.getResponseCode();
        InputStream stream = status >= 200 && status < 400
                ? connection.getInputStream()
                : connection.getErrorStream();
        String response = read(stream);
        connection.disconnect();

        if (response.trim().isEmpty()) {
            throw new ApiException("EMPTY_RESPONSE", "Réponse vide du serveur (HTTP " + status + ").");
        }

        JSONObject root;
        try {
            root = new JSONObject(response);
        } catch (Exception parseError) {
            throw new ApiException("INVALID_RESPONSE", "Réponse non JSON du serveur (HTTP " + status + ").");
        }

        if (!root.optBoolean("ok", false)) {
            JSONObject error = root.optJSONObject("error");
            String code = error == null ? "API_ERROR" : error.optString("code", "API_ERROR");
            String message = error == null ? "Erreur API." : error.optString("message", "Erreur API.");
            if (authenticated && allowAuthenticationRepair && "AUTH_INVALID".equals(code)) {
                repairAuthentication(baseUrl, requestToken);
                return post(action, payload, true, false);
            }
            throw new ApiException(code, message);
        }
        JSONObject data = root.optJSONObject("data");
        return data == null ? new JSONObject() : data;'''
new='''        try {
            connection.setDoOutput(true);
            byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
            connection.setFixedLengthStreamingMode(body.length);
            try (OutputStream output = connection.getOutputStream()) {
                output.write(body);
            }

            int status = connection.getResponseCode();
            InputStream stream = status >= 200 && status < 400
                    ? connection.getInputStream()
                    : connection.getErrorStream();
            String response = read(stream);

            if (response.trim().isEmpty()) {
                throw new ApiException("EMPTY_RESPONSE", "Réponse vide du serveur (HTTP " + status + ").");
            }

            JSONObject root;
            try {
                root = new JSONObject(response);
            } catch (Exception parseError) {
                throw new ApiException("INVALID_RESPONSE", "Réponse non JSON du serveur (HTTP " + status + ").");
            }

            if (!root.optBoolean("ok", false)) {
                JSONObject error = root.optJSONObject("error");
                String code = error == null ? "API_ERROR" : error.optString("code", "API_ERROR");
                String message = error == null ? "Erreur API." : error.optString("message", "Erreur API.");
                if (authenticated && allowAuthenticationRepair && "AUTH_INVALID".equals(code)) {
                    repairAuthentication(baseUrl, requestToken);
                    return post(action, payload, true, false,
                            connectTimeoutMs, readTimeoutMs);
                }
                throw new ApiException(code, message);
            }
            JSONObject data = root.optJSONObject("data");
            return data == null ? new JSONObject() : data;
        } finally {
            connection.disconnect();
        }'''
s=one(s,old,new,'connection lifecycle')
write(p,s)

# -----------------------------------------------------------------------------
# RobotService: profile-local network circuit breaker. Never disables a Robot;
# simply skips a failing profile briefly so another SIM can keep moving.
# -----------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/RobotService.java'
s=read(p)
s=one(s,
'''    private final Map<String, Long> lastHeartbeatByProfile = new HashMap<>();
    private long backoffMs = AppConfig.IDLE_POLL_MS;''',
'''    private final Map<String, Long> lastHeartbeatByProfile = new HashMap<>();
    private final Map<String, Long> apiRetryAtByProfile = new HashMap<>();
    private final Map<String, Integer> apiFailureCountByProfile = new HashMap<>();
    private long backoffMs = AppConfig.IDLE_POLL_MS;''', 'profile circuit maps')

# clear circuit on explicit start/stop
s=s.replace('''                AppConfig.setRobotEnabled(this, profileId, false);
                lastHeartbeatByProfile.remove(profileId);''',
'''                AppConfig.setRobotEnabled(this, profileId, false);
                lastHeartbeatByProfile.remove(profileId);
                clearProfileApiFailure(profileId);''',1)
s=s.replace('''            AppConfig.setRobotEnabled(this, profileId, true);
            lastHeartbeatByProfile.remove(profileId);''',
'''            AppConfig.setRobotEnabled(this, profileId, true);
            lastHeartbeatByProfile.remove(profileId);
            clearProfileApiFailure(profileId);''',1)

# skip temporarily unhealthy profile before opening network
anchor='''                if (!AppConfig.isPaired(this, profileId) || !AppConfig.isRobotMode(this, profileId)) continue;
                if (PendingCommandStore.get(this, profileId) != null) continue;

                ApiClient api = ApiClient.forProfile(this, profileId);'''
replacement='''                if (!AppConfig.isPaired(this, profileId) || !AppConfig.isRobotMode(this, profileId)) continue;
                if (PendingCommandStore.get(this, profileId) != null) continue;
                long retryAt = apiRetryAtByProfile.containsKey(profileId)
                        ? apiRetryAtByProfile.get(profileId) : 0L;
                if (retryAt > System.currentTimeMillis()) {
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : réseau en reprise; autres SIM prioritaires";
                    continue;
                }

                ApiClient api = ApiClient.forProfile(this, profileId);'''
s=one(s,anchor,replacement,'skip failed profile')

# success clears breaker after lease response (regardless available)
s=s.replace('''                    JSONObject lease = api.leaseCommand();
                    if (lease.optBoolean("available", false)) {''',
'''                    JSONObject lease = api.leaseCommand();
                    clearProfileApiFailure(profileId);
                    if (lease.optBoolean("available", false)) {''',1)

# catch failures schedule local cooldown, but semantic API errors are separated:
old='''                } catch (ApiClient.ApiException apiError) {
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : " + apiError.code + " — " + safeMessage(apiError);
                } catch (Exception profileError) {
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : réseau — " + safeMessage(profileError);
                }'''
new='''                } catch (ApiClient.ApiException apiError) {
                    // API business/auth errors are explicit server answers, not transport stalls.
                    clearProfileApiFailure(profileId);
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : " + apiError.code + " — " + safeMessage(apiError);
                } catch (Exception profileError) {
                    long retryAt = markProfileApiFailure(profileId);
                    long seconds = Math.max(1L, (retryAt - System.currentTimeMillis() + 999L) / 1000L);
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : réseau lent; nouvelle tentative dans ~" + seconds
                            + " s, autres SIM non bloquées";
                }'''
s=one(s,old,new,'transport failure isolation')

# helper before safeMessage near bottom
anchor='''    private static String safeMessage(Exception error) {
        String message = error.getMessage();'''
helpers='''    private long markProfileApiFailure(String profileId) {
        int count = apiFailureCountByProfile.containsKey(profileId)
                ? apiFailureCountByProfile.get(profileId) + 1 : 1;
        count = Math.min(4, count);
        apiFailureCountByProfile.put(profileId, count);
        long delay = Math.min(30_000L, 5_000L * (1L << (count - 1)));
        long retryAt = System.currentTimeMillis() + delay;
        apiRetryAtByProfile.put(profileId, retryAt);
        return retryAt;
    }

    private void clearProfileApiFailure(String profileId) {
        if (profileId == null || profileId.isEmpty()) return;
        apiFailureCountByProfile.remove(profileId);
        apiRetryAtByProfile.remove(profileId);
    }

    private static String safeMessage(Exception error) {
        String message = error.getMessage();'''
s=one(s,anchor,helpers,'circuit helper methods')
write(p,s)

# -----------------------------------------------------------------------------
# Static contract test.
# -----------------------------------------------------------------------------
test=r'''import fs from 'node:fs';
const api=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/ApiClient.java','utf8');
const robot=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/RobotService.java','utf8');
for(const required of ['postControl("heartbeat"','postControl("lease_command"','postControl("network_dashboard"','postControl("command_status"','7_000, 10_000','connection.setUseCaches(false)','finally {','connection.disconnect()']){
  if(!api.includes(required)) throw new Error('control-plane HTTP contract missing: '+required);
}
if(!api.includes('12_000, 18_000')) throw new Error('conservative transaction timeout removed');
for(const required of ['apiRetryAtByProfile','apiFailureCountByProfile','markProfileApiFailure','clearProfileApiFailure','autres SIM non bloquées','Math.min(30_000L']){
  if(!robot.includes(required)) throw new Error('profile transport isolation missing: '+required);
}
if(!robot.includes('JSONObject lease = api.leaseCommand();\n                    clearProfileApiFailure(profileId);')) throw new Error('circuit success reset missing');
if(robot.includes('IDLE_POLL_MS = 3_000')) throw new Error('poll frequency increased instead of isolating faults');
console.log('v2.6.8 control plane: bounded polling HTTP and per-profile transport isolation OK');
'''
write('app/src/test/v268-control-plane.mjs',test)
