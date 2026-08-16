package com.profitloop.blueauto;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.JsResult;
import android.webkit.JsPromptResult;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.net.ConnectException;
import java.net.SocketTimeoutException;
import java.net.UnknownHostException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.UUID;

import javax.net.ssl.SSLException;

public class MainActivity extends Activity {
    private static final int REQUEST_CORE_PERMISSIONS = 550;
    private static final int GOLD = Color.rgb(255, 205, 92);
    private static final int CYAN = Color.rgb(78, 225, 255);
    private static final int VIOLET = Color.rgb(135, 92, 255);
    private static final int SURFACE = Color.rgb(15, 37, 70);
    private static final int BACKGROUND = Color.rgb(5, 18, 42);
    private static final String PAIRING_DIAGNOSTIC_KEY = "pairing_diagnostic_v254";

    private TextView nativeStatus;
    private WebView webView;
    private AlertDialog managementDialog;
    private Button manageButton;
    private volatile boolean robotStartInProgress;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        AppConfig.migrateLegacyProfile(this);
        applyRobotWindowPolicy();
        if (AppConfig.isPaired(this)) showControlScreen();
        else showPairingScreen(false);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
    }

    private void showPairingScreen(boolean addingAccount) {
        disposeWebView();
        ScrollView scroll = new ScrollView(this);
        applyMagicBackground(scroll);
        LinearLayout form = verticalContainer();
        scroll.addView(form);

        form.addView(title("BLUE MAGIC — APPAIRAGE SÉCURISÉ"));
        form.addView(help("Vérifiez l’adresse et le secret avant l’appairage. Le PIN Camtel reste uniquement dans le Keystore du téléphone."));

        TextView installedVersion = help("VERSION INSTALLÉE : " + installedVersionLabel());
        installedVersion.setTextColor(CYAN);
        form.addView(installedVersion);

        TextView diagnostic = help(AppConfig.prefs(this).getString(PAIRING_DIAGNOSTIC_KEY,
                "DIAGNOSTIC : aucun test effectué sur cette installation."));
        diagnostic.setTextColor(GOLD);
        form.addView(diagnostic);

        EditText apiUrl = field("Adresse du serveur Blue Magic", AppConfig.pairingApiUrl(this), false);
        EditText nodeCode = field("Identifiant Camtel (ex. OU3, DSM7 ou POS16)", "", false);
        EditText phone = field("Numéro SIM du compte (9 chiffres)", "", false);
        EditText parent = field("Supérieur : OU3 pour DSM / DSM7_OU3 pour PoS", "", false);
        Spinner role = spinner(new String[]{"DAE", "DSM", "POS"});
        Spinner mode = spinner(new String[]{"REMOTE", "ROBOT"});
        Spinner simSlot = spinner(SimCallManager.slotLabels(this));
        String savedActivation = "";
        try {
            savedActivation = SecurePairingStore.read(this);
        } catch (Exception ignored) {
        }
        EditText pairingSecret = field("Secret d’appairage", savedActivation, true);
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
        form.addView(label("Slot contenant la SIM de ce compte"));
        form.addView(simSlot);
        form.addView(help("Le secret est conservé chiffré après un appairage réussi. Il reste vérifiable et modifiable ici."));
        form.addView(pairingSecret);
        form.addView(operatorPin);

        CheckBox revealSecrets = new CheckBox(this);
        revealSecrets.setText("Afficher le secret d’appairage et le PIN");
        revealSecrets.setTextColor(Color.WHITE);
        revealSecrets.setOnCheckedChangeListener((button, checked) -> {
            pairingSecret.setInputType(InputType.TYPE_CLASS_TEXT | (checked
                    ? InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                    : InputType.TYPE_TEXT_VARIATION_PASSWORD));
            operatorPin.setInputType(InputType.TYPE_CLASS_NUMBER | (checked
                    ? InputType.TYPE_NUMBER_VARIATION_NORMAL
                    : InputType.TYPE_NUMBER_VARIATION_PASSWORD));
            pairingSecret.setSelection(pairingSecret.length());
            operatorPin.setSelection(operatorPin.length());
        });
        form.addView(revealSecrets);

        TextView feedback = help("ROBOT est le mode polyvalent : il exécute les commandes et peut aussi en créer. REMOTE est uniquement une télécommande. Chaque compte conserve séparément son PIN et son slot SIM.");
        form.addView(feedback);

        Button testServer = actionButton("VÉRIFIER LE SERVEUR", CYAN);
        form.addView(testServer);
        testServer.setOnClickListener(v -> {
            String selectedApiUrl = AppConfig.normalizeApiUrl(apiUrl.getText().toString());
            if (!selectedApiUrl.toLowerCase(Locale.ROOT).startsWith("https://")) {
                showPairingIssue(scroll, apiUrl, feedback, diagnostic,
                        "LOCAL_API_INVALID", "L’adresse du serveur doit commencer par https://");
                return;
            }
            testServer.setEnabled(false);
            testServer.setText("VÉRIFICATION EN COURS…");
            updatePairingDiagnostic(diagnostic, "SERVER_CHECK_SENT",
                    "Connexion au serveur depuis ce téléphone en cours.");
            new Thread(() -> {
                try {
                    JSONObject health = new ApiClient(this, selectedApiUrl, "").health();
                    String service = health.optString("service", "serveur");
                    String version = health.optString("version", "version inconnue");
                    String database = health.optString("database", "état D1 inconnu");
                    runOnUiThread(() -> {
                        testServer.setEnabled(true);
                        testServer.setText("SERVEUR VÉRIFIÉ — RETESTER");
                        String message = "Connexion HTTPS réussie : " + service + " • " + version
                                + " • D1 " + database + ".";
                        feedback.setTextColor(CYAN);
                        feedback.setText(message);
                        updatePairingDiagnostic(diagnostic, "SERVER_CHECK_OK", message);
                        toast(message);
                    });
                } catch (Exception error) {
                    runOnUiThread(() -> {
                        testServer.setEnabled(true);
                        testServer.setText("ÉCHEC SERVEUR — RETESTER");
                        String code = diagnosticCode(error, "SERVER_CHECK");
                        String message = "Connexion serveur impossible : " + readable(error);
                        feedback.setTextColor(Color.rgb(255, 139, 152));
                        feedback.setText(message);
                        updatePairingDiagnostic(diagnostic, code, message);
                        showDiagnosticDialog(code, message);
                    });
                }
            }).start();
        });

        Button pair = actionButton("APPAIRER CE TÉLÉPHONE", GOLD);
        form.addView(pair);
        pair.setOnClickListener(v -> {
            updatePairingDiagnostic(diagnostic, "PAIR_CLICK_RECEIVED",
                    "Le bouton APPAIRER fonctionne. Validation locale du formulaire en cours.");
            String node = nodeCode.getText().toString().trim().toUpperCase();
            String sim = normalizeCameroonPhone(phone.getText().toString());
            String selectedRole = role.getSelectedItem().toString();
            String selectedMode = mode.getSelectedItem().toString();
            String parentNode = "DAE".equals(selectedRole)
                    ? "" : parent.getText().toString().trim().toUpperCase();
            String secret = pairingSecret.getText().toString().trim();
            String pin = operatorPin.getText().toString().trim();
            int selectedSlot = simSlot.getSelectedItemPosition();

            if (!node.matches("[A-Z0-9/_-]{3,64}")) {
                showPairingIssue(scroll, nodeCode, feedback, diagnostic,
                        "LOCAL_NODE_INVALID", "Le code local doit contenir au moins 3 lettres ou chiffres.");
                return;
            }
            if (!sim.matches("6\\d{8}")) {
                showPairingIssue(scroll, phone, feedback, diagnostic,
                        "LOCAL_PHONE_INVALID",
                        "Saisissez un numéro camerounais valide de 9 chiffres commençant par 6.");
                return;
            }
            phone.setText(sim);
            if (!"DAE".equals(selectedRole) && !parentNode.matches("[A-Z0-9/_-]{3,64}")) {
                showPairingIssue(scroll, parent, feedback, diagnostic,
                        "LOCAL_PARENT_REQUIRED",
                        "Un DSM doit indiquer son DAE supérieur et un PoS son DSM supérieur.");
                return;
            }
            if (!parentNode.isEmpty() && parentNode.equals(node)) {
                showPairingIssue(scroll, parent, feedback, diagnostic,
                        "LOCAL_PARENT_EQUALS_NODE",
                        "Le supérieur doit être différent du compte en cours d’appairage.");
                return;
            }
            if (secret.length() < 24) {
                showPairingIssue(scroll, pairingSecret, feedback, diagnostic,
                        "LOCAL_SECRET_INCOMPLETE", "Le secret d’appairage est absent ou incomplet.");
                return;
            }
            String selectedApiUrl = AppConfig.normalizeApiUrl(apiUrl.getText().toString());
            if (!selectedApiUrl.toLowerCase(Locale.ROOT).startsWith("https://")) {
                showPairingIssue(scroll, apiUrl, feedback, diagnostic,
                        "LOCAL_API_INVALID", "L’adresse du serveur doit commencer par https://");
                return;
            }
            if (("ROBOT".equals(selectedMode) || "HYBRID".equals(selectedMode)) && !pin.matches("\\d{4}")) {
                showPairingIssue(scroll, operatorPin, feedback, diagnostic,
                        "LOCAL_PIN_INVALID", "Un Robot doit recevoir le PIN Camtel exact à 4 chiffres.");
                return;
            }

            pair.setEnabled(false);
            pair.setText("APPAIRAGE EN COURS…");
            feedback.setTextColor(CYAN);
            feedback.setText("Connexion sécurisée à " + selectedApiUrl + "…");
            updatePairingDiagnostic(diagnostic, "PAIR_REQUEST_SENT",
                    "Formulaire valide. Requête HTTPS d’appairage envoyée au serveur.");
            toast("Demande d’appairage envoyée. Patientez quelques secondes.");
            new Thread(() -> {
                String stage = "PAIR_NETWORK";
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("node_code", node);
                    payload.put("phone_number", sim);
                    payload.put("parent_node_code", parentNode);
                    payload.put("role", selectedRole);
                    payload.put("mode", selectedMode);
                    payload.put("pairing_secret", secret);
                    payload.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
                    JSONObject data = new ApiClient(this, selectedApiUrl, "").pair(payload);
                    stage = "PAIR_SERVER_RESPONSE";
                    String token = data.optString("device_token", "");
                    String deviceId = data.optString("device_id", "");
                    String canonicalNode = data.optString("node_code", node);
                    String canonicalParent = data.optString("parent_node_code", parentNode);
                    if (token.isEmpty()) throw new IllegalStateException("Jeton appareil absent.");
                    stage = "PAIR_LOCAL_PROFILE_SAVE";
                    AppConfig.savePairing(this, deviceId, token, canonicalNode, sim, canonicalParent,
                            selectedRole, selectedMode, selectedApiUrl, selectedSlot);
                    stage = "PAIR_LOCAL_SECRET_SAVE";
                    SecurePairingStore.save(this, secret);
                    if (!pin.isEmpty()) SecurePinStore.save(this, pin);
                    stage = "PAIR_SIM_BINDING";
                    SimIdentityManager.Verification simVerification =
                            SimIdentityManager.bindSelectedSim(this, AppConfig.profileId(this));
                    runOnUiThread(() -> {
                        updatePairingDiagnostic(diagnostic, "PAIRING_COMPLETE",
                                "Serveur accepté, profil enregistré et écran de contrôle prêt.");
                        Toast.makeText(this, "REMOTE".equals(selectedMode)
                                ? "Téléphone appairé en mode Remote."
                                : simVerification.valid
                                ? "Téléphone appairé et SIM liée au bon slot."
                                : "Compte appairé, mais Robot arrêté : " + simVerification.message,
                                Toast.LENGTH_LONG).show();
                        recreate();
                    });
                } catch (Exception error) {
                    String failedStage = stage;
                    runOnUiThread(() -> {
                        pair.setEnabled(true);
                        pair.setText("RÉESSAYER L’APPAIRAGE");
                        String code = diagnosticCode(error, failedStage);
                        String message = "Échec de l’appairage : " + readable(error);
                        feedback.setTextColor(Color.rgb(255, 139, 152));
                        feedback.setText(message);
                        updatePairingDiagnostic(diagnostic, code, message);
                        showDiagnosticDialog(code, message);
                        scroll.post(() -> scroll.smoothScrollTo(0, feedback.getTop()));
                    });
                }
            }).start();
        });

        if (addingAccount && AppConfig.hasProfiles(this)) {
            Button cancel = actionButton("ANNULER — REVENIR AU COMPTE ACTIF", CYAN);
            cancel.setOnClickListener(v -> showControlScreen());
            form.addView(cancel);
        }

        setContentView(scroll);
    }

    private void showPairingIssue(ScrollView scroll, View target, TextView feedback,
                                  TextView diagnostic, String code, String message) {
        feedback.setTextColor(Color.rgb(255, 139, 152));
        feedback.setText("À corriger : " + message);
        if (target instanceof EditText) ((EditText) target).setError(message);
        target.requestFocus();
        updatePairingDiagnostic(diagnostic, code, message);
        showDiagnosticDialog(code, message);
        scroll.post(() -> scroll.smoothScrollTo(0, Math.max(0, target.getTop() - dp(18))));
    }

    private void updatePairingDiagnostic(TextView diagnostic, String code, String message) {
        String timestamp = new SimpleDateFormat("HH:mm:ss", Locale.ROOT).format(new Date());
        String report = "DIAGNOSTIC " + timestamp + " • " + code + "\n" + message;
        AppConfig.prefs(this).edit().putString(PAIRING_DIAGNOSTIC_KEY, report).commit();
        diagnostic.setText(report);
    }

    private void showDiagnosticDialog(String code, String message) {
        new AlertDialog.Builder(this)
                .setTitle("Diagnostic d’appairage — " + code)
                .setMessage(message + "\n\nNotez ou photographiez ce code. Aucun secret n’est affiché.")
                .setPositiveButton("COMPRIS", null)
                .show();
    }

    private static String diagnosticCode(Exception error, String stage) {
        if (error instanceof ApiClient.ApiException) {
            String code = ((ApiClient.ApiException) error).code;
            return code == null || code.trim().isEmpty() ? "API_ERROR" : code;
        }
        if (error instanceof UnknownHostException) return "NETWORK_DNS";
        if (error instanceof SocketTimeoutException) return "NETWORK_TIMEOUT";
        if (error instanceof SSLException) return "NETWORK_TLS";
        if (error instanceof ConnectException) return "NETWORK_CONNECT";
        return stage == null || stage.trim().isEmpty() ? "PAIR_UNKNOWN" : stage;
    }

    private static String normalizeCameroonPhone(String value) {
        String digits = value == null ? "" : value.replaceAll("\\D", "");
        if (digits.length() == 12 && digits.startsWith("237")) return digits.substring(3);
        return digits;
    }

    @SuppressWarnings("deprecation")
    private String installedVersionLabel() {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            long versionCode = Build.VERSION.SDK_INT >= 28
                    ? info.getLongVersionCode() : info.versionCode;
            return info.versionName + " • versionCode " + versionCode;
        } catch (Exception error) {
            return "version inconnue • " + error.getClass().getSimpleName();
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void showControlScreen() {
        disposeWebView();
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        applyMagicBackground(page);
        page.setPadding(0, 0, 0, 0);
        nativeStatus = help("");
        nativeStatus.setTextColor(CYAN);
        nativeStatus.setTextSize(12);
        nativeStatus.setPadding(dp(4), 0, dp(4), dp(3));
        page.addView(nativeStatus);
        nativeStatus.setVisibility(View.GONE);

        LinearLayout compactBar = new LinearLayout(this);
        compactBar.setOrientation(LinearLayout.HORIZONTAL);
        Button accounts = actionButton("COMPTES (" + AppConfig.profileCount(this) + ")", GOLD);
        manageButton = actionButton("☰ GÉRER", VIOLET);
        compactBar.addView(accounts, weighted());
        compactBar.addView(manageButton, weighted());
        page.addView(compactBar);
        compactBar.setVisibility(View.GONE);

        webView = new WebView(this);
        webView.setBackgroundColor(BACKGROUND);
        page.addView(webView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(page);

        accounts.setOnClickListener(v -> showAccountManager());
        manageButton.setOnClickListener(v -> setManagementOpen(true));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        AppConfig.setUserAgent(this, settings.getUserAgentString());
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(false);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN) {
            settings.setAllowFileAccessFromFileURLs(false);
            settings.setAllowUniversalAccessFromFileURLs(false);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        }
        webView.addJavascriptInterface(new NativeBridge(), "AndroidBridge");
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onJsConfirm(WebView view, String url, String message, JsResult result) {
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Confirmation Blue Magic")
                        .setMessage(message)
                        .setPositiveButton("CONFIRMER", (dialog, which) -> result.confirm())
                        .setNegativeButton("ANNULER", (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel())
                        .show();
                return true;
            }

            @Override
            public boolean onJsPrompt(WebView view, String url, String message, String defaultValue, JsPromptResult result) {
                final EditText input = new EditText(MainActivity.this);
                input.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_FLAG_DECIMAL);
                input.setText(defaultValue == null ? "" : defaultValue);
                input.setSelectAllOnFocus(true);
                int pad = dp(18); input.setPadding(pad, dp(8), pad, dp(8));
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Taux de commission")
                        .setMessage(message)
                        .setView(input)
                        .setPositiveButton("VALIDER LE TAUX", (dialog, which) -> result.confirm(input.getText().toString().trim()))
                        .setNegativeButton("ANNULER", (dialog, which) -> result.cancel())
                        .setOnCancelListener(dialog -> result.cancel())
                        .show();
                return true;
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            @SuppressWarnings("deprecation")
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                Uri uri = Uri.parse(url);
                return !"file".equalsIgnoreCase(uri.getScheme())
                        || uri.getPath() == null || !uri.getPath().startsWith("/android_asset/");
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                return !"file".equalsIgnoreCase(uri.getScheme())
                        || uri.getPath() == null || !uri.getPath().startsWith("/android_asset/");
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) nativeStatus.setText("Interface Android intégrée indisponible; relancez Blue Magic.");
            }

        });
        webView.loadUrl("file:///android_asset/index.html");
        refreshNativeStatus();
    }

    private void setManagementOpen(boolean opening) {
        if (opening) {
            showManagementCenter();
            return;
        }
        if (managementDialog != null && managementDialog.isShowing()) {
            managementDialog.dismiss();
        }
        managementDialog = null;
        if (manageButton != null) manageButton.setText("☰ GÉRER");
    }

    /**
     * Responsive native management center.
     *
     * The previous implementation inserted a fixed 260dp ScrollView above the WebView. On short
     * Android 6 terminals that consumed most of the usable height. This dialog keeps the dashboard
     * intact, groups actions by intent and uses two compact columns whenever the screen is wide
     * enough. Ultra-narrow screens automatically fall back to one column without hiding actions.
     */
    private void showManagementCenter() {
        if (managementDialog != null && managementDialog.isShowing()) return;

        final boolean robotMode = AppConfig.isRobotMode(this);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setVerticalScrollBarEnabled(true);
        scroll.setScrollbarFadingEnabled(false);
        LinearLayout tools = new LinearLayout(this);
        tools.setOrientation(LinearLayout.VERTICAL);
        tools.setPadding(dp(10), dp(6), dp(10), dp(12));
        scroll.addView(tools);

        TextView intro = help(AppConfig.nodeCode(this) + " • "
                + AppConfig.displayMode(AppConfig.mode(this))
                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + "\nActions regroupées pour rester lisibles même sur les petits téléphones.");
        intro.setTextColor(CYAN);
        intro.setPadding(dp(2), 0, dp(2), dp(4));
        tools.addView(intro);

        tools.addView(managementSectionTitle("COMPTE & SIM"));
        Button accounts = managementActionButton("👥 COMPTES (" + AppConfig.profileCount(this) + ")", GOLD);
        Button addAccount = managementActionButton("＋ AJOUTER COMPTE", CYAN);
        addManagementPair(tools, accounts, addAccount);
        Button verifySim = managementActionButton("🔗 VÉRIFIER / LIER SIM", VIOLET);
        Button repairPairing = managementActionButton("🛠 RÉPARER APPAIRAGE", CYAN);
        addManagementFull(tools, repairPairing);
        Button switchMode = managementActionButton(AppConfig.isRobotMode(this)
                ? "↔ PASSER EN REMOTE" : "↔ PASSER EN ROBOT", GOLD);
        addManagementFull(tools, switchMode);

        Button pinSettings = null;
        Button networkPinChange = null;
        Button networkPinReset = null;
        Button prepare = null;
        Button battery = null;
        Button toggle = null;
        if (robotMode) {
            tools.addView(managementSectionTitle("PIN CAMTEL"));
            pinSettings = managementActionButton("🔐 PIN LOCAL", GOLD);
            networkPinChange = managementActionButton("🔁 MODIFIER LE PIN CAMTEL", CYAN);
            addManagementPair(tools, pinSettings, networkPinChange);
            networkPinReset = managementActionButton("🆘 DEMANDER RESET PIN", VIOLET);
            addManagementFull(tools, networkPinReset);

            tools.addView(managementSectionTitle("ROBOT & TÉLÉPHONE"));
            prepare = managementActionButton("1. AUTORISATIONS", GOLD);
            battery = managementActionButton("🔋 BATTERIE SANS RESTRICTION", CYAN);
            // Autorisations, batterie et démarrage sont désormais visibles directement dans la Tour de contrôle.
            toggle = managementActionButton(AppConfig.robotEnabled(this)
                    ? "■ ARRÊTER ROBOT" : "▶ DÉMARRER ROBOT", VIOLET);
        }

        tools.addView(managementSectionTitle("FILES & SÉCURITÉ"));
        Button pendingOperations = managementActionButton("⏳ FILES / ANNULER OPÉRATION BLOQUÉE", GOLD);
        addManagementFull(tools, pendingOperations);

        managementDialog = new AlertDialog.Builder(this)
                .setTitle("Blue Magic — Centre de gestion")
                .setView(scroll)
                .setNegativeButton("FERMER", null)
                .create();
        managementDialog.setOnDismissListener(dialog -> {
            managementDialog = null;
            if (manageButton != null) manageButton.setText("☰ GÉRER");
        });
        managementDialog.setOnShowListener(dialog -> {
            if (manageButton != null) manageButton.setText("✕ FERMER");
            android.view.Window window = managementDialog.getWindow();
            if (window != null) {
                float density = getResources().getDisplayMetrics().density;
                int screenWidth = getResources().getDisplayMetrics().widthPixels;
                int screenHeight = getResources().getDisplayMetrics().heightPixels;
                int width = Math.min(screenWidth - Math.round(12 * density), dp(620));
                int height = Math.min(Math.round(screenHeight * 0.88f), dp(650));
                window.setLayout(Math.max(dp(260), width), Math.max(dp(300), height));
            }
        });

        accounts.setOnClickListener(v -> { setManagementOpen(false); showAccountManager(); });
        addAccount.setOnClickListener(v -> { setManagementOpen(false); showPairingScreen(true); });
        verifySim.setOnClickListener(v -> { setManagementOpen(false); confirmAndBindCurrentSim(); });
        repairPairing.setOnClickListener(v -> { setManagementOpen(false); showPairingRepairDialog(); });
        switchMode.setOnClickListener(v -> { setManagementOpen(false); showModeSwitcher(); });
        pendingOperations.setOnClickListener(v -> { setManagementOpen(false); showPendingOperations(); });
        if (robotMode) {
            final Button pinButton = pinSettings;
            final Button changeButton = networkPinChange;
            final Button resetButton = networkPinReset;
            final Button permissionButton = prepare;
            final Button batteryButton = battery;
            final Button toggleButton = toggle;
            pinButton.setOnClickListener(v -> { setManagementOpen(false); showPinEditorDialog(); });
            changeButton.setOnClickListener(v -> { setManagementOpen(false); showOperatorPinChangeDialog(); });
            resetButton.setOnClickListener(v -> { setManagementOpen(false); confirmResetOperatorPin(); });
            permissionButton.setOnClickListener(v -> { setManagementOpen(false); prepareRobotPermissions(); });
            batteryButton.setOnClickListener(v -> { setManagementOpen(false); openBatterySettings(); });
            toggleButton.setOnClickListener(v -> toggleRobotFromManagement());
        }

        managementDialog.show();
    }

    private TextView managementSectionTitle(String text) {
        TextView title = label(text);
        title.setTextColor(CYAN);
        title.setTextSize(10);
        title.setPadding(dp(3), dp(10), dp(3), dp(3));
        return title;
    }

    private Button managementActionButton(String text, int color) {
        Button button = actionButton(text, color);
        float widthDp = getResources().getDisplayMetrics().widthPixels
                / getResources().getDisplayMetrics().density;
        button.setTextSize(widthDp < 340f ? 9f : 10f);
        button.setMinHeight(dp(widthDp < 340f ? 40 : 44));
        button.setSingleLine(false);
        button.setMaxLines(2);
        button.setGravity(android.view.Gravity.CENTER);
        button.setPadding(dp(4), dp(2), dp(4), dp(2));
        return button;
    }

    private void addManagementPair(LinearLayout parent, Button left, Button right) {
        float widthDp = getResources().getDisplayMetrics().widthPixels
                / getResources().getDisplayMetrics().density;
        if (widthDp < 290f) {
            addManagementFull(parent, left);
            addManagementFull(parent, right);
            return;
        }
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.addView(left, weighted());
        row.addView(right, weighted());
        parent.addView(row);
    }

    private void addManagementFull(LinearLayout parent, Button button) {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(dp(2), dp(3), dp(2), dp(3));
        parent.addView(button, params);
    }

    private void toggleRobotFromManagement() {
        if (AppConfig.robotEnabled(this)) {
            if (isActiveUssdForCurrentProfile()) {
                toast("Une transaction USSD est en cours. Attendez son résultat avant d’arrêter ce Robot.");
                return;
            }
            RobotService.stop(this);
        } else {
            if (!AppConfig.isRobotMode(this)) {
                toast("Ce compte est en mode REMOTE. Passez-le d’abord en mode ROBOT.");
                return;
            }
            if (!startRobotSafely()) return;
        }
        setManagementOpen(false);
        applyRobotWindowPolicy();
        refreshNativeStatus();
    }

    private void openBatterySettings() {
        try {
            startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
            toast("Choisissez Blue Magic puis « Sans restriction » / « Ne pas optimiser » si disponible.");
        } catch (Exception error) {
            toast("Ouvrez Batterie > Blue Magic > Sans restriction / Ne pas optimiser.");
        }
    }

    private void showPinEditorDialog() {
        if (!AppConfig.isRobotMode(this)) {
            toast("Entrez d’abord dans le hall Robot pour enregistrer son PIN local.");
            return;
        }
        if (!canModifyActiveProfile()) return;

        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20), dp(8), dp(20), 0);

        TextView explanation = help("Ce PIN reste chiffré dans ce téléphone. Il n’est jamais envoyé au serveur ni au JavaScript.");
        explanation.setTextColor(Color.DKGRAY);
        content.addView(explanation);

        EditText pin = field("Nouveau PIN Camtel (4 chiffres)", "", true);
        pin.setTextColor(Color.BLACK);
        pin.setHintTextColor(Color.DKGRAY);
        pin.setBackgroundColor(Color.rgb(238, 243, 250));
        pin.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        content.addView(pin);

        CheckBox reveal = new CheckBox(this);
        reveal.setText("Afficher le PIN pendant la saisie");
        reveal.setTextColor(Color.DKGRAY);
        reveal.setOnCheckedChangeListener((button, checked) -> {
            pin.setInputType(InputType.TYPE_CLASS_NUMBER | (checked
                    ? InputType.TYPE_NUMBER_VARIATION_NORMAL
                    : InputType.TYPE_NUMBER_VARIATION_PASSWORD));
            pin.setSelection(pin.length());
        });
        content.addView(reveal);

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("PIN Camtel — " + AppConfig.nodeCode(this))
                .setView(content)
                .setPositiveButton("ENREGISTRER", null)
                .setNegativeButton("Annuler", null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    String value = pin.getText().toString().trim();
                    try {
                        SecurePinStore.save(this, value);
                        AppConfig.setPinBlocked(this, false);
                        pin.setText("");
                        dialog.dismiss();
                        toast("PIN chiffré enregistré. Arrêt d’urgence levé.");
                        refreshNativeStatus();
                    } catch (Exception error) {
                        pin.setError(readable(error));
                        pin.requestFocus();
                    }
                }));
        dialog.show();
    }

    private void showOperatorPinChangeDialog() {
        if (!AppConfig.isRobotMode(this) || !canModifyActiveProfile()) {
            toast("La modification du PIN réseau s’effectue uniquement sur le téléphone Robot de cette SIM.");
            return;
        }
        if (!SecurePinStore.hasPin(this, AppConfig.profileId(this))) {
            toast("Enregistrez d’abord le PIN Camtel actuel dans le stockage local sécurisé.");
            return;
        }
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(20), dp(8), dp(20), 0);
        content.addView(help("Le nouveau PIN reste chiffré sur ce Robot et n’est jamais envoyé au Worker, à D1 ni au JavaScript."));
        EditText first = field("Nouveau PIN Camtel (4 chiffres)", "", true);
        EditText second = field("Confirmer le nouveau PIN", "", true);
        first.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        second.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        content.addView(first); content.addView(second);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Changer le PIN réseau — " + AppConfig.nodeCode(this))
                .setView(content).setPositiveButton("LANCER LA MODIFICATION", null)
                .setNegativeButton("Annuler", null).create();
        dialog.setOnShowListener(x -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String a = first.getText().toString().trim();
            String b = second.getText().toString().trim();
            if (!a.matches("\\d{4}") || !a.equals(b)) { second.setError("Les deux PIN de 4 chiffres doivent être identiques."); return; }
            try { PendingPinChangeStore.save(this, AppConfig.profileId(this), a); }
            catch (Exception error) { second.setError(readable(error)); return; }
            first.setText(""); second.setText(""); dialog.dismiss();
            queueLocalMaintenance("MODIFY_PIN_LOCAL", "Modification PIN Camtel mise en file.");
        }));
        dialog.show();
    }

    private void confirmResetOperatorPin() {
        if (!AppConfig.isRobotMode(this) || !canModifyActiveProfile()) return;
        new AlertDialog.Builder(this).setTitle("Demander un reset PIN ?")
                .setMessage("Blue Magic exécutera *550*5*1# sur la SIM active. Le PIN provisoire reçu par SMS restera local au téléphone et ne sera pas envoyé au serveur.")
                .setPositiveButton("CONFIRMER", (d,w) -> queueLocalMaintenance("RESET_PIN_SELF", "Reset PIN mis en file."))
                .setNegativeButton("Annuler", null).show();
    }

    private void queueLocalMaintenance(String requestType, String confirmation) {
        new Thread(() -> {
            try {
                JSONObject payload = new JSONObject();
                payload.put("request_type", requestType);
                payload.put("client_request_id", "local_" + UUID.randomUUID().toString().replace("-", ""));
                new ApiClient(this).createCommand(payload);
                RobotService.startEnabled(this);
                runOnUiThread(() -> toast(confirmation));
            } catch (Exception error) {
                if ("MODIFY_PIN_LOCAL".equals(requestType)) PendingPinChangeStore.clear(this, AppConfig.profileId(this));
                runOnUiThread(() -> toast("Commande refusée : " + readable(error)));
            }
        }).start();
    }

    private void showAccountManager() {
        String[] labels = AppConfig.profileLabels(this);
        String[] ids = AppConfig.profileIds(this);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Comptes Blue Magic")
                .setItems(labels, (ignored, index) -> {
                    if (index < 0 || index >= ids.length) return;
                    if (ids[index].equals(AppConfig.profileId(this))) {
                        showSimSlotChooser();
                        return;
                    }
                    if (AppConfig.activateProfile(this, ids[index])) recreate();
                })
                .setPositiveButton("Ajouter", null)
                .setNeutralButton("Supprimer l’actif", null)
                .setNegativeButton("Fermer", null)
                .create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                dialog.dismiss();
                showPairingScreen(true);
            });
            dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                if (!canModifyActiveProfile()) return;
                new AlertDialog.Builder(this)
                        .setTitle("Supprimer " + AppConfig.nodeCode(this) + " ?")
                        .setMessage("Le Robot sera d’abord arrêté sur le serveur, puis le compte et son PIN chiffré seront retirés de ce téléphone.")
                        .setPositiveButton("SUPPRIMER", (confirm, which) -> deleteActiveProfileSafely())
                        .setNegativeButton("Annuler", null)
                        .show();
            });
        });
        dialog.show();
    }

    private void showSimSlotChooser() {
        String[] slots = SimCallManager.slotLabels(this);
        int[] selected = {Math.min(AppConfig.simSlot(this), slots.length - 1)};
        new AlertDialog.Builder(this)
                .setTitle("SIM utilisée par " + AppConfig.nodeCode(this))
                .setSingleChoiceItems(slots, selected[0], (dialog, which) -> selected[0] = which)
                .setPositiveButton("ENREGISTRER", (dialog, which) -> {
                    if (!canModifyActiveProfile()) return;
                    AppConfig.updateActiveSimSlot(this, selected[0]);
                    confirmAndBindCurrentSim();
                    refreshNativeStatus();
                })
                .setNegativeButton("Annuler", null)
                .show();
    }

    private boolean canModifyActiveProfile() {
        if (PendingCommandStore.get(this, AppConfig.profileId(this)) != null) {
            toast("Ce compte exécute une commande : attendez sa fin avant de le modifier.");
            return false;
        }
        return true;
    }

    private boolean isActiveUssdForCurrentProfile() {
        JSONObject pending = PendingCommandStore.get(this, AppConfig.profileId(this));
        if (pending == null) return false;
        String state = pending.optString("local_state", PendingCommandStore.LEASED);
        return !PendingCommandStore.REPORT_PENDING.equals(state);
    }

    private void deleteActiveProfileSafely() {
        final String profileId = AppConfig.profileId(this);
        if (profileId.isEmpty()) return;
        AppConfig.setRobotEnabled(this, profileId, false);
        RobotService.stop(this, profileId);
        toast("Arrêt du Robot et suppression du compte…");
        new Thread(() -> {
            try {
                ApiClient.forProfile(this, profileId).heartbeat();
            } catch (Exception ignored) {
                // La suppression locale reste possible hors réseau. La reprise par preuve de la
                // même SIM physique neutralisera ensuite cet éventuel propriétaire fantôme.
            }
            runOnUiThread(() -> {
                AppConfig.removeActiveProfile(this);
                recreate();
            });
        }).start();
    }

    private void showModeSwitcher() {
        if (isActiveUssdForCurrentProfile()) {
            toast("Une transaction est en cours sur ce compte. Attendez sa fin avant de changer de mode.");
            return;
        }
        final String targetMode = AppConfig.isRobotMode(this) ? "REMOTE" : "ROBOT";
        if ("REMOTE".equals(targetMode)) {
            new AlertDialog.Builder(this)
                    .setTitle("Passer en mode Remote ?")
                    .setMessage("Ce compte cessera de recevoir les commandes USSD, mais les autres Robots du téléphone resteront actifs.")
                    .setPositiveButton("PASSER EN REMOTE", (dialog, which) ->
                            changeActiveMode("REMOTE"))
                    .setNegativeButton("Annuler", null)
                    .show();
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Entrer dans le hall Robot ?")
                .setMessage("Le compte passera dans l’espace Robot sans démarrer et sans exiger immédiatement les autorisations. Dans ☰ GÉRER, accordez ensuite les autorisations, choisissez le slot, liez la SIM physique, enregistrez le PIN puis touchez DÉMARRER ROBOT. Vous pourrez revenir en Remote à tout moment.")
                .setPositiveButton("ENTRER DANS LE HALL ROBOT", (dialog, which) ->
                        changeActiveMode("ROBOT"))
                .setNegativeButton("Annuler", null)
                .show();
    }

    private void showPairingRepairDialog() {
        if (isActiveUssdForCurrentProfile()) {
            toast("Attendez la fin de la transaction avant de réparer l’appairage.");
            return;
        }
        LinearLayout content = verticalContainer();
        content.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText apiUrl = field("Adresse du serveur Blue Magic", AppConfig.apiUrl(this), false);
        String savedSecret = "";
        try {
            savedSecret = SecurePairingStore.read(this);
        } catch (Exception ignored) {
        }
        EditText pairingSecret = field("Secret d’appairage", savedSecret, true);
        CheckBox reveal = new CheckBox(this);
        reveal.setText("Afficher le secret d’appairage");
        reveal.setTextColor(Color.WHITE);
        reveal.setOnCheckedChangeListener((button, checked) -> {
            pairingSecret.setInputType(InputType.TYPE_CLASS_TEXT | (checked
                    ? InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                    : InputType.TYPE_TEXT_VARIATION_PASSWORD));
            pairingSecret.setSelection(pairingSecret.length());
        });
        TextView feedback = help("Cette réparation conserve le PIN, la SIM, le mode et les autres comptes. Elle remplace seulement l’adresse et le jeton de ce compte.");
        content.addView(apiUrl);
        content.addView(pairingSecret);
        content.addView(reveal);
        content.addView(feedback);

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle("Appairage de " + AppConfig.nodeCode(this))
                .setView(content)
                .setPositiveButton("RÉPARER", null)
                .setNegativeButton("Annuler", null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    String endpoint = AppConfig.normalizeApiUrl(apiUrl.getText().toString());
                    String secret = pairingSecret.getText().toString();
                    if (!endpoint.toLowerCase().startsWith("https://") || secret.length() < 24) {
                        feedback.setText("Vérifiez l’adresse HTTPS et le secret d’appairage.");
                        return;
                    }
                    dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(false);
                    feedback.setText("Vérification et renouvellement du jeton…");
                    new Thread(() -> {
                        try {
                            JSONObject payload = new JSONObject();
                            payload.put("node_code", AppConfig.nodeCode(this));
                            payload.put("phone_number", AppConfig.phoneNumber(this));
                            payload.put("parent_node_code", AppConfig.parentNode(this));
                            payload.put("role", AppConfig.role(this));
                            payload.put("mode", AppConfig.mode(this));
                            payload.put("pairing_secret", secret);
                            payload.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
                            String profileId = AppConfig.profileId(this);
                            payload.put("replace_device_id", AppConfig.serverDeviceId(this, profileId));
                            SimIdentityManager.Verification sim =
                                    SimIdentityManager.verify(this, profileId);
                            payload.put("repair_sim_verified", sim.valid);
                            payload.put("repair_sim_fingerprint", sim.attestation());
                            payload.put("repair_robot_enabled", AppConfig.robotEnabled(this, profileId));
                            payload.put("sim_slot", Math.max(0, AppConfig.simSlot(this, profileId)));
                            JSONObject data = new ApiClient(this, endpoint, "").pair(payload);
                            String token = data.optString("device_token", "");
                            String serverDeviceId = data.optString("device_id", "");
                            String canonicalNode = data.optString("node_code", AppConfig.nodeCode(this));
                            if (!AppConfig.repairActivePairing(this, serverDeviceId, token,
                                    canonicalNode, endpoint)) {
                                throw new IllegalStateException("Impossible d’enregistrer le nouveau jeton.");
                            }
                            SecurePairingStore.save(this, secret);
                            runOnUiThread(() -> {
                                dialog.dismiss();
                                Toast.makeText(this, "Appairage réparé sans supprimer le compte.", Toast.LENGTH_LONG).show();
                                recreate();
                            });
                        } catch (Exception error) {
                            runOnUiThread(() -> {
                                dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(true);
                                feedback.setText("Échec : " + readable(error));
                            });
                        }
                    }).start();
                }));
        dialog.show();
    }

    private void changeActiveMode(String mode) {
        toast("Changement de mode en cours…");
        new Thread(() -> {
            try {
                if ("REMOTE".equals(mode)) {
                    updateDeviceModeCompat(mode);
                    AppConfig.setRobotEnabled(this, false);
                    AppConfig.updateActiveMode(this, mode);
                    RobotService.stop(this);
                } else {
                    // Entrer dans le hall Robot ne donne aucun droit d'exécution. L'élection ne
                    // se fera qu'après autorisations, liaison de la SIM et pression sur DÉMARRER.
                    updateDeviceModeCompat(mode);
                    AppConfig.setRobotEnabled(this, false);
                    if (!AppConfig.updateActiveMode(this, mode)) {
                        throw new IllegalStateException("Le profil local n’a pas pu être enregistré.");
                    }
                }
                runOnUiThread(() -> {
                    Toast.makeText(this, "ROBOT".equals(mode)
                                    ? "Hall Robot ouvert. Configurez les autorisations et liez la SIM avant de démarrer."
                                    : "Mode Remote activé sur ce compte.",
                            Toast.LENGTH_LONG).show();
                    recreate();
                });
            } catch (Exception error) {
                if ("ROBOT".equals(mode)) AppConfig.setRobotEnabled(this, false);
                runOnUiThread(() -> new AlertDialog.Builder(this)
                        .setTitle("ROBOT".equals(mode) ? "Hall Robot indisponible" : "Changement refusé")
                        .setMessage(readable(error))
                        .setPositiveButton("COMPRIS", null)
                        .show());
            }
        }).start();
    }

    private void updateDeviceModeCompat(String mode) throws Exception {
        try {
            new ApiClient(this).updateDeviceMode(mode);
            return;
        } catch (ApiClient.ApiException error) {
            if (!"UNKNOWN_ACTION".equals(error.code) && !"AUTH_INVALID".equals(error.code)) throw error;
        }

        String secret = SecurePairingStore.read(this);
        if (secret.length() < 24) {
            throw new IllegalStateException("Le Worker est ancien. Ouvrez « Vérifier / réparer l’appairage » et saisissez le secret.");
        }
        JSONObject payload = new JSONObject();
        payload.put("node_code", AppConfig.nodeCode(this));
        payload.put("phone_number", AppConfig.phoneNumber(this));
        payload.put("parent_node_code", AppConfig.parentNode(this));
        payload.put("role", AppConfig.role(this));
        payload.put("mode", mode);
        payload.put("pairing_secret", secret);
        payload.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
        String profileId = AppConfig.profileId(this);
        payload.put("replace_device_id", AppConfig.serverDeviceId(this, profileId));
        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, profileId);
        payload.put("repair_sim_verified", sim.valid);
        payload.put("repair_sim_fingerprint", sim.attestation());
        payload.put("repair_robot_enabled", AppConfig.robotEnabled(this, profileId));
        payload.put("sim_slot", Math.max(0, AppConfig.simSlot(this, profileId)));
        JSONObject data = new ApiClient(this, AppConfig.apiUrl(this), "").pair(payload);
        if (!AppConfig.repairActivePairing(this, data.optString("device_id", ""),
                data.optString("device_token", ""),
                data.optString("node_code", AppConfig.nodeCode(this)), AppConfig.apiUrl(this))) {
            throw new IllegalStateException("Le nouveau mode n’a pas pu être enregistré localement.");
        }
    }

    private void showPendingOperations() {
        String[] allIds = AppConfig.profileIds(this);
        String[] allLabels = AppConfig.profileLabels(this);
        List<String> ids = new ArrayList<>();
        List<String> labels = new ArrayList<>();
        for (int i = 0; i < allIds.length; i++) {
            JSONObject pending = PendingCommandStore.get(this, allIds[i]);
            if (pending == null) continue;
            ids.add(allIds[i]);
            String state = pending.optString("local_state", PendingCommandStore.LEASED);
            String publicId = pending.optString("public_id", "");
            labels.add(allLabels[i] + "\n" + state + (publicId.isEmpty() ? "" : " • " + publicId));
        }
        if (ids.isEmpty()) {
            toast("Aucune opération locale ne bloque ce téléphone.");
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Opérations locales à libérer")
                .setItems(labels.toArray(new String[0]), (dialog, which) -> {
                    String profileId = ids.get(which);
                    JSONObject pending = PendingCommandStore.get(this, profileId);
                    String state = pending == null ? "" : pending.optString("local_state", "");
                    new AlertDialog.Builder(this)
                            .setTitle("Libérer cette file ?")
                            .setMessage(PendingCommandStore.REPORT_PENDING.equals(state)
                                    ? "Une synchronisation immédiate sera tentée, mais la preuve locale sera conservée si le serveur ne répond pas. Cet état ne bloque plus les autres SIM."
                                    : "La fenêtre USSD sera fermée si possible. Si la composition a déjà commencé, l’opération sera classée À VÉRIFIER pour éviter toute répétition.")
                            .setPositiveButton("LIBÉRER", (confirm, button) -> {
                                RobotService.cancelPending(this, profileId);
                                toast("Annulation demandée pour cette SIM. Les autres files restent actives.");
                            })
                            .setNegativeButton("Garder", null)
                            .show();
                })
                .setNegativeButton("Fermer", null)
                .show();
    }

    private void prepareRobotPermissions() {
        requestCorePermissions();
        if (!BlueAccessibilityService.isEnabled(this)) {
            toast("Dans Accessibilité : touchez Blue Magic, puis activez « Utiliser le service ».");
            openAccessibilitySettings();
            return;
        }
        try {
            toast("Dans Batterie : ouvrez Blue Magic et choisissez « Sans restriction » si ce choix existe.");
            startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
        } catch (Exception ignored) {
            toast("Ouvrez Batterie > Blue Magic > Sans restriction.");
        }
    }

    private void requestCorePermissions() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return;
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE,
                    Manifest.permission.READ_PHONE_STATE, Manifest.permission.READ_PHONE_NUMBERS,
                    Manifest.permission.RECEIVE_SMS,
                    Manifest.permission.POST_NOTIFICATIONS}, REQUEST_CORE_PERMISSIONS);
        } else if (Build.VERSION.SDK_INT >= 26) {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE,
                    Manifest.permission.READ_PHONE_STATE, Manifest.permission.READ_PHONE_NUMBERS,
                    Manifest.permission.RECEIVE_SMS}, REQUEST_CORE_PERMISSIONS);
        } else {
            requestPermissions(new String[]{Manifest.permission.CALL_PHONE,
                    Manifest.permission.READ_PHONE_STATE, Manifest.permission.RECEIVE_SMS}, REQUEST_CORE_PERMISSIONS);
        }
    }

    private boolean startRobotSafely() {
        if (robotStartInProgress) {
            toast("Vérification du Robot déjà en cours…");
            return false;
        }
        requestCorePermissions();
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            toast("Accordez Téléphone et État du téléphone, puis touchez de nouveau DÉMARRER ROBOT.");
            return false;
        }
        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, AppConfig.profileId(this));
        if (!sim.valid) {
            AppConfig.setRobotEnabled(this, false);
            if (SimIdentityManager.BINDING_REQUIRED.equals(sim.code)
                    || SimIdentityManager.SIM_CHANGED.equals(sim.code)) {
                confirmAndBindCurrentSim();
            } else {
                toast("Robot refusé : " + sim.message);
            }
            refreshNativeStatus();
            return false;
        }
        AppConfig.setRobotEnabled(this, true);
        robotStartInProgress = true;
        refreshNativeStatus();
        new Thread(() -> {
            try {
                new ApiClient(this).heartbeat(true);
                RobotService.start(this);
                robotStartInProgress = false;
                runOnUiThread(() -> {
                    if (!BlueAccessibilityService.isEnabled(this)) {
                        toast("Robot démarré pour TEST_NUMBER. Activez l’Accessibilité avant tout achat ou vente.");
                    } else {
                        toast("Robot démarré sur la SIM vérifiée de ce téléphone.");
                    }
                    refreshNativeStatus();
                });
            } catch (Exception error) {
                AppConfig.setRobotEnabled(this, false);
                robotStartInProgress = false;
                runOnUiThread(() -> {
                    refreshNativeStatus();
                    if (error instanceof ApiClient.ApiException
                            && "ROBOT_ALREADY_ACTIVE".equals(((ApiClient.ApiException) error).code)) {
                        offerVerifiedSimTakeover(sim);
                        return;
                    }
                    new AlertDialog.Builder(this)
                            .setTitle("Robot non démarré")
                            .setMessage(readable(error))
                            .setPositiveButton("COMPRIS", null)
                            .show();
                });
            }
        }).start();
        return true;
    }

    private void offerVerifiedSimTakeover(SimIdentityManager.Verification expectedSim) {
        new AlertDialog.Builder(this)
                .setTitle("Robot existant ou fantôme")
                .setMessage("Un autre appareil est encore enregistré comme Robot de ce compte. Si la SIM officielle est physiquement dans ce téléphone et dans le slot choisi, Blue Magic peut la vérifier de nouveau, arrêter uniquement l’ancien Robot lié à cette même SIM, puis démarrer celui-ci. Si la vérification échoue, rien ne sera remplacé.")
                .setPositiveButton("VÉRIFIER LA SIM ET REMPLACER", (dialog, which) ->
                        replaceRobotWithVerifiedSim(expectedSim))
                .setNegativeButton("GARDER L’ANCIEN ROBOT", null)
                .show();
    }

    private void replaceRobotWithVerifiedSim(SimIdentityManager.Verification expectedSim) {
        final String profileId = AppConfig.profileId(this);
        final SimIdentityManager.Verification current =
                SimIdentityManager.verify(this, profileId);
        if (!current.valid || !current.attestation().equals(expectedSim.attestation())) {
            AppConfig.setRobotEnabled(this, false);
            toast("Remplacement refusé : la SIM physique ou le slot ne correspond plus à ce compte.");
            refreshNativeStatus();
            return;
        }
        robotStartInProgress = true;
        toast("Preuve de la SIM confirmée. Remplacement du Robot fantôme…");
        new Thread(() -> {
            try {
                new ApiClient(this).activateRobot(current, AppConfig.simSlot(this), true);
                AppConfig.setRobotEnabled(this, true);
                RobotService.start(this);
                robotStartInProgress = false;
                runOnUiThread(() -> {
                    toast("Ancien Robot de cette SIM arrêté. Ce téléphone est maintenant le Robot actif.");
                    refreshNativeStatus();
                });
            } catch (Exception error) {
                AppConfig.setRobotEnabled(this, false);
                robotStartInProgress = false;
                runOnUiThread(() -> {
                    refreshNativeStatus();
                    new AlertDialog.Builder(this)
                            .setTitle("Remplacement refusé")
                            .setMessage(readable(error))
                            .setPositiveButton("COMPRIS", null)
                            .show();
                });
            }
        }).start();
    }

    private void confirmAndBindCurrentSim() {
        requestCorePermissions();
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            toast("Accordez État du téléphone, puis recommencez la vérification SIM.");
            return;
        }
        String profileId = AppConfig.profileId(this);
        SimIdentityManager.Verification current = SimIdentityManager.verify(this, profileId);
        if (current.valid) {
            AppConfig.clearCallRoute(this, profileId);
            toast("SIM vérifiée pour " + AppConfig.nodeCode(this)
                    + " dans le slot " + (AppConfig.simSlot(this) + 1)
                    + ". La route Téléphone sera résolue au moment de l’USSD.");
            refreshNativeStatus();
            return;
        }
        if (!SimIdentityManager.BINDING_REQUIRED.equals(current.code)
                && !SimIdentityManager.SIM_CHANGED.equals(current.code)) {
            AppConfig.setRobotEnabled(this, false);
            toast("Liaison refusée : " + current.message);
            refreshNativeStatus();
            return;
        }

        String message = "Vérifiez physiquement :\n\nCompte : " + AppConfig.nodeCode(this)
                + "\nNuméro Camtel : " + AppConfig.phoneNumber(this)
                + "\nEmplacement : SIM " + (AppConfig.simSlot(this) + 1)
                + (current.carrier.isEmpty() ? "" : "\nSIM détectée : " + current.carrier)
                + "\n\nEn confirmant, ce Robot refusera ensuite toute autre SIM dans ce slot.";
        new AlertDialog.Builder(this)
                .setTitle("Lier cette SIM au Robot ?")
                .setMessage(message)
                .setPositiveButton("J’AI VÉRIFIÉ — LIER", (dialog, which) -> {
                    SimIdentityManager.Verification bound =
                            SimIdentityManager.bindSelectedSim(this, profileId);
                    if (!bound.valid) {
                        AppConfig.setRobotEnabled(this, false);
                        toast("Liaison refusée : " + bound.message);
                        refreshNativeStatus();
                        return;
                    }
                    AppConfig.clearCallRoute(this, profileId);
                    toast("SIM liée avec succès. Vous pouvez démarrer le Robot.");
                    refreshNativeStatus();
                })
                .setNegativeButton("Annuler", null)
                .show();
    }

    private void openAccessibilitySettings() {
        toast("Cherchez Blue Magic, ouvrez-le, puis activez « Utiliser le service ».");
        startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS));
    }

    private void refreshNativeStatus() {
        if (nativeStatus == null) return;
        boolean robotMode = AppConfig.isRobotMode(this);
        if (!robotMode) {
            // A Remote is a control terminal. SIM verification and Accessibility are Robot-only
            // requirements and showing them here was both confusing and wasteful on short screens.
            nativeStatus.setText(AppConfig.nodeCode(this)
                    + " • REMOTE • Télécommande prête"
                    + (AppConfig.profileCount(this) > 1
                    ? " • " + AppConfig.profileCount(this) + " comptes sur ce téléphone" : ""));
            nativeStatus.setTextColor(CYAN);
            return;
        }

        String profileId = AppConfig.profileId(this);
        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, profileId);
        boolean robotEnabled = AppConfig.robotEnabled(this);
        boolean accessibility = BlueAccessibilityService.isEnabled(this);
        if (robotEnabled && !sim.valid) {
            AppConfig.setRobotEnabled(this, false);
            RobotService.stop(this);
            robotEnabled = false;
        }

        StringBuilder status = new StringBuilder();
        status.append(AppConfig.nodeCode(this))
                .append(" • ROBOT • SIM ").append(AppConfig.simSlot(this) + 1)
                .append(sim.valid ? " VÉRIFIÉE" : " BLOQUÉE")
                .append(" • ").append(robotEnabled ? "ACTIF" : "ARRÊTÉ");
        int activeCount = AppConfig.enabledRobotCount(this);
        if (activeCount > 1) status.append(" • ").append(activeCount).append(" Robots locaux");

        if (sim != null && !sim.valid) {
            status.append("\n⛔ ").append(sim.message);
        } else if (AppConfig.pinBlocked(this)) {
            status.append("\n⛔ PIN BLOQUÉ : corriger avant toute nouvelle transaction");
        } else if (robotEnabled && !accessibility) {
            status.append("\n⚠ Accessibilité à activer avant achat/vente • TEST_NUMBER reste direct");
        } else if (robotEnabled && DeviceLockState.isSecurelyLocked(this)) {
            status.append("\n🔒 Écran sécurisé : déverrouillage humain requis avant USSD");
        } else if (robotEnabled && DeviceLockState.isInsecurelyLocked(this)) {
            status.append("\n✨ Verrou simple : assistance ponctuelle uniquement si une commande arrive");
        }

        nativeStatus.setText(status.toString());
        nativeStatus.setTextColor((!sim.valid || AppConfig.pinBlocked(this)
                || (robotEnabled && !accessibility)) ? GOLD : CYAN);
    }

    @Override
    protected void onResume() {
        super.onResume();
        applyRobotWindowPolicy();
        if (AppConfig.anyRobotEnabled(this)) {
            View root = webView == null ? nativeStatus : webView;
            if (root != null) root.postDelayed(() -> RobotService.startEnabled(this), 250L);
        }
        refreshNativeStatus();
    }

    private void applyRobotWindowPolicy() {
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
                | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(false);
            setTurnScreenOn(false);
        }
    }

    @Override
    protected void onDestroy() {
        disposeWebView();
        super.onDestroy();
    }

    private void disposeWebView() {
        if (webView == null) return;
        webView.removeJavascriptInterface("AndroidBridge");
        webView.stopLoading();
        webView.destroy();
        webView = null;
    }

    public final class NativeBridge {
        @JavascriptInterface
        public String getConfiguration() {
            try {
                JSONObject value = new JSONObject();
                value.put("node_code", AppConfig.nodeCode(MainActivity.this));
                value.put("phone_number", AppConfig.phoneNumber(MainActivity.this));
                value.put("profile_id", AppConfig.profileId(MainActivity.this));
                value.put("role", AppConfig.role(MainActivity.this));
                value.put("parent_node_code", AppConfig.parentNode(MainActivity.this));
                value.put("mode", AppConfig.displayMode(AppConfig.mode(MainActivity.this)));
                value.put("sim_slot", AppConfig.simSlot(MainActivity.this));
                value.put("robot_enabled", AppConfig.robotEnabled(MainActivity.this));
                value.put("pin_blocked", AppConfig.pinBlocked(MainActivity.this));
                value.put("accessibility_enabled", BlueAccessibilityService.isEnabled(MainActivity.this));
                value.put("accessibility_connected", BlueAccessibilityService.isConnected());
                value.put("pin_configured", SecurePinStore.hasPin(MainActivity.this,
                        AppConfig.profileId(MainActivity.this)));
                SimIdentityManager.Verification sim = AppConfig.isRobotMode(MainActivity.this)
                        ? SimIdentityManager.verify(MainActivity.this,
                        AppConfig.profileId(MainActivity.this)) : null;
                value.put("sim_verified", sim == null || sim.valid);
                value.put("sim_status", sim == null ? "NOT_REQUIRED" : sim.code);
                return value.toString();
            } catch (Exception ignored) {
                return "{}";
            }
        }

        @JavascriptInterface
        public void previewCommand(String requestType, String targetNode, String targetPhone,
                                   String amount, String clientRequestId, String capacityCheckId,
                                   String commandArgument) {
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("request_type", requestType == null ? "" : requestType);
                    payload.put("target_node_code", targetNode == null ? "" : targetNode.trim().toUpperCase());
                    payload.put("target_phone", targetPhone == null ? "" : targetPhone.trim());
                    payload.put("amount", amount == null ? "" : amount.trim());
                    payload.put("client_request_id", validRequestId(clientRequestId));
                    payload.put("capacity_check_id", capacityCheckId == null ? "" : capacityCheckId.trim());
                    payload.put("transaction_id", commandArgument == null ? "" : commandArgument.trim());
                    JSONObject data = new ApiClient(MainActivity.this).previewCommand(payload);
                    callback("onCommandPreview", data);
                } catch (Exception error) {
                    callbackError("onCommandPreview", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void previewCommandWithCommissionRate(String requestType, String targetNode, String targetPhone,
                                                     String amount, String clientRequestId, String capacityCheckId,
                                                     String commandArgument, int commissionRateBps) {
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("request_type", requestType == null ? "" : requestType);
                    payload.put("target_node_code", targetNode == null ? "" : targetNode.trim().toUpperCase());
                    payload.put("target_phone", targetPhone == null ? "" : targetPhone.trim());
                    payload.put("amount", amount == null ? "" : amount.trim());
                    payload.put("client_request_id", validRequestId(clientRequestId));
                    payload.put("capacity_check_id", capacityCheckId == null ? "" : capacityCheckId.trim());
                    payload.put("transaction_id", commandArgument == null ? "" : commandArgument.trim());
                    payload.put("commission_rate_bps", commissionRateBps);
                    callback("onCommandPreview", new ApiClient(MainActivity.this).previewCommand(payload));
                } catch (Exception error) { callbackError("onCommandPreview", error); }
            }).start();
        }

        @JavascriptInterface
        public void createCommand(String requestType, String targetNode, String targetPhone,
                                  String amount, String clientRequestId,
                                  String confirmationFingerprint, String capacityCheckId,
                                  String commandArgument) {
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("request_type", requestType == null ? "" : requestType);
                    payload.put("target_node_code", targetNode == null ? "" : targetNode.trim().toUpperCase());
                    payload.put("target_phone", targetPhone == null ? "" : targetPhone.trim());
                    payload.put("amount", amount == null ? "" : amount.trim());
                    payload.put("client_request_id", validRequestId(clientRequestId));
                    payload.put("confirmation_fingerprint", confirmationFingerprint == null
                            ? "" : confirmationFingerprint.trim().toLowerCase(Locale.ROOT));
                    payload.put("capacity_check_id", capacityCheckId == null ? "" : capacityCheckId.trim());
                    payload.put("transaction_id", commandArgument == null ? "" : commandArgument.trim());
                    JSONObject data = new ApiClient(MainActivity.this).createCommand(payload);
                    callback("onCommandCreated", data);
                    // Sur un téléphone qui héberge aussi le Robot, supprimer toute attente du
                    // watchdog et déclencher immédiatement un cycle après la création.
                    if (AppConfig.anyRobotEnabled(MainActivity.this)) {
                        RobotService.startEnabled(MainActivity.this);
                    }
                } catch (Exception error) {
                    callbackError("onCommandCreated", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void createCommandWithCommissionRate(String requestType, String targetNode, String targetPhone,
                                                     String amount, String clientRequestId,
                                                     String confirmationFingerprint, String capacityCheckId,
                                                     String commandArgument, int commissionRateBps) {
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("request_type", requestType == null ? "" : requestType);
                    payload.put("target_node_code", targetNode == null ? "" : targetNode.trim().toUpperCase());
                    payload.put("target_phone", targetPhone == null ? "" : targetPhone.trim());
                    payload.put("amount", amount == null ? "" : amount.trim());
                    payload.put("client_request_id", validRequestId(clientRequestId));
                    payload.put("confirmation_fingerprint", confirmationFingerprint == null ? "" : confirmationFingerprint.trim().toLowerCase(Locale.ROOT));
                    payload.put("capacity_check_id", capacityCheckId == null ? "" : capacityCheckId.trim());
                    payload.put("transaction_id", commandArgument == null ? "" : commandArgument.trim());
                    payload.put("commission_rate_bps", commissionRateBps);
                    callback("onCommandCreated", new ApiClient(MainActivity.this).createCommand(payload));
                    if (AppConfig.anyRobotEnabled(MainActivity.this)) RobotService.startEnabled(MainActivity.this);
                } catch (Exception error) { callbackError("onCommandCreated", error); }
            }).start();
        }

        @JavascriptInterface
        public void synchronizeNow() {
            RobotService.forceSync(MainActivity.this);
            runOnUiThread(() -> toast("Synchronisation de tous les comptes relancée immédiatement."));
        }

        @JavascriptInterface
        public void checkPurchaseCapacity(String amount, String clientRequestId) {
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("request_type", "REQUEST_SUPPLY");
                    payload.put("amount", amount == null ? "" : amount.trim());
                    payload.put("client_request_id", validRequestId(clientRequestId));
                    callback("onPurchaseCapacity", new ApiClient(MainActivity.this)
                            .checkPurchaseCapacity(payload));
                    if (AppConfig.anyRobotEnabled(MainActivity.this)) {
                        RobotService.startEnabled(MainActivity.this);
                    }
                } catch (Exception error) {
                    callbackError("onPurchaseCapacity", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void getPurchaseCapacityStatus(String capacityCheckId) {
            new Thread(() -> {
                try {
                    callback("onPurchaseCapacity", new ApiClient(MainActivity.this)
                            .purchaseCapacityStatus(capacityCheckId));
                } catch (Exception error) {
                    callbackError("onPurchaseCapacity", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void loadDashboard() {
            new Thread(() -> {
                try {
                    callback("onDashboard", new ApiClient(MainActivity.this).dashboard());
                } catch (Exception error) {
                    callbackError("onDashboard", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void refreshDashboardLive() {
            new Thread(() -> {
                try {
                    JSONObject audit = new ApiClient(MainActivity.this).networkBalanceAudit();
                    audit.put("_action", "network_balance_audit");
                    callback("onPlatformAction", audit);
                    callback("onDashboard", new ApiClient(MainActivity.this).dashboard());
                    if (AppConfig.anyRobotEnabled(MainActivity.this)) {
                        RobotService.startEnabled(MainActivity.this);
                    }
                } catch (Exception error) {
                    callbackError("onPlatformAction", error);
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
        public void cancelCommand(String commandId) {
            new Thread(() -> {
                try {
                    callback("onCommandCancelled", new ApiClient(MainActivity.this).cancelCommand(commandId));
                } catch (Exception error) {
                    callbackError("onCommandCancelled", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void startRobot() {
            runOnUiThread(() -> startRobotSafely());
        }

        @JavascriptInterface
        public void stopRobot() {
            runOnUiThread(() -> {
                RobotService.stop(MainActivity.this);
                refreshNativeStatus();
            });
        }

        @JavascriptInterface
        public void openManagement() {
            runOnUiThread(() -> setManagementOpen(true));
        }

        @JavascriptInterface
        public void openAccounts() {
            runOnUiThread(() -> showAccountManager());
        }

        @JavascriptInterface
        public void openPinSettings() {
            runOnUiThread(() -> showPinEditorDialog());
        }

        @JavascriptInterface
        public void changeOperatorPin() {
            runOnUiThread(() -> showOperatorPinChangeDialog());
        }

        @JavascriptInterface
        public void resetOperatorPin() {
            runOnUiThread(() -> confirmResetOperatorPin());
        }

        @JavascriptInterface
        public void openBatteryOptimizationSettings() {
            runOnUiThread(MainActivity.this::openBatterySettings);
        }

        @JavascriptInterface
        public void verifySim() {
            runOnUiThread(() -> confirmAndBindCurrentSim());
        }

        @JavascriptInterface
        public void prepareRobotPermissions() {
            runOnUiThread(() -> MainActivity.this.prepareRobotPermissions());
        }

        @JavascriptInterface
        public void platformAction(String action, String payloadJson) {
            new Thread(() -> {
                try {
                    JSONObject payload = payloadJson == null || payloadJson.trim().isEmpty()
                            ? new JSONObject() : new JSONObject(payloadJson);
                    JSONObject data = new ApiClient(MainActivity.this).platformAction(action, payload);
                    data.put("_action", action == null ? "" : action);
                    callback("onPlatformAction", data);
                } catch (Exception error) {
                    callbackError("onPlatformAction", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void executeRawUSSD(String raw) {
            runOnUiThread(() -> {
                try {
                    if (!AppConfig.isRobotMode(MainActivity.this)) throw new IllegalStateException("Mode Robot requis.");
                    String ussd = raw == null ? "" : raw.trim();
                    if (!ussd.matches("\\*[0-9*]{1,80}#")) throw new IllegalArgumentException("Code USSD brut invalide.");
                    String pin = SecurePinStore.read(MainActivity.this, AppConfig.profileId(MainActivity.this));
                    if (!pin.isEmpty() && ussd.contains(pin)) throw new SecurityException("Le Sandbox refuse d’exposer le PIN enregistré au JavaScript.");
                    SimCallManager.placeUssdCall(MainActivity.this, ussd, AppConfig.profileId(MainActivity.this));
                    toast("Commande Sandbox lancée sur la SIM sélectionnée. Lisez le retour Blue dans la fenêtre Téléphone.");
                } catch (Exception error) { toast("Sandbox refusée : " + readable(error)); }
            });
        }

        @JavascriptInterface
        public void checkServerHealth() {
            new Thread(() -> {
                try {
                    callback("onServerHealth", new ApiClient(MainActivity.this).health());
                } catch (Exception error) {
                    callbackError("onServerHealth", error);
                }
            }).start();
        }

        @JavascriptInterface
        public void setFormEditing(boolean editing) {
            runOnUiThread(() -> {
                setManagementOpen(false);
                if (nativeStatus != null) nativeStatus.setVisibility(editing ? View.GONE : View.VISIBLE);
            });
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
            if (error instanceof ApiClient.ApiException) {
                data.put("code", ((ApiClient.ApiException) error).code);
            } else {
                data.put("code", error.getClass().getSimpleName());
            }
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
        applyMagicBackground(layout);
        layout.setPadding(dp(18), dp(24), dp(18), dp(24));
        return layout;
    }

    private void applyMagicBackground(View view) {
        GradientDrawable background = new GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                new int[]{Color.rgb(74, 51, 10), Color.rgb(12, 48, 96), BACKGROUND});
        background.setGradientType(GradientDrawable.LINEAR_GRADIENT);
        view.setBackground(background);
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
        ArrayAdapter<String> adapter = new ArrayAdapter<String>(this,
                android.R.layout.simple_spinner_item, values) {
            @Override
            public View getView(int position, View convertView, android.view.ViewGroup parent) {
                TextView view = (TextView) super.getView(position, convertView, parent);
                styleSpinnerText(view);
                return view;
            }

            @Override
            public View getDropDownView(int position, View convertView, android.view.ViewGroup parent) {
                TextView view = (TextView) super.getDropDownView(position, convertView, parent);
                styleSpinnerText(view);
                return view;
            }
        };
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);
        spinner.setAdapter(adapter);
        spinner.setBackgroundColor(Color.WHITE);
        return spinner;
    }

    private void styleSpinnerText(TextView view) {
        view.setTextColor(Color.BLACK);
        view.setBackgroundColor(Color.WHITE);
        view.setTextSize(16);
        view.setPadding(dp(12), dp(10), dp(12), dp(10));
    }

    private Button actionButton(String text, int color) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(color == CYAN || color == GOLD ? BACKGROUND : Color.WHITE);
        button.setBackgroundColor(color);
        button.setAllCaps(false);
        button.setTextSize(11);
        button.setPadding(dp(6), dp(3), dp(6), dp(3));
        button.setMinHeight(dp(42));
        return button;
    }

    private LinearLayout.LayoutParams weighted() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(0,
                LinearLayout.LayoutParams.WRAP_CONTENT, 1f);
        params.setMargins(dp(2), dp(3), dp(2), dp(3));
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
