from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')

def once(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f'v290 final anchor {label}: expected 1, got {text.count(old)}')
    return text.replace(old, new, 1)

# Device-bound relay identity: private key never leaves AndroidKeyStore.
write('app/src/main/java/com/profitloop/blueauto/RelayIdentityStore.java', r'''package com.profitloop.blueauto;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;

final class RelayIdentityStore {
    private static final String STORE = "AndroidKeyStore";
    private static final String ALIAS = "bir_relay_identity_v290";
    private RelayIdentityStore() {}

    private static void ensure() throws Exception {
        KeyStore ks = KeyStore.getInstance(STORE); ks.load(null);
        if (ks.containsAlias(ALIAS)) return;
        KeyPairGenerator g = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, STORE);
        g.initialize(new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setKeySize(2048)
                .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                .build());
        g.generateKeyPair();
    }

    static String publicKeyBase64() throws Exception {
        ensure(); KeyStore ks = KeyStore.getInstance(STORE); ks.load(null);
        PublicKey key = ks.getCertificate(ALIAS).getPublicKey();
        return Base64.encodeToString(key.getEncoded(), Base64.NO_WRAP);
    }

    static String fingerprint() throws Exception { return OfflineLedgerDb.sha256(publicKeyBase64()); }

    static String sign(String canonical) throws Exception {
        ensure(); KeyStore ks = KeyStore.getInstance(STORE); ks.load(null);
        PrivateKey key = (PrivateKey) ks.getKey(ALIAS, null);
        Signature sig = Signature.getInstance("SHA256withRSA");
        sig.initSign(key); sig.update(canonical.getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(sig.sign(), Base64.NO_WRAP);
    }

    static boolean verify(String publicKeyBase64, String canonical, String signatureBase64) {
        try {
            byte[] encoded = Base64.decode(publicKeyBase64, Base64.DEFAULT);
            PublicKey key = KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(encoded));
            Signature sig = Signature.getInstance("SHA256withRSA");
            sig.initVerify(key); sig.update(canonical.getBytes(StandardCharsets.UTF_8));
            return sig.verify(Base64.decode(signatureBase64, Base64.DEFAULT));
        } catch (Exception ignored) { return false; }
    }
}
''')

