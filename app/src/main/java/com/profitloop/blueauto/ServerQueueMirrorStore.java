package com.profitloop.blueauto;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Device-local mirror of server-visible queue state. It is informational/recovery state only:
 * it never contains lease secrets and it can never authorize a USSD redial.
 */
final class ServerQueueMirrorStore {
    private static final String PREFS = "bir_server_queue_mirror_v293";

    private ServerQueueMirrorStore() {}

    static void save(Context context, String profileId, JSONObject snapshot) {
        if (context == null || profileId == null || profileId.isEmpty() || snapshot == null) return;
        try {
            JSONObject clean = new JSONObject();
            clean.put("node_code", snapshot.optString("node_code", AppConfig.nodeCode(context, profileId)));
            clean.put("generated_at", snapshot.optString("generated_at", ""));
            clean.put("server_time_ms", snapshot.optLong("server_time_ms", System.currentTimeMillis()));
            clean.put("pending_count", snapshot.optInt("pending_count", 0));
            clean.put("active_count", snapshot.optInt("active_count", 0));
            clean.put("oldest_pending_age_seconds", snapshot.optLong("oldest_pending_age_seconds", 0L));
            JSONArray rows = snapshot.optJSONArray("commands");
            clean.put("commands", rows == null ? new JSONArray() : rows);
            prefs(context).edit().putString(key(profileId), clean.toString()).commit();
        } catch (Exception ignored) {
        }
    }

    static void observeBusy(Context context, String profileId, JSONObject leaseResponse) {
        if (leaseResponse == null) return;
        JSONObject active = leaseResponse.optJSONObject("active_command");
        if (active == null) return;
        try {
            JSONObject snapshot = get(context, profileId);
            if (snapshot == null) snapshot = new JSONObject();
            JSONArray rows = snapshot.optJSONArray("commands");
            if (rows == null) rows = new JSONArray();
            JSONArray merged = new JSONArray();
            String id = active.optString("public_id", "");
            merged.put(active);
            for (int i = 0; i < rows.length(); i++) {
                JSONObject row = rows.optJSONObject(i);
                if (row == null || (!id.isEmpty() && id.equals(row.optString("public_id", "")))) continue;
                merged.put(row);
            }
            snapshot.put("node_code", AppConfig.nodeCode(context, profileId));
            snapshot.put("generated_at", "LOCAL_BUSY_OBSERVATION");
            snapshot.put("server_time_ms", System.currentTimeMillis());
            snapshot.put("active_count", 1);
            snapshot.put("commands", merged);
            save(context, profileId, snapshot);
        } catch (Exception ignored) {
        }
    }

    static JSONObject get(Context context, String profileId) {
        if (context == null || profileId == null || profileId.isEmpty()) return null;
        String raw = prefs(context).getString(key(profileId), "");
        if (raw == null || raw.isEmpty()) return null;
        try {
            return new JSONObject(raw);
        } catch (Exception ignored) {
            return null;
        }
    }

    static JSONObject unified(Context context, String profileId) {
        try {
            JSONObject result = new JSONObject();
            result.put("profile_id", profileId);
            result.put("node_code", AppConfig.nodeCode(context, profileId));
            JSONObject local = PendingCommandStore.get(context, profileId);
            result.put("local_active", local == null ? JSONObject.NULL : local);
            JSONObject server = get(context, profileId);
            result.put("server", server == null ? new JSONObject() : server);
            result.put("offline_pending_events", LocalEventStore.pendingCount(context));
            result.put("accessibility_enabled", BlueAccessibilityService.isEnabled(context));
            result.put("accessibility_connected", BlueAccessibilityService.isConnected());
            result.put("generated_at_ms", System.currentTimeMillis());
            return result;
        } catch (Exception ignored) {
            return new JSONObject();
        }
    }

    static void clear(Context context, String profileId) {
        prefs(context).edit().remove(key(profileId)).apply();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static String key(String profileId) {
        return "queue_" + profileId;
    }
}
