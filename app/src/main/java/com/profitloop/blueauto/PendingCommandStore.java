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

    private PendingCommandStore() {}

    static synchronized JSONObject get(Context context) {
        return get(context, AppConfig.profileId(context));
    }

    static synchronized JSONObject get(Context context, String profileId) {
        if (profileId == null) profileId = "";
        String raw = AppConfig.prefs(context).getString(AppConfig.pendingCommandKey(context, profileId), "");
        if (raw.isEmpty()) return null;
        try {
            JSONObject command = new JSONObject(raw);
            if (!profileId.isEmpty()) command.put("local_profile_id", profileId);
            return command;
        } catch (Exception ignored) {
            clear(context, profileId);
            return null;
        }
    }

    static synchronized JSONObject getActiveUssd(Context context) {
        for (String profileId : AppConfig.profileIds(context)) {
            JSONObject command = get(context, profileId);
            if (command == null) continue;
            String state = command.optString("local_state", LEASED);
            if (DIALING.equals(state) || AWAITING_PIN.equals(state)
                    || PIN_SUBMITTED.equals(state) || AWAITING_RESULT.equals(state)) return command;
        }
        return null;
    }

    static synchronized boolean hasAnyPending(Context context) {
        for (String profileId : AppConfig.profileIds(context)) {
            if (get(context, profileId) != null) return true;
        }
        return false;
    }

    static synchronized void save(Context context, JSONObject command) {
        String profileId = command.optString("local_profile_id", AppConfig.profileId(context));
        save(context, profileId, command);
    }

    static synchronized void save(Context context, String profileId, JSONObject command) {
        try {
            command.put("local_profile_id", profileId);
        } catch (Exception ignored) {
        }
        AppConfig.prefs(context).edit()
                .putString(AppConfig.pendingCommandKey(context, profileId), command.toString()).commit();
    }

    static synchronized void updateState(Context context, String state) {
        updateState(context, AppConfig.profileId(context), state);
    }

    static synchronized void updateState(Context context, String profileId, String state) {
        JSONObject command = get(context, profileId);
        if (command == null) return;
        try {
            command.put("local_state", state);
            command.put("state_changed_at", System.currentTimeMillis());
            save(context, profileId, command);
        } catch (Exception ignored) {
        }
    }

    static synchronized void clear(Context context) {
        clear(context, AppConfig.profileId(context));
    }

    static synchronized void clear(Context context, String profileId) {
        AppConfig.prefs(context).edit().remove(AppConfig.pendingCommandKey(context, profileId)).commit();
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