# Replace token-derived relay signatures with verifiable AndroidKeyStore signatures.
p='app/src/main/java/com/profitloop/blueauto/OfflineSyncManager.java'; s=read(p)
start=s.index('final class OfflineSyncManager')
write(p, r'''package com.profitloop.blueauto;

import android.content.Context;
import org.json.JSONArray;
import org.json.JSONObject;

final class OfflineSyncManager {
    private OfflineSyncManager(){}

    static void syncSome(Context c,int limit){
        for(String profile:AppConfig.profileIds(c)) syncProfile(c,profile,limit);
        syncRelayed(c,limit);
    }

    static void syncProfile(Context c,String profile,int limit){
        JSONArray items=LocalEventStore.pending(c,profile,Math.max(1,limit));
        if(items.length()==0)return;
        try{
            JSONObject response=ApiClient.forProfile(c,profile).syncLocalEvents(items);
            JSONArray accepted=response.optJSONArray("accepted_event_ids");
            if(accepted!=null){for(int i=0;i<accepted.length();i++) LocalEventStore.markSynced(c,accepted.optString(i)); return;}
        }catch(Exception ignored){}
        // Compatibility with the live 2.8 Worker: preserve events locally and only send operator
        // evidence through the historical passive endpoint. Never replay a financial command.
        for(int i=0;i<items.length();i++){
            JSONObject e=items.optJSONObject(i); if(e==null)continue;
            JSONObject p=e.optJSONObject("payload"); String raw=p==null?"":p.optString("result_message","");
            if(raw.length()<4)continue;
            try{ApiClient.forProfile(c,profile).recordOperatorMessage(raw);}catch(Exception ignored){break;}
            LocalEventStore.retryLater(c,e.optString("event_id"),60_000L);
        }
    }

    static JSONArray relayBundle(Context c,int limit){
        JSONArray src=LocalEventStore.pending(c,"",limit),out=new JSONArray();
        for(int i=0;i<src.length();i++){
            JSONObject e=src.optJSONObject(i); if(e==null)continue;
            String profile=e.optString("profile_id",""); if(!AppConfig.isPaired(c,profile))continue;
            try{
                JSONObject x=new JSONObject(e.toString());
                x.put("protocol","BIR_RELAY_EVENT_V1");
                x.put("source_device_id",AppConfig.serverDeviceId(c,profile));
                x.put("source_node_code",AppConfig.nodeCode(c,profile));
                x.put("relay_public_key",RelayIdentityStore.publicKeyBase64());
                x.put("relay_fingerprint",RelayIdentityStore.fingerprint());
                x.put("relay_hops",Math.max(0,x.optInt("relay_hops",0)));
                x.put("relay_signature",RelayIdentityStore.sign(canonical(x)));
                out.put(x);
            }catch(Exception ignored){}
        }
        return out;
    }

    static void acceptRelayBundle(Context c,JSONArray bundle){
        if(bundle==null)return;
        for(int i=0;i<bundle.length();i++){
            JSONObject e=bundle.optJSONObject(i); if(!validRelayEnvelope(e))continue;
            if(e.optInt("relay_hops",0)>=3)continue;
            try{JSONObject copy=new JSONObject(e.toString());copy.put("relay_hops",e.optInt("relay_hops",0)+1);LocalEventStore.importRelayEnvelope(c,copy);}catch(Exception ignored){}
        }
    }

    static void syncRelayed(Context c,int limit){
        JSONArray in=LocalEventStore.relayInbox(c,limit); if(in.length()==0||!AppConfig.isPaired(c))return;
        ApiClient courier=new ApiClient(c);
        for(int i=0;i<in.length();i++){
            JSONObject e=in.optJSONObject(i); if(e==null||!validRelayEnvelope(e))continue;
            String id=e.optString("event_id","");
            try{courier.relaySync(e);LocalEventStore.markRelaySynced(c,id);}catch(Exception error){LocalEventStore.retryRelayLater(c,id,60_000L);break;}
        }
    }

    static boolean validRelayEnvelope(JSONObject e){
        if(e==null||!"BIR_RELAY_EVENT_V1".equals(e.optString("protocol","")))return false;
        String id=e.optString("event_id",""),pub=e.optString("relay_public_key",""),fp=e.optString("relay_fingerprint",""),sig=e.optString("relay_signature","");
        if(!id.matches("evt_[A-Za-z0-9]{16,80}")||pub.length()<100||sig.length()<100||!fp.matches("[a-f0-9]{64}"))return false;
        if(!fp.equals(OfflineLedgerDb.sha256(pub)))return false;
        return RelayIdentityStore.verify(pub,canonical(e),sig);
    }

    private static String canonical(JSONObject e){
        JSONObject p=e.optJSONObject("payload");
        return e.optString("event_id","")+"|"+e.optString("source_device_id","")+"|"+e.optString("source_node_code","")+"|"+e.optLong("created_at",0L)+"|"+e.optString("kind","")+"|"+(p==null?"{}":p.toString());
    }
}
''')

