from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def read(rel): return (ROOT / rel).read_text(encoding='utf-8')
def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
def once(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f'v290 anchor {label}: expected 1, got {text.count(old)}')
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Identity: same app/package/signing family. v2.9 is an additive candidate.
# ---------------------------------------------------------------------------
p='app/build.gradle'; s=read(p)
s=once(s,'versionCode 54\n        versionName "2.8.1"','versionCode 55\n        versionName "2.9.0"','version')
write(p,s)

p='app/src/main/java/com/profitloop/blueauto/ApiClient.java'; s=read(p)
s=s.replace('payload.put("app_version", "2.8.1");','payload.put("app_version", "2.9.0");')
s=once(s,'import org.json.JSONObject;','import org.json.JSONArray;\nimport org.json.JSONObject;','ApiClient JSONArray import')
s=once(s,
'''    JSONObject recordOperatorMessage(String message) throws Exception {\n        JSONObject payload = new JSONObject();\n        payload.put("message", message == null ? "" : trim(message, 1800));\n        return post("record_operator_message", payload, true);\n    }''',
'''    JSONObject recordOperatorMessage(String message) throws Exception {\n        JSONObject payload = new JSONObject();\n        payload.put("message", message == null ? "" : trim(message, 1800));\n        return post("record_operator_message", payload, true);\n    }\n\n    JSONObject syncLocalEvents(JSONArray events) throws Exception {\n        JSONObject payload = new JSONObject();\n        payload.put("events", events == null ? new JSONArray() : events);\n        return postControl("sync_local_events", payload, true);\n    }\n\n    JSONObject relaySync(JSONObject envelope) throws Exception {\n        return postControl("relay_sync", envelope == null ? new JSONObject() : envelope, true);\n    }''','ApiClient offline sync methods')
write(p,s)

# ---------------------------------------------------------------------------
# Durable local append-only event/outbox store.
# ---------------------------------------------------------------------------
write('app/src/main/java/com/profitloop/blueauto/LocalEventStore.java', r'''package com.profitloop.blueauto;

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
        v.put("created_at", System.currentTimeMillis()); v.put("sync_state", "PENDING");
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
''')

# ---------------------------------------------------------------------------
# Cached node directory. Enables superior->child local USSD after one sync.
# ---------------------------------------------------------------------------
write('app/src/main/java/com/profitloop/blueauto/OfflineDirectoryStore.java', r'''package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

final class OfflineDirectoryStore {
    private static final String PREFIX="offline_directory_v290_";
    private OfflineDirectoryStore(){}
    private static String key(String profileId){return PREFIX+(profileId==null?"":profileId);}
    static synchronized JSONObject all(Context c,String profileId){try{return new JSONObject(AppConfig.prefs(c).getString(key(profileId),"{}"));}catch(Exception e){return new JSONObject();}}
    static synchronized void put(Context c,String profileId,String node,String phone,String role,String parent){
        node=node==null?"":node.trim().toUpperCase(); phone=phone==null?"":phone.replaceAll("\\D","");
        if(node.isEmpty()||!phone.matches("\\d{9}"))return;
        try{JSONObject root=all(c,profileId),v=new JSONObject();v.put("node_code",node);v.put("phone_number",phone);v.put("role",role==null?"":role);v.put("parent_node_code",parent==null?"":parent);v.put("cached_at",System.currentTimeMillis());root.put(node,v);AppConfig.prefs(c).edit().putString(key(profileId),root.toString()).apply();}catch(Exception ignored){}
    }
    static JSONObject find(Context c,String profileId,String node){return all(c,profileId).optJSONObject(node==null?"":node.trim().toUpperCase());}
    static void ingestDashboard(Context c,String profileId,JSONObject dashboard){
        JSONArray nodes=dashboard==null?null:dashboard.optJSONArray("nodes"); if(nodes==null)return;
        for(int i=0;i<nodes.length();i++){JSONObject n=nodes.optJSONObject(i);if(n==null)continue;put(c,profileId,n.optString("node_code"),n.optString("phone_number"),n.optString("role"),n.optString("parent_node_code"));}
    }
    static void ingestPreview(Context c,String profileId,JSONObject response){
        JSONObject p=response==null?null:response.optJSONObject("preview"); if(p==null)return;
        put(c,profileId,p.optString("target_node_code"),p.optString("target_phone"),p.optString("target_role"),p.optString("target_parent_node_code"));
    }
}
''')

