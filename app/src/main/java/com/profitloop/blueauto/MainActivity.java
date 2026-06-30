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
import android.telephony.SmsMessage;
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
    private static final String API_URL = "https://votre-serveur.com/api.php"; // À remplacer par votre URL de production

    private String nodeCode = "";
    private String pairingKey = "";
    private BroadcastReceiver smsReceiver;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        // UI Android Native de Secours / Configuration Initiale
        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#0B0C10"));
        mainLayout.setPadding(30, 30, 30, 30);

        llConfig = new LinearLayout(this);
        llConfig.setOrientation(LinearLayout.VERTICAL);

        tvStatus = new TextView(this);
        tvStatus.setText("⚙️ CONFIGURATION DU NOEUD PROFITLOOP");
        tvStatus.setTextColor(Color.parseColor("#C5A059"));
        tvStatus.setTextSize(16);
        llConfig.addView(tvStatus);

        etNodeCode = new EditText(this);
        etNodeCode.setHint("Code Nœud (Ex: POS-001/DSM-01/DAE-01)");
        etNodeCode.setHintTextColor(Color.GRAY);
        etNodeCode.setTextColor(Color.WHITE);
        llConfig.addView(etNodeCode);

        etPairingKey = new EditText(this);
        etPairingKey.setHint("Clé de Sécurité Réseau");
        etPairingKey.setHintTextColor(Color.GRAY);
        etPairingKey.setTextColor(Color.WHITE);
        llConfig.addView(etPairingKey);

        btnSave = new Button(this);
        btnSave.setText("VALIDER ET INITIALISER LE TERMINAL");
        btnSave.setBackgroundColor(Color.parseColor("#C5A059"));
        btnSave.setTextColor(Color.BLACK);
        llConfig.addView(btnSave);

        mainLayout.addView(llConfig);

        // Configuration de la WebView principale
        webView = new WebView(this);
        LinearLayout.LayoutParams webParam = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT);
        webView.setLayoutParams(webParam);
        mainLayout.addView(webView);

        setContentView(mainLayout);

        // Chargement des préférences mémorisées
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        nodeCode = prefs.getString(KEY_NODE, "");
        pairingKey = prefs.getString(KEY_KEY, "");

        configureWebView();

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
                webView.loadUrl("https://votre-serveur.com/index.html");
                Toast.makeText(this, "Terminal rattaché avec succès.", Toast.LENGTH_SHORT).show();
            }
        });

        if (!nodeCode.isEmpty()) {
            llConfig.setVisibility(View.GONE);
            webView.loadUrl("https://votre-serveur.com/index.html");
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
        // Injection du Pont JavaScript sécurisé
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
    }

    // PONT JAVASCRIPT : Permet à l'interface HTML/JS d'interagir avec le matériel
    public class AndroidBridge {
        @JavascriptInterface
        public String getNativeNodeCode() { return nodeCode; }

        @JavascriptInterface
        public String getNativePairKey() { return pairingKey; }

        @JavascriptInterface
        public void executeUSSD(String codeUssd) {
            runOnUiThread(() -> {
                Toast.makeText(MainActivity.this, "Exécution USSD : " + codeUssd, Toast.LENGTH_LONG).show();
                lancerAppelUssd(codeUssd);
            });
        }
    }

    private void lancerAppelUssd(String code) {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            // Remplacement du # de fin par son équivalent encodé pour l'URI Android
            String uriCode = code.replace("#", Uri.encode("#"));
            Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + uriCode));
            startActivity(intent);
        }
    }

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
                            String body = sms.getMessageBody();
                            // Routage asynchrone immédiat du SMS reçu vers le serveur central
                            transmettreSmsAuServeurBrut(body);
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

                String jsonInputString = "{\"message\": \"" + messageSms.replace("\"", "\\\"") + "\", \"noeud\": \"" + nodeCode + "\"}";

                try (OutputStream os = conn.getOutputStream()) {
                    byte[] input = jsonInputString.getBytes(StandardCharsets.UTF_8);
                    os.write(input, 0, input.length);
                }
                conn.getResponseCode(); // Valide l'envoi
            } catch (Exception e) {
                e.printStackTrace();
            }
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
    }
}
