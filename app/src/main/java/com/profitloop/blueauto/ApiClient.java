package com.profitloop.blueauto;

import android.content.Context;
import android.os.Build;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

final class ApiClient {
    private final Context context;
    private final String endpointOverride;
    private String tokenOverride;
    private final String profileIdOverride;

    ApiClient(Context context) {
        this(context, "", "", "");
    }

    ApiClient(Context context, String endpointOverride, String tokenOverride) {
        this(context, endpointOverride, tokenOverride, "");
    }

    private ApiClient(Context context, String endpointOverride, String tokenOverride,
                      String profileIdOverride) {
        this.context = context.getApplicationContext();
        this.endpointOverride = endpointOverride == null || endpointOverride.trim().isEmpty()
                ? "" : AppConfig.normalizeApiUrl(endpointOverride);
        this.tokenOverride = tokenOverride == null ? "" : tokenOverride.trim();
        this.profileIdOverride = profileIdOverride == null ? "" : profileIdOverride;
    }

    static ApiClient forProfile(Context context, String profileId) {
        return new ApiClient(context, AppConfig.apiUrl(context, profileId),
                AppConfig.token(context, profileId), profileId);
    }

    JSONObject pair(JSONObject payload) throws Exception {
        return post("pair_device", payload, false);
    }

    JSONObject health() throws Exception {
        return post("health", new JSONObject(), false);
    }

    JSONObject heartbeat() throws Exception {
        return heartbeat(false);
    }

    JSONObject heartbeat(boolean claimRobot) throws Exception {
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
    }

