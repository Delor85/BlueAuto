package com.profitloop.blueauto;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URI;
import java.util.UUID;

final class AppConfig {
    static final String PREFS = "blue_magic_native_v2";
    static final String DEFAULT_API = "https://magicservice-blue.gt.tc/api.php";
    static final long HEARTBEAT_MS = 300_000L;
    static final long IDLE_POLL_MS = 30_000L;
    static final long COMMAND_TIMEOUT_MS = 120_000L;

    private static final String PROFILES_KEY = "profiles_v3";
    private static final String ACTIVE_PROFILE_KEY = "active_profile_id_v3";

    private AppConfig() {}

    static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static synchronized void migrateLegacyProfile(Context context) {
        SharedPreferences preferences = prefs(context);
        if (preferences.contains(PROFILES_KEY)) return;

        JSONArray profiles = new JSONArray();
        String token = preferences.getString("device_token", "");
        String node = preferences.getString("node_code", "");
        if (!token.isEmpty() && !node.isEmpty()) {
            String profileId = UUID.randomUUID().toString();
            JSONObject profile = new JSONObject();
            try {
                profile.put("id", profileId);
                profile.put("api_url", normalizeApiUrl(preferences.getString("api_url", DEFAULT_API)));
                profile.put("device_token", token);
                profile.put("node_code", node);
                profile.put("phone_number", preferences.getString("phone_number", ""));
                profile.put("parent_node_code", preferences.getString("parent_node_code", ""));
                profile.put("role", preferences.getString("role", ""));
                profile.put("device_mode", preferences.getString("device_mode", "REMOTE"));
                profile.put("sim_slot", preferences.getInt("sim_slot", 0));
                profiles.put(profile);
            } catch (Exception ignored) {
            }

            SharedPreferences.Editor editor = preferences.edit()
                    .putString(ACTIVE_PROFILE_KEY, profileId);
            copyLegacyValue(preferences, editor, "operator_pin_cipher", pinCipherKey(profileId));
            copyLegacyValue(preferences, editor, "pending_command_json", pendingCommandKey(profileId));
            editor.putBoolean(robotEnabledKey(profileId), preferences.getBoolean("robot_enabled", false));
            editor.putBoolean(pinBlockedKey(profileId), preferences.getBoolean("pin_blocked", false));
            editor.apply();
        }
        preferences.edit().putString(PROFILES_KEY, profiles.toString()).apply();
    }

    private static void copyLegacyValue(SharedPreferences preferences, SharedPreferences.Editor editor,
                                        String oldKey, String newKey) {
        String value = preferences.getString(oldKey, "");
        if (!value.isEmpty()) editor.putString(newKey, value);
    }

    static String normalizeApiUrl(String value) {
        String normalized = value == null ? "" : value.trim();
        normalized = normalized.replaceAll("/+$", "");
        if (!normalized.endsWith("api.php") && !normalized.endsWith("/api")) normalized += "/api";
        return normalized;
    }

    static String apiUrl(Context context) {
        JSONObject profile = activeProfile(context);
        if (profile != null) return profile.optString("api_url", DEFAULT_API);
        return normalizeApiUrl(prefs(context).getString("pairing_api_url",
                prefs(context).getString("api_url", DEFAULT_API)));
    }

    static void setPairingApiUrl(Context context, String value) {
        prefs(context).edit().putString("pairing_api_url", normalizeApiUrl(value)).apply();
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
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("device_token", "");
    }

    static String userAgent(Context context) {
        return prefs(context).getString("webview_user_agent", "");
    }

    static void setUserAgent(Context context, String value) {
        prefs(context).edit().putString("webview_user_agent", value == null ? "" : value).apply();
    }

    static String profileId(Context context) {
        migrateLegacyProfile(context);
        return prefs(context).getString(ACTIVE_PROFILE_KEY, "");
    }

    static String nodeCode(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("node_code", "");
    }

    static String phoneNumber(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("phone_number", "");
    }

    static int simSlot(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? 0 : Math.max(0, profile.optInt("sim_slot", 0));
    }

    static String mode(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");
    }

    static String role(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("role", "");
    }

    static boolean isPaired(Context context) {
        return !token(context).isEmpty() && !nodeCode(context).isEmpty();
    }

    static boolean hasProfiles(Context context) {
        return profileCount(context) > 0;
    }

    static int profileCount(Context context) {
        return profiles(context).length();
    }

