package com.profitloop.blueauto;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

final class AppConfig {
    static final String PREFS = "blue_magic_native_v2";
    static final String DEFAULT_API = "https://blue-magic-api.mbolodelorpro.workers.dev/api";
    static final String CLOUDFLARE_API = DEFAULT_API;
    static final long HEARTBEAT_MS = 60_000L;
    static final long IDLE_POLL_MS = 5_000L;
    static final long COMMAND_TIMEOUT_MS = 120_000L;
    static final long LOCKED_POLL_MS = 5_000L;
    static final long NEXT_COMMAND_GAP_MS = 8_000L;

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

    static String apiUrl(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? apiUrl(context) : profile.optString("api_url", DEFAULT_API);
    }

    static void setPairingApiUrl(Context context, String value) {
        prefs(context).edit().putString("pairing_api_url", normalizeApiUrl(value)).apply();
    }

    static String pairingApiUrl(Context context) {
        if (hasProfiles(context)) return apiUrl(context);
        return normalizeApiUrl(CLOUDFLARE_API);
    }

    static String webUrl(Context context) {
        return apiUrl(context).replaceFirst("/(?:api\\.php|api)(?:\\?.*)?$", "/index.html");
    }

    static String allowedHost(Context context) {
        try {
            return new URI(webUrl(context)).getHost();
        } catch (Exception ignored) {
            return "blue-magic-api.mbolodelorpro.workers.dev";
        }
    }

    static String token(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("device_token", "");
    }

    static String token(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("device_token", "");
    }

    static String serverDeviceId(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        if (profile == null) return "";
        String explicit = profile.optString("server_device_id", "").trim();
        if (!explicit.isEmpty()) return explicit;
        String original = profile.optString("id", "").trim();
        return original.matches("[0-9a-fA-F-]{36}") ? original : "";
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

    static String nodeCode(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("node_code", "");
    }

    static String phoneNumber(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("phone_number", "");
    }

    static String phoneNumber(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("phone_number", "");
    }

    static int simSlot(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? 0 : Math.max(0, profile.optInt("sim_slot", 0));
    }

    static int simSlot(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? 0 : Math.max(0, profile.optInt("sim_slot", 0));
    }

    static String simBindingType(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("sim_binding_type", "");
    }

    static String simBindingHash(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("sim_binding_hash", "");
    }

    static String callAccountId(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("call_account_id", "");
    }

    static String callAccountComponent(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("call_account_component", "");
    }

    static String callRouteConfidence(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("call_route_confidence", "");
    }

    static String mode(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");
    }

    static String mode(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "REMOTE" : profile.optString("device_mode", "REMOTE");
    }

    static synchronized boolean updateMode(Context context, String profileId, String mode) {
        String normalized = mode == null ? "REMOTE" : mode.trim().toUpperCase(Locale.ROOT);
        if (!"REMOTE".equals(normalized) && !"ROBOT".equals(normalized)) return false;
        JSONArray all = profiles(context);
        for (int i = 0; i < all.length(); i++) {
            JSONObject profile = all.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) {
                try {
                    profile.put("device_mode", normalized);
                    if ("REMOTE".equals(normalized)) setRobotEnabled(context, profileId, false);
                    return prefs(context).edit().putString(PROFILES_KEY, all.toString()).commit();
                } catch (Exception ignored) { return false; }
            }
        }
        return false;
    }

    static String role(Context context) {
        JSONObject profile = activeProfile(context);
        return normalizedRole(profile);
    }

    static String role(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return normalizedRole(profile);
    }

    static String parentNode(Context context) {
        JSONObject profile = activeProfile(context);
        return profile == null ? "" : profile.optString("parent_node_code", "");
    }

    static String parentNode(Context context, String profileId) {
        JSONObject profile = profile(context, profileId);
        return profile == null ? "" : profile.optString("parent_node_code", "");
    }

    static boolean isPaired(Context context) {
        return !token(context).isEmpty() && !nodeCode(context).isEmpty();
    }

