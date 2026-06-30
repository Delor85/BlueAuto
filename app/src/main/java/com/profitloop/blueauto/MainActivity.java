package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.view.View;
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
    private EditText etSimNumber, etPairingKey;
    private Spinner spDeviceMode;
    private Button btnSave;
    private TextView tvStatus;
    
    private static final int REQUEST_PERMISSIONS = 1;
    private static final String PREFS_NAME = "BlueAutoUnityPrefs";
    private static final String KEY_SIM = "SimNum";
    private static final String KEY_KEY = "PairKey";
    private static final String KEY_MODE = "DevMode"; // 0: Robot 24/7, 1: Télécommande, 2: Hybride

    private Handler pollingHandler = new Handler();
    private int currentMode = 1; 
    private String simNumber = "";
    private String pairingKey = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) { // <- FIX : Changé 'Bundle' en 'void'
        super.onCreate(savedInstanceState);

        // --- DESIGN TECH FUTURISTE LUXE NATIVE ---
        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#0B0C10"));

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(20, 15, 20, 15);
        panel.setBackgroundColor(Color.parseColor("#1F2833"));

        spDeviceMode = new Spinner(this);
        String[] modes = {"🤖 Mode : Robot Serveur 24/7 (SIM Bureau)", "📱 Mode : Télécommande Mobile (Voyage)", "🔄 Mode : Hybride (Tout-en-un / Unique)"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, modes);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spDeviceMode.setAdapter(adapter);

        LinearLayout rowFields = new LinearLayout(this);
        rowFields.setOrientation(LinearLayout.HORIZONTAL);
        rowFields.setPadding(0, 10, 0, 10);

        etSimNumber = new EditText(this);
        etSimNumber.setHint("N° SIM Ligne");
        etSimNumber.setHintTextColor(Color.parseColor("#888888"));
        etSimNumber.setTextColor(Color.WHITE);
        etSimNumber.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f));

        etPairingKey = new EditText(this);
        etPairingKey.setHint("Clé Sécurité");
        etPairingKey.setHintTextColor(Color.parseColor("#888888"));
        etPairingKey.setTextColor(Color.WHITE);
        etPairingKey.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f));

        btnSave = new Button(this);
        btnSave.setText("LIER");
        btnSave.setBackgroundColor(Color.parseColor("#C5A059")); 
        btnSave.setTextColor(Color.BLACK);

        rowFields.addView(etSimNumber);
        rowFields.addView(etPairingKey);
        rowFields.addView(btnSave);

        tvStatus = new TextView(this);
        tvStatus.setText("Liaison internet déconnectée.");
        tvStatus.setTextColor(Color.parseColor("#888888"));
        tvStatus.setTextSize(11);

        panel.addView(spDeviceMode);
        panel.addView(rowFields);
        panel.addView(tvStatus);
        mainLayout.addView(panel);

        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT));
        mainLayout.addView(webView);
        setContentView(mainLayout);

        // --- WEB ENGINE CONFIG ---
        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");

        // --- CHARGEMENT SYNCHRONISÉ DES CONFIGURATIONS ---
        final SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        simNumber = prefs.getString(KEY_SIM, "");
        pairingKey = prefs.getString(KEY_KEY, "");
        currentMode = prefs.getInt(KEY_MODE, 1);

        etSimNumber.setText(simNumber);
        etPairingKey.setText(pairingKey);
        spDeviceMode.setSelection(currentMode);

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
                simNumber = etSimNumber.getText().toString().trim();
                pairingKey = etPairingKey.getText().toString().trim();
                currentMode = spDeviceMode.getSelectedItemPosition();

                if(!simNumber.isEmpty() && !pairingKey.isEmpty()) {
                    prefs.edit().putString(KEY_SIM, simNumber).putString(KEY_KEY, pairingKey).putInt(KEY_MODE, currentMode).apply();
                    Toast.makeText(MainActivity.this, "Appareil synchronisé au réseau sécurisé.", Toast.LENGTH_SHORT).show();
                    actualiserAffichageMode(currentMode);
                } else {
                    Toast.makeText(MainActivity.this, "Remplissez tous les champs de liaison.", Toast.LENGTH_SHORT).show();
                }
            }
        });

        // Demande globale des droits matériels
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.READ_SMS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS}, REQUEST_PERMISSIONS);
        }

        pollingHandler.post(pollingRunnable);
    }

    private void actualiserAffichageMode(int mode) {
        if(mode == 0) { 
            webView.setVisibility(View.GONE); 
            tvStatus.setText("MOTEUR ACTIF : Écoute USSD & Analyse SMS en arrière-plan (24h/27 - Écran Veille)");
            tvStatus.setTextColor(Color.parseColor("#66FCF1")); 
        } else if(mode == 1) { 
            webView.setVisibility(View.VISIBLE);
            tvStatus.setText("CONNECTÉ : Mode Télécommande Mobile Sécurisée");
            tvStatus.setTextColor(Color.parseColor("#C5A059")); 
        } else { 
            webView.setVisibility(View.VISIBLE);
            tvStatus.setText("CONNECTÉ : Mode Hybride (Exécute ses propres ordres)");
            tvStatus.setTextColor(Color.WHITE);
        }
    }

    public class WebAppInterface {
        @JavascriptInterface
        public void executeUSSD(String ussdCode) {
            runOnUiThread(() -> {
                if (currentMode == 1) {
                    Toast.makeText(MainActivity.this, "Impossible : Vous êtes en mode Télécommande.", Toast.LENGTH_SHORT).show();
                } else {
                    lancerAppelUssd(ussdCode);
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
            if ((currentMode == 0 || currentMode == 2) && !simNumber.isEmpty() && !pairingKey.isEmpty()) {
                recupererOrdreDuServeurCloud();
            }
            pollingHandler.postDelayed(this, 4000);
        }
    };

    private void recupererOrdreDuServeurCloud() {
        new Thread(() -> {
            try {
                URL url = new URL("https://magicservice-blue.gt.tc/api.php?action=recuperer_ordres_robot&sim=" + simNumber + "&token=" + pairingKey);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("GET");
                if (conn.getResponseCode() == 200) {
                    BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder res = new StringBuilder();
                    String line;
                    while ((line = in.readLine()) != null) res.append(line);
                    in.close();

                    JSONObject json = new JSONObject(res.toString());
                    if (json.getBoolean("ordre_disponible")) {
                        final String ussd = json.getString("ussd");
                        runOnUiThread(() -> lancerAppelUssd(ussd));
                    }
                }
                conn.disconnect();
            } catch (Exception e) { e.printStackTrace(); }
        }).start();
    }

    public static void sendSmsToWeb(final String body) {
        new Thread(() -> {
            try {
                URL url = new URL("https://magicservice-blue.gt.tc/api.php?action=incoming_sms");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                conn.setDoOutput(true);

                // Échappement basique des guillemets pour le JSON string brut
                String safeBody = body.replace("\"", "\\\"");
                String jsonInputString = "{\"message\":\"" + safeBody + "\"}";

                try (OutputStream os = conn.getOutputStream()) { os.write(jsonInputString.getBytes("utf-8")); }
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception e) { e.printStackTrace(); }
        }).start();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack() && currentMode != 0) webView.goBack(); else super.onBackPressed();
    }
}