# ---------------------------------------------------------------------------
# Local Robot command preparation. REQUEST_SUPPLY remains network-dependent.
# ---------------------------------------------------------------------------
write('app/src/main/java/com/profitloop/blueauto/OfflineRobotEngine.java', r'''package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONObject;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;
import java.util.UUID;

final class OfflineRobotEngine {
    private OfflineRobotEngine(){}
    static boolean supports(String requestType,String role){
        String t=norm(requestType),r=norm(role);
        if("REQUEST_SUPPLY".equals(t))return false;
        if("SUPPLY_CHILD".equals(t)||"CHILD_BALANCE".equals(t)||"INIT_CHILD_PIN_RESET".equals(t)||"SUSPEND_CHILD".equals(t)||"REACTIVATE_CHILD".equals(t)||"FREEZE_CHILD".equals(t)||"REACTIVATE_FROZEN_CHILD".equals(t))return "DAE".equals(r)||"DSM".equals(r);
        if("RETAIL_SALE".equals(t))return "POS".equals(r);
        return "TEST_NUMBER".equals(t)||"CHECK_BALANCE".equals(t)||"LAST_TRANSACTIONS".equals(t)||"TRANSACTION_DETAIL".equals(t)||"RESET_PIN_SELF".equals(t)||"MODIFY_PIN_LOCAL".equals(t)||"FREEZE_SELF".equals(t);
    }
    static boolean canRunHere(Context c,String requestType){String p=AppConfig.profileId(c);return AppConfig.isRobotMode(c,p)&&AppConfig.robotEnabled(c,p)&&supports(requestType,AppConfig.role(c,p));}

    static JSONObject preview(Context c,String requestType,String targetNode,String targetPhone,String amount,String argument,int rateBps) throws Exception {
        String profile=AppConfig.profileId(c), type=norm(requestType), role=AppConfig.role(c,profile), node=up(targetNode), phone=digits(targetPhone), amt=digits(amount);
        if(!canRunHere(c,type))throw new IllegalStateException("Cette commande nécessite un Robot local actif ou une connexion Remote.");
        if(needsChild(type)){
            JSONObject cached=OfflineDirectoryStore.find(c,profile,node);
            if(cached==null)throw new IllegalStateException("Annuaire enfant absent hors connexion. Synchronisez ce réseau une fois en ligne puis réessayez.");
            phone=digits(cached.optString("phone_number"));
        }
        String op=operation(type); validate(role,type,node,phone,amt,argument);
        int base=amt.isEmpty()?0:Integer.parseInt(amt),bps=Math.max(0,Math.min(5000,rateBps));
        int commission="SUPPLY_CHILD".equals(type)?(int)Math.floor(base*bps/10000.0):0,total=base+commission;
        JSONObject p=new JSONObject(); p.put("request_type",type);p.put("operation",op);p.put("target_node_code",node);p.put("target_phone",phone);p.put("amount",String.valueOf(total));p.put("requested_base_amount",base);p.put("base_amount",base);p.put("commission_rate_bps",bps);p.put("commission_amount",commission);p.put("total_amount",total);p.put("executor_node_code",AppConfig.nodeCode(c,profile));p.put("executor_phone",AppConfig.phoneNumber(c,profile));p.put("execution_path","LOCAL_ROBOT");p.put("offline_capable",true);p.put("command_argument",argument==null?"":argument.trim());
        String fingerprint=sha256(type+"|"+node+"|"+phone+"|"+base+"|"+bps+"|"+total+"|"+AppConfig.nodeCode(c,profile));p.put("confirmation_fingerprint",fingerprint);
        JSONObject result=new JSONObject();result.put("preview",p);return result;
    }

    static JSONObject queue(Context c,String requestType,String targetNode,String targetPhone,String amount,String argument,int rateBps,String fingerprint) throws Exception {
        JSONObject result=preview(c,requestType,targetNode,targetPhone,amount,argument,rateBps),p=result.getJSONObject("preview");
        if(fingerprint==null||!fingerprint.equalsIgnoreCase(p.optString("confirmation_fingerprint")))throw new SecurityException("La confirmation locale ne correspond plus aux données affichées.");
        String profile=AppConfig.profileId(c); if(PendingCommandStore.get(c,profile)!=null)throw new IllegalStateException("Une commande est déjà en cours sur cette SIM.");
        String id="local_"+UUID.randomUUID().toString().replace("-","");
        JSONObject cmd=new JSONObject();cmd.put("public_id",id);cmd.put("lease_token",randomHex());cmd.put("local_origin",true);cmd.put("request_type",p.optString("request_type"));cmd.put("operation",p.optString("operation"));cmd.put("command_kind",p.optString("operation"));cmd.put("command_argument",p.optString("command_argument"));cmd.put("requester_node_code",AppConfig.nodeCode(c,profile));cmd.put("executor_node_code",AppConfig.nodeCode(c,profile));cmd.put("executor_phone",AppConfig.phoneNumber(c,profile));cmd.put("target_node_code",p.optString("target_node_code"));cmd.put("target_phone",p.optString("target_phone"));cmd.put("amount",String.valueOf(p.optInt("total_amount",0)));cmd.put("requested_base_amount",p.optInt("base_amount",0));cmd.put("commission_rate_bps",p.optInt("commission_rate_bps",0));cmd.put("commission_amount",p.optInt("commission_amount",0));cmd.put("total_amount",p.optInt("total_amount",0));cmd.put("requires_pin",requiresPin(p.optString("operation")));cmd.put("local_profile_id",profile);cmd.put("local_state",PendingCommandStore.LEASED);cmd.put("state","PENDING");cmd.put("created_at",isoNow());cmd.put("state_changed_at",System.currentTimeMillis());
        PendingCommandStore.save(c,profile,cmd);
        JSONObject event=new JSONObject(cmd.toString());event.remove("lease_token");LocalEventStore.append(c,profile,id,"LOCAL_COMMAND_QUEUED",event);
        RobotService.startEnabled(c);
        JSONObject out=new JSONObject();JSONObject ui=new JSONObject(cmd.toString());ui.put("robot_ready",true);ui.put("robot_status","LOCAL_ROBOT");ui.put("robot_message","Commande prise en charge directement par ce Robot, sans dépendre du serveur pour l’exécution.");out.put("command",ui);out.put("local",true);return out;
    }

    static JSONObject queueMaintenance(Context c,String requestType)throws Exception{return queue(c,requestType,"","","0","",0,preview(c,requestType,"","","0","",0).getJSONObject("preview").getString("confirmation_fingerprint"));}
    private static boolean needsChild(String t){return "SUPPLY_CHILD".equals(t)||"CHILD_BALANCE".equals(t)||"INIT_CHILD_PIN_RESET".equals(t)||"SUSPEND_CHILD".equals(t)||"REACTIVATE_CHILD".equals(t)||"FREEZE_CHILD".equals(t)||"REACTIVATE_FROZEN_CHILD".equals(t);}
    private static String operation(String t){if("CHECK_BALANCE".equals(t))return "BALANCE_OWN";if("LAST_TRANSACTIONS".equals(t))return "HISTORY_LAST5";if("TRANSACTION_DETAIL".equals(t))return "TRANSACTION_DETAIL";if("SUPPLY_CHILD".equals(t))return "DISTRIBUTION_TRANSFER";if("RETAIL_SALE".equals(t))return "RETAIL_TRANSFER";if("CHILD_BALANCE".equals(t))return "BALANCE_CHILD";return t;}
    private static boolean requiresPin(String op){return "DISTRIBUTION_TRANSFER".equals(op)||"RETAIL_TRANSFER".equals(op);}
    private static void validate(String role,String type,String node,String phone,String amount,String argument){if(("SUPPLY_CHILD".equals(type)||"RETAIL_SALE".equals(type))&&!amount.matches("[1-9]\\d{0,8}"))throw new IllegalArgumentException("Montant invalide.");if((needsChild(type)||"RETAIL_SALE".equals(type))&&!phone.matches("\\d{9}"))throw new IllegalArgumentException("Numéro cible hors-ligne indisponible ou invalide.");if(needsChild(type)&&node.isEmpty())throw new IllegalArgumentException("Nœud enfant requis.");if("TRANSACTION_DETAIL".equals(type)&&(argument==null||!argument.matches("[A-Za-z0-9_-]{6,64}")))throw new IllegalArgumentException("Identifiant transaction invalide.");}
    private static String norm(String v){return v==null?"":v.trim().toUpperCase(Locale.ROOT);}private static String up(String v){return norm(v);}private static String digits(String v){if(v==null)return"";int dot=v.indexOf('.');if(dot>=0)v=v.substring(0,dot);return v.replaceAll("[^0-9]","");}
    private static String randomHex(){return UUID.randomUUID().toString().replace("-","")+UUID.randomUUID().toString().replace("-","");}
    private static String isoNow(){return new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX",Locale.ROOT).format(new java.util.Date());}
    private static String sha256(String v)throws Exception{byte[] d=MessageDigest.getInstance("SHA-256").digest(v.getBytes(StandardCharsets.UTF_8));StringBuilder b=new StringBuilder();for(byte x:d)b.append(String.format(Locale.ROOT,"%02x",x&255));return b.toString();}
}
''')

