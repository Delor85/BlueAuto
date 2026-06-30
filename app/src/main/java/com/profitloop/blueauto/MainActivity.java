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
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.CompoundButton;
import android.widget.EditText;
import android.widget.LinearLayout;
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
    private EditText etSimNumber;
    private CheckBox cbRobotMode;
    private Button btnSave;
    private TextView tvStatus;
    
    private static final int REQUEST_CALL_PERMISSION = 1;
    private static final String PREFS_NAME = "BlueAutoHubPrefs";
    private static final String KEY_SIM_NUMBER = "LocalSimNumber";
    private static final String KEY_ROBOT_ACTIVE = "IsRobotActive";

    private Handler pollingHandler = new Handler();
    private boolean isRobotEnabled = false;
    private String configuredSim = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // --- INTERFACE GRAPHIQUE HYBRIDE SOMBRE ---
        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#0B0C10"));

        // Panneau de configuration supérieur (Compact)
        LinearLayout configPanel = new LinearLayout(this);
        configPanel.setOrientation(LinearLayout.VERTICAL);
        configPanel.setPadding(20, 15, 20, 15);
        configPanel.setBackgroundColor(Color.parseColor("#1F2833"));

        cbRobotMode = new CheckBox(this);
        cbRobotMode.setText("Activer le mode Robot (SIM locale dans ce téléphone)");
        cbRobotMode.setTextColor(Color.parseColor("#66FCF1"));
        
        LinearLayout rowLayout = new LinearLayout(this);
        rowLayout.setOrientation(LinearLayout.HORIZONTAL);
        rowLayout.setVisibility(View.GONE);

        etSimNumber = new EditText(this);
        etSimNumber.setHint("Numéro de la SIM (ex: 620550255)");
        etSimNumber.setHintTextColor(Color.parseColor("#888888"));
        etSimNumber.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
        etSimNumber.setLayoutParams(lp);

        btnSave = new Button(this);
        btnSave.setText("OK");
        btnSave.setBackgroundColor(Color.parseColor("#C5A059"));
        btnSave.setTextColor(Color.BLACK);

        rowLayout.addView(etSimNumber);
        rowLayout.addView(btnSave);

        tvStatus = new TextView(this);
        tvStatus.setText("Statut : Mode Dashboard pur");
        tvStatus.setTextColor(Color.parseColor("#888888"));
        tvStatus.setTextSize(11);
        tvStatus.setPadding(0, 5, 0, 0);

        configPanel.addView(cbRobotMode);
        configPanel.addView(rowLayout);
        configPanel.addView(tvStatus);
        mainLayout.addView(configPanel);

        // Zone d'affichage du Dashboard Web
        webView = new WebView(this);
        LinearLayout.LayoutParams webParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT);
        webView.setLayoutParams(webParams);
        mainLayout.addView(webView);

        setContentView(mainLayout);

        // --- OPTIMISATION DU MOTEUR WEB ---
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webView.setWebViewClient(new WebViewClient());
        
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");

        // --- GESTION DE LA MÉMOIRE ---
        final SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        configuredSim = prefs.getString(KEY_SIM_NUMBER, "");
        isRobotEnabled = prefs.getBoolean(KEY_ROBOT_ACTIVE, false);

        if (!configuredSim.isEmpty()) {
            etSimNumber.setText(configuredSim);
        }
        cbRobotMode.setChecked(isRobotEnabled);
        rowLayout.setVisibility(isRobotEnabled ? View.VISIBLE : View.GONE);

        cbRobotMode.setOnCheckedChangeListener(new CompoundButton.OnCheckedChangeListener() {
            @Override
            public void onCheckedChanged(CompoundButton buttonView, boolean isChecked) {
                rowLayout.setVisibility(isChecked ? View.VISIBLE : View.GONE);
                if(!isChecked) {
                    isRobotEnabled = false;
                    prefs.edit().putBoolean(KEY_ROBOT_ACTIVE, false).apply();
                    tvStatus.setText("Statut : Mode Dashboard pur");
                    tvStatus.setTextColor(Color.parseColor("#888888"));
                }
            }
        });

        btnSave.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String num = etSimNumber.getText().toString().trim();
                if (!num.isEmpty()) {
                    configuredSim = num;
                    isRobotEnabled = true;
                    prefs.edit().putString(KEY_SIM_NUMBER, num).putBoolean(KEY_ROBOT_ACTIVE, true).apply();
                    Toast.makeText(MainActivity.this, "Configuration Sauvegardée", Toast.LENGTH_SHORT).show();
                    tvStatus.setText("Statut : Robot actif sur la SIM [" + num + "] (Arrière-plan)");
                    tvStatus.setTextColor(Color.parseColor("#66FCF1"));
                }
            }
        });

        if (isRobotEnabled && !configuredSim.isEmpty()) {
            tvStatus.setText("Statut : Robot actif sur la SIM [" + configuredSim + "] (Arrière-plan)");
            tvStatus.setTextColor(Color.parseColor("#66FCF1"));
        }

        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE}, REQUEST_CALL_PERMISSION);
        }

        pollingHandler.post(pollingRunnable);
    }

    // --- MOTEUR DE FOND : VÉRIFICATION NATIVE USSD ---
    private final Runnable pollingRunnable = new Runnable() {
        @Override
        public void run() {
            if (isRobotEnabled && !configuredSim.isEmpty()) {
                verifierOrdresServeur(configuredSim);
            }
            pollingHandler.postDelayed(this, 4000);
        }
    };

    private void verifierOrdresServeur(final String sim) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL("https://magicservice-blue.gt.tc/api.php?action=recuperer_ordres_robot&sim=" + sim);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    
                    if (conn.getResponseCode() == 200) {
                        BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                        StringBuilder response = new StringBuilder();
                        String line;
                        while ((line = in.readLine()) != null) { response.append(line); }
                        in.close();

                        JSONObject json = new JSONObject(response.toString());
                        if (json.getBoolean("ordre_disponible")) {
                            final String ussd = json.getString("ussd");
                            
                            runOnUiThread(new Runnable() {
                                @Override
                                public void run() {
                                    if (checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                                        Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + Uri.encode(ussd)));
                                        startActivity(intent);
                                    }
                                }
                            });
                        }
                    }
                    conn.disconnect();
                } catch (Exception e) { e.printStackTrace(); }
            }
        }).start();
    }

    // --- INTERCEPTION ET ENVOI DES SMS AU BACKEND (LA MÉTHODE RECORRIGÉE) ---
    public static void sendSmsToWeb(final String body) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL("https://magicservice-blue.gt.tc/api.php?action=incoming_sms");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                    conn.setDoOutput(true);
                    
                    String safeBody = body.replace("\"", "\\\"");
                    String jsonInputString = "{\"message\":\"" + safeBody + "\"}";
                    
                    try (OutputStream os = conn.getOutputStream()) {
                        os.write(jsonInputString.getBytes("utf-8"));
                    }
                    conn.getResponseCode();
                    conn.disconnect();
                } catch (Exception e) { e.printStackTrace(); }
            }
        }).start();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) { webView.goBack(); } else { super.onBackPressed(); }
    }
}