    static String[] profileIds(Context context) {
        JSONArray profiles = profiles(context);
        String[] result = new String[profiles.length()];
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            result[i] = profile == null ? "" : profile.optString("id", "");
        }
        return result;
    }

    static String[] profileLabels(Context context) {
        JSONArray profiles = profiles(context);
        String[] result = new String[profiles.length()];
        String active = profileId(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile == null) {
                result[i] = "Compte inconnu";
                continue;
            }
            String marker = active.equals(profile.optString("id", "")) ? "✓ " : "";
            result[i] = marker + profile.optString("node_code", "—")
                    + " • " + profile.optString("role", "—")
                    + " • " + displayMode(profile.optString("device_mode", "REMOTE"))
                    + " • SIM " + (profile.optInt("sim_slot", 0) + 1);
        }
        return result;
    }

    static synchronized void savePairing(Context context, String profileId, String token,
                                         String nodeCode, String phoneNumber, String parentNode,
                                         String role, String mode, String apiUrl, int simSlot) throws Exception {
        migrateLegacyProfile(context);
        JSONArray profiles = profiles(context);
        JSONObject profile = new JSONObject();
        profile.put("id", profileId == null || profileId.isEmpty() ? UUID.randomUUID().toString() : profileId);
        profile.put("api_url", normalizeApiUrl(apiUrl));
        profile.put("device_token", token);
        profile.put("node_code", nodeCode);
        profile.put("phone_number", phoneNumber);
        profile.put("parent_node_code", parentNode == null ? "" : parentNode);
        profile.put("role", role);
        profile.put("device_mode", mode);
        profile.put("sim_slot", Math.max(0, simSlot));
        profiles.put(profile);

        prefs(context).edit()
                .putString(PROFILES_KEY, profiles.toString())
                .putString(ACTIVE_PROFILE_KEY, profile.optString("id"))
                .putString("pairing_api_url", normalizeApiUrl(apiUrl))
                .apply();
    }

    static synchronized boolean activateProfile(Context context, String id) {
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && id.equals(profile.optString("id", ""))) {
                prefs(context).edit().putString(ACTIVE_PROFILE_KEY, id).commit();
                return true;
            }
        }
        return false;
    }

    static synchronized boolean updateActiveSimSlot(Context context, int slot) {
        JSONArray profiles = profiles(context);
        String active = profileId(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && active.equals(profile.optString("id", ""))) {
                try {
                    profile.put("sim_slot", Math.max(0, slot));
                    return prefs(context).edit().putString(PROFILES_KEY, profiles.toString()).commit();
                } catch (Exception ignored) {
                    return false;
                }
            }
        }
        return false;
    }

    static synchronized boolean removeActiveProfile(Context context) {
        JSONArray oldProfiles = profiles(context);
        String active = profileId(context);
        JSONArray kept = new JSONArray();
        for (int i = 0; i < oldProfiles.length(); i++) {
            JSONObject profile = oldProfiles.optJSONObject(i);
            if (profile != null && !active.equals(profile.optString("id", ""))) kept.put(profile);
        }
        if (kept.length() == oldProfiles.length()) return false;

        SharedPreferences.Editor editor = prefs(context).edit()
                .putString(PROFILES_KEY, kept.toString())
                .remove(pinCipherKey(active))
                .remove(pendingCommandKey(active))
                .remove(robotEnabledKey(active))
                .remove(pinBlockedKey(active));
        if (kept.length() == 0) editor.remove(ACTIVE_PROFILE_KEY);
        else editor.putString(ACTIVE_PROFILE_KEY, kept.optJSONObject(0).optString("id", ""));
        return editor.commit();
    }

    static boolean isRobotMode(Context context) {
        String value = mode(context);
        return "ROBOT".equals(value) || "HYBRID".equals(value);
    }

    static String displayMode(String mode) {
        return "HYBRID".equals(mode) ? "ROBOT" : mode;
    }

    static boolean robotEnabled(Context context) {
        return prefs(context).getBoolean(robotEnabledKey(profileId(context)), false);
    }

    static void setRobotEnabled(Context context, boolean enabled) {
        prefs(context).edit().putBoolean(robotEnabledKey(profileId(context)), enabled).apply();
    }

    static boolean pinBlocked(Context context) {
        return prefs(context).getBoolean(pinBlockedKey(profileId(context)), false);
    }

    static void setPinBlocked(Context context, boolean blocked) {
        prefs(context).edit().putBoolean(pinBlockedKey(profileId(context)), blocked).apply();
    }

    static String pinCipherKey(Context context) {
        return pinCipherKey(profileId(context));
    }

    static String pendingCommandKey(Context context) {
        return pendingCommandKey(profileId(context));
    }

    private static String pinCipherKey(String id) {
        return "profile_" + safeId(id) + "_operator_pin_cipher";
    }

    private static String pendingCommandKey(String id) {
        return "profile_" + safeId(id) + "_pending_command_json";
    }

    private static String robotEnabledKey(String id) {
        return "profile_" + safeId(id) + "_robot_enabled";
    }

    private static String pinBlockedKey(String id) {
        return "profile_" + safeId(id) + "_pin_blocked";
    }

    private static String safeId(String id) {
        return id == null || id.isEmpty() ? "unpaired" : id.replaceAll("[^A-Za-z0-9_-]", "_");
    }

    private static synchronized JSONArray profiles(Context context) {
        migrateLegacyProfile(context);
        try {
            return new JSONArray(prefs(context).getString(PROFILES_KEY, "[]"));
        } catch (Exception ignored) {
            return new JSONArray();
        }
    }

    private static JSONObject activeProfile(Context context) {
        JSONArray profiles = profiles(context);
        String active = prefs(context).getString(ACTIVE_PROFILE_KEY, "");
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && active.equals(profile.optString("id", ""))) return profile;
        }
        if (profiles.length() > 0) {
            JSONObject first = profiles.optJSONObject(0);
            if (first != null) {
                prefs(context).edit().putString(ACTIVE_PROFILE_KEY, first.optString("id", "")).apply();
                return first;
            }
        }
        return null;
    }
}
