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
import android.net.NetworkInfo;
import android.net.wifi.p2p.WifiP2pConfig;
import android.net.wifi.p2p.WifiP2pDevice;
import android.net.wifi.p2p.WifiP2pInfo;
import android.net.wifi.p2p.WifiP2pManager;
import android.net.wifi.p2p.nsd.WifiP2pDnsSdServiceInfo;
import android.net.wifi.p2p.nsd.WifiP2pDnsSdServiceRequest;
import android.os.Build;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * B.I.R. Relay exchanges only pending sanitized event envelopes between nearby B.I.R. phones.
 * It never carries an executable USSD order, PIN, pairing secret or device token. The transport
 * is opportunistic: Wi-Fi Direct first, Bluetooth RFCOMM as a paired-device fallback.
 */
final class BirRelayManager {
    static final String PREF_ENABLED = "bir_relay_enabled_v290";
    static final int WIFI_PORT = 38881;
    private static final String SERVICE_TYPE = "_birrelay._tcp";
    private static final UUID BT_UUID = UUID.fromString("2fd7dbe7-ef24-4aac-83ec-1ab7a5cc3bb2");
    private static final int MAX_PACKET = 900_000;
    private static volatile BirRelayManager instance;

    static BirRelayManager get(Context context) {
        if (instance == null) {
            synchronized (BirRelayManager.class) {
                if (instance == null) instance = new BirRelayManager(context.getApplicationContext());
            }
        }
        return instance;
    }

    static boolean isEnabled(Context context) {
        return AppConfig.prefs(context).getBoolean(PREF_ENABLED, false);
    }

    static void setEnabled(Context context, boolean enabled) {
        AppConfig.prefs(context).edit().putBoolean(PREF_ENABLED, enabled).apply();
        if (enabled) get(context).kick(); else if (instance != null) instance.stopDiscovery();
    }

    static JSONObject status(Context context) {
        JSONObject out = OfflineLedgerDb.get(context).stats();
        try {
            out.put("enabled", isEnabled(context));
            out.put("permissions_ready", permissionsReady(context));
            out.put("wifi_direct_supported", context.getPackageManager().hasSystemFeature(PackageManager.FEATURE_WIFI_DIRECT));
            out.put("bluetooth_supported", context.getPackageManager().hasSystemFeature(PackageManager.FEATURE_BLUETOOTH));
            out.put("last_exchange_at", AppConfig.prefs(context).getLong("bir_relay_last_exchange_v290", 0L));
            out.put("last_peer", AppConfig.prefs(context).getString("bir_relay_last_peer_v290", ""));
        } catch (Exception ignored) {}
        return out;
    }

    static boolean permissionsReady(Context context) {
        if (Build.VERSION.SDK_INT >= 33
                && context.checkSelfPermission("android.permission.NEARBY_WIFI_DEVICES") != PackageManager.PERMISSION_GRANTED) return false;
        if (Build.VERSION.SDK_INT >= 31) {
            if (context.checkSelfPermission("android.permission.BLUETOOTH_SCAN") != PackageManager.PERMISSION_GRANTED) return false;
            if (context.checkSelfPermission("android.permission.BLUETOOTH_CONNECT") != PackageManager.PERMISSION_GRANTED) return false;
            if (context.checkSelfPermission("android.permission.BLUETOOTH_ADVERTISE") != PackageManager.PERMISSION_GRANTED) return false;
        } else if (context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            return false;
        }
        return true;
    }

    private final Context context;
    private final ExecutorService io = Executors.newCachedThreadPool();
    private final AtomicBoolean discovering = new AtomicBoolean(false);
    private WifiP2pManager wifi;
    private WifiP2pManager.Channel channel;
    private WifiP2pDnsSdServiceRequest serviceRequest;
    private BroadcastReceiver receiver;
    private volatile ServerSocket wifiServer;
    private volatile BluetoothServerSocket btServer;

    private BirRelayManager(Context context) { this.context = context; }

    void kick() {
        if (!isEnabled(context) || !permissionsReady(context)) return;
        if (OfflineLedgerDb.get(context).pendingEnvelopes(1).length() == 0) return;
        if (!discovering.compareAndSet(false, true)) return;
        startWifiDirect();
        startBluetooth();
        io.execute(() -> {
            try { Thread.sleep(45_000L); } catch (InterruptedException ignored) { Thread.currentThread().interrupt(); }
            stopDiscovery();
        });
    }