# ---------------------------------------------------------------------------
# Outbox sync + cryptographic relay envelopes. The live v2.8 Worker may reject
# sync_local_events/relay_sync until a separately authorized server gate.
# ---------------------------------------------------------------------------
write('app/src/main/java/com/profitloop/blueauto/OfflineSyncManager.java', r'''package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

final class OfflineSyncManager {
    private OfflineSyncManager(){}
    static void syncSome(Context c,int limit){for(String profile:AppConfig.profileIds(c))syncProfile(c,profile,limit);syncRelayed(c,limit);}
    static void syncProfile(Context c,String profile,int limit){
        JSONArray items=LocalEventStore.pending(c,profile,Math.max(1,limit));if(items.length()==0)return;
        try{JSONObject response=ApiClient.forProfile(c,profile).syncLocalEvents(items);JSONArray accepted=response.optJSONArray("accepted_event_ids");if(accepted!=null){for(int i=0;i<accepted.length();i++)LocalEventStore.markSynced(c,accepted.optString(i));return;}}
        catch(Exception ignored){}
        // Compatibility bridge for current production: passive Blue result can still update the
        // source node balance/insights. Keep the richer event pending for the future sync endpoint.
        for(int i=0;i<items.length();i++){JSONObject e=items.optJSONObject(i);if(e==null)continue;JSONObject p=e.optJSONObject("payload");String raw=p==null?"":p.optString("result_message","");if(raw.length()<4)continue;try{ApiClient.forProfile(c,profile).recordOperatorMessage(raw);}catch(Exception ignored){break;}LocalEventStore.retryLater(c,e.optString("event_id"),60_000L);}
    }
    static JSONArray relayBundle(Context c,int limit){JSONArray src=LocalEventStore.pending(c,"",limit),out=new JSONArray();for(int i=0;i<src.length();i++){JSONObject e=src.optJSONObject(i);if(e==null)continue;String profile=e.optString("profile_id","");if(!AppConfig.isPaired(c,profile))continue;try{JSONObject x=new JSONObject(e.toString());x.put("source_device_id",AppConfig.serverDeviceId(c,profile));x.put("source_node_code",AppConfig.nodeCode(c,profile));x.put("signature",sign(c,profile,x));out.put(x);}catch(Exception ignored){}}return out;}
    static void acceptRelayBundle(Context c,JSONArray bundle){if(bundle==null)return;for(int i=0;i<bundle.length();i++){JSONObject e=bundle.optJSONObject(i);if(e!=null)LocalEventStore.importRelayEnvelope(c,e);}}
    static void syncRelayed(Context c,int limit){JSONArray in=LocalEventStore.relayInbox(c,limit);if(in.length()==0||!AppConfig.isPaired(c))return;ApiClient courier=new ApiClient(c);for(int i=0;i<in.length();i++){JSONObject e=in.optJSONObject(i);if(e==null)continue;String id=e.optString("event_id","");try{courier.relaySync(e);LocalEventStore.markRelaySynced(c,id);}catch(Exception error){LocalEventStore.retryRelayLater(c,id,60_000L);break;}}}
    private static String sign(Context c,String profile,JSONObject event)throws Exception{String token=AppConfig.token(c,profile);byte[] digest=MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.UTF_8));StringBuilder kh=new StringBuilder();for(byte b:digest)kh.append(String.format(Locale.ROOT,"%02x",b&255));String canonical=event.optString("event_id")+"|"+event.optString("source_device_id")+"|"+event.optString("source_node_code")+"|"+event.optLong("created_at")+"|"+event.optString("kind")+"|"+event.optJSONObject("payload");Mac mac=Mac.getInstance("HmacSHA256");mac.init(new SecretKeySpec(kh.toString().getBytes(StandardCharsets.UTF_8),"HmacSHA256"));byte[] out=mac.doFinal(canonical.getBytes(StandardCharsets.UTF_8));StringBuilder h=new StringBuilder();for(byte b:out)h.append(String.format(Locale.ROOT,"%02x",b&255));return h.toString();}
}
''')

# ---------------------------------------------------------------------------
# B.I.R. Relay: nearby Wi-Fi Direct exchange only, short user-triggered window.
# No SMS path. Bluetooth permissions are reserved for a future same Relay layer,
# but this candidate does not create an SMS or financial-command transport.
# ---------------------------------------------------------------------------
write('app/src/main/java/com/profitloop/blueauto/BirRelayManager.java', r'''package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pInfo;
import android.net.wifi.p2p.WifiP2pManager;
import android.net.wifi.p2p.nsd.WifiP2pDnsSdServiceInfo;
import android.net.wifi.p2p.nsd.WifiP2pDnsSdServiceRequest;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicBoolean;

final class BirRelayManager {
    private static final String SERVICE="_birrelay._tcp"; private static final int PORT=49831;
    private static final long WINDOW_MS=30_000L; private static BirRelayManager live;
    private final Activity activity; private final WifiP2pManager manager; private final WifiP2pManager.Channel channel;
    private final AtomicBoolean transferred=new AtomicBoolean(false); private BroadcastReceiver receiver; private long startedAt;
    private BirRelayManager(Activity a){activity=a;manager=(WifiP2pManager)a.getSystemService(Context.WIFI_P2P_SERVICE);channel=manager==null?null:manager.initialize(a,a.getMainLooper(),null);}
    static synchronized String start(Activity a){if(LocalEventStore.pendingCount(a)<=0)return "Aucun événement en attente à relayer.";if(!permissionsReady(a))return "Autorisations Appareils à proximité / localisation requises pour B.I.R. Relay.";if(live!=null)live.stop();live=new BirRelayManager(a);return live.begin()?"B.I.R. Relay recherche un appareil B.I.R. proche pendant 30 secondes.":"Wi‑Fi Direct indisponible sur ce téléphone.";}
    static boolean permissionsReady(Activity a){if(Build.VERSION.SDK_INT>=33&&a.checkSelfPermission("android.permission.NEARBY_WIFI_DEVICES")!=PackageManager.PERMISSION_GRANTED)return false;return Build.VERSION.SDK_INT>=33||a.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED;}
    static String[] permissions(){return Build.VERSION.SDK_INT>=33?new String[]{"android.permission.NEARBY_WIFI_DEVICES"}:new String[]{Manifest.permission.ACCESS_FINE_LOCATION};}
    private boolean begin(){if(manager==null||channel==null)return false;startedAt=System.currentTimeMillis();register();Map<String,String> record=new HashMap<>();record.put("v","1");record.put("app","BIR");WifiP2pDnsSdServiceInfo info=WifiP2pDnsSdServiceInfo.newInstance("BIR-RELAY",SERVICE,record);manager.addLocalService(channel,info,new WifiP2pManager.ActionListener(){public void onSuccess(){discover();}public void onFailure(int r){stop();}});activity.getWindow().getDecorView().postDelayed(this::stop,WINDOW_MS);return true;}
    private void register(){IntentFilter f=new IntentFilter();f.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);receiver=new BroadcastReceiver(){public void onReceive(Context c,Intent i){if(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION.equals(i.getAction()))manager.requestConnectionInfo(channel,BirRelayManager.this::onInfo);}};activity.registerReceiver(receiver,f);}
    private void discover(){manager.setDnsSdResponseListeners(channel,(instance,registrationType,device)->{if("BIR-RELAY".equals(instance)&&!transferred.get())connect(device);},(full,txt,device)->{});WifiP2pDnsSdServiceRequest req=WifiP2pDnsSdServiceRequest.newInstance();manager.addServiceRequest(channel,req,new WifiP2pManager.ActionListener(){public void onSuccess(){manager.discoverServices(channel,new WifiP2pManager.ActionListener(){public void onSuccess(){}public void onFailure(int r){}});}public void onFailure(int r){}});}
    private void connect(WifiP2pDevice d){WifiP2pConfig c=new WifiP2pConfig();c.deviceAddress=d.deviceAddress;manager.connect(channel,c,new WifiP2pManager.ActionListener(){public void onSuccess(){}public void onFailure(int r){}});}
    private void onInfo(WifiP2pInfo info){if(info==null||!info.groupFormed||transferred.get())return;new Thread(()->{try{if(info.isGroupOwner)serve();else client(info.groupOwnerAddress.getHostAddress());transferred.set(true);OfflineSyncManager.syncRelayed(activity,50);}catch(Exception ignored){}finally{activity.runOnUiThread(()->android.widget.Toast.makeText(activity,transferred.get()?"B.I.R. Relay : échange terminé.":"B.I.R. Relay : aucun échange confirmé.",android.widget.Toast.LENGTH_LONG).show());stop();}},"BIR-Relay-v290").start();}
    private void serve()throws Exception{try(ServerSocket ss=new ServerSocket(PORT)){ss.setSoTimeout(12000);try(Socket s=ss.accept()){exchange(s);}}}
    private void client(String host)throws Exception{try(Socket s=new Socket()){s.connect(new InetSocketAddress(host,PORT),8000);exchange(s);}}
    private void exchange(Socket socket)throws Exception{socket.setSoTimeout(10000);BufferedWriter w=new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(),"UTF-8"));BufferedReader r=new BufferedReader(new InputStreamReader(socket.getInputStream(),"UTF-8"));JSONObject mine=new JSONObject();mine.put("protocol","BIR_RELAY_1");mine.put("events",OfflineSyncManager.relayBundle(activity,50));w.write(mine.toString());w.write("\n");w.flush();String line=r.readLine();if(line!=null){JSONObject peer=new JSONObject(line);if("BIR_RELAY_1".equals(peer.optString("protocol")))OfflineSyncManager.acceptRelayBundle(activity,peer.optJSONArray("events"));}}
    private synchronized void stop(){if(receiver!=null){try{activity.unregisterReceiver(receiver);}catch(Exception ignored){}receiver=null;}if(manager!=null&&channel!=null){try{manager.clearLocalServices(channel,null);manager.clearServiceRequests(channel,null);manager.removeGroup(channel,null);}catch(Exception ignored){}}if(live==this)live=null;}
}
''')

