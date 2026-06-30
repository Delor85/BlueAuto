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
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Toast;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private WebView webView;
    private EditText etSimNumber;
    private Button btnSaveSim;
    private static final int REQUEST_CALL_PERMISSION = 1;
    private static final String PREFS_NAME = "BlueAutoPrefs";
    private static final String KEY_SIM_NUMBER = "SimNumber";

    @Override
    protected Bundle onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Layout Principal Premium Sombre
        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#0B0C10"));

        // Barre de configuration horizontale
        LinearLayout configLayout = new LinearLayout(this);
        configLayout.setOrientation(LinearLayout.HORIZONTAL);
        configLayout.setPadding(20, 20, 20, 20);
        configLayout.setBackgroundColor(Color.parseColor("#1F2833"));

        etSimNumber = new EditText(this);
        etSimNumber.setHint("N° de cette SIM (ex: 620550255)");
        etSimNumber.setHintTextColor(Color.parseColor("#888888"));
        etSimNumber.setTextColor(Color.WHITE);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f);
        etSimNumber.setLayoutParams(lp);

        btnSaveSim = new Button(this);
        btnSaveSim.setText("SAUVEGARDER");
        btnSaveSim.setBackgroundColor(Color.parseColor("#C5A059")); // Accent Or
        btnSaveSim.setTextColor(Color.BLACK);

        configLayout.addView(etSimNumber);
        configLayout.addView(btnSaveSim);
        mainLayout.addView(configLayout);

        // WebView de l'infrastructure
        webView = new WebView(this);
        LinearLayout.LayoutParams webViewParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT);
        webView.setLayoutParams(webViewParams);
        webView.setBackgroundColor(Color.parseColor("#0B0C10"));
        mainLayout.addView(webView);

        setContentView(mainLayout);

        // Moteur Web
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());

        // Chargement mémoire
        final SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String savedSim = prefs.getString(KEY_SIM_NUMBER, "");
        if (!savedSim.isEmpty()) {
            etSimNumber.setText(savedSim);
            chargerRobot(savedSim);
        }

        btnSaveSim.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String num = etSimNumber.getText().toString().trim();
                if(!num.isEmpty()) {
                    prefs.edit().putString(KEY_SIM_NUMBER, num).apply();
                    Toast.makeText(MainActivity.this, "SIM Enregistrée : " + num, Toast.LENGTH_SHORT).show();
                    chargerRobot(num);
                } else {
                    Toast.makeText(MainActivity.this, "Entrez un numéro", Toast.LENGTH_SHORT).show();
                }
            }
        });

        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE}, REQUEST_CALL_PERMISSION);
        }
    }

    private void chargerRobot(String simNumber) {
        webView.loadUrl("https://magicservice-blue.gt.tc/bureau.html?sim=" + simNumber);
    }

    public class WebAppInterface {
        MainActivity mContext;
        WebAppInterface(MainActivity c) { mContext = c; }

        @JavascriptInterface
        public void executeUSSD(final String ussdCode) {
            mContext.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (mContext.checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                        String encodedCode = Uri.encode(ussdCode);
                        Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + encodedCode));
                        mContext.startActivity(intent);
                    }
                }
            });
        }
    }

    public static void sendSmsToWeb(final String body) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    URL url = new URL("https://magicservice-blue.gt.tc/api.php");
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                    conn.setDoOutput(true);
                    String safeBody = body.replace("\"", "\\\"");
                    String jsonInputString = "{\"action\":\"incoming_sms\",\"message\":\"" + safeBody + "\"}";
                    try (OutputStream os = conn.getOutputStream()) {
                        os.write(jsonInputString.getBytes("utf-8"));
                    }
                    conn.getResponseCode();
                    conn.disconnect();
                } catch (Exception e) { e.printStackTrace(); }
            }
        }).start();
    }
}