    private void startWifiDirect() {
        if (!context.getPackageManager().hasSystemFeature(PackageManager.FEATURE_WIFI_DIRECT)) return;
        try {
            wifi = (WifiP2pManager) context.getSystemService(Context.WIFI_P2P_SERVICE);
            if (wifi == null) return;
            channel = wifi.initialize(context, Looper.getMainLooper(), () -> stopDiscovery());
            registerReceiver();
            Map<String,String> record = new HashMap<>();
            record.put("port", String.valueOf(WIFI_PORT));
            record.put("proto", "BIR_RELAY_V1");
            record.put("key", safeFingerprint());
            WifiP2pDnsSdServiceInfo service = WifiP2pDnsSdServiceInfo.newInstance(
                    "BIR-" + shortDevice(), SERVICE_TYPE, record);
            wifi.clearLocalServices(channel, new SimpleAction(() -> wifi.addLocalService(channel, service,
                    new SimpleAction(this::discoverWifiServices))));
        } catch (SecurityException ignored) { stopDiscovery(); }
    }

    private void discoverWifiServices() {
        try {
            wifi.setDnsSdResponseListeners(channel, (instanceName, registrationType, device) -> {
                if (registrationType != null && registrationType.contains(SERVICE_TYPE)) connectWifi(device);
            }, (fullDomain, record, device) -> {
                if (record != null && "BIR_RELAY_V1".equals(record.get("proto"))) connectWifi(device);
            });
            serviceRequest = WifiP2pDnsSdServiceRequest.newInstance();
            wifi.addServiceRequest(channel, serviceRequest, new SimpleAction(() ->
                    wifi.discoverServices(channel, new SimpleAction(() -> {}))));
        } catch (SecurityException ignored) {}
    }

    private void connectWifi(WifiP2pDevice device) {
        if (device == null || device.deviceAddress == null) return;
        try {
            WifiP2pConfig config = new WifiP2pConfig();
            config.deviceAddress = device.deviceAddress;
            wifi.connect(channel, config, new SimpleAction(() -> {}));
        } catch (SecurityException ignored) {}
    }

    private void registerReceiver() {
        if (receiver != null) return;
        receiver = new BroadcastReceiver() {
            @Override public void onReceive(Context c, Intent intent) {
                if (!WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION.equals(intent.getAction())) return;
                NetworkInfo network = intent.getParcelableExtra(WifiP2pManager.EXTRA_NETWORK_INFO);
                if (network == null || !network.isConnected() || wifi == null || channel == null) return;
                try {
                    wifi.requestConnectionInfo(channel, BirRelayManager.this::onWifiConnectionInfo);
                } catch (SecurityException ignored) {}
            }
        };
        IntentFilter filter = new IntentFilter();
        filter.addAction(WifiP2pManager.WIFI_P2P_CONNECTION_CHANGED_ACTION);
        context.registerReceiver(receiver, filter);
    }

    private void onWifiConnectionInfo(WifiP2pInfo info) {
        if (info == null || !info.groupFormed) return;
        if (info.isGroupOwner) startWifiServer();
        else if (info.groupOwnerAddress != null) io.execute(() -> {
            try (Socket socket = new Socket()) {
                socket.connect(new InetSocketAddress(info.groupOwnerAddress, WIFI_PORT), 6_000);
                exchange(socket, "WIFI_DIRECT");
            } catch (Exception ignored) {}
        });
    }

    private void startWifiServer() {
        if (wifiServer != null) return;
        io.execute(() -> {
            try (ServerSocket server = new ServerSocket(WIFI_PORT)) {
                wifiServer = server;
                server.setSoTimeout(40_000);
                while (discovering.get()) {
                    try (Socket socket = server.accept()) { exchange(socket, "WIFI_DIRECT"); }
                    catch (java.net.SocketTimeoutException timeout) { break; }
                }
            } catch (Exception ignored) {} finally { wifiServer = null; }
        });
    }

