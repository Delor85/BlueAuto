package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.telephony.TelephonyManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        // Activation du pont entre le Web et le matériel
        webView.getSettings().setJavaScriptEnabled(true);
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
        
        // Chargement de ta plateforme
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");

        // Vérification des permissions critiques au démarrage
        demanderPermissions();
    }

    // Le PONT : Permet au JavaScript de ton site d'appeler le téléphone
    public class AndroidBridge {
        @JavascriptInterface
        public void executeUSSD(final String ussdCode) {
            runOnUiThread(() -> {
                TelephonyManager tm = (TelephonyManager) getSystemService(TELEPHONY_SERVICE);
                try {
                    tm.sendUssdRequest(ussdCode, new TelephonyManager.UssdResponseCallback() {
                        @Override
                        public void onReceiveUssdResponse(TelephonyManager tm, String request, CharSequence response) {
                            // On renvoie le résultat du USSD vers le JavaScript pour traitement
                            webView.evaluateJavascript("window.onUssdResult('" + response.toString() + "')", null);
                        }
                        @Override
                        public void onReceiveUssdResponseFailed(TelephonyManager tm, String request, int failureCode) {
                            webView.evaluateJavascript("window.onUssdError('Echec code: " + failureCode + "')", null);
                        }
                    }, new Handler(Looper.getMainLooper()));
                } catch (SecurityException e) {
                    Toast.makeText(MainActivity.this, "Erreur permission", Toast.LENGTH_SHORT).show();
                }
            });
        }
    }

    private void demanderPermissions() {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE}, 1);
        }
    }
}
