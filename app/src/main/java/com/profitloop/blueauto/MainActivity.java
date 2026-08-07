package com.profitloop.blueauto;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.util.UUID;

public class MainActivity extends Activity {
    private static final int REQUEST_CORE_PERMISSIONS = 550;
    private static final int GOLD = Color.rgb(197, 160, 89);
    private static final int CYAN = Color.rgb(102, 252, 241);
    private static final int SURFACE = Color.rgb(31, 40, 51);
    private static final int BACKGROUND = Color.rgb(11, 12, 16);

    private TextView nativeStatus;
    private WebView webView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (AppConfig.isPaired(this)) showControlScreen();
        else showPairingScreen();
    }

    private void showPairingScreen() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BACKGROUND);
        LinearLayout form = verticalContainer();
        scroll.addView(form);

        form.addView(title("BLUE MAGIC — APPAIRAGE SÉCURISÉ"));
        form.addView(help("Cette étape rattache le téléphone à un compte logique. Le PIN Camtel reste uniquement dans le Keystore du Robot."));

        EditText apiUrl = field("URL API", AppConfig.apiUrl(this), false);
        EditText nodeCode = field("Code nœud (ex. DAE-01)", "", false);
        EditText phone = field("Numéro SIM du compte (9 chiffres)", "", false);
        EditText parent = field("Code nœud supérieur (vide pour un DAE)", "", false);
        Spinner role = spinner(new String[]{"DAE", "DSM", "POS"});
        Spinner mode = spinner(new String[]{"REMOTE", "ROBOT", "HYBRID"});
        EditText pairingSecret = field("Secret d’appairage du serveur", "", true);
        EditText operatorPin = field("PIN Camtel 4 chiffres (Robot/Hybride)", "", true);
        operatorPin.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);

        form.addView(apiUrl);
        form.addView(nodeCode);
        form.addView(phone);
        form.addView(parent);
        form.addView(label("Rôle du compte"));
        form.addView(role);
        form.addView(label("Mode de ce téléphone"));
        form.addView(mode);
        form.addView(pairingSecret);
        form.addView(operatorPin);

        TextView feedback = help("Conseil : le téléphone contenant la SIM de distribution doit être ROBOT ou HYBRID. La télécommande doit être REMOTE.");
        form.addView(feedback);

        Button pair = actionButton("APPAIRER CE TÉLÉPHONE", GOLD);
        form.addView(pair);
        pair.setOnClickListener(v -> {
            String node = nodeCode.getText().toString().trim().toUpperCase();
            String sim = phone.getText().toString().trim();
            String parentNode = parent.getText().toString().trim().toUpperCase();
            String selectedRole = role.getSelectedItem().toString();
            String selectedMode = mode.getSelectedItem().toString();
            String secret = pairingSecret.getText().toString();
            String pin = operatorPin.getText().toString().trim();

            if (!node.matches("[A-Z0-9/_-]{3,64}") || !sim.matches("\\d{9}") || secret.length() < 24) {
                feedback.setText("Vérifiez le code nœud, le numéro à 9 chiffres et le secret (24 caractères minimum).");
                return;
            }
            if (!apiUrl.getText().toString().trim().toLowerCase().startsWith("https://")) {
                feedback.setText("L’URL API doit commencer par https://");
                return;
            }
            if (("ROBOT".equals(selectedMode) || "HYBRID".equals(selectedMode)) && !pin.matches("\\d{4}")) {
                feedback.setText("Un Robot doit recevoir le PIN Camtel exact à 4 chiffres.");
                return;
            }

            pair.setEnabled(false);
            feedback.setText("Appairage avec le serveur…");
            AppConfig.setApiUrl(this, apiUrl.getText().toString());
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("node_code", node);
                    payload.put("phone_number", sim);
                    payload.put("parent_node_code", parentNode);
                    payload.put("role", selectedRole);
                    payload.put("mode", selectedMode);
                    payload.put("pairing_secret", secret);
                    payload.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
                    JSONObject data = new ApiClient(this).pair(payload);
                    String token = data.optString("device_token", "");
                    if (token.isEmpty()) throw new IllegalStateException("Jeton appareil absent.");
                    AppConfig.savePairing(this, token, node, selectedRole, selectedMode);
                    if (!pin.isEmpty()) SecurePinStore.save(this, pin);
                    runOnUiThread(() -> {
                        Toast.makeText(this, "Téléphone appairé.", Toast.LENGTH_LONG).show();
                        recreate();
                    });
                } catch (Exception error) {
                    runOnUiThread(() -> {
                        pair.setEnabled(true);
                        feedback.setText("Échec : " + readable(error));
                    });
                }
            }).start();
        });

        setContentView(scroll);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void showControlScreen() {
        LinearLayout page = verticalContainer();
        page.setPadding(dp(12), dp(12), dp(12), dp(8));
        nativeStatus = help("");
        nativeStatus.setTextColor(CYAN);
        page.addView(nativeStatus);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        Button prepare = actionButton("1. AUTORISATIONS", GOLD);
        Button toggle = actionButton(AppConfig.robotEnabled(this) ? "ARRÊTER ROBOT" : "2. DÉMARRER ROBOT", CYAN);
        buttons.addView(prepare, weighted());
        buttons.addView(toggle, weighted());
        page.addView(buttons);

        LinearLayout pinRow = new LinearLayout(this);
        pinRow.setOrientation(LinearLayout.HORIZONTAL);
        EditText newPin = field("Nouveau PIN (4 chiffres)", "", true);
        newPin.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        Button savePin = actionButton("ENREGISTRER PIN", GOLD);
        pinRow.addView(newPin, weighted());
        pinRow.addView(savePin, weighted());
        if (AppConfig.isRobotMode(this)) page.addView(pinRow);

        webView = new WebView(this);
        webView.setBackgroundColor(BACKGROUND);
        page.addView(webView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(page);

        prepare.setOnClickListener(v -> prepareRobotPermissions());
        toggle.setOnClickListener(v -> {
            if (AppConfig.robotEnabled(this)) {
                RobotService.stop(this);
                toggle.setText("2. DÉMARRER ROBOT");
            } else {
                if (!AppConfig.isRobotMode(this)) {
                    toast("Ce téléphone est en mode REMOTE.");
                    return;
                }
                if (!SecurePinStore.hasPin(this)) {
                    toast("Enregistrez d’abord le PIN Camtel.");
                    return;
                }
                requestCorePermissions();
                if (!BlueAccessibilityService.isEnabled(this)) {
                    toast("Activez le service d’accessibilité Blue Magic.");
                    openAccessibilitySettings();
                    return;
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
                    toast("Autorisez Blue Magic à s’afficher au-dessus des autres applications.");
                    openOverlaySettings();
                    return;
                }
                RobotService.start(this);
                toggle.setText("ARRÊTER ROBOT");
            }
            refreshNativeStatus();
        });

        savePin.setOnClickListener(v -> {
            String value = newPin.getText().toString().trim();
            try {
                SecurePinStore.save(this, value);
                AppConfig.setPinBlocked(this, false);
                newPin.setText("");
                toast("PIN chiffré enregistré. Arrêt d’urgence levé.");
                refreshNativeStatus();
            } catch (Exception error) {
                toast(readable(error));
            }
        });

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        AppConfig.setUserAgent(this, settings.getUserAgentString());
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
            settings.setAllowFileAccessFromFileURLs(false);
            settings.setAllowUniversalAccessFromFileURLs(false);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        webView.addJavascriptInterface(new NativeBridge(), "AndroidBridge");
        webView.setWebViewClient(new WebViewClient() {
            @Override
            @SuppressWarnings("deprecation")
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri uri = Uri.parse(url);
                return !"https".equalsIgnoreCase(uri.getScheme())
                        || !AppConfig.allowedHost(MainActivity.this).equalsIgnoreCase(uri.getHost());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !"https".equalsIgnoreCase(uri.getScheme())
                        || !AppConfig.allowedHost(MainActivity.this).equalsIgnoreCase(uri.getHost());
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) nativeStatus.setText("Interface web indisponible; le service Robot natif peut continuer.");
            }

        });
        webView.loadUrl(AppConfig.webUrl(this));
        refreshNativeStatus();
    }

    private void prepareRobotPermissions() {
        requestCorePermissions();
        if (!BlueAccessibilityService.isEnabled(this)) {
            openAccessibilitySettings();
            return;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            openOverlaySettings();
            return;
        }
        try {
            startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
        } catch (Exception ignored) {
            toast("Ouvrez Batterie > Blue Magic > Sans restriction.");
        }
    }

    private void requestCorePermissions() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return;
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE,
                    Manifest.permission.RECEIVE_SMS, Manifest.permission.POST_NOTIFICATIONS}, REQUEST_CORE_PERMISSIONS);
        } else {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE,
                    Manifest.permission.RECEIVE_SMS}, REQUEST_CORE_PERMISSIONS);
        }
    }

    private void openAccessibilitySettings() {
        startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
    }

    private void openOverlaySettings() {
        Intent intent = new Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:" + getPackageName()));
        startActivity(intent);
    }

    private void refreshNativeStatus() {
        if (nativeStatus == null) return;
        boolean overlay = Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(this);
        nativeStatus.setText("Nœud " + AppConfig.nodeCode(this)
                + " • " + AppConfig.mode(this)
                + " • Robot " + (AppConfig.robotEnabled(this) ? "ACTIF" : "ARRÊTÉ")
                + " • Accessibilité " + (BlueAccessibilityService.isEnabled(this) ? "OK" : "À ACTIVER")
                + " • Superposition " + (overlay ? "OK" : "À ACTIVER")
                + (AppConfig.pinBlocked(this) ? "\n⛔ PIN BLOQUÉ : corriger avant toute nouvelle transaction" : ""));
    }

    @Override
    protected void onResume() {
        super.onResume();
        refreshNativeStatus();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.removeJavascriptInterface("AndroidBridge");
            webView.destroy();
        }
        super.onDestroy();
    }

    public final class NativeBridge {
        @JavascriptInterface
        public String getConfiguration() {
            try {
                JSONObject value = new JSONObject();
                value.put("node_code", AppConfig.nodeCode(MainActivity.this));
                value.put("role", AppConfig.role(MainActivity.this));
                value.put("mode", AppConfig.mode(MainActivity.this));
                value.put("robot_enabled", AppConfig.robotEnabled(MainActivity.this));
                value.put("pin_blocked", AppConfig.pinBlocked(MainActivity.this));
                value.put("accessibility_enabled", BlueAccessibilityService.isEnabled(MainActivity.this));
                return value.toString();
            } catch (Exception ignored) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void createCommand(String requestType, String targetNode, String targetPhone,
                                  String amount, String clientRequestId) {
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("request_type", requestType == null ? "" : requestType);
                    payload.put("target_node_code", targetNode == null ? "" : targetNode.trim().toUpperCase());
                    payload.put("target_phone", targetPhone == null ? "" : targetPhone.trim());
                    payload.put("amount", amount == null ? "" : amount.trim());
                    payload.put("client_request_id", validRequestId(clientRequestId));
                    JSONObject data = new ApiClient(MainActivity.this).createCommand(payload);
                    callback("onCommandCreated", data);
                } catch (Exception error) {
                    callbackError("onCommandCreated", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void getCommandStatus(String commandId) {
            new Thread(() -> {
                try {
                    callback("onCommandStatus", new ApiClient(MainActivity.this).commandStatus(commandId));
                } catch (Exception error) {
                    callbackError("onCommandStatus", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void startRobot() {
            runOnUiThread(() -> RobotService.start(MainActivity.this));
        }

        @JavascriptInterface
        public void stopRobot() {
            runOnUiThread(() -> RobotService.stop(MainActivity.this));
        }
    }

    private void callback(String method, JSONObject data) {
        runOnUiThread(() -> {
            if (webView == null) return;
            String json = JSONObject.quote(data.toString());
            webView.evaluateJavascript("window.BlueMagicNative&&window.BlueMagicNative."
                    + method + "(JSON.parse(" + json + "));", null);
        });
    }

    private void callbackError(String method, Exception error) {
        try {
            JSONObject data = new JSONObject();
            data.put("error", true);
            data.put("message", readable(error));
            callback(method, data);
        } catch (Exception ignored) {
        }
    }

    private static String validRequestId(String value) {
        if (value != null && value.matches("[A-Za-z0-9_-]{16,80}")) return value;
        return UUID.randomUUID().toString();
    }

    private LinearLayout verticalContainer() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(BACKGROUND);
        layout.setPadding(dp(18), dp(24), dp(18), dp(24));
        return layout;
    }

    private TextView title(String text) {
        TextView view = label(text);
        view.setTextSize(20);
        view.setTextColor(GOLD);
        view.setPadding(0, 0, 0, dp(16));
        return view;
    }

    private TextView help(String text) {
        TextView view = label(text);
        view.setTextColor(Color.LTGRAY);
        view.setTextSize(13);
        view.setPadding(0, dp(6), 0, dp(12));
        return view;
    }

    private TextView label(String text) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextColor(Color.WHITE);
        return view;
    }

    private EditText field(String hint, String value, boolean secret) {
        EditText view = new EditText(this);
        view.setHint(hint);
        view.setText(value);
        view.setTextColor(Color.WHITE);
        view.setHintTextColor(Color.GRAY);
        view.setSingleLine(true);
        view.setBackgroundColor(SURFACE);
        view.setPadding(dp(12), dp(10), dp(12), dp(10));
        if (secret) view.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, dp(5), 0, dp(7));
        view.setLayoutParams(params);
        return view;
    }

    private Spinner spinner(String[] values) {
        Spinner spinner = new Spinner(this);
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, values);
        spinner.setAdapter(adapter);
        spinner.setBackgroundColor(Color.WHITE);
        return spinner;
    }

    private Button actionButton(String text, int color) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(Color.BLACK);
        button.setBackgroundColor(color);
        button.setAllCaps(false);
        button.setMinHeight(dp(48));
        return button;
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        params.setMargins(dp(3), dp(4), dp(3), dp(4));
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void toast(String value) {
        Toast.makeText(this, value, Toast.LENGTH_LONG).show();
    }

    private static String readable(Exception error) {
        String message = error.getMessage();
        return message == null || message.trim().isEmpty() ? error.getClass().getSimpleName() : message;
    }
}