# Nearby Relay = Wi-Fi Direct first, Bluetooth RFCOMM fallback. No SMS, no financial order transport.
write('app/src/main/java/com/profitloop/blueauto/BirRelayManager.java', r'''package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothServerSocket;
import android.bluetooth.BluetoothSocket;
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
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;

final class BirRelayManager {
    private static final String SERVICE="_birrelay._tcp";
    private static final int PORT=49831;
    private static final long WINDOW_MS=40_000L;
    private static final UUID BT_UUID=UUID.fromString("2fd7dbe7-ef24-4aac-83ec-1ab7a5cc3bb2");
    private static BirRelayManager live;
    private final Activity activity;
    private final WifiP2pManager manager;
    private final WifiP2pManager.Channel channel;
    private final AtomicBoolean transferred=new AtomicBoolean(false);
    private BroadcastReceiver receiver;
    private volatile BluetoothServerSocket btServer;

    private BirRelayManager(Activity a){activity=a;manager=(WifiP2pManager)a.getSystemService(Context.WIFI_P2P_SERVICE);channel=manager==null?null:manager.initialize(a,a.getMainLooper(),null);}

    static synchronized String start(Activity a){
        if(LocalEventStore.pendingCount(a)<=0)return "Aucun événement en attente à relayer.";
        if(!permissionsReady(a))return "Autorisations Appareils à proximité / localisation requises pour B.I.R. Relay.";
        if(live!=null)live.stop(); live=new BirRelayManager(a); live.begin();
        return "B.I.R. Relay recherche un appareil B.I.R. proche par Wi‑Fi Direct / Bluetooth pendant 40 secondes.";
    }

    static boolean permissionsReady(Activity a){
        if(Build.VERSION.SDK_INT>=33&&a.checkSelfPermission("android.permission.NEARBY_WIFI_DEVICES")!=PackageManager.PERMISSION_GRANTED)return false;
        if(Build.VERSION.SDK_INT>=31){
            if(a.checkSelfPermission("android.permission.BLUETOOTH_SCAN")!=PackageManager.PERMISSION_GRANTED)return false;
            if(a.checkSelfPermission("android.permission.BLUETOOTH_CONNECT")!=PackageManager.PERMISSION_GRANTED)return false;
        }
        return Build.VERSION.SDK_INT>=33||a.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED;
    }

    static String[] permissions(){
        if(Build.VERSION.SDK_INT>=33)return new String[]{"android.permission.NEARBY_WIFI_DEVICES","android.permission.BLUETOOTH_SCAN","android.permission.BLUETOOTH_CONNECT"};
        if(Build.VERSION.SDK_INT>=31)return new String[]{Manifest.permission.ACCESS_FINE_LOCATION,"android.permission.BLUETOOTH_SCAN","android.permission.BLUETOOTH_CONNECT"};
        return new String[]{Manifest.permission.ACCESS_FINE_LOCATION};
    }

    private void begin(){
        startBluetooth();
        if(manager!=null&&channel!=null)startWifi();
        activity.getWindow().getDecorView().postDelayed(this::stop,WINDOW_MS);
    }

    private void startWifi(){
        register(); Map<String,String> record=new HashMap<>(); record.put("v","1");record.put("app","BIR");
        WifiP2pDnsSdServiceInfo info=WifiP2pDnsSdServiceInfo.newInstance("BIR-RELAY",SERVICE,record);
        try{manager.addLocalService(channel,info,new WifiP2pManager.ActionListener(){public void onSuccess(){discover();}public void onFailure(int r){}});}catch(SecurityException ignored){}
    }

    private void register(){
        IntentFilter f=new IntentFilter();f.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);
        receiver=new BroadcastReceiver(){public void onReceive(Context c,Intent i){if(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION.equals(i.getAction()))try{manager.requestConnectionInfo(channel,BirRelayManager.this::onInfo);}catch(SecurityException ignored){}}};
        activity.registerReceiver(receiver,f);
    }

    private void discover(){
        try{
            manager.setDnsSdResponseListeners(channel,(instance,registrationType,device)->{if("BIR-RELAY".equals(instance)&&!transferred.get())connect(device);},(full,txt,device)->{});
            WifiP2pDnsSdServiceRequest req=WifiP2pDnsSdServiceRequest.newInstance();
            manager.addServiceRequest(channel,req,new WifiP2pManager.ActionListener(){public void onSuccess(){try{manager.discoverServices(channel,new WifiP2pManager.ActionListener(){public void onSuccess(){}public void onFailure(int r){}});}catch(SecurityException ignored){}}public void onFailure(int r){}});
        }catch(SecurityException ignored){}
    }

    private void connect(WifiP2pDevice d){try{WifiP2pConfig c=new WifiP2pConfig();c.deviceAddress=d.deviceAddress;manager.connect(channel,c,new WifiP2pManager.ActionListener(){public void onSuccess(){}public void onFailure(int r){}});}catch(SecurityException ignored){}}

    private void onInfo(WifiP2pInfo info){
        if(info==null||!info.groupFormed||transferred.get())return;
        new Thread(()->{try{if(info.isGroupOwner)serveWifi();else clientWifi(info.groupOwnerAddress.getHostAddress());success("Wi‑Fi Direct");}catch(Exception ignored){}},"BIR-Relay-Wifi-v290").start();
    }

    private void serveWifi()throws Exception{try(ServerSocket ss=new ServerSocket(PORT)){ss.setSoTimeout(12000);try(Socket s=ss.accept()){exchange(s);}}}
    private void clientWifi(String host)throws Exception{try(Socket s=new Socket()){s.connect(new InetSocketAddress(host,PORT),8000);exchange(s);}}

    private void startBluetooth(){
        BluetoothAdapter adapter=BluetoothAdapter.getDefaultAdapter(); if(adapter==null||!adapter.isEnabled())return;
        new Thread(()->{
            try(BluetoothServerSocket server=adapter.listenUsingInsecureRfcommWithServiceRecord("BIR Relay",BT_UUID)){
                btServer=server; BluetoothSocket socket=server.accept((int)WINDOW_MS); if(socket!=null){try{exchange(socket);success("Bluetooth");}finally{socket.close();}}
            }catch(Exception ignored){}finally{btServer=null;}
        },"BIR-Relay-BT-Server-v290").start();
        new Thread(()->{
            try{Set<BluetoothDevice> bonded=adapter.getBondedDevices();int n=0;for(BluetoothDevice d:bonded){if(transferred.get()||n++>=6)break;try(BluetoothSocket socket=d.createInsecureRfcommSocketToServiceRecord(BT_UUID)){socket.connect();exchange(socket);success("Bluetooth");break;}catch(Exception ignored){}}}catch(SecurityException ignored){}
        },"BIR-Relay-BT-Client-v290").start();
    }

    private void exchange(Socket socket)throws Exception{socket.setSoTimeout(10000);exchange(new BufferedReader(new InputStreamReader(socket.getInputStream(),"UTF-8")),new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(),"UTF-8")));}
    private void exchange(BluetoothSocket socket)throws Exception{exchange(new BufferedReader(new InputStreamReader(socket.getInputStream(),"UTF-8")),new BufferedWriter(new OutputStreamWriter(socket.getOutputStream(),"UTF-8")));}

    private void exchange(BufferedReader r,BufferedWriter w)throws Exception{
        JSONObject mine=new JSONObject();mine.put("protocol","BIR_RELAY_1");mine.put("events",OfflineSyncManager.relayBundle(activity,50));
        w.write(mine.toString());w.write("\n");w.flush(); String line=r.readLine();
        if(line!=null&&line.length()<900000){JSONObject peer=new JSONObject(line);if("BIR_RELAY_1".equals(peer.optString("protocol")))OfflineSyncManager.acceptRelayBundle(activity,peer.optJSONArray("events"));}
    }

    private void success(String transport){
        if(!transferred.compareAndSet(false,true))return; OfflineSyncManager.syncRelayed(activity,50);
        activity.runOnUiThread(()->android.widget.Toast.makeText(activity,"B.I.R. Relay : échange signé terminé par "+transport+".",android.widget.Toast.LENGTH_LONG).show()); stop();
    }

    private synchronized void stop(){
        if(receiver!=null){try{activity.unregisterReceiver(receiver);}catch(Exception ignored){}receiver=null;}
        try{if(btServer!=null)btServer.close();}catch(Exception ignored){}
        if(manager!=null&&channel!=null){try{manager.clearLocalServices(channel,null);manager.clearServiceRequests(channel,null);manager.removeGroup(channel,null);}catch(Exception ignored){}}
        if(live==this)live=null;
    }
}
''')

