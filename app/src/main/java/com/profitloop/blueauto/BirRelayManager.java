package com.profitloop.blueauto;

import android.Manifest;
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
import android.os.Handler;
import android.os.Looper;

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
    private static final long AUTO_COOLDOWN_MS=15*60_000L;
    private static final String AUTO_RELAY_AT="bir_relay_auto_at_v295";
    private static final UUID BT_UUID=UUID.fromString("2fd7dbe7-ef24-4aac-83ec-1ab7a5cc3bb2");
    private static BirRelayManager live;
    private final Context context;
    private final WifiP2pManager manager;
    private final WifiP2pManager.Channel channel;
    private final AtomicBoolean transferred=new AtomicBoolean(false);
    private BroadcastReceiver receiver;
    private volatile BluetoothServerSocket btServer;

    private BirRelayManager(Context c){context=c.getApplicationContext();manager=(WifiP2pManager)context.getSystemService(Context.WIFI_P2P_SERVICE);channel=manager==null?null:manager.initialize(context,Looper.getMainLooper(),null);}

    static synchronized String start(Context c){
        if(LocalEventStore.pendingCount(c)<=0)return "Aucun événement en attente à relayer.";
        if(!permissionsReady(c))return "Autorisations Appareils à proximité / localisation requises pour B.I.R. Relay.";
        if(live!=null)live.stop(); live=new BirRelayManager(c); live.begin();
        return "B.I.R. Relay recherche un appareil B.I.R. proche par Wi‑Fi Direct / Bluetooth pendant 40 secondes.";
    }

    static synchronized boolean maybeStart(Context c){
        if(live!=null||LocalEventStore.pendingCount(c)<=0||!permissionsReady(c))return false;
        long now=System.currentTimeMillis(),last=AppConfig.prefs(c).getLong(AUTO_RELAY_AT,0L);
        if(last>0L&&now-last<AUTO_COOLDOWN_MS)return false;
        AppConfig.prefs(c).edit().putLong(AUTO_RELAY_AT,now).apply();
        live=new BirRelayManager(c);live.begin();return true;
    }

    static boolean permissionsReady(Context a){
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
        new Handler(Looper.getMainLooper()).postDelayed(this::stop,WINDOW_MS);
    }

    private void startWifi(){
        register(); Map<String,String> record=new HashMap<>(); record.put("v","1");record.put("app","BIR");
        WifiP2pDnsSdServiceInfo info=WifiP2pDnsSdServiceInfo.newInstance("BIR-RELAY",SERVICE,record);
        try{manager.addLocalService(channel,info,new WifiP2pManager.ActionListener(){public void onSuccess(){discover();}public void onFailure(int r){}});}catch(SecurityException ignored){}
    }

    private void register(){
        IntentFilter f=new IntentFilter();f.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);
        receiver=new BroadcastReceiver(){public void onReceive(Context c,Intent i){if(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION.equals(i.getAction()))try{manager.requestConnectionInfo(channel,BirRelayManager.this::onInfo);}catch(SecurityException ignored){}}};
        if(Build.VERSION.SDK_INT>=33)context.registerReceiver(receiver,f,Context.RECEIVER_NOT_EXPORTED);else context.registerReceiver(receiver,f);
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
        JSONObject mine=new JSONObject();mine.put("protocol","BIR_RELAY_1");mine.put("events",OfflineSyncManager.relayBundle(context,50));
        w.write(mine.toString());w.write("\n");w.flush(); String line=r.readLine();
        if(line!=null&&line.length()<900000){JSONObject peer=new JSONObject(line);if("BIR_RELAY_1".equals(peer.optString("protocol")))OfflineSyncManager.acceptRelayBundle(context,peer.optJSONArray("events"));}
    }

    private void success(String transport){
        if(!transferred.compareAndSet(false,true))return; OfflineSyncManager.syncRelayed(context,50);
        new Handler(Looper.getMainLooper()).post(()->android.widget.Toast.makeText(context,"B.I.R. Relay : échange signé terminé par "+transport+".",android.widget.Toast.LENGTH_LONG).show()); stop();
    }

    private synchronized void stop(){
        if(receiver!=null){try{context.unregisterReceiver(receiver);}catch(Exception ignored){}receiver=null;}
        try{if(btServer!=null)btServer.close();}catch(Exception ignored){}
        if(manager!=null&&channel!=null){try{manager.clearLocalServices(channel,null);manager.clearServiceRequests(channel,null);manager.removeGroup(channel,null);}catch(Exception ignored){}}
        if(live==this)live=null;
    }
}