# ---------------------------------------------------------------------------
# Manifest: nearby transport permissions only. No SMS sending permission added.
# ---------------------------------------------------------------------------
p='app/src/main/AndroidManifest.xml'; s=read(p)
s=once(s,'    <uses-permission android:name="android.permission.INTERNET" />', '''    <uses-permission android:name="android.permission.INTERNET" />\n    <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />\n    <uses-permission android:name="android.permission.CHANGE_WIFI_STATE" />\n    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" android:maxSdkVersion="32" />\n    <uses-permission android:name="android.permission.NEARBY_WIFI_DEVICES" android:usesPermissionFlags="neverForLocation" />\n    <uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />\n    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" android:maxSdkVersion="30" />\n    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />\n    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />''','relay permissions')
if 'SEND_SMS' in s: raise SystemExit('v290 must not add SMS sending')
write(p,s)

# ---------------------------------------------------------------------------
# UssdCommandFactory: preserve strict server validation but accept locally built
# envelopes identified by local_origin=true.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/UssdCommandFactory.java'; s=read(p)
s=once(s,
'''        String commandId = string(command, "public_id");\n        String leaseToken = string(command, "lease_token");\n        if (!commandId.matches("[A-Za-z0-9_-]{16,80}")) {\n            throw new SecurityException("Identifiant de commande serveur invalide.");\n        }\n        if (!leaseToken.matches("[a-fA-F0-9]{32,128}")) {\n            throw new SecurityException("Jeton de réservation serveur invalide.");\n        }''',
'''        String commandId = string(command, "public_id");\n        String leaseToken = string(command, "lease_token");\n        boolean localOrigin = command.optBoolean("local_origin", false);\n        if (localOrigin) {\n            if (!commandId.matches("local_[A-Za-z0-9]{16,80}"))\n                throw new SecurityException("Identifiant de commande locale invalide.");\n            if (!leaseToken.matches("[a-fA-F0-9]{32,128}"))\n                throw new SecurityException("Jeton anti-doublon local invalide.");\n        } else {\n            if (!commandId.matches("[A-Za-z0-9_-]{16,80}"))\n                throw new SecurityException("Identifiant de commande serveur invalide.");\n            if (!leaseToken.matches("[a-fA-F0-9]{32,128}"))\n                throw new SecurityException("Jeton de réservation serveur invalide.");\n        }''','local envelope validation')
write(p,s)

