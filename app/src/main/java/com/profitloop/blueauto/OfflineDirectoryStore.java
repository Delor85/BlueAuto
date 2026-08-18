package com.profitloop.blueauto;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Small native cache of the last server network directory. It lets a Robot resolve a known
 * direct child while Internet is unavailable. It never invents a node: unknown/stale entries
 * fail closed and the user must synchronize once while online.
 */
final class OfflineDirectoryStore {
    private static final String PREFIX = "offline_directory_v290_";
    private static final String AT_PREFIX = "offline_directory_at_v290_";
    private static final long MAX_AGE_MS = 30L * 24L * 60L * 60_000L;

    private OfflineDirectoryStore() {}

    static void save(Context context, String profileId, JSONObject dashboard) {
        if (profileId == null || profileId.isEmpty() || dashboard == null) return;
        JSONArray nodes = dashboard.optJSONArray("nodes");
        if (nodes == null) return;
        JSONObject compact = new JSONObject();
        try {
            for (int i = 0; i < nodes.length(); i++) {
                JSONObject node = nodes.optJSONObject(i);
                if (node == null) continue;
                String code = node.optString("node_code", "").trim().toUpperCase();
                String phone = digits(node.optString("phone_number", ""));
                if (code.isEmpty() || !phone.matches("\\d{9}")) continue;
                JSONObject item = new JSONObject();
                item.put("node_code", code);
                item.put("phone_number", phone);
                item.put("parent_node_code", node.optString("parent_node_code", "").trim().toUpperCase());
                item.put("role", node.optString("role", "").trim().toUpperCase());
                compact.put(code, item);
            }
            AppConfig.prefs(context).edit()
                    .putString(PREFIX + profileId, compact.toString())
                    .putLong(AT_PREFIX + profileId, System.currentTimeMillis()).apply();
        } catch (Exception ignored) {
        }
    }

    static JSONObject directChild(Context context, String profileId, String nodeCode) {
        String wanted = nodeCode == null ? "" : nodeCode.trim().toUpperCase();
        if (wanted.isEmpty()) return null;
        long at = AppConfig.prefs(context).getLong(AT_PREFIX + profileId, 0L);
        if (at <= 0L || System.currentTimeMillis() - at > MAX_AGE_MS) return null;
        String raw = AppConfig.prefs(context).getString(PREFIX + profileId, "");
        if (raw.isEmpty()) return null;
        try {
            JSONObject item = new JSONObject(raw).optJSONObject(wanted);
            if (item == null) return null;
            String parent = item.optString("parent_node_code", "").trim().toUpperCase();
            String me = AppConfig.nodeCode(context, profileId).trim().toUpperCase();
            if (!me.equals(parent)) return null;
            String expectedRole = "DAE".equalsIgnoreCase(AppConfig.role(context, profileId)) ? "DSM" : "POS";
            if (!expectedRole.equalsIgnoreCase(item.optString("role", ""))) return null;
            return item;
        } catch (Exception ignored) {
            return null;
        }
    }

    static long ageMs(Context context, String profileId) {
        long at = AppConfig.prefs(context).getLong(AT_PREFIX + profileId, 0L);
        return at <= 0L ? Long.MAX_VALUE : Math.max(0L, System.currentTimeMillis() - at);
    }

    private static String digits(String value) {
        return value == null ? "" : value.replaceAll("[^0-9]", "");
    }
}
