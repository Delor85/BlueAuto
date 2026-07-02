package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.telephony.TelephonyManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);

        // Pont entre le code Web (JS) et la puce SIM (Java)
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");
        
        demanderPermissions();
    }

    public class AndroidBridge {
        @JavascriptInterface
        public void executeUSSD(final String ussdCode) {
            runOnUiThread(() -> {
                TelephonyManager tm = (TelephonyManager) getSystemService(TELEPHONY_SERVICE);
                try {
                    tm.sendUssdRequest(ussdCode, new TelephonyManager.UssdResponseCallback() {
                        @Override
                        public void onReceiveUssdResponse(TelephonyManager tm, String request, CharSequence response) {
                            webView.post(() -> webView.evaluateJavascript("window.handleNativeUSSDResponse('success', '" + response.toString() + "')", null));
                        }
                        @Override
                        public void onReceiveUssdResponseFailed(TelephonyManager tm, String request, int failureCode) {
                            webView.post(() -> webView.evaluateJavascript("window.handleNativeUSSDResponse('error', 'Code: " + failureCode + "')", null));
                        }
                    }, new Handler(Looper.getMainLooper()));
                } catch (SecurityException e) {
                    Toast.makeText(MainActivity.this, "Erreur de permission", Toast.LENGTH_SHORT).show();
                }
            });
        }
    }

    private void demanderPermissions() {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS}, 1);
        }
    }
}package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.telephony.TelephonyManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;
    private String nodeCode = "DSM-ROBOT-01"; // À lier à tes SharedPreferences existantes

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        
        // --- Intégration du Pont Robotique ---
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");
        
        demanderPermissions();
    }

    public class AndroidBridge {
        @JavascriptInterface
        public String getNativeNodeCode() { return nodeCode; }

        @JavascriptInterface
        public void executeUSSD(final String ussdCode) {
            runOnUiThread(() -> {
                TelephonyManager tm = (TelephonyManager) getSystemService(TELEPHONY_SERVICE);
                try {
                    // Exécution silencieuse native (API 26+)
                    tm.sendUssdRequest(ussdCode, new TelephonyManager.UssdResponseCallback() {
                        @Override
                        public void onReceiveUssdResponse(TelephonyManager tm, String request, CharSequence response) {
                            webView.post(() -> webView.evaluateJavascript("window.handleNativeUSSDResponse('success', '" + response.toString() + "')", null));
                        }
                        @Override
                        public void onReceiveUssdResponseFailed(TelephonyManager tm, String request, int failureCode) {
                            webView.post(() -> webView.evaluateJavascript("window.handleNativeUSSDResponse('error', 'Code erreur: " + failureCode + "')", null));
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
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.RECEIVE_SMS, Manifest.permission.READ_SMS}, 1);
        }
    }
}package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.telephony.TelephonyManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        
        // On injecte le pont JavaScript
        webView.addJavascriptInterface(new AndroidBridge(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        
        // Chargement de ta plateforme
        webView.loadUrl("https://magicservice-blue.gt.tc/index.html");

        // Demande les permissions au démarrage
        demanderPermissions();
    }

    // --- LE PONT (BRIDGE) : Ce qui permet au Web de parler à la SIM ---
    public class AndroidBridge {
        @JavascriptInterface
        public String getNativeNodeCode() {
            // Ici tu peux renvoyer un ID unique basé sur l'IMEI du tel si besoin
            return "DSM-ROBOT-01"; 
        }

        @JavascriptInterface
        public void executeUSSD(final String ussdCode) {
            runOnUiThread(() -> {
                TelephonyManager tm = (TelephonyManager) getSystemService(TELEPHONY_SERVICE);
                try {
                    tm.sendUssdRequest(ussdCode, new TelephonyManager.UssdResponseCallback() {
                        @Override
                        public void onReceiveUssdResponse(TelephonyManager tm, String request, CharSequence response) {
                            // Envoie la réponse au JavaScript
                            webView.post(() -> webView.evaluateJavascript("window.handleNativeUSSDResponse('success', '" + response.toString() + "')", null));
                        }
                        @Override
                        public void onReceiveUssdResponseFailed(TelephonyManager tm, String request, int failureCode) {
                            webView.post(() -> webView.evaluateJavascript("window.handleNativeUSSDResponse('error', 'Code erreur: " + failureCode + "')", null));
                        }
                    }, new Handler(Looper.getMainLooper()));
                } catch (SecurityException e) {
                    Toast.makeText(MainActivity.this, "Permission manquante", Toast.LENGTH_SHORT).show();
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
