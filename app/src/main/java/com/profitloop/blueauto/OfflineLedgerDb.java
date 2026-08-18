package com.profitloop.blueauto;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Durable append-first local ledger. Financial/operator evidence is written here before any
 * attempt to tell the server. Relay transports only sanitized envelope payloads from this DB;
 * PINs, device tokens and pairing secrets never enter it.
 */
final class OfflineLedgerDb extends SQLiteOpenHelper {
    private static final String DB_NAME = "bir_offline_v290.db";
    private static final int DB_VERSION = 1;
    private static volatile OfflineLedgerDb instance;

    static OfflineLedgerDb get(Context context) {
        if (instance == null) {
            synchronized (OfflineLedgerDb.class) {
                if (instance == null) instance = new OfflineLedgerDb(context.getApplicationContext());
            }
        }
        return instance;
    }

    private OfflineLedgerDb(Context context) {
        super(context, DB_NAME, null, DB_VERSION);
        setWriteAheadLoggingEnabled(true);
    }

    @Override public void onConfigure(SQLiteDatabase db) {
        super.onConfigure(db);
        db.setForeignKeyConstraintsEnabled(true);
    }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE events ("
                + "event_id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, public_id TEXT, operation TEXT, "
                + "state TEXT NOT NULL, source TEXT NOT NULL, amount INTEGER NOT NULL DEFAULT 0, "
                + "base_amount INTEGER NOT NULL DEFAULT 0, commission_amount INTEGER NOT NULL DEFAULT 0, "
                + "commission_rate_bps INTEGER NOT NULL DEFAULT 0, target_node TEXT, target_phone TEXT, "
                + "transaction_id TEXT, operator_event_at TEXT, observed_at TEXT NOT NULL, message TEXT, "
                + "payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL, sync_state TEXT NOT NULL, "
                + "created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)");
        db.execSQL("CREATE INDEX idx_events_profile_time ON events(profile_id, created_at DESC)");
        db.execSQL("CREATE INDEX idx_events_sync ON events(sync_state, updated_at)");
        db.execSQL("CREATE INDEX idx_events_public ON events(public_id)");
        db.execSQL("CREATE TABLE relay_seen (event_id TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL, seen_at INTEGER NOT NULL)");
    }

    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        // Version 1 only. Future migrations must be additive; never drop financial history.
    }

    static boolean isLocal(JSONObject command) {
        return command != null && command.optBoolean("local_only", false);
    }

    synchronized JSONObject record(Context context, String profileId, JSONObject command,
                                   String state, String message, String transactionId,
                                   boolean needsServerSync) {
        try {
            String eventId = command.optString("event_id", "");
            if (eventId.isEmpty()) eventId = "evt_" + java.util.UUID.randomUUID().toString().replace("-", "");
            String observed = isoNow();
            JSONObject payload = new JSONObject();
            payload.put("protocol", "BIR_OFFLINE_EVENT_V1");
            payload.put("event_id", eventId);
            payload.put("origin_node_code", AppConfig.nodeCode(context, profileId));
            payload.put("origin_profile_id", profileId);
            payload.put("public_id", command.optString("public_id", ""));
            payload.put("operation", UssdCommandFactory.operation(command));
            payload.put("state", state == null ? "UNKNOWN" : state);
            payload.put("amount", command.optLong("amount", 0L));
            payload.put("requested_base_amount", command.optLong("requested_base_amount", command.optLong("amount", 0L)));
            payload.put("commission_amount", command.optLong("commission_amount", 0L));
            payload.put("commission_rate_bps", command.optInt("commission_rate_bps", 0));
            payload.put("target_node_code", command.optString("target_node_code", ""));
            payload.put("target_phone", command.optString("target_phone", ""));
            payload.put("transaction_id", transactionId == null ? "" : transactionId);
            payload.put("operator_event_at", command.optString("operator_event_at", ""));
            payload.put("observed_at", observed);
            payload.put("message", sanitize(message));
            payload.put("source", command.optString("origin", isLocal(command) ? "LOCAL_ROBOT" : "REMOTE_LEASE"));
            payload.put("relay_hops", Math.max(0, command.optInt("relay_hops", 0)));
            String payloadText = payload.toString();
            String digest = sha256(payloadText);
            payload.put("payload_sha256", digest);
            payloadText = payload.toString();

            long now = System.currentTimeMillis();
            ContentValues values = new ContentValues();
            values.put("event_id", eventId);
            values.put("profile_id", profileId);
            values.put("public_id", command.optString("public_id", ""));
            values.put("operation", UssdCommandFactory.operation(command));
            values.put("state", state == null ? "UNKNOWN" : state);
            values.put("source", command.optString("origin", isLocal(command) ? "LOCAL_ROBOT" : "REMOTE_LEASE"));
            values.put("amount", command.optLong("amount", 0L));
            values.put("base_amount", command.optLong("requested_base_amount", command.optLong("amount", 0L)));
            values.put("commission_amount", command.optLong("commission_amount", 0L));
            values.put("commission_rate_bps", command.optInt("commission_rate_bps", 0));
            values.put("target_node", command.optString("target_node_code", ""));
            values.put("target_phone", command.optString("target_phone", ""));
            values.put("transaction_id", transactionId == null ? "" : transactionId);
            values.put("operator_event_at", command.optString("operator_event_at", ""));
            values.put("observed_at", observed);
            values.put("message", sanitize(message));
            values.put("payload", payloadText);
            values.put("payload_sha256", digest);
            values.put("sync_state", needsServerSync ? "PENDING" : "LOCAL_ONLY");
            values.put("created_at", now);
            values.put("updated_at", now);
            getWritableDatabase().insertWithOnConflict("events", null, values, SQLiteDatabase.CONFLICT_REPLACE);
            pruneIfNeeded();
            return payload;
        } catch (Exception error) {
            return new JSONObject();
        }
    }

    synchronized void markSynced(String eventId) {
        if (eventId == null || eventId.isEmpty()) return;
        ContentValues values = new ContentValues();
        values.put("sync_state", "SYNCED");
        values.put("updated_at", System.currentTimeMillis());
        getWritableDatabase().update("events", values, "event_id=?", new String[]{eventId});
    }

    synchronized void markPending(String eventId) {
        if (eventId == null || eventId.isEmpty()) return;
        ContentValues values = new ContentValues();
        values.put("sync_state", "PENDING");
        values.put("updated_at", System.currentTimeMillis());
        getWritableDatabase().update("events", values, "event_id=?", new String[]{eventId});
    }

    synchronized JSONArray pendingEnvelopes(int limit) {
        JSONArray out = new JSONArray();
        int safe = Math.max(1, Math.min(200, limit));
        Cursor cursor = getReadableDatabase().query("events", new String[]{"payload"},
                "sync_state IN ('PENDING','RELAY_PENDING')", null, null, null,
                "created_at ASC", String.valueOf(safe));
        try {
            while (cursor.moveToNext()) {
                try { out.put(new JSONObject(cursor.getString(0))); } catch (Exception ignored) {}
            }
        } finally { cursor.close(); }
        return out;
    }

    synchronized JSONArray recent(String profileId, int limit) {
        JSONArray out = new JSONArray();
        Cursor cursor = getReadableDatabase().query("events", new String[]{"payload"},
                profileId == null || profileId.isEmpty() ? null : "profile_id=?",
                profileId == null || profileId.isEmpty() ? null : new String[]{profileId},
                null, null, "created_at DESC", String.valueOf(Math.max(1, Math.min(1000, limit))));
        try {
            while (cursor.moveToNext()) {
                try { out.put(new JSONObject(cursor.getString(0))); } catch (Exception ignored) {}
            }
        } finally { cursor.close(); }
        return out;
    }

    synchronized boolean importRelayEnvelope(JSONObject envelope) {
        if (envelope == null || !"BIR_OFFLINE_EVENT_V1".equals(envelope.optString("protocol", ""))) return false;
        String eventId = envelope.optString("event_id", "");
        String supplied = envelope.optString("payload_sha256", "");
        if (!eventId.matches("evt_[A-Za-z0-9_-]{16,96}") || !supplied.matches("[a-f0-9]{64}")) return false;
        try {
            JSONObject copy = new JSONObject(envelope.toString());
            copy.remove("payload_sha256");
            if (!supplied.equals(sha256(copy.toString()))) return false;
            Cursor seen = getReadableDatabase().query("relay_seen", new String[]{"event_id"},
                    "event_id=?", new String[]{eventId}, null, null, null, "1");
            try { if (seen.moveToFirst()) return false; } finally { seen.close(); }
            int hops = Math.max(0, envelope.optInt("relay_hops", 0));
            if (hops >= 3) return false;
            copy.put("relay_hops", hops + 1);
            String digest = sha256(copy.toString());
            copy.put("payload_sha256", digest);
            long now = System.currentTimeMillis();
            ContentValues values = new ContentValues();
            values.put("event_id", eventId);
            values.put("profile_id", "RELAY");
            values.put("public_id", copy.optString("public_id", ""));
            values.put("operation", copy.optString("operation", ""));
            values.put("state", copy.optString("state", "UNKNOWN"));
            values.put("source", "RELAY");
            values.put("amount", copy.optLong("amount", 0L));
            values.put("base_amount", copy.optLong("requested_base_amount", 0L));
            values.put("commission_amount", copy.optLong("commission_amount", 0L));
            values.put("commission_rate_bps", copy.optInt("commission_rate_bps", 0));
            values.put("target_node", copy.optString("target_node_code", ""));
            values.put("target_phone", copy.optString("target_phone", ""));
            values.put("transaction_id", copy.optString("transaction_id", ""));
            values.put("operator_event_at", copy.optString("operator_event_at", ""));
            values.put("observed_at", copy.optString("observed_at", isoNow()));
            values.put("message", sanitize(copy.optString("message", "")));
            values.put("payload", copy.toString());
            values.put("payload_sha256", digest);
            values.put("sync_state", "RELAY_PENDING");
            values.put("created_at", now);
            values.put("updated_at", now);
            getWritableDatabase().insertWithOnConflict("events", null, values, SQLiteDatabase.CONFLICT_IGNORE);
            ContentValues marker = new ContentValues();
            marker.put("event_id", eventId); marker.put("payload_sha256", supplied); marker.put("seen_at", now);
            getWritableDatabase().insertWithOnConflict("relay_seen", null, marker, SQLiteDatabase.CONFLICT_IGNORE);
            return true;
        } catch (Exception ignored) { return false; }
    }

    synchronized JSONObject stats() {
        JSONObject out = new JSONObject();
        Cursor c = getReadableDatabase().rawQuery(
                "SELECT COUNT(*), SUM(CASE WHEN sync_state IN ('PENDING','RELAY_PENDING') THEN 1 ELSE 0 END) FROM events", null);
        try {
            if (c.moveToFirst()) {
                out.put("events", c.getLong(0));
                out.put("pending_sync", c.isNull(1) ? 0 : c.getLong(1));
            }
        } catch (Exception ignored) {} finally { c.close(); }
        return out;
    }

    private synchronized void pruneIfNeeded() {
        Cursor c = getReadableDatabase().rawQuery("SELECT COUNT(*) FROM events", null);
        long count = 0L;
        try { if (c.moveToFirst()) count = c.getLong(0); } finally { c.close(); }
        if (count <= 50_000L) return;
        // Never prune unsynchronized events. Keep newest 40k synchronized/local-only rows.
        getWritableDatabase().execSQL("DELETE FROM events WHERE event_id IN (SELECT event_id FROM events "
                + "WHERE sync_state IN ('SYNCED','LOCAL_ONLY') ORDER BY created_at ASC LIMIT 10000)");
    }

    static String sanitize(String value) {
        String safe = value == null ? "" : value.replaceAll("(?i)(pin\\s*[:=]?\\s*)\\d{4}", "$1••••");
        return safe.length() > 600 ? safe.substring(0, 600) : safe;
    }

    static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            for (byte b : digest) out.append(String.format(Locale.ROOT, "%02x", b & 0xff));
            return out.toString();
        } catch (Exception error) { throw new IllegalStateException(error); }
    }

    static String isoNow() {
        SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);
        fmt.setTimeZone(TimeZone.getTimeZone("UTC"));
        return fmt.format(new Date());
    }
}
