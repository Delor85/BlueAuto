package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private WebView webView;
    private static final int REQUEST_CALL_PERMISSION = 1;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Création de la vue Web en plein écran
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);

        // Liaison : permet à la page Web d'envoyer des ordres USSD à Android
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        
        // Chargement du tableau de bord du serveur
        webView.loadUrl("https://magicservice-blue.gt.tc/bureau.html");

        // Demande de permission d'appel (Standard Android natif)
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE}, REQUEST_CALL_PERMISSION);
        }
    }

    // Le récepteur d'ordres USSD venant du Web
    public class WebAppInterface {
        MainActivity mContext;

        WebAppInterface(MainActivity c) {
            mContext = c;
        }

        @JavascriptInterface
        public void executeUSSD(final String ussdCode) {
            mContext.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (mContext.checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                        String encodedCode = Uri.encode(ussdCode);
                        Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + encodedCode));
                        mContext.startActivity(intent);
                        Toast.makeText(mContext, "Robot : Envoi USSD " + ussdCode, Toast.LENGTH_SHORT).show();
                    } else {
                        Toast.makeText(mContext, "Erreur : Permission refusée !", Toast.LENGTH_LONG).show();
                    }
                }
            });
        }
    }

    // ✨ RÉPARATION : La fonction réclamée par SmsReceiver.java
    // Elle intercepte les SMS reçus par la SIM et les pousse vers ton API
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

                    // Structuration propre du message reçu au format JSON
                    String safeBody = body.replace("\"", "\\\"");
                    String jsonInputString = "{\"action\":\"incoming_sms\",\"message\":\"" + safeBody + "\"}";

                    try (OutputStream os = conn.getOutputStream()) {
                        byte[] input = jsonInputString.getBytes("utf-8");
                        os.write(input, 0, input.length);
                    }
                    
                    // Déclenchement de la requête réseau
                    conn.getResponseCode();
                    conn.disconnect();
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }).start();
    }
}
