package com.profitloop.blueauto;

import android.content.Context;
import android.content.SharedPreferences;

import java.net.URI;

final class AppConfig {
    static final String PREFS = "blue_magic_native_v2";
    static final String DEFAULT_API = "https://magicservice-blue.gt.tc/api.php";
    static final long HEARTBEAT_MS = 300_000L;
    static final long IDLE_POLL_MS = 30_000L;
    static final long COMMAND_TIMEOUT_MS = 120_000L;

    private AppConfig() {}

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static String apiUrl(Context context) {
        return prefs(context).getString("api_url", DEFAULT_API);
    }

    static void setApiUrl(Context context, String value) {
        String normalized = value == null ? "" : value.trim();
        normalized = normalized.replaceAll("/+$", "");
        if (!normalized.endsWith("api.php") && !normalized.endsWith("/api")) {
            normalized += "/api";
        }
        prefs(context).edit().putString("api_url", normalized).apply();
    }

    static String webUrl(Context context) {
        return apiUrl(context).replaceFirst("/(?:api\\.php|api)(?:\\?.*)?$", "/index.html");
    }

    static String allowedHost(Context context) {
        try {
            return new URI(webUrl(context)).getHost();
        } catch (Exception ignored) {
            return "magicservice-blue.gt.tc";
        }
    }

    static String token(Context context) {
        return prefs(context).getString("device_token", "");
    }

    static String userAgent(Context context) {
        return prefs(context).getString("webview_user_agent", "");
    }

    static void setUserAgent(Context context, String value) {
        prefs(context).edit().putString("webview_user_agent", value == null ? "" : value).apply();
    }

    static String nodeCode(Context context) {
        return prefs(context).getString("node_code", "");
    }

    static String mode(Context context) {
        return prefs(context).getString("device_mode", "REMOTE");
    }

    static String role(Context context) {
        return prefs(context).getString("role", "");
    }

    static boolean isPaired(Context context) {
        return !token(context).isEmpty() && !nodeCode(context).isEmpty();
    }

    static boolean isRobotMode(Context context) {
        String value = mode(context);
        return "ROBOT".equals(value) || "HYBRID".equals(value);
    }

    static boolean robotEnabled(Context context) {
        return prefs(context).getBoolean("robot_enabled", false);
    }

    static void setRobotEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean("robot_enabled", enabled).apply();
    }

    static boolean pinBlocked(Context context) {
        return prefs(context).getBoolean("pin_blocked", false);
    }

    static void setPinBlocked(Context context, boolean blocked) {
        prefs(context).edit().putBoolean("pin_blocked", blocked).apply();
    }

    static void savePairing(Context context, String token, String nodeCode, String role, String mode) {
        prefs(context).edit()
                .putString("device_token", token)
                .putString("node_code", nodeCode)
                .putString("role", role)
                .putString("device_mode", mode)
                .apply();
    }
}
