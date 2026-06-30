package com.profitloop.blueauto;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private static final int REQUEST_CALL_PERMISSION = 1;

    @Override
    protected Bundle onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // Création et configuration de la vue Web
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);

        // Liaison : permet à la page Web d'envoyer des ordres USSD à Android
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        
        // Chargement de la page de contrôle du serveur
        webView.loadUrl("https://magicservice-blue.gt.tc/bureau.html");

        // Demande automatique de la permission d'appel au démarrage
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CALL_PHONE}, REQUEST_CALL_PERMISSION);
        }
    }

    // Le récepteur d'ordres
    public class WebAppInterface {
        MainActivity mContext;

        WebAppInterface(MainActivity c) {
            mContext = c;
        }

        @JavascriptInterface
        public void executeUSSD(String ussdCode) {
            mContext.runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (ContextCompat.checkSelfPermission(mContext, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                        // Encodage propre du caractère # pour les appels directs
                        String encodedCode = Uri.encode(ussdCode);
                        Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + encodedCode));
                        mContext.startActivity(intent);
                        Toast.makeText(mContext, "Robot : Envoi USSD " + ussdCode, Toast.LENGTH_SHORT).show();
                    } else {
                        Toast.makeText(mContext, "Erreur : Permission d'appel refusée !", Toast.LENGTH_LONG).show();
                    }
                }
            });
        }
    }
}