# UI must describe both relay transports and preserve the user's exact two-mode rule.
p='app/src/main/assets/control-tower-v290.js'; s=read(p)
s=s.replace('par Wi‑Fi Direct. Aucun SMS', 'par Wi‑Fi Direct ou Bluetooth. Aucun SMS')
s=s.replace('over Wi‑Fi Direct. Relay transmits', 'over Wi‑Fi Direct or Bluetooth. Relay transmits')
write(p,s)

# Strengthen contract: no SMS path, both nearby transports, signed envelopes, exact two modes.
p='app/src/test/v290-robot-offline-relay-contract.mjs'; s=read(p)
s=s.replace("must(relay.includes('WifiP2pManager')&&relay.includes('BIR_RELAY_1'),'B.I.R. Relay transport missing');",
            "must(relay.includes('WifiP2pManager')&&relay.includes('BluetoothSocket')&&relay.includes('BIR_RELAY_1'),'B.I.R. Relay Wi-Fi Direct/Bluetooth transport missing');")
s=s.replace("must(!manifest.includes('SEND_SMS'),'SMS fallback is forbidden');",
            "must(!manifest.includes('SEND_SMS'),'SMS fallback is forbidden');\nmust(text('app/src/main/java/com/profitloop/blueauto/OfflineSyncManager.java').includes('RelayIdentityStore.sign')&&text('app/src/main/java/com/profitloop/blueauto/OfflineSyncManager.java').includes('validRelayEnvelope'),'signed Relay envelope verification missing');")
write(p,s)

print('BIR v2.9 final convergence hardening applied')
