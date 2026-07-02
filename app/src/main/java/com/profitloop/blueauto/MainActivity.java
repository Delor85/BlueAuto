package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
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

public class MainActivity extends Activity {

    private WebView webView;
    private PowerManager.WakeLock wakeLock;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // 1. GESTION DU WAKELOCK (Empêche le téléphone de s'endormir)
        PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
        wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BlueAuto::RobotWakeLock");
        wakeLock.acquire();

        // 2. CREATION DE LA WEBVIEW DYNAMIQUEMENT (Sans fichier XML)
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);

        // Injection du Pont Natif Android <-> Javascript
        webView.addJavascriptInterface(new AndroidBridge(this), "AndroidBridge");

        // Chargement de l'interface hébergée sur InfinityFree
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");

        // Vérification et demande des permissions
        demanderPermissions();
    }

    private void demanderPermissions() {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.READ_PHONE_STATE}, 1);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Libération de la batterie à la fermeture réelle de l'app
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
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

        @JavascriptInterface
        public String getNativeNodeCode() {
            return "ROBOT-MASTER-01"; // Identifiant du téléphone
        }

        @JavascriptInterface
        public void executeUSSD(String ussdCode) {
            TelephonyManager manager = (TelephonyManager) mContext.getSystemService(Context.TELEPHONY_SERVICE);

            if (mContext.checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
                
                // Exécution silencieuse sans pop-up
                if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                    
                    TelephonyManager.UssdResponseCallback callback = new TelephonyManager.UssdResponseCallback() {
                        @Override
                        public void onReceiveUssdResponse(TelephonyManager telephonyManager, String request, CharSequence response) {
                            super.onReceiveUssdResponse(telephonyManager, request, response);
                            String cleanResponse = response.toString().replace("\n", " ");
                            renvoyerResultatAuWeb("success", cleanResponse);
                        }

                        @Override
                        public void onReceiveUssdResponseFailed(TelephonyManager telephonyManager, String request, int failureCode) {
                            super.onReceiveUssdResponseFailed(telephonyManager, request, failureCode);
                            renvoyerResultatAuWeb("error", "Code d'erreur réseau : " + failureCode);
                        }
                    };

                    manager.sendUssdRequest(ussdCode, callback, new Handler(Looper.getMainLooper()));
                } else {
                    Toast.makeText(mContext, "Android 8.0 minimum requis", Toast.LENGTH_LONG).show();
                }
            }
        }

        private void renvoyerResultatAuWeb(String status, String message) {
            new Handler(Looper.getMainLooper()).post(() -> {
                webView.evaluateJavascript("javascript:handleNativeUSSDResponse('" + status + "', '" + message + "');", null);
            });
        }
    }
}
