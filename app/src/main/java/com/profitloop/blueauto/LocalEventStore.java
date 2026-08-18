package com.profitloop.blueauto;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.UUID;

final class LocalEventStore extends SQLiteOpenHelper {
    private static final String DB_NAME = "bir_offline_v290.db";
    private static final int DB_VERSION = 1;
    private static LocalEventStore instance;

    private LocalEventStore(Context context) { super(context, DB_NAME, null, DB_VERSION); }
    static synchronized LocalEventStore get(Context context) {
        if (instance == null) instance = new LocalEventStore(context.getApplicationContext());
        return instance;
    }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE events (id TEXT PRIMARY KEY, profile_id TEXT NOT NULL, command_id TEXT, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at INTEGER NOT NULL, sync_state TEXT NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0, next_retry_at INTEGER NOT NULL DEFAULT 0, relay_hops INTEGER NOT NULL DEFAULT 0)");
        db.execSQL("CREATE INDEX idx_events_sync ON events(sync_state,next_retry_at,created_at)");
        db.execSQL("CREATE INDEX idx_events_profile ON events(profile_id,created_at)");
        db.execSQL("CREATE TABLE relay_inbox (id TEXT PRIMARY KEY, envelope TEXT NOT NULL, received_at INTEGER NOT NULL, sync_state TEXT NOT NULL DEFAULT 'PENDING', attempts INTEGER NOT NULL DEFAULT 0, next_retry_at INTEGER NOT NULL DEFAULT 0)");
        db.execSQL("CREATE INDEX idx_relay_sync ON relay_inbox(sync_state,next_retry_at,received_at)");
    }
    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {}

    static String append(Context context, String profileId, String commandId, String kind, JSONObject payload) {
        String id = "evt_" + UUID.randomUUID().toString().replace("-", "");
        ContentValues v = new ContentValues();
        v.put("id", id); v.put("profile_id", profileId == null ? "" : profileId);
        v.put("command_id", commandId == null ? "" : commandId);
        v.put("kind", kind == null ? "EVENT" : kind);
        v.put("payload", payload == null ? "{}" : payload.toString());
        v.put("created_at", System.currentTimeMillis()); v.put("sync_state", "LOCAL_COMMAND_RESULT".equals(kind) ? "PENDING" : "LOCAL");
        get(context).getWritableDatabase().insertOrThrow("events", null, v);
        return id;
    }

    static JSONArray pending(Context context, String profileId, int limit) {
        JSONArray out = new JSONArray(); long now = System.currentTimeMillis();
        String where = "sync_state='PENDING' AND next_retry_at<=?";
        String[] args;
        if (profileId != null && !profileId.isEmpty()) { where += " AND profile_id=?"; args = new String[]{String.valueOf(now), profileId}; }
        else args = new String[]{String.valueOf(now)};
        try (Cursor c = get(context).getReadableDatabase().query("events", null, where, args, null, null, "created_at ASC", String.valueOf(Math.max(1, Math.min(100, limit))))) {
            while (c.moveToNext()) out.put(eventJson(c));
        } catch (Exception ignored) {}
        return out;
    }

    static int pendingCount(Context context) {
        try (Cursor c = get(context).getReadableDatabase().rawQuery("SELECT COUNT(*) FROM events WHERE sync_state='PENDING'", null)) {
            return c.moveToFirst() ? c.getInt(0) : 0;
        }
    }

    static void markSynced(Context context, String id) {
        ContentValues v=new ContentValues(); v.put("sync_state","SYNCED"); v.put("next_retry_at",0);
        get(context).getWritableDatabase().update("events",v,"id=?",new String[]{id});
        prune(context);
    }

    static void retryLater(Context context, String id, long delayMs) {
        SQLiteDatabase db=get(context).getWritableDatabase();
        db.execSQL("UPDATE events SET attempts=attempts+1,next_retry_at=? WHERE id=?",new Object[]{System.currentTimeMillis()+Math.max(5000L,delayMs),id});
    }

    static void importRelayEnvelope(Context context, JSONObject envelope) {
        if (envelope == null) return; String id=envelope.optString("event_id","");
        if (!id.matches("evt_[A-Za-z0-9]{16,80}")) return;
        ContentValues v=new ContentValues(); v.put("id",id); v.put("envelope",envelope.toString()); v.put("received_at",System.currentTimeMillis()); v.put("sync_state","PENDING");
        get(context).getWritableDatabase().insertWithOnConflict("relay_inbox",null,v,SQLiteDatabase.CONFLICT_IGNORE);
    }

    static JSONArray relayInbox(Context context, int limit) {
        JSONArray out=new JSONArray(); long now=System.currentTimeMillis();
        try(Cursor c=get(context).getReadableDatabase().query("relay_inbox",new String[]{"envelope"},"sync_state='PENDING' AND next_retry_at<=?",new String[]{String.valueOf(now)},null,null,"received_at ASC",String.valueOf(Math.max(1,Math.min(100,limit))))){
            while(c.moveToNext()){try{out.put(new JSONObject(c.getString(0)));}catch(Exception ignored){}}
        } catch(Exception ignored){}
        return out;
    }

    static void markRelaySynced(Context context,String id){ContentValues v=new ContentValues();v.put("sync_state","SYNCED");get(context).getWritableDatabase().update("relay_inbox",v,"id=?",new String[]{id});}
    static void retryRelayLater(Context context,String id,long delayMs){get(context).getWritableDatabase().execSQL("UPDATE relay_inbox SET attempts=attempts+1,next_retry_at=? WHERE id=?",new Object[]{System.currentTimeMillis()+Math.max(5000L,delayMs),id});}

    private static JSONObject eventJson(Cursor c) throws Exception {
        JSONObject o=new JSONObject();
        o.put("event_id",c.getString(c.getColumnIndexOrThrow("id")));
        o.put("profile_id",c.getString(c.getColumnIndexOrThrow("profile_id")));
        o.put("command_id",c.getString(c.getColumnIndexOrThrow("command_id")));
        o.put("kind",c.getString(c.getColumnIndexOrThrow("kind")));
        o.put("created_at",c.getLong(c.getColumnIndexOrThrow("created_at")));
        o.put("payload",new JSONObject(c.getString(c.getColumnIndexOrThrow("payload"))));
        return o;
    }

    private static void prune(Context context){
        long cutoff=System.currentTimeMillis()-90L*24L*60L*60L*1000L;
        get(context).getWritableDatabase().delete("events","sync_state='SYNCED' AND created_at<?",new String[]{String.valueOf(cutoff)});
        get(context).getWritableDatabase().delete("relay_inbox","sync_state='SYNCED' AND received_at<?",new String[]{String.valueOf(cutoff)});
    }
}