# ---------------------------------------------------------------------------
# MainActivity: local preview/queue interception, local maintenance, Relay UI
# bridge and cached directory ingestion. REQUEST_SUPPLY stays online.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/MainActivity.java'; s=read(p)
# Local maintenance should never need server just to execute on its own SIM.
s=once(s,
'''                JSONObject payload = new JSONObject();\n                payload.put("request_type", requestType);\n                payload.put("client_request_id", "local_" + UUID.randomUUID().toString().replace("-", ""));\n                new ApiClient(this).createCommand(payload);\n                RobotService.startEnabled(this);''',
'''                OfflineRobotEngine.queueMaintenance(this, requestType);\n                RobotService.startEnabled(this);''','local maintenance')
# Cache all dashboard snapshots returned through the native bridge.
s=s.replace('callback("onDashboard", data);','OfflineDirectoryStore.ingestDashboard(MainActivity.this, AppConfig.profileId(MainActivity.this), data);\n                    callback("onDashboard", data);')
# Intercept preview (no commission overload).
old='''                    JSONObject data = new ApiClient(MainActivity.this).previewCommand(payload);\n                    callback("onCommandPreview", data);'''
new='''                    JSONObject data;\n                    if (OfflineRobotEngine.canRunHere(MainActivity.this, requestType)) {\n                        data = OfflineRobotEngine.preview(MainActivity.this, requestType, targetNode, targetPhone,\n                                amount, commandArgument, 0);\n                    } else {\n                        data = new ApiClient(MainActivity.this).previewCommand(payload);\n                        OfflineDirectoryStore.ingestPreview(MainActivity.this, AppConfig.profileId(MainActivity.this), data);\n                    }\n                    callback("onCommandPreview", data);'''
s=once(s,old,new,'preview local intercept')
# Commission preview overload.
old='''                    payload.put("commission_rate_bps", commissionRateBps);\n                    callback("onCommandPreview", new ApiClient(MainActivity.this).previewCommand(payload));'''
new='''                    payload.put("commission_rate_bps", commissionRateBps);\n                    JSONObject data;\n                    if (OfflineRobotEngine.canRunHere(MainActivity.this, requestType)) {\n                        data = OfflineRobotEngine.preview(MainActivity.this, requestType, targetNode, targetPhone,\n                                amount, commandArgument, commissionRateBps);\n                    } else {\n                        data = new ApiClient(MainActivity.this).previewCommand(payload);\n                        OfflineDirectoryStore.ingestPreview(MainActivity.this, AppConfig.profileId(MainActivity.this), data);\n                    }\n                    callback("onCommandPreview", data);'''
s=once(s,old,new,'commission preview local intercept')
# Create normal command local intercept.
old='''                    JSONObject data = new ApiClient(MainActivity.this).createCommand(payload);\n                    callback("onCommandCreated", data);'''
new='''                    JSONObject data;\n                    if (OfflineRobotEngine.canRunHere(MainActivity.this, requestType)) {\n                        data = OfflineRobotEngine.queue(MainActivity.this, requestType, targetNode, targetPhone, amount,\n                                commandArgument, 0, confirmationFingerprint);\n                    } else {\n                        data = new ApiClient(MainActivity.this).createCommand(payload);\n                    }\n                    callback("onCommandCreated", data);'''
s=once(s,old,new,'create local intercept')
# Create commission command local intercept.
old='''                    payload.put("commission_rate_bps", commissionRateBps);\n                    callback("onCommandCreated", new ApiClient(MainActivity.this).createCommand(payload));'''
new='''                    payload.put("commission_rate_bps", commissionRateBps);\n                    JSONObject data;\n                    if (OfflineRobotEngine.canRunHere(MainActivity.this, requestType)) {\n                        data = OfflineRobotEngine.queue(MainActivity.this, requestType, targetNode, targetPhone, amount,\n                                commandArgument, commissionRateBps, confirmationFingerprint);\n                    } else {\n                        data = new ApiClient(MainActivity.this).createCommand(payload);\n                    }\n                    callback("onCommandCreated", data);'''
s=once(s,old,new,'commission create local intercept')
# Expose outbox + Relay to web UI.
s=once(s,
'''        @JavascriptInterface\n        public void checkServerHealth() {''',
'''        @JavascriptInterface\n        public String getOfflineStatus() {\n            try {\n                JSONObject data = new JSONObject();\n                data.put("pending_events", LocalEventStore.pendingCount(MainActivity.this));\n                data.put("relay_permissions", BirRelayManager.permissionsReady(MainActivity.this));\n                data.put("mode", AppConfig.displayMode(AppConfig.mode(MainActivity.this)));\n                return data.toString();\n            } catch (Exception ignored) { return "{}"; }\n        }\n\n        @JavascriptInterface\n        public void startBirRelay() {\n            runOnUiThread(() -> {\n                if (!BirRelayManager.permissionsReady(MainActivity.this)) {\n                    requestPermissions(BirRelayManager.permissions(), 559);\n                    toast(ui("Accordez l’autorisation Appareils à proximité puis touchez de nouveau B.I.R. Relay.",\n                            "Grant Nearby devices permission, then tap B.I.R. Relay again."));\n                    return;\n                }\n                toast(BirRelayManager.start(MainActivity.this));\n            });\n        }\n\n        @JavascriptInterface\n        public void syncOfflineNow() {\n            new Thread(() -> { OfflineSyncManager.syncSome(MainActivity.this, 25);\n                runOnUiThread(() -> toast(ui("Synchronisation locale relancée.", "Local synchronization restarted.")));\n            }, "BIR-OfflineSync-v290").start();\n        }\n\n        @JavascriptInterface\n        public void checkServerHealth() {''','Relay bridge')
# Configuration includes offline state.
s=once(s,'                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));', '                value.put("mock_owner_server_entitled", SecureOwnerStore.has(MainActivity.this, "MOCK_OWNER"));\n                value.put("offline_pending_events", LocalEventStore.pendingCount(MainActivity.this));\n                value.put("robot_offline_capable", AppConfig.isRobotMode(MainActivity.this));')
write(p,s)

