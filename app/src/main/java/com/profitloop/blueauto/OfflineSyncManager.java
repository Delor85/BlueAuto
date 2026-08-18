package com.profitloop.blueauto;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Bounded, idempotent synchronization of the local/Relay outbox. */
final class OfflineSyncManager {
    private static final ExecutorService EXECUTOR = Executors.newSingleThreadExecutor();
    private static final AtomicBoolean RUNNING = new AtomicBoolean(false);
    private static volatile long unsupportedUntil = 0L;

    private OfflineSyncManager() {}

    static void flushAsync(Context context) {
        Context app = context.getApplicationContext();
        if (!RUNNING.compareAndSet(false, true)) return;
        EXECUTOR.execute(() -> {
            try { flush(app, 30); } finally { RUNNING.set(false); }
        });
    }

    static int flush(Context context, int limit) {
        if (!AppConfig.hasProfiles(context) || System.currentTimeMillis() < unsupportedUntil) return 0;
        registerRelayIdentity(context);
        JSONArray pending = OfflineLedgerDb.get(context).pendingEnvelopes(Math.max(1, Math.min(100, limit)));
        if (pending.length() == 0) return 0;
        String active = AppConfig.profileId(context);
        String route = AppConfig.isPaired(context, active) ? active : firstPaired(context);
        if (route.isEmpty()) return 0;
        int synced = 0;
        ApiClient api = ApiClient.forProfile(context, route);
        for (int i = 0; i < pending.length(); i++) {
            JSONObject envelope = pending.optJSONObject(i);
            if (envelope == null) continue;
            try {
                JSONObject payload = new JSONObject();
                payload.put("envelope", envelope);
                JSONObject result = api.platformAction("offline_event_sync", payload);
                if (result.optBoolean("accepted", false) || result.optBoolean("duplicate", false)) {
                    OfflineLedgerDb.get(context).markSynced(envelope.optString("event_id", ""));
                    synced++;
                }
            } catch (ApiClient.ApiException error) {
                if ("UNKNOWN_ACTION".equals(error.code)) {
                    // v2.8 production remains fully usable. Do not hammer an older Worker every cycle.
                    unsupportedUntil = System.currentTimeMillis() + 6L * 60L * 60_000L;
                    break;
                }
                break;
            } catch (Exception error) { break; }
        }
        return synced;
    }

    private static void registerRelayIdentity(Context context) {
        try {
            String publicKey = RelayIdentityStore.publicKeyBase64();
            String fingerprint = RelayIdentityStore.fingerprint();
            for (String profileId : AppConfig.profileIds(context)) {
                if (!AppConfig.isPaired(context, profileId)) continue;
                String key = "relay_registered_v290_" + profileId + "_" + fingerprint;
                if (AppConfig.prefs(context).getBoolean(key, false)) continue;
                JSONObject payload = new JSONObject();
                payload.put("public_key", publicKey);
                payload.put("fingerprint", fingerprint);
                try {
                    ApiClient.forProfile(context, profileId).platformAction("relay_register", payload);
                    AppConfig.prefs(context).edit().putBoolean(key, true).apply();
                } catch (ApiClient.ApiException error) {
                    if ("UNKNOWN_ACTION".equals(error.code)) unsupportedUntil = System.currentTimeMillis() + 6L * 60L * 60_000L;
                    return;
                }
            }
        } catch (Exception ignored) {}
    }

    private static String firstPaired(Context context) {
        for (String id : AppConfig.profileIds(context)) if (AppConfig.isPaired(context, id)) return id;
        return "";
    }
}