    private void startBluetooth() {
        if (!context.getPackageManager().hasSystemFeature(PackageManager.FEATURE_BLUETOOTH)) return;
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter == null || !adapter.isEnabled()) return;
        io.execute(() -> {
            try (BluetoothServerSocket server = adapter.listenUsingInsecureRfcommWithServiceRecord("BIR Relay", BT_UUID)) {
                btServer = server;
                BluetoothSocket socket = server.accept(40_000);
                if (socket != null) {
                    try { exchange(socket, "BLUETOOTH"); } finally { socket.close(); }
                }
            } catch (Exception ignored) {} finally { btServer = null; }
        });
        io.execute(() -> {
            try {
                Set<BluetoothDevice> bonded = adapter.getBondedDevices();
                int attempts = 0;
                for (BluetoothDevice device : bonded) {
                    if (!discovering.get() || attempts++ >= 6) break;
                    try (BluetoothSocket socket = device.createInsecureRfcommSocketToServiceRecord(BT_UUID)) {
                        socket.connect();
                        exchange(socket, "BLUETOOTH");
                        break;
                    } catch (Exception ignored) {}
                }
            } catch (SecurityException ignored) {}
        });
    }

    private void exchange(Socket socket, String transport) throws Exception {
        socket.setSoTimeout(8_000);
        DataInputStream in = new DataInputStream(socket.getInputStream());
        DataOutputStream out = new DataOutputStream(socket.getOutputStream());
        exchange(in, out, transport);
    }

    private void exchange(BluetoothSocket socket, String transport) throws Exception {
        DataInputStream in = new DataInputStream(socket.getInputStream());
        DataOutputStream out = new DataOutputStream(socket.getOutputStream());
        exchange(in, out, transport);
    }

    private void exchange(DataInputStream in, DataOutputStream out, String transport) throws Exception {
        JSONObject bundle = new JSONObject();
        bundle.put("protocol", "BIR_RELAY_V1");
        bundle.put("sender", shortDevice());
        bundle.put("transport", transport);
        bundle.put("events", OfflineLedgerDb.get(context).pendingEnvelopes(100));
        writePacket(out, bundle.toString());
        String incomingText = readPacket(in);
        JSONObject incoming = new JSONObject(incomingText);
        if (!"BIR_RELAY_V1".equals(incoming.optString("protocol", ""))) return;
        JSONArray events = incoming.optJSONArray("events");
        int imported = 0;
        if (events != null) {
            for (int i = 0; i < events.length(); i++) {
                if (OfflineLedgerDb.get(context).importRelayEnvelope(events.optJSONObject(i))) imported++;
            }
        }
        AppConfig.prefs(context).edit()
                .putLong("bir_relay_last_exchange_v290", System.currentTimeMillis())
                .putString("bir_relay_last_peer_v290", incoming.optString("sender", "nearby") + " / " + transport)
                .putInt("bir_relay_last_imported_v290", imported).apply();
        OfflineSyncManager.flushAsync(context);
    }

    private static void writePacket(DataOutputStream out, String text) throws Exception {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        if (bytes.length > MAX_PACKET) throw new IllegalArgumentException("Relay bundle too large");
        out.writeInt(bytes.length); out.write(bytes); out.flush();
    }

    private static String readPacket(DataInputStream in) throws Exception {
        int length = in.readInt();
        if (length <= 0 || length > MAX_PACKET) throw new IllegalArgumentException("Invalid relay packet");
        byte[] bytes = new byte[length]; in.readFully(bytes);
        return new String(bytes, StandardCharsets.UTF_8);
    }

    synchronized void stopDiscovery() {
        discovering.set(false);
        try { if (wifiServer != null) wifiServer.close(); } catch (Exception ignored) {}
        try { if (btServer != null) btServer.close(); } catch (Exception ignored) {}
        if (wifi != null && channel != null) {
            try { if (serviceRequest != null) wifi.removeServiceRequest(channel, serviceRequest, new SimpleAction(() -> {})); } catch (Exception ignored) {}
            try { wifi.clearLocalServices(channel, new SimpleAction(() -> {})); } catch (Exception ignored) {}
        }
        if (receiver != null) {
            try { context.unregisterReceiver(receiver); } catch (Exception ignored) {}
            receiver = null;
        }
    }

    private String shortDevice() {
        String id = AppConfig.serverDeviceId(context, AppConfig.profileId(context));
        if (id == null || id.isEmpty()) id = safeFingerprint();
        return id.length() > 12 ? id.substring(0, 12) : id;
    }

    private String safeFingerprint() {
        try { return RelayIdentityStore.fingerprint(); } catch (Exception ignored) { return "unknown"; }
    }

    private static final class SimpleAction implements WifiP2pManager.ActionListener {
        private final Runnable success;
        SimpleAction(Runnable success) { this.success = success; }
        @Override public void onSuccess() { if (success != null) success.run(); }
        @Override public void onFailure(int reason) {}
    }
}