# ---------------------------------------------------------------------------
# RobotService: server command is leased once then executed locally. Keep a
# single DIALING fence for idempotence, suppress chatty intermediate events.
# Local commands never depend on an API lease and wait safely for Accessibility.
# ---------------------------------------------------------------------------
p='app/src/main/java/com/profitloop/blueauto/RobotService.java'; s=read(p)
s=once(s,
'''            List<String> profiles = AppConfig.enabledRobotProfileIds(this);\n            if (!profiles.isEmpty()) acquireStandbyWakeLock();''',
'''            List<String> profiles = AppConfig.enabledRobotProfileIds(this);\n            if (!profiles.isEmpty()) acquireStandbyWakeLock();\n            // Synchronization is secondary to execution: failures here never block local USSD.\n            OfflineSyncManager.syncSome(this, 4);''','outbox sync cycle')
# Initial readiness: keep local pending command rather than releasing a non-existent lease.
s=once(s,
'''                if (PendingCommandStore.LEASED.equals(state)) {\n                    releaseUnexecutedLease(owner, active, ApiClient.forProfile(this, owner),\n                            readiness.message);\n                } else {''',
'''                if (PendingCommandStore.LEASED.equals(state)) {\n                    if (active.optBoolean("local_origin", false)) {\n                        if (readiness.hardFailure) finishCommand(owner, false, "LOCAL_ROBOT_NOT_READY", readiness.message, "");\n                        else handleRobotNotReady(owner, readiness);\n                    } else {\n                        releaseUnexecutedLease(owner, active, ApiClient.forProfile(this, owner), readiness.message);\n                    }\n                } else {''','local readiness keep')
# Conflicts: do not discard a second local queued command.
s=once(s,
'''                    if (PendingCommandStore.LEASED.equals(\n                            conflict.optString("local_state", PendingCommandStore.LEASED))) {\n                        releaseUnexecutedLease(conflictProfile, conflict,\n                                ApiClient.forProfile(this, conflictProfile),\n                                "Une autre session USSD utilise déjà ce téléphone.");''',
'''                    if (PendingCommandStore.LEASED.equals(\n                            conflict.optString("local_state", PendingCommandStore.LEASED))) {\n                        if (conflict.optBoolean("local_origin", false)) continue;\n                        releaseUnexecutedLease(conflictProfile, conflict,\n                                ApiClient.forProfile(this, conflictProfile),\n                                "Une autre session USSD utilise déjà ce téléphone.");''','local conflict hold')
# Active command nullable API.
s=once(s,'                    ApiClient leasedApi = ApiClient.forProfile(this, owner);','                    ApiClient leasedApi = activeUssd.optBoolean("local_origin", false) ? null : ApiClient.forProfile(this, owner);','nullable leased api')
# Mark remote order received locally after lease.
s=once(s,
'''                        command.put("state_changed_at", System.currentTimeMillis());\n                        PendingCommandStore.save(this, profileId, command);''',
'''                        command.put("state_changed_at", System.currentTimeMillis());\n                        PendingCommandStore.save(this, profileId, command);\n                        try { JSONObject received = new JSONObject(command.toString()); received.remove("lease_token");\n                            LocalEventStore.append(this, profileId, command.optString("public_id"), "REMOTE_ORDER_RECEIVED", received);\n                        } catch (Exception ignored) {}''','remote lease journal')
# Execute: only DIALING fence to server; all subsequent progress stays local.
s=once(s,
'''                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);\n                api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot déverrouillé.", "");\n                updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");\n\n                String next = requiresPin ? PendingCommandStore.AWAITING_PIN\n                        : PendingCommandStore.AWAITING_RESULT;\n                PendingCommandStore.updateState(this, profileId, next);\n                api.sendEvent(command, next, requiresPin\n                        ? "En attente de la fenêtre de confirmation PIN."\n                        : "Commande directe avec PIN local déjà composé; attente du résultat opérateur.", "");''',
'''                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);\n                if (api != null) {\n                    // This single fence is intentionally kept: it prevents another Robot from\n                    // re-leasing a transaction after physical USSD may have started.\n                    api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot.", "");\n                }\n                updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");\n\n                String next = requiresPin ? PendingCommandStore.AWAITING_PIN\n                        : PendingCommandStore.AWAITING_RESULT;\n                PendingCommandStore.updateState(this, profileId, next);''','minimal server events')
# PIN progress purely local.
old='''        try {\n            ApiClient api = ApiClient.forProfile(this, profileId);\n            api.sendEvent(command, state, message, "");\n            if ("PIN_SUBMITTED".equals(state)) {\n                PendingCommandStore.updateState(this, profileId, PendingCommandStore.AWAITING_RESULT);\n                api.sendEvent(command, "AWAITING_RESULT",\n                        "Validation envoyée; attente confirmation Blue.", "");\n            }\n        } catch (Exception ignored) {\n        }'''
new='''        try {\n            if ("PIN_SUBMITTED".equals(state)) {\n                PendingCommandStore.updateState(this, profileId, PendingCommandStore.AWAITING_RESULT);\n            }\n            JSONObject progress = new JSONObject(); progress.put("state", state); progress.put("message", message == null ? "" : message);\n            LocalEventStore.append(this, profileId, command.optString("public_id"), "LOCAL_PROGRESS", progress);\n        } catch (Exception ignored) {}'''
s=once(s,old,new,'local progress only')
# Finish local before server reporting.
s=once(s,
'''        boolean reported = false;\n        try {\n            String detail = message == null ? "" : message;''',
'''        boolean localOrigin = command.optBoolean("local_origin", false);\n        if (localOrigin) {\n            try {\n                JSONObject result = new JSONObject(command.toString());\n                result.remove("lease_token"); result.put("state", state); result.put("error_code", code);\n                result.put("result_message", message == null ? "" : message);\n                result.put("operator_transaction_id", transactionId == null ? "" : transactionId);\n                result.put("completed_at_ms", System.currentTimeMillis());\n                LocalEventStore.append(this, profileId, command.optString("public_id"), "LOCAL_COMMAND_RESULT", result);\n            } catch (Exception ignored) {}\n            if (success && "MODIFY_PIN_LOCAL".equals(UssdCommandFactory.operation(command))) {\n                try { PendingPinChangeStore.commit(this, profileId); } catch (Exception ignored) {}\n            }\n            PendingCommandStore.clear(this, profileId);\n            lastCommandFinishedAt = System.currentTimeMillis(); releaseCommandWakeLock(); BlueAccessibilityService.kick(this);\n            executor.execute(() -> OfflineSyncManager.syncProfile(this, profileId, 8));\n            updateNotification(success ? "Commande locale réussie — synchronisation asynchrone" : "Commande locale terminée — preuve conservée");\n            scheduleCycle(1_000L); return;\n        }\n\n        boolean reported = false;\n        try {\n            String detail = message == null ? "" : message;''','local finish branch')
# Release functions handle local commands / null API.
s=once(s,
'''    private void releaseLockedLease(String profileId, JSONObject command, ApiClient api) {\n        boolean secure = DeviceLockState.isSecurelyLocked(this);''',
'''    private void releaseLockedLease(String profileId, JSONObject command, ApiClient api) {\n        boolean secure = DeviceLockState.isSecurelyLocked(this);\n        if (command != null && command.optBoolean("local_origin", false)) {\n            releaseCommandWakeLock();\n            updateNotification(robotSummary(secure ? "Écran sécurisé — commande locale conservée jusqu’au déverrouillage humain" : "Écran verrouillé — commande locale conservée et reprise automatique"));\n            scheduleWatchdog(this, 15_000L); return;\n        }''','local locked keep')
s=once(s,
'''    private void releaseUnexecutedLease(String profileId, JSONObject command, ApiClient api,\n                                        String reason) {\n        try {\n            api.releaseCommand(command, "Robot non éligible avant composition : " + reason);''',
'''    private void releaseUnexecutedLease(String profileId, JSONObject command, ApiClient api,\n                                        String reason) {\n        if (command != null && command.optBoolean("local_origin", false)) {\n            updateNotification(robotSummary("Commande locale conservée — " + reason));\n            scheduleWatchdog(this, 15_000L); return;\n        }\n        try {\n            if (api != null) api.releaseCommand(command, "Robot non éligible avant composition : " + reason);''','local unexecuted keep')
s=once(s,
'''    private void holdLeaseForAccessibility(String profileId, JSONObject command, ApiClient api) {\n        boolean granted = BlueAccessibilityService.isEnabled(this);''',
'''    private void holdLeaseForAccessibility(String profileId, JSONObject command, ApiClient api) {\n        boolean granted = BlueAccessibilityService.isEnabled(this);\n        if (command != null && command.optBoolean("local_origin", false)) {\n            updateNotification(robotSummary(granted ? "Accessibilité autorisée, service Android en reconnexion — commande locale conservée" : "Accessibilité désactivée par Android/utilisateur — commande locale conservée, réactivation requise"));\n            scheduleWatchdog(this, granted ? 5_000L : 30_000L); return;\n        }''','local accessibility keep')
write(p,s)