    JSONObject releaseCommand(JSONObject command, String reason) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("command_id", command.optString("public_id", ""));
        payload.put("lease_token", command.optString("lease_token", ""));
        payload.put("reason", reason == null ? "" : reason);
        return post("release_command", payload, true);
    }

    JSONObject updateDeviceMode(String mode) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("mode", mode);
        return post("update_device_mode", payload, true);
    }

    JSONObject activateRobot() throws Exception {
        String targetProfile = profileIdOverride.isEmpty()
                ? AppConfig.profileId(context) : profileIdOverride;
        SimIdentityManager.Verification sim = SimIdentityManager.verify(context, targetProfile);
        return activateRobot(sim, AppConfig.simSlot(context, targetProfile));
    }

    JSONObject activateRobot(SimIdentityManager.Verification sim, int simSlot) throws Exception {
        return activateRobot(sim, simSlot, false);
    }

    JSONObject activateRobot(SimIdentityManager.Verification sim, int simSlot,
                             boolean replaceVerifiedSameSimRobot) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("app_version", "2.6.8");
        payload.put("android_version", Build.VERSION.RELEASE);
        payload.put("device_model", Build.MANUFACTURER + " " + Build.MODEL);
        payload.put("sim_verified", sim.valid);
        payload.put("sim_fingerprint", sim.attestation());
        payload.put("sim_slot", Math.max(0, simSlot));
        payload.put("replace_verified_same_sim_robot", replaceVerifiedSameSimRobot);
        return post("activate_robot", payload, true);
    }

    JSONObject createCommand(JSONObject payload) throws Exception {
        return post("create_command", payload, true);
    }

    JSONObject previewCommand(JSONObject payload) throws Exception {
        return post("preview_command", payload, true);
    }

    JSONObject checkPurchaseCapacity(JSONObject payload) throws Exception {
        return post("check_purchase_capacity", payload, true);
    }

    JSONObject purchaseCapacityStatus(String checkId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("capacity_check_id", checkId);
        return post("purchase_capacity_status", payload, true);
    }

    JSONObject recordOperatorMessage(String message) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("message", message == null ? "" : trim(message, 1800));
        return post("record_operator_message", payload, true);
    }

    JSONObject platformAction(String action, JSONObject payload) throws Exception {
        String safe = action == null ? "" : action.trim();
        if (!safe.matches("(?:operator_insights|operator_catalog|platform_snapshot|network_balance_audit|shadow_enroll|debt_save|debt_list|kyc_save|mercenary_save|mercenary_list|mercenary_sale|commission_policy|commission_set_default|commission_set_child)")) {
            throw new ApiException("ACTION_NOT_ALLOWED", "Action plateforme non autorisée par le pont natif.");
        }
        return post(safe, payload == null ? new JSONObject() : payload, true);
    }

    JSONObject networkBalanceAudit() throws Exception {
        return post("network_balance_audit", new JSONObject(), true);
    }

    JSONObject dashboard() throws Exception {
        return post("network_dashboard", new JSONObject(), true);
    }

    JSONObject commandStatus(String publicId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("command_id", publicId);
        return post("command_status", payload, true);
    }

    JSONObject cancelCommand(String publicId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("command_id", publicId);
        return post("cancel_command", payload, true);
    }

    JSONObject sendEvent(JSONObject command, String state, String message, String transactionId) throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("command_id", command.optString("public_id"));
        payload.put("lease_token", command.optString("lease_token"));
        payload.put("state", state);
        if (message != null && !message.isEmpty()) payload.put("message", trim(message, 1800));
        if (transactionId != null && !transactionId.isEmpty()) payload.put("operator_transaction_id", transactionId);
        return post("command_event", payload, true);
    }

    private JSONObject post(String action, JSONObject payload, boolean authenticated) throws Exception {
        return post(action, payload, authenticated, true);
    }

    private JSONObject post(String action, JSONObject payload, boolean authenticated,
                            boolean allowAuthenticationRepair) throws Exception {
        String baseUrl = endpointOverride.isEmpty() ? AppConfig.apiUrl(context) : endpointOverride;
        String endpoint = baseUrl + "?action="
                + URLEncoder.encode(action, "UTF-8");
        HttpURLConnection connection = (HttpURLConnection) new URL(endpoint).openConnection();
        connection.setConnectTimeout(12_000);
        connection.setReadTimeout(18_000);
        connection.setRequestMethod("POST");
        connection.setRequestProperty("Accept", "application/json");
        connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        String userAgent = AppConfig.userAgent(context);
        if (userAgent.isEmpty()) {
            userAgent = "Mozilla/5.0 (Linux; Android " + Build.VERSION.RELEASE + "; "
                    + Build.MODEL + ") AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36";
        }
        connection.setRequestProperty("User-Agent", userAgent);
        connection.setRequestProperty("X-BlueMagic-Client", "android-native-v2");
        String requestToken = "";
        if (authenticated) {
            requestToken = tokenOverride.isEmpty()
                    ? (profileIdOverride.isEmpty() ? AppConfig.token(context)
                    : AppConfig.token(context, profileIdOverride))
                    : tokenOverride;
            if (requestToken.isEmpty()) throw new ApiException("NOT_PAIRED", "Appareil non appairé.");
            connection.setRequestProperty("X-Device-Token", requestToken);
        }

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
        return data == null ? new JSONObject() : data;
    }

    private void repairAuthentication(String baseUrl, String rejectedToken) throws Exception {
        synchronized (ApiClient.class) {
            repairAuthenticationLocked(baseUrl, rejectedToken);
        }
    }

    private void repairAuthenticationLocked(String baseUrl, String rejectedToken) throws Exception {
        String targetProfile = profileIdOverride.isEmpty()
                ? AppConfig.profileId(context) : profileIdOverride;
        String latestToken = AppConfig.token(context, targetProfile);
        if (!latestToken.isEmpty() && !latestToken.equals(rejectedToken)) {
            tokenOverride = latestToken;
            return;
        }

        String secret;
        try {
            secret = SecurePairingStore.read(context);
        } catch (Exception error) {
            throw new ApiException("PAIRING_REPAIR_REQUIRED",
                    "Jeton expiré. Ouvrez « Vérifier / réparer l’appairage » et confirmez le secret.");
        }
        if (secret.length() < 24) {
            throw new ApiException("PAIRING_REPAIR_REQUIRED",
                    "Jeton expiré. Ouvrez « Vérifier / réparer l’appairage » et confirmez le secret.");
        }

        JSONObject pairing = new JSONObject();
        pairing.put("node_code", AppConfig.nodeCode(context, targetProfile));
        pairing.put("phone_number", AppConfig.phoneNumber(context, targetProfile));
        pairing.put("parent_node_code", AppConfig.parentNode(context, targetProfile));
        pairing.put("role", AppConfig.role(context, targetProfile));
        pairing.put("mode", AppConfig.mode(context, targetProfile));
        pairing.put("pairing_secret", secret);
        pairing.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
        pairing.put("replace_device_id", AppConfig.serverDeviceId(context, targetProfile));
        SimIdentityManager.Verification sim = SimIdentityManager.verify(context, targetProfile);
        pairing.put("repair_sim_verified", sim.valid);
        pairing.put("repair_sim_fingerprint", sim.attestation());
        pairing.put("repair_robot_enabled", AppConfig.robotEnabled(context, targetProfile));
        pairing.put("sim_slot", Math.max(0, AppConfig.simSlot(context, targetProfile)));

        JSONObject data = new ApiClient(context, baseUrl, "")
                .post("pair_device", pairing, false, false);
        String renewedToken = data.optString("device_token", "");
        if (!AppConfig.repairPairing(context, targetProfile,
                data.optString("device_id", ""), renewedToken,
                data.optString("node_code", AppConfig.nodeCode(context, targetProfile)), baseUrl)) {
            throw new ApiException("PAIRING_REPAIR_FAILED",
                    "Le nouveau jeton n’a pas pu être enregistré sur ce compte.");
        }
        tokenOverride = renewedToken;
    }

    private static String read(InputStream stream) throws Exception {
        if (stream == null) return "";
        StringBuilder value = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) value.append(line);
        }
        return value.toString();
    }

    private static String trim(String value, int max) {
        return value.length() <= max ? value : value.substring(0, max);
    }

    static final class ApiException extends Exception {
        final String code;

        ApiException(String code, String message) {
            super(message);
            this.code = code;
        }
    }
}
