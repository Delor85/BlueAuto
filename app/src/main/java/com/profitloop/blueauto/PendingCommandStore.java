package com.profitloop.blueauto;

import android.content.Context;

import org.json.JSONObject;

final class PendingCommandStore {
    static final String LEASED = "LEASED";
    static final String DIALING = "DIALING";
    static final String AWAITING_PIN = "AWAITING_PIN";
    static final String PIN_SUBMITTED = "PIN_SUBMITTED";
    static final String AWAITING_RESULT = "AWAITING_RESULT";
    static final String REPORT_PENDING = "REPORT_PENDING";

    private static final String KEY = "pending_command_json";

    private PendingCommandStore() {}

    static synchronized JSONObject get(Context context) {
        String raw = AppConfig.prefs(context).getString(KEY, "");
        if (raw.isEmpty()) return null;
        try {
            return new JSONObject(raw);
        } catch (Exception ignored) {
            clear(context);
            return null;
        }
    }

    static synchronized void save(Context context, JSONObject command) {
        AppConfig.prefs(context).edit().putString(KEY, command.toString()).commit();
    }

    static synchronized void updateState(Context context, String state) {
        JSONObject command = get(context);
        if (command == null) return;
        try {
            command.put("local_state", state);
            command.put("state_changed_at", System.currentTimeMillis());
            save(context, command);
        } catch (Exception ignored) {
        }
    }

    static synchronized void clear(Context context) {
        AppConfig.prefs(context).edit().remove(KEY).commit();
    }

    static boolean isExpired(JSONObject command) {
        if (command == null) return false;
        long changedAt = command.optLong("state_changed_at", command.optLong("leased_at", 0L));
        String state = command.optString("local_state", LEASED);
        return (AWAITING_PIN.equals(state) || PIN_SUBMITTED.equals(state) || AWAITING_RESULT.equals(state))
                && changedAt > 0L
                && System.currentTimeMillis() - changedAt > AppConfig.COMMAND_TIMEOUT_MS;
    }
}