# ---------------------------------------------------------------------------
# Commission policy expose default rate to balance presentation.
# ---------------------------------------------------------------------------
p='app/src/main/assets/control-tower-v271.js'; s=read(p)
s=once(s,
'''window.BIRCommissionPolicy={getRateBps:effectiveRate,setOneShotRate:function(child,bps){oneShot[upper(child)]=Number(bps||0);},clearOneShotRate:function(child){delete oneShot[upper(child)];},serverSupportsPersistent:function(){return commissionServerSupport===true;}};''',
'''window.BIRCommissionPolicy={getRateBps:effectiveRate,getDefaultRateBps:function(){return Number(commissionPolicy().default_bps||0);},setOneShotRate:function(child,bps){oneShot[upper(child)]=Number(bps||0);},clearOneShotRate:function(child){delete oneShot[upper(child)];},serverSupportsPersistent:function(){return commissionServerSupport===true;}};''','default commission getter')
write(p,s)

# ---------------------------------------------------------------------------
# v2.9 Web overlay: 3-part DAE/DSM balance, single PoS balance, Relay controls,
# explicit offline wording and additional EN coverage.
# ---------------------------------------------------------------------------
write('app/src/main/assets/control-tower-v290.js', r'''(function(){
'use strict';
function id(x){return document.getElementById(x);}function b(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}function cfg(){try{return JSON.parse((b()&&b().getConfiguration&&b().getConfiguration())||'{}');}catch(e){return {};}}function upper(v){return String(v||'').toUpperCase();}function numText(v){var m=String(v||'').replace(/[^0-9-]/g,'');return m?Number(m):NaN;}function money(n){return isFinite(n)?String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' ')+' F':'—';}
var c=cfg(),lang='fr';try{lang=b()&&b().getUiLanguage&&b().getUiLanguage()==='en'?'en':'fr';}catch(e){}function t(fr,en){return lang==='en'?en:fr;}
var EXTRA={'Lecture du solde en cours…':'Reading balance…','Solde réel hors commission':'Real balance excluding commission','Commission au taux par défaut':'Commission at default rate','Solde global réel':'Real total balance','Hors connexion':'Offline','Événements à synchroniser':'Events waiting to sync','Relayer maintenant':'Relay now','Synchroniser maintenant':'Sync now','Commande locale':'Local command','Annuaire enfant absent hors connexion. Synchronisez ce réseau une fois en ligne puis réessayez.':'Child directory is unavailable offline. Sync this network once while online, then retry.','Cette commande nécessite un Robot local actif ou une connexion Remote.':'This command requires an active local Robot or a Remote connection.','Commande prise en charge directement par ce Robot, sans dépendre du serveur pour l’exécution.':'This Robot handles the command directly without relying on the server for execution.','Accessibilité autorisée mais service Android en reconnexion. Le Robot reste actif logiquement et reprendra automatiquement sans perdre la file.':'Accessibility is enabled but the Android service is reconnecting. The Robot remains logically active and resumes automatically without losing its queue.'};
function translate(root){if(lang!=='en'||!root)return;var w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false),n;while((n=w.nextNode())){if(n.parentNode&&/^(SCRIPT|STYLE)$/.test(n.parentNode.tagName))continue;var x=n.nodeValue,trim=String(x||'').trim();if(EXTRA[trim])n.nodeValue=x.replace(trim,EXTRA[trim]);}}
function defaultBps(){try{return window.BIRCommissionPolicy&&window.BIRCommissionPolicy.getDefaultRateBps?Number(window.BIRCommissionPolicy.getDefaultRateBps()||0):0;}catch(e){return upper(c.role)==='DAE'?1000:upper(c.role)==='DSM'?800:0;}}
function ensureBalance(){var card=document.querySelector('.bir-balance-card'),role=upper(c.role),head=id('birCamtelBalance'),grid=card&&card.querySelector('.bir-finance-grid');if(!card||!head)return;if(role==='POS'){if(grid)grid.style.display='none';var kicker=card.querySelector('.bir-kicker');if(kicker)kicker.textContent=t('SOLDE BLUE RÉEL','REAL BLUE BALANCE');return;}if(role!=='DAE'&&role!=='DSM')return;if(grid)grid.style.display='none';if(id('v290BalanceSplit'))return;var wrap=document.createElement('div');wrap.id='v290BalanceSplit';wrap.className='v290-balance-split';wrap.innerHTML='<div class="v290-balance-main-note">'+t('Le montant principal retire la part commission calculée au taux par défaut.','The primary amount removes the commission share calculated at the default rate.')+'</div><div class="v290-balance-two"><div><span>'+t('Commission au taux par défaut','Commission at default rate')+'</span><b id="v290CommissionBalance">—</b><small id="v290DefaultRate">—</small></div><div><span>'+t('Solde global réel','Real total balance')+'</span><b id="v290GlobalBalance">—</b><small>'+t('Solde principal + commission','Primary balance + commission')+'</small></div></div>';card.appendChild(wrap);var kicker=card.querySelector('.bir-kicker');if(kicker)kicker.textContent=t('SOLDE RÉEL HORS COMMISSION','REAL BALANCE EXCLUDING COMMISSION');updateSplit();new MutationObserver(updateSplit).observe(head,{childList:true,characterData:true,subtree:true});}
var updating=false;function updateSplit(){if(updating)return;var head=id('birCamtelBalance'),comm=id('v290CommissionBalance'),totalOut=id('v290GlobalBalance');if(!head||!comm||!totalOut)return;var total=numText(head.getAttribute('data-v290-total')||head.textContent);if(!isFinite(total))return;var bps=Math.max(0,defaultBps()),net=Math.floor(total*10000/(10000+bps)),commission=total-net;updating=true;head.setAttribute('data-v290-total',String(total));head.textContent=String(net).replace(/\B(?=(\d{3})+(?!\d))/g,' ');comm.textContent=money(commission);totalOut.textContent=money(total);if(id('v290DefaultRate'))id('v290DefaultRate').textContent=t('Taux par défaut : ','Default rate: ')+(bps/100).toFixed(bps%100?2:0)+' %';updating=false;}
function relayPanel(){var support=document.querySelector('[data-tab-panel="support"]');if(!support||id('v290Relay'))return;var st={};try{st=JSON.parse((b()&&b().getOfflineStatus&&b().getOfflineStatus())||'{}');}catch(e){}var card=document.createElement('article');card.id='v290Relay';card.className='panel v290-relay';card.innerHTML='<p class="eyebrow">B.I.R. RELAY</p><h3>'+t('Résilience hors connexion entre appareils proches','Offline resilience between nearby devices')+'</h3><p>'+t('Deux appareils B.I.R. proches peuvent échanger leurs événements en attente par Wi‑Fi Direct. Aucun SMS, aucun PIN et aucune commande financière n’est transmis par Relay.','Two nearby B.I.R. devices can exchange pending events over Wi‑Fi Direct. Relay transmits no SMS, PIN or financial command.')+'</p><div class="v290-relay-kpi"><span>'+t('Événements à synchroniser','Events waiting to sync')+'</span><b id="v290Pending">'+Number(st.pending_events||0)+'</b></div><div class="module-actions"><button id="v290RelayNow">'+t('RELAYER MAINTENANT','RELAY NOW')+'</button><button id="v290SyncNow" class="secondary">'+t('SYNCHRONISER MAINTENANT','SYNC NOW')+'</button></div><small>'+t('Relay s’ouvre seulement pendant une courte fenêtre à la demande afin d’économiser la batterie.','Relay opens only for a short on-demand window to save battery.')+'</small>';support.insertBefore(card,support.firstChild);id('v290RelayNow').onclick=function(){if(b()&&b().startBirRelay)b().startBirRelay();};id('v290SyncNow').onclick=function(){if(b()&&b().syncOfflineNow)b().syncOfflineNow();};}
function offlineNotice(){var reports=document.querySelector('[data-tab-panel="reports"]');if(!reports||id('v290OfflineRule'))return;var x=document.createElement('div');x.id='v290OfflineRule';x.className='notice v290-offline-rule';x.textContent=t('ROBOT OFFLINE-FIRST : les commandes exécutables par la SIM locale continuent sans Internet. REQUEST_SUPPLY et Remote restent réseau-dépendants. Les résultats sont synchronisés après exécution.','OFFLINE-FIRST ROBOT: commands executable by the local SIM continue without Internet. REQUEST_SUPPLY and Remote still require network. Results sync after execution.');reports.insertBefore(x,reports.firstChild);}
function init(){c=cfg();ensureBalance();relayPanel();offlineNotice();translate(document.body);if(window.MutationObserver)new MutationObserver(function(m){for(var i=0;i<m.length;i++)for(var j=0;j<m[i].addedNodes.length;j++)if(m[i].addedNodes[j].nodeType===1)translate(m[i].addedNodes[j]);}).observe(document.body,{childList:true,subtree:true});}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(init,120);});else setTimeout(init,120);
})();
''')
write('app/src/main/assets/control-tower-v290.css', r'''.v290-balance-split{margin-top:14px}.v290-balance-main-note{font-size:13px;opacity:.8;margin:0 0 10px}.v290-balance-two{display:grid;grid-template-columns:1fr 1fr;gap:10px}.v290-balance-two>div,.v290-relay-kpi{border:1px solid rgba(78,225,255,.22);border-radius:18px;padding:14px;background:rgba(3,18,48,.45)}.v290-balance-two span,.v290-relay-kpi span{display:block;font-size:13px;opacity:.82}.v290-balance-two b,.v290-relay-kpi b{display:block;font-size:23px;margin-top:5px}.v290-balance-two small{display:block;margin-top:4px;opacity:.68}.v290-relay{border-color:rgba(255,205,92,.45)}.v290-relay-kpi{display:flex;align-items:center;justify-content:space-between;margin:12px 0}.v290-offline-rule{border-color:rgba(78,225,255,.35)}@media(max-width:360px){.v290-balance-two{grid-template-columns:1fr}.v290-balance-two b{font-size:20px}}
''')
# Include overlay after v280.
p='app/src/main/assets/index.html'; s=read(p)
s=once(s,'    <link rel="stylesheet" href="control-tower-v280.css">','    <link rel="stylesheet" href="control-tower-v280.css">\n    <link rel="stylesheet" href="control-tower-v290.css">','v290 css')
s=once(s,'<script src="control-tower-v280.js"></script>','<script src="control-tower-v280.js"></script>\n<script src="control-tower-v290.js"></script>','v290 js')
write(p,s)

