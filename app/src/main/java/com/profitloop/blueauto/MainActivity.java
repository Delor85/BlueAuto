package com.profitloop.blueauto;

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
