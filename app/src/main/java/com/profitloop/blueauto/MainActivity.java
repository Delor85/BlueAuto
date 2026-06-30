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
import android.telephony.SmsMessage;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private WebView webView;
    private EditText etNodeCode, etPairingKey;
    private Spinner spDeviceMode;
    private Button btnSave;
    private TextView tvStatus;
    
    private static final int REQUEST_PERMISSIONS = 1;
    private static final String PREFS_NAME = "BlueAutoStructuralPrefs";
    private static final String KEY_NODE = "NodeCode";
    private static final String KEY_KEY = "PairKey";
    private static final String KEY_MODE = "DevMode"; 

    // Simulation d'un navigateur réel pour contourner le pare-feu du serveur (Anti-403)
    private static final String USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36";

    private Handler pollingHandler = new Handler();
    private int currentMode = 2; 
    private String nodeCode = "";
    private String pairingKey = "";
    private BroadcastReceiver smsReceiver;

    public static String staticNodeCode = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#0B0C10"));

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(20, 15, 20, 15);
        panel.setBackgroundColor(Color.parseColor("#1F2833"));

        spDeviceMode = new Spinner(this);
        String[] modes = {"🤖 Mode : Robot Fixe (Exécuteur SIM)", "📱 Mode : Télécommande Mobile (À Distance)", "🔄 Mode : Hybride (Tout-en-un Local)"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, modes);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spDeviceMode.setAdapter(adapter);

        LinearLayout rowFields = new LinearLayout(this);
        rowFields.setOrientation(LinearLayout.HORIZONTAL);
        rowFields.setPadding(0, 10, 0, 10);

        etNodeCode = new EditText(this);
        etNodeCode.setHint("Ex: DSM-01/DAE-01");
        etNodeCode.setHintTextColor(Color.parseColor("#888888"));
        etNodeCode.setTextColor(Color.WHITE);
        etNodeCode.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.2f));

        etPairingKey = new EditText(this);
        etPairingKey.setHint("Clé");
        etPairingKey.setHintTextColor(Color.parseColor("#888888"));
        etPairingKey.setTextColor(Color.WHITE);
        etPairingKey.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f));

        btnSave = new Button(this);
        btnSave.setText("VALIDER");
        btnSave.setBackgroundColor(Color.parseColor("#C5A059")); 
        btnSave.setTextColor(Color.BLACK);

        rowFields.addView(etNodeCode);
        rowFields.addView(etPairingKey);
        rowFields.addView(btnSave);

        tvStatus = new TextView(this);
        tvStatus.setText("Structure réseau déconnectée.");
        tvStatus.setTextColor(Color.parseColor("#888888"));
        tvStatus.setTextSize(12);

        panel.addView(spDeviceMode);
        panel.addView(rowFields);
        panel.addView(tvStatus);
        mainLayout.addView(panel);

        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT));
        mainLayout.addView(webView);
        setContentView(mainLayout);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setUserAgentString(USER_AGENT); // Sécurité anti-403 aussi pour la WebView
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());

        final SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        nodeCode = prefs.getString(KEY_NODE, "");
        pairingKey = prefs.getString(KEY_KEY, "");
        currentMode = prefs.getInt(KEY_MODE, 2); 

        staticNodeCode = nodeCode;

        etNodeCode.setText(nodeCode);
        etPairingKey.setText(pairingKey);
        spDeviceMode.setSelection(currentMode);

        chargerPageWebAiguillee();
        actualiserAffichageMode(currentMode);

        spDeviceMode.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                actualiserAffichageMode(position);
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        btnSave.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                // Nettoyage strict de la saisie (suppression des espaces générés par l'autocomplétion ou retours à la ligne)
                nodeCode = etNodeCode.getText().toString().trim().replaceAll("\\s+", "");
                pairingKey = etPairingKey.getText().toString().trim().replaceAll("\\s+", "");
                currentMode = spDeviceMode.getSelectedItemPosition();

                if(!nodeCode.isEmpty() && !pairingKey.isEmpty()) {
                    staticNodeCode = nodeCode;
                    prefs.edit().putString(KEY_NODE, nodeCode).putString(KEY_KEY, pairingKey).putInt(KEY_MODE, currentMode).apply();
                    Toast.makeText(MainActivity.this, "Nœud enregistré et synchronisé.", Toast.LENGTH_SHORT).show();
                    chargerPageWebAiguillee();
                    actualiserAffichageMode(currentMode);
                } else {
                    Toast.makeText(MainActivity.this, "Veuillez remplir tous les champs.", Toast.LENGTH_SHORT).show();
                }
            }
        });

        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS}, REQUEST_PERMISSIONS);
        }

        startSmsListener();
        pollingHandler.post(pollingRunnable);
    }

    private void chargerPageWebAiguillee() {
        if (!nodeCode.isEmpty()) {
            webView.loadUrl("https://magicservice-blue.gt.tc/index.html?noeud=" + Uri.encode(nodeCode) + "&token=" + Uri.encode(pairingKey));
        } else {
            webView.loadUrl("https://magicservice-blue.gt.tc/index.html");
        }
    }

    private void actualiserAffichageMode(int mode) {
        if(mode == 0) { 
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            webView.setVisibility(View.GONE); 
            tvStatus.setText("🤖 ROBOT SYNC : Liaison réseau en cours...");
            tvStatus.setTextColor(Color.YELLOW);
        } else { 
            getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            webView.setVisibility(View.VISIBLE);
            tvStatus.setText("📱 HUB CONNECTÉ : Nœud " + (nodeCode.isEmpty() ? "aucun" : nodeCode));
            tvStatus.setTextColor(Color.GREEN);
        }
    }

    public class WebAppInterface {
        @JavascriptInterface
        public void executeUSSD(String ussdCode) {
            runOnUiThread(() -> {
                if (currentMode == 0 || currentMode == 2) {
                    lancerAppelUssd(ussdCode);
                } else {
                    Toast.makeText(MainActivity.this, "Routage via le Cloud...", Toast.LENGTH_SHORT).show();
                }
            });
        }
    }

    private void lancerAppelUssd(String code) {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + Uri.encode(code)));
            startActivity(intent);
        }
    }

    private final Runnable pollingRunnable = new Runnable() {
        @Override
        public void run() {
            if (currentMode == 0 && !nodeCode.isEmpty() && !pairingKey.isEmpty()) {
                interrogerServeurPourOrdre();
            }
            pollingHandler.postDelayed(this, 3000); 
        }
    };

    private void interrogerServeurPourOrdre() {
        new Thread(() -> {
            try {
                URL url = new URL("https://magicservice-blue.gt.tc/api.php?action=recuperer_ordres_robot&noeud=" + Uri.encode(nodeCode) + "&token=" + Uri.encode(pairingKey));
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(6000);
                
                // INJECTION DU USER AGENT POUR ADAPTER LE PASSAGE AU PARE-FEU SERVEUR
                conn.setRequestProperty("User-Agent", USER_AGENT);
                
                int responseCode = conn.getResponseCode();
                if (responseCode == 200) {
                    BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder res = new StringBuilder();
                    String line;
                    while ((line = in.readLine()) != null) res.append(line);
                    in.close();

                    JSONObject json = new JSONObject(res.toString());
                    runOnUiThread(() -> {
                        tvStatus.setText("🤖 ROBOT ACTIF ● CLOUD SYNCHRONISÉ (" + nodeCode + ")");
                        tvStatus.setTextColor(Color.parseColor("#66FCF1"));
                    });

                    if (json.has("ordre_disponible") && json.getBoolean("ordre_disponible")) {
                        final String ussd = json.getString("ussd");
                        runOnUiThread(() -> lancerAppelUssd(ussd));
                    }
                } else {
                    runOnUiThread(() -> {
                        tvStatus.setText("❌ ERREUR SERVEUR : Code " + responseCode + " (Vérifie l'API)");
                        tvStatus.setTextColor(Color.RED);
                    });
                }
                conn.disconnect();
            } catch (final Exception e) {
                runOnUiThread(() -> {
                    tvStatus.setText("❌ PANNE DE LIAISON INTERNET : " + e.getMessage());
                    tvStatus.setTextColor(Color.RED);
                });
            }
        }).start();
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
                            sendSmsToWeb(sms.getMessageBody(), nodeCode);
                        }
                    }
                }
            }
        };
        registerReceiver(smsReceiver, filter);
    }

    public static void sendSmsToWeb(final String body) {
        sendSmsToWeb(body, staticNodeCode);
    }

    public static void sendSmsToWeb(final String body, final String currentEncodingNode) {
        new Thread(() -> {
            try {
                URL url = new URL("https://magicservice-blue.gt.tc/api.php?action=incoming_sms");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                conn.setRequestProperty("User-Agent", USER_AGENT); // Protection pare-feu
                conn.setDoOutput(true);

                JSONObject payload = new JSONObject();
                payload.put("message", body);
                payload.put("noeud", currentEncodingNode);

                try (OutputStream os = conn.getOutputStream()) { os.write(payload.toString().getBytes("utf-8")); }
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception e) { e.printStackTrace(); }
        }).start();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (smsReceiver != null) unregisterReceiver(smsReceiver);
    }
}