# ---------------------------------------------------------------------------
# Real Android resources EN catalog begins replacing hard-coded future strings.
# Existing Java ui(fr,en) remains for old screens; new work must use resources.
# ---------------------------------------------------------------------------
write('app/src/main/res/values-en/strings.xml', '''<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <string name="app_name">B.I.R.</string>\n    <string name="accessibility_service_name">B.I.R. Robot Accessibility</string>\n    <string name="accessibility_service_description">Checks the Blue USSD confirmation, enters the PIN stored locally on the phone and captures the operator result. The PIN is never sent to the server.</string>\n</resources>\n''')

# ---------------------------------------------------------------------------
# Contract: two modes only, offline local execution, no SMS fallback, Relay,
# three-part DAE/DSM balance, PoS single balance, no Cloudflare changes.
# ---------------------------------------------------------------------------
write('app/src/test/v290-robot-offline-relay-contract.mjs', r'''import fs from 'node:fs';
function text(p){return fs.readFileSync(p,'utf8')}
const gradle=text('app/build.gradle'),main=text('app/src/main/java/com/profitloop/blueauto/MainActivity.java'),robot=text('app/src/main/java/com/profitloop/blueauto/RobotService.java'),manifest=text('app/src/main/AndroidManifest.xml'),index=text('app/src/main/assets/index.html'),v290=text('app/src/main/assets/control-tower-v290.js'),offline=text('app/src/main/java/com/profitloop/blueauto/OfflineRobotEngine.java'),relay=text('app/src/main/java/com/profitloop/blueauto/BirRelayManager.java');
const must=(ok,msg)=>{if(!ok)throw new Error(msg)};
must(gradle.includes('versionCode 55')&&gradle.includes('versionName "2.9.0"'),'v2.9 identity missing');
must(gradle.includes('applicationId "com.profitloop.blueauto"'),'historical package changed');
must(main.includes('new String[]{"REMOTE", "ROBOT"}'),'exact two modes must remain');
must(!main.includes('new String[]{"REMOTE", "ROBOT", "HYBRID"}'),'HYBRID mode reintroduced');
must(offline.includes('"REQUEST_SUPPLY".equals(t))return false'),'REQUEST_SUPPLY must stay online-dependent');
must(offline.includes('"SUPPLY_CHILD"')&&offline.includes('"RETAIL_SALE"')&&offline.includes('"CHECK_BALANCE"'),'local Robot coverage incomplete');
must(robot.includes('local_origin')&&robot.includes('OfflineSyncManager.syncSome'),'offline queue not wired');
must(robot.includes('single fence is intentionally kept'),'server idempotence fence missing');
must(relay.includes('WifiP2pManager')&&relay.includes('BIR_RELAY_1'),'B.I.R. Relay transport missing');
must(!manifest.includes('SEND_SMS'),'SMS fallback is forbidden');
must(index.includes('control-tower-v290.js'),'v2.9 overlay missing');
must(v290.includes('SOLDE RÉEL HORS COMMISSION')&&v290.includes('Commission au taux par défaut')&&v290.includes('Solde global réel'),'DAE/DSM three-part balance missing');
must(v290.includes("if(role==='POS'){if(grid)grid.style.display='none'"),'PoS single balance guard missing');
must(fs.existsSync('app/src/main/res/values-en/strings.xml'),'native EN resources missing');
console.log('BIR v2.9 Robot offline + Relay contract: OK');
''')

print('v2.9 Robot offline-first/Relay app patch prepared')
