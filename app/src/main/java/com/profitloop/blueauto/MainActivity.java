package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.telephony.SmsMessage;
import android.telephony.TelephonyManager;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public class MainActivity extends Activity {
    private WebView webView;
    private EditText etNodeCode, etPairingKey;
    private Button btnSave;
    private TextView tvStatus;
    private LinearLayout llConfig;
    
    private static final int REQUEST_PERMISSIONS = 1;
    private static final String PREFS_NAME = "ProfitLoopPrefs";
    private static final String KEY_NODE = "NodeCode";
    private static final String KEY_KEY = "PairKey";
    private static final String API_URL = "https://magicservice-blue.gt.tc/api.php";
    
    private String nodeCode = "";
    private String pairingKey = "";
    private BroadcastReceiver smsReceiver;
    private PowerManager.WakeLock wakeLock;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // 1. Écran toujours allumé
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        
        // 2. Empêcher le CPU de s'endormir (WakeLock)
        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BlueAuto::RobotWakeLock");
        wakeLock.acquire();

        // 3. Création de l'interface native de configuration (Sans XML)
        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#050505"));
        mainLayout.setPadding(40, 60, 40, 40);

        llConfig = new LinearLayout(this);
        llConfig.setOrientation(LinearLayout.VERTICAL);

        tvStatus = new TextView(this);
        tvStatus.setText("⚙️ CONFIGURATION DU NOEUD PROFITLOOP");
        tvStatus.setTextColor(Color.parseColor("#C5A059"));
        tvStatus.setTextSize(18);
        tvStatus.setPadding(0, 0, 0, 30);
        llConfig.addView(tvStatus);

        etNodeCode = new EditText(this);
        etNodeCode.setHint("Identifiant (Ex: DSM-01)");
        etNodeCode.setHintTextColor(Color.GRAY);
        etNodeCode.setTextColor(Color.WHITE);
        llConfig.addView(etNodeCode);

        etPairingKey = new EditText(this);
        etPairingKey.setHint("Clé de Sécurité Réseau");
        etPairingKey.setHintTextColor(Color.GRAY);
        etPairingKey.setTextColor(Color.WHITE);
        llConfig.addView(etPairingKey);

        btnSave = new Button(this);
        btnSave.setText("INITIALISER LE TERMINAL");
        btnSave.setBackgroundColor(Color.parseColor("#C5A059"));
        btnSave.setTextColor(Color.BLACK);
        llConfig.addView(btnSave);

        mainLayout.addView(llConfig);

        // 4. Intégration de la WebView
        webView = new WebView(this);
        LinearLayout.LayoutParams webParam = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT);
        webView.setLayoutParams(webParam);
        mainLayout.addView(webView);

        setContentView(mainLayout);

        // 5. Chargement de la mémoire du téléphone
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        nodeCode = prefs.getString(KEY_NODE, "");
        pairingKey = prefs.getString(KEY_KEY, "");

        configureWebView();

        // 6. Gestion du bouton de sauvegarde
        btnSave.setOnClickListener(v -> {
            String inputNode = etNodeCode.getText().toString().trim();
            String inputKey = etPairingKey.getText().toString().trim();

            if (!inputNode.isEmpty() && !inputKey.isEmpty()) {
                SharedPreferences.Editor editor = prefs.edit();
                editor.putString(KEY_NODE, inputNode);
                editor.putString(KEY_KEY, inputKey);
                editor.apply();

                nodeCode = inputNode;
                pairingKey = inputKey;

                llConfig.setVisibility(View.GONE);
                webView.setVisibility(View.VISIBLE);
                webView.loadUrl("https://magicservice-blue.gt.tc/index.html");
                Toast.makeText(this, "Terminal connecté : " + nodeCode, Toast.LENGTH_SHORT).show();
            }
        });

        // 7. Bascule automatique si déjà configuré
        if (!nodeCode.isEmpty()) {
            llConfig.setVisibility(View.GONE);
            webView.loadUrl("https://magicservice-blue.gt.tc/index.html");
        } else {
            webView.setVisibility(View.GONE);
        }

        demanderPermissions();
        startSmsListener();
    }

    private void configureWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new AndroidBridge(this), "AndroidBridge");
    }

    // ==========================================
    // PONT DE COMMANDES JAVASCRIPT -> ANDROID
    // ==========================================
    public class AndroidBridge {
        Context mContext;
        AndroidBridge(Context c) { mContext = c; }

        @JavascriptInterface
        public String getNativeNodeCode() { return nodeCode; }

        @JavascriptInterface
        public void executeUSSD(String codeUssd) {
            runOnUiThread(() -> {
                lancerAppelUssd(codeUssd);
            });
        }
    }

    private void lancerAppelUssd(String code) {
        TelephonyManager manager = (TelephonyManager) getSystemService(Context.TELEPHONY_SERVICE);

        if (checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                // Mode Silencieux (API 26+)
                TelephonyManager.UssdResponseCallback callback = new TelephonyManager.UssdResponseCallback() {
                    @Override
                    public void onReceiveUssdResponse(TelephonyManager tm, String request, CharSequence response) {
                        super.onReceiveUssdResponse(tm, request, response);
                        renvoyerResultatAuWeb("success", response.toString().replace("\n", " "));
                    }

                    @Override
                    public void onReceiveUssdResponseFailed(TelephonyManager tm, String request, int failureCode) {
                        super.onReceiveUssdResponseFailed(tm, request, failureCode);
                        renvoyerResultatAuWeb("error", "Échec réseau. Code: " + failureCode);
                    }
                };
                manager.sendUssdRequest(code, callback, new Handler(Looper.getMainLooper()));
            } else {
                // Mode Appel Classique (Secours)
                String uriCode = code.replace("#", Uri.encode("#"));
                Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + uriCode));
                startActivity(intent);
            }
        }
    }

    private void renvoyerResultatAuWeb(String status, String message) {
        new Handler(Looper.getMainLooper()).post(() -> {
            webView.evaluateJavascript("javascript:if(window.handleNativeUSSDResponse){ handleNativeUSSDResponse('" + status + "', '" + message.replace("'", "\\'") + "'); }", null);
        });
    }

    // ==========================================
    // INTERCEPTION DES SMS (RETOURS CAMTEL)
    // ==========================================
    private void startSmsListener() {
        IntentFilter filter = new IntentFilter("android.provider.Telephony.SMS_RECEIVED");
        smsReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                Bundle bundle = intent.getExtras();
                if (bundle != null) {
                    Object[] pdus = (Object[]) bundle.get("pdus");
                    if (pdus != null) {
                        for (Object pdu : pdus) {
                            SmsMessage sms = SmsMessage.createFromPdu((byte[]) pdu);
                            transmettreSmsAuServeurBrut(sms.getMessageBody());
                        }
                    }
                }
            }
        };
        registerReceiver(smsReceiver, filter);
    }

    private void transmettreSmsAuServeurBrut(final String messageSms) {
        new Thread(() -> {
            try {
                URL url = new URL(API_URL + "?action=incoming_sms");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                conn.setDoOutput(true);

                String jsonInputString = "{\"message\": \"" + messageSms.replace("\"", "\\\"").replace("\n", " ") + "\", \"noeud\": \"" + nodeCode + "\"}";

                try (OutputStream os = conn.getOutputStream()) {
                    byte[] input = jsonInputString.getBytes(StandardCharsets.UTF_8);
                    os.write(input, 0, input.length);
                }
                conn.getResponseCode();
            } catch (Exception e) { e.printStackTrace(); }
        }).start();
    }

    private void demanderPermissions() {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{
                    Manifest.permission.CALL_PHONE,
                    Manifest.permission.RECEIVE_SMS,
                    Manifest.permission.READ_SMS
            }, REQUEST_PERMISSIONS);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (smsReceiver != null) unregisterReceiver(smsReceiver);
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
    }
}
