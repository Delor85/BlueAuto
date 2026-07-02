package com.profitloop.blueauto;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.telephony.TelephonyManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private PowerManager.WakeLock wakeLock;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        // 1. GESTION DU WAKELOCK (Empêche le téléphone de dormir)
        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BlueAuto::RobotWakeLock");
        wakeLock.acquire(); // Maintient le processeur actif

        // 2. CONFIGURATION DE LA WEBVIEW
        webView = findViewById(R.id.webview);
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);

        // Injection du Pont Natif
        webView.addJavascriptInterface(new AndroidBridge(this), "AndroidBridge");

        // Chargement de l'interface PWA
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");

        // Demande des permissions au démarrage
        demanderPermissions();
    }

    private void demanderPermissions() {
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED ||
            ActivityCompat.checkSelfPermission(this, Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.READ_PHONE_STATE}, 1);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release(); // Libère la batterie quand on ferme vraiment l'app
        }
    }

    // =========================================================================
    // LE PONT JAVASCRIPT -> ANDROID NATIF
    // =========================================================================
    public class AndroidBridge {
        Context mContext;

        AndroidBridge(Context c) {
            mContext = c;
        }

        // Retourne un ID unique pour ce Robot (à configurer manuellement ou générer)
        @JavascriptInterface
        public String getNativeNodeCode() {
            return "ROBOT-MASTER-01"; // À dynamiser selon tes besoins
        }

        // Fonction appelée par uusdEngine.js
        @JavascriptInterface
        public void executeUSSD(String ussdCode) {
            TelephonyManager manager = (TelephonyManager) mContext.getSystemService(Context.TELEPHONY_SERVICE);

            if (ActivityCompat.checkSelfPermission(mContext, Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                
                // Exécution silencieuse (Nécessite Android 8 / API 26 minimum)
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    
                    TelephonyManager.UssdResponseCallback callback = new TelephonyManager.UssdResponseCallback() {
                        @Override
                        public void onReceiveUssdResponse(TelephonyManager telephonyManager, String request, CharSequence response) {
                            super.onReceiveUssdResponse(telephonyManager, request, response);
                            // Le réseau a répondu, on renvoie la réponse au Javascript
                            String cleanResponse = response.toString().replace("\n", " ");
                            renvoyerResultatAuWeb("success", cleanResponse);
                        }

                        @Override
                        public void onReceiveUssdResponseFailed(TelephonyManager telephonyManager, String request, int failureCode) {
                            super.onReceiveUssdResponseFailed(telephonyManager, request, failureCode);
                            // Erreur réseau ou code PIN
                            renvoyerResultatAuWeb("error", "Code d'erreur réseau : " + failureCode);
                        }
                    };

                    // Lancement de l'USSD en arrière-plan
                    manager.sendUssdRequest(ussdCode, callback, new Handler(Looper.getMainLooper()));
                } else {
                    // Fallback pour les très vieux téléphones (non recommandé pour ce projet)
                    Toast.makeText(mContext, "Android 8.0 minimum requis pour le mode silencieux", Toast.LENGTH_LONG).show();
                }
            }
        }

        // Permet d'exécuter du JS depuis Java pour mettre à jour l'interface
        private void renvoyerResultatAuWeb(String status, String message) {
            new Handler(Looper.getMainLooper()).post(() -> {
                // Appelle une fonction JS dans ton index.html/ussdEngine.js
                webView.evaluateJavascript("javascript:handleNativeUSSDResponse('" + status + "', '" + message + "');", null);
            });
        }
    }
}
