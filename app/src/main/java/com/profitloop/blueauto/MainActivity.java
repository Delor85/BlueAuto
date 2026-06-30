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
        
        // Création et configuration plein écran de la vue Web
        webView = new WebView(this);
        setContentView(webView);

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);

        // Liaison sacrée : permet à la page Web d'envoyer des ordres à Android
        webView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());
        
        // Chargement direct de la page de contrôle du bureau
        webView.loadUrl("https://magicservice-blue.gt.tc/bureau.html");

        // Vérification et demande automatique de la permission d'appel au démarrage
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
                        // Encodage propre du caractère # pour éviter les blocages Android
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
}package com.profitloop.blueauto;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

public class MainActivity extends Activity {
    private static WebView myWebView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        myWebView = new WebView(this);
        myWebView.getSettings().setJavaScriptEnabled(true);
        myWebView.getSettings().setDomStorageEnabled(true);
        
        // Sécurité du pont Android/PWA
        myWebView.addJavascriptInterface(new WebAppInterface(this), "AndroidBridge");
        
        myWebView.setWebViewClient(new WebViewClient());
        
        // METS TON LIEN INFINITYFREE ICI EN BAS :
        myWebView.loadUrl("https://magicservice-blue.gt.tc");
        
        setContentView(myWebView);
    }

    public static void sendSmsToWeb(String message) {
        if (myWebView != null) {
            myWebView.post(() -> myWebView.loadUrl("javascript:if(window.handleAndroidSms){ window.handleAndroidSms('" + message.replace("'", "\\'") + "'); }"));
        }
    }
}

class WebAppInterface {
    Context mContext;

    WebAppInterface(Context c) {
        mContext = c;
    }

    @JavascriptInterface
    public void executeUssd(String code) {
        Toast.makeText(mContext, "Exécution USSD : " + code, Toast.LENGTH_SHORT).show();
        String encodedCode = Uri.encode(code);
        Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + encodedCode));
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        mContext.startActivity(intent);
    }
}
