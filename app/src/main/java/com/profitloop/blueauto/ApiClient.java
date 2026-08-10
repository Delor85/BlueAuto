package com.profitloop.blueauto;

import android.content.Context;
import android.os.Build;
import android.webkit.CookieManager;

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
    private final String tokenOverride;
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

    JSONObject heartbeat() throws Exception {
        JSONObject payload = new JSONObject();
        payload.put("app_version", "2.4.1-regression-guard");
        payload.put("android_version", Build.VERSION.RELEASE);
        payload.put("device_model", Build.MANUFACTURER + " " + Build.MODEL);
        payload.put("robot_enabled", profileIdOverride.isEmpty()
                ? AppConfig.robotEnabled(context)
                : AppConfig.robotEnabled(context, profileIdOverride));
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

    JSONObject createCommand(JSONObject payload) throws Exception {
        return post("create_command", payload, true);
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
        if (authenticated) {
            String token = tokenOverride.isEmpty() ? AppConfig.token(context) : tokenOverride;
            if (token.isEmpty()) throw new ApiException("NOT_PAIRED", "Appareil non appairé.");
            connection.setRequestProperty("X-Device-Token", token);
        }

        try {
            String cookie = CookieManager.getInstance().getCookie(baseUrl);
            if (cookie != null && !cookie.trim().isEmpty()) {
                connection.setRequestProperty("Cookie", cookie);
            }
        } catch (Throwable ignored) {
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
            throw new ApiException(code, message);
        }
        JSONObject data = root.optJSONObject("data");
        return data == null ? new JSONObject() : data;
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