    static boolean isPaired(Context context, String profileId) {
        return !token(context, profileId).isEmpty() && !nodeCode(context, profileId).isEmpty();
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
            String id = profile.optString("id", "");
            String robotState = isRobotMode(context, id)
                    ? (robotEnabled(context, id) ? " • ACTIF" : " • ARRÊTÉ") : "";
            result[i] = marker + profile.optString("node_code", "—")
                    + " • " + normalizedRole(profile)
                    + " • " + displayMode(profile.optString("device_mode", "REMOTE"))
                    + " • SIM " + (profile.optInt("sim_slot", 0) + 1)
                    + robotState;
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
                    int normalized = Math.max(0, slot);
                    if (profile.optInt("sim_slot", 0) != normalized) {
                        profile.put("sim_slot", normalized);
                        profile.remove("sim_binding_type");
                        profile.remove("sim_binding_hash");
                        removeCallRoute(profile);
                        setRobotEnabled(context, active, false);
                    }
                    return prefs(context).edit().putString(PROFILES_KEY, profiles.toString()).commit();
                } catch (Exception ignored) {
                    return false;
                }
            }
        }
        return false;
    }

    static synchronized boolean updateSimBinding(Context context, String profileId,
                                                 String type, String hash) {
        if (profileId == null || profileId.isEmpty() || type == null || type.isEmpty()
                || hash == null || !hash.matches("[a-f0-9]{64}")) return false;
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) {
                try {
                    profile.put("sim_binding_type", type);
                    profile.put("sim_binding_hash", hash);
                    return prefs(context).edit()
                            .putString(PROFILES_KEY, profiles.toString()).commit();
                } catch (Exception ignored) {
                    return false;
                }
            }
        }
        return false;
    }

    static synchronized void clearSimBinding(Context context, String profileId) {
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) {
                profile.remove("sim_binding_type");
                profile.remove("sim_binding_hash");
                removeCallRoute(profile);
                prefs(context).edit().putString(PROFILES_KEY, profiles.toString()).commit();
                return;
            }
        }
    }

    static synchronized boolean updateCallRoute(Context context, String profileId,
                                                String accountId, String component,
                                                String confidence) {
        if (profileId == null || profileId.isEmpty() || accountId == null || accountId.isEmpty()
                || component == null || component.isEmpty()) return false;
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) {
                try {
                    profile.put("call_account_id", accountId);
                    profile.put("call_account_component", component);
                    profile.put("call_route_confidence", confidence == null ? "" : confidence);
                    return prefs(context).edit().putString(PROFILES_KEY, profiles.toString()).commit();
                } catch (Exception ignored) {
                    return false;
                }
            }
        }
        return false;
    }

    static synchronized void clearCallRoute(Context context, String profileId) {
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) {
                removeCallRoute(profile);
                prefs(context).edit().putString(PROFILES_KEY, profiles.toString()).commit();
                return;
            }
        }
    }

    private static void removeCallRoute(JSONObject profile) {
        profile.remove("call_account_id");
        profile.remove("call_account_component");
        profile.remove("call_route_confidence");
    }

    static synchronized boolean updateActiveMode(Context context, String mode) {
        if (!"REMOTE".equals(mode) && !"ROBOT".equals(mode)) return false;
        JSONArray profiles = profiles(context);
        String active = profileId(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && active.equals(profile.optString("id", ""))) {
                try {
                    profile.put("device_mode", mode);
                    return prefs(context).edit()
                            .putString(PROFILES_KEY, profiles.toString()).commit();
                } catch (Exception ignored) {
                    return false;
                }
            }
        }
        return false;
    }

    static synchronized boolean repairActivePairing(Context context, String serverDeviceId,
                                                     String token, String canonicalNode,
                                                     String apiUrl) {
        return repairPairing(context, profileId(context), serverDeviceId, token, canonicalNode,
                apiUrl);
    }

    static synchronized boolean repairPairing(Context context, String profileId,
                                               String serverDeviceId, String token,
                                               String canonicalNode, String apiUrl) {
        if (token == null || token.trim().isEmpty()) return false;
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) {
                try {
                    profile.put("server_device_id", serverDeviceId == null ? "" : serverDeviceId);
                    profile.put("device_token", token.trim());
                    profile.put("node_code", canonicalNode);
                    profile.put("api_url", normalizeApiUrl(apiUrl));
                    return prefs(context).edit()
                            .putString(PROFILES_KEY, profiles.toString())
                            .putString("pairing_api_url", normalizeApiUrl(apiUrl))
                            .commit();
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

    static boolean isRobotMode(Context context, String profileId) {
        String value = mode(context, profileId);
        return "ROBOT".equals(value) || "HYBRID".equals(value);
    }

    static String displayMode(String mode) {
        return "HYBRID".equals(mode) ? "ROBOT" : mode;
    }

    static boolean robotEnabled(Context context) {
        return robotEnabled(context, profileId(context));
    }

    static boolean robotEnabled(Context context, String profileId) {
        return prefs(context).getBoolean(robotEnabledKey(profileId), false);
    }

    static void setRobotEnabled(Context context, boolean enabled) {
        setRobotEnabled(context, profileId(context), enabled);
    }

    static void setRobotEnabled(Context context, String profileId, boolean enabled) {
        prefs(context).edit().putBoolean(robotEnabledKey(profileId), enabled).commit();
    }

    static boolean pinBlocked(Context context) {
        return pinBlocked(context, profileId(context));
    }

    static boolean pinBlocked(Context context, String profileId) {
        return prefs(context).getBoolean(pinBlockedKey(profileId), false);
    }

    static void setPinBlocked(Context context, boolean blocked) {
        setPinBlocked(context, profileId(context), blocked);
    }

    static void setPinBlocked(Context context, String profileId, boolean blocked) {
        prefs(context).edit().putBoolean(pinBlockedKey(profileId), blocked).apply();
    }

    static String pinCipherKey(Context context) {
        return pinCipherKey(profileId(context));
    }

    static String pinCipherKey(Context context, String profileId) {
        return pinCipherKey(profileId);
    }

    static String pendingCommandKey(Context context) {
        return pendingCommandKey(profileId(context));
    }

    static String pendingCommandKey(Context context, String profileId) {
        return pendingCommandKey(profileId);
    }

    static List<String> enabledRobotProfileIds(Context context) {
        JSONArray profiles = profiles(context);
        List<String> ids = new ArrayList<>();
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile == null) continue;
            String id = profile.optString("id", "");
            if (!id.isEmpty() && isRobotMode(context, id) && robotEnabled(context, id)) ids.add(id);
        }
        return ids;
    }

    static boolean anyRobotEnabled(Context context) {
        return !enabledRobotProfileIds(context).isEmpty();
    }

    static int enabledRobotCount(Context context) {
        return enabledRobotProfileIds(context).size();
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

    private static JSONObject profile(Context context, String profileId) {
        if (profileId == null || profileId.isEmpty()) return null;
        JSONArray profiles = profiles(context);
        for (int i = 0; i < profiles.length(); i++) {
            JSONObject profile = profiles.optJSONObject(i);
            if (profile != null && profileId.equals(profile.optString("id", ""))) return profile;
        }
        return null;
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

    /**
     * Profiles created by early Blue Magic builds did not always persist the role. Keeping an
     * empty legacy value made the ES5 interface hide every financial card while TEST_NUMBER
     * remained visible. Recover only identities that are unambiguous in the Camtel hierarchy;
     * the Worker still performs the authoritative role and parent checks for every command.
     */
    private static String normalizedRole(JSONObject profile) {
        if (profile == null) return "";
        String configured = profile.optString("role", "").trim().toUpperCase(Locale.ROOT);
        if ("DAE".equals(configured) || "DSM".equals(configured) || "POS".equals(configured)) {
            return configured;
        }

        String node = profile.optString("node_code", "").trim().toUpperCase(Locale.ROOT);
        if (node.matches("^POS(?:[-_/].*|\\d.*)$")) return "POS";
        if (node.matches("^DSM(?:[-_/].*|\\d.*)$")) return "DSM";
        if (!node.isEmpty() && profile.optString("parent_node_code", "").trim().isEmpty()) {
            return "DAE";
        }
        return "";
    }
}
