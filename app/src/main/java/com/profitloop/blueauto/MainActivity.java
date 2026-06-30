package com.profitloop.blueauto;

import android.Manifest;
import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private WebView webView;
    private EditText etNodeCode, etPairingKey;
    private Spinner spDeviceMode;
    private Button btnSave;
    private TextView tvStatus;
    
    private static final int REQUEST_PERMISSIONS = 1;
    private static final String PREFS_NAME = "BlueAutoStructuralPrefs";
    private static final String KEY_NODE = "NodeCode";
    private static final String KEY_KEY = "PairKey";
    private static final String KEY_MODE = "DevMode"; 

    private int currentMode = 2; 
    private String nodeCode = "";
    private String pairingKey = "";
    private BroadcastReceiver smsReceiver;

    public static String staticNodeCode = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        LinearLayout mainLayout = new LinearLayout(this);
        mainLayout.setOrientation(LinearLayout.VERTICAL);
        mainLayout.setBackgroundColor(Color.parseColor("#0B0C10"));

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(20, 15, 20, 15);
        panel.setBackgroundColor(Color.parseColor("#1F2833"));

        spDeviceMode = new Spinner(this);
        String[] modes = {"🤖 Mode : Robot Fixe (Exécuteur SIM)", "📱 Mode : Télécommande Mobile (À Distance)", "🔄 Mode : Hybride (Tout-en-un Local)"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this, android.R.layout.simple_spinner_item, modes);
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spDeviceMode.setAdapter(adapter);

        LinearLayout rowFields = new LinearLayout(this);
        rowFields.setOrientation(LinearLayout.HORIZONTAL);
        rowFields.setPadding(0, 10, 0, 10);

        etNodeCode = new EditText(this);
        etNodeCode.setHint("Ex: DSM-01/DAE-01");
        etNodeCode.setHintTextColor(Color.parseColor("#888888"));
        etNodeCode.setTextColor(Color.WHITE);
        etNodeCode.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.2f));

        etPairingKey = new EditText(this);
        etPairingKey.setHint("Clé");
        etPairingKey.setHintTextColor(Color.parseColor("#888888"));
        etPairingKey.setTextColor(Color.WHITE);
        etPairingKey.setLayoutParams(new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.0f));

        btnSave = new Button(this);
        btnSave.setText("VALIDER");
        btnSave.setBackgroundColor(Color.parseColor("#C5A059")); 
        btnSave.setTextColor(Color.BLACK);

        rowFields.addView(etNodeCode);
        rowFields.addView(etPairingKey);
        rowFields.addView(btnSave);

        tvStatus = new TextView(this);
        tvStatus.setText("Liaison de l'infrastructure...");
        tvStatus.setTextColor(Color.parseColor("#888888"));
        tvStatus.setTextSize(12);

        panel.addView(spDeviceMode);
        panel.addView(rowFields);
        panel.addView(tvStatus);
        mainLayout.addView(panel);

        webView = new WebView(this);
        webView.setLayoutParams(new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.MATCH_PARENT));
        mainLayout.addView(webView);
        setContentView(mainLayout);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        
        // On force l'identification du navigateur pour écraser les barrières de sécurité
        ws.setUserAgentString("Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36");
        
        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient());

        final SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        nodeCode = prefs.getString(KEY_NODE, "");
        pairingKey = prefs.getString(KEY_KEY, "");
        currentMode = prefs.getInt(KEY_MODE, 2); 

        staticNodeCode = nodeCode;

        etNodeCode.setText(nodeCode);
        etPairingKey.setText(pairingKey);
        spDeviceMode.setSelection(currentMode);

        chargerPageWebAiguillee();

        spDeviceMode.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) {
                if (position == 0) {
                    getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                } else {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                }
                tvStatus.setText("Configuration : Mode sélectionné appliqué.");
            }
            @Override
            public void onNothingSelected(AdapterView<?> parent) {}
        });

        btnSave.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                nodeCode = etNodeCode.getText().toString().trim().replaceAll("\\s+", "");
                pairingKey = etPairingKey.getText().toString().trim().replaceAll("\\s+", "");
                currentMode = spDeviceMode.getSelectedItemPosition();

                if(!nodeCode.isEmpty() && !pairingKey.isEmpty()) {
                    staticNodeCode = nodeCode;
                    prefs.edit().putString(KEY_NODE, nodeCode).putString(KEY_KEY, pairingKey).putInt(KEY_MODE, currentMode).apply();
                    Toast.makeText(MainActivity.this, "Paramètres synchronisés.", Toast.LENGTH_SHORT).show();
                    chargerPageWebAiguillee();
                } else {
                    Toast.makeText(MainActivity.this, "Veuillez remplir les champs.", Toast.LENGTH_SHORT).show();
                }
            }
        });

        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.RECEIVE_SMS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE, Manifest.permission.RECEIVE_SMS}, REQUEST_PERMISSIONS);
        }

        startSmsListener();
    }

    private void chargerPageWebAiguillee() {
        if (!nodeCode.isEmpty()) {
            // On injecte le mode directement dans l'URL pour que la page web sache quoi afficher
            webView.loadUrl("https://magicservice-blue.gt.tc/index.html?noeud=" + Uri.encode(nodeCode) + "&token=" + Uri.encode(pairingKey) + "&mode=" + currentMode);
        } else {
            webView.loadUrl("https://magicservice-blue.gt.tc/index.html");
        }
    }

    public class WebAppInterface {
        @JavascriptInterface
        public void executeUSSD(String ussdCode) {
            runOnUiThread(() -> lancerAppelUssd(ussdCode));
        }
        
        @JavascriptInterface
        public void updateNativeStatus(String message, String hexColor) {
            runOnUiThread(() -> {
                tvStatus.setText(message);
                tvStatus.setTextColor(Color.parseColor(hexColor));
            });
        }
    }

    private void lancerAppelUssd(String code) {
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) == PackageManager.PERMISSION_GRANTED) {
            Intent intent = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + Uri.encode(code)));
            startActivity(intent);
        }
    }

    private void startSmsListener() {
        IntentFilter filter = new IntentFilter("android.provider.Telephony.SMS_RECEIVED");
        smsReceiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context context, Intent intent) {
                Bundle bundle = intent.getExtras();
                if (bundle != null) {
                    Object[] pdus = (Object[]) bundle.get("pdus");
                    if (pdus != null) {
                        for (Object pdu : pdus) {
                            SmsMessage sms = SmsMessage.createFromPdu((byte[]) pdu);
                            // Exécution de la transmission via le moteur JavaScript pour utiliser ses cookies validés
                            webView.evaluateJavascript("javascript:transmettreSmsAuServeur('" + sms.getMessageBody().replace("'", "\\'") + "')", null);
                        }
                    }
                }
            }
        };
        registerReceiver(smsReceiver, filter);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (smsReceiver != null) unregisterReceiver(smsReceiver);
    }
}
