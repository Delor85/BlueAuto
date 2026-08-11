package com.profitloop.blueauto;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
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

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public class MainActivity extends Activity {
    private static final int REQUEST_CORE_PERMISSIONS = 550;
    private static final int GOLD = Color.rgb(255, 205, 92);
    private static final int CYAN = Color.rgb(78, 225, 255);
    private static final int VIOLET = Color.rgb(135, 92, 255);
    private static final int SURFACE = Color.rgb(15, 37, 70);
    private static final int BACKGROUND = Color.rgb(5, 18, 42);

    private TextView nativeStatus;
    private WebView webView;
    private View managementPanel;
    private Button manageButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        AppConfig.migrateLegacyProfile(this);
        applyRobotWindowPolicy();
        if (AppConfig.isPaired(this)) showControlScreen();
        else showPairingScreen(false);
    }

    private void showPairingScreen(boolean addingAccount) {
        disposeWebView();
        ScrollView scroll = new ScrollView(this);
        applyMagicBackground(scroll);
        LinearLayout form = verticalContainer();
        scroll.addView(form);

        form.addView(title("BLUE MAGIC — APPAIRAGE SÉCURISÉ"));
        form.addView(help("Vérifiez l’adresse et le secret avant l’appairage. Le PIN Camtel reste uniquement dans le Keystore du téléphone."));

        EditText apiUrl = field("Adresse du serveur Blue Magic", AppConfig.pairingApiUrl(this), false);
        EditText nodeCode = field("Code local (ex. SU2, DSM7 ou POS5)", "", false);
        EditText phone = field("Numéro SIM du compte (9 chiffres)", "", false);
        EditText parent = field("Code nœud supérieur (vide pour un DAE)", "", false);
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
            int selectedSlot = simSlot.getSelectedItemPosition();

            if (!node.matches("[A-Z0-9/_-]{3,64}") || !sim.matches("\\d{9}") || secret.length() < 24) {
                feedback.setText("Vérifiez le code nœud, le numéro à 9 chiffres et le secret d’appairage.");
                return;
            }
            String selectedApiUrl = AppConfig.normalizeApiUrl(apiUrl.getText().toString());
            if (!selectedApiUrl.toLowerCase().startsWith("https://")) {
                feedback.setText("L’adresse du serveur doit commencer par https://");
                return;
            }
            if (("ROBOT".equals(selectedMode) || "HYBRID".equals(selectedMode)) && !pin.matches("\\d{4}")) {
                feedback.setText("Un Robot doit recevoir le PIN Camtel exact à 4 chiffres.");
                return;
            }

            pair.setEnabled(false);
            feedback.setText("Appairage avec " + selectedApiUrl + "…");
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
                    JSONObject data = new ApiClient(this, selectedApiUrl, "").pair(payload);
                    String token = data.optString("device_token", "");
                    String deviceId = data.optString("device_id", "");
                    String canonicalNode = data.optString("node_code", node);
                    if (token.isEmpty()) throw new IllegalStateException("Jeton appareil absent.");
                    AppConfig.savePairing(this, deviceId, token, canonicalNode, sim, parentNode,
                            selectedRole, selectedMode, selectedApiUrl, selectedSlot);
                    SecurePairingStore.save(this, secret);
                    if (!pin.isEmpty()) SecurePinStore.save(this, pin);
                    SimIdentityManager.Verification simVerification =
                            SimIdentityManager.bindSelectedSim(this, AppConfig.profileId(this));
                    runOnUiThread(() -> {
                        Toast.makeText(this, "REMOTE".equals(selectedMode)
                                ? "Téléphone appairé en mode Remote."
                                : simVerification.valid
                                ? "Téléphone appairé et SIM liée au bon slot."
                                : "Compte appairé, mais Robot arrêté : " + simVerification.message,
                                Toast.LENGTH_LONG).show();
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

        if (addingAccount && AppConfig.hasProfiles(this)) {
            Button cancel = actionButton("ANNULER — REVENIR AU COMPTE ACTIF", CYAN);
            cancel.setOnClickListener(v -> showControlScreen());
            form.addView(cancel);
        }

        setContentView(scroll);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void showControlScreen() {
        disposeWebView();
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        applyMagicBackground(page);
        page.setPadding(dp(10), dp(8), dp(10), dp(6));
        nativeStatus = help("");
        nativeStatus.setTextColor(CYAN);
        nativeStatus.setTextSize(12);
        nativeStatus.setPadding(dp(4), 0, dp(4), dp(3));
        page.addView(nativeStatus);

        LinearLayout compactBar = new LinearLayout(this);
        compactBar.setOrientation(LinearLayout.HORIZONTAL);
        Button accounts = actionButton("COMPTES (" + AppConfig.profileCount(this) + ")", GOLD);
        manageButton = actionButton("☰ GÉRER", VIOLET);
        compactBar.addView(accounts, weighted());
        compactBar.addView(manageButton, weighted());
        page.addView(compactBar);

        ScrollView toolsScroll = new ScrollView(this);
        toolsScroll.setFillViewport(false);
        LinearLayout tools = new LinearLayout(this);
        tools.setOrientation(LinearLayout.VERTICAL);
        tools.setPadding(dp(2), dp(3), dp(2), dp(5));
        toolsScroll.addView(tools);
        toolsScroll.setVisibility(View.GONE);
        managementPanel = toolsScroll;
        page.addView(toolsScroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(260)));

        LinearLayout accountButtons = new LinearLayout(this);
        accountButtons.setOrientation(LinearLayout.HORIZONTAL);
        Button addAccount = actionButton("AJOUTER UN COMPTE", CYAN);
        Button verifySim = actionButton("VÉRIFIER / LIER LA SIM", VIOLET);
        accountButtons.addView(addAccount, weighted());
        accountButtons.addView(verifySim, weighted());
        tools.addView(accountButtons);

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        Button prepare = actionButton("1. AUTORISATIONS", GOLD);
        Button toggle = actionButton(AppConfig.robotEnabled(this) ? "ARRÊTER ROBOT" : "2. DÉMARRER ROBOT", CYAN);
        buttons.addView(prepare, weighted());
        buttons.addView(toggle, weighted());
        if (AppConfig.isRobotMode(this)) tools.addView(buttons);

        Button switchMode = actionButton(AppConfig.isRobotMode(this)
                ? "PASSER CE COMPTE EN REMOTE" : "PASSER CE COMPTE EN ROBOT", GOLD);
        tools.addView(switchMode);

        Button repairPairing = actionButton("VÉRIFIER / RÉPARER L’APPAIRAGE", CYAN);
        tools.addView(repairPairing);

        Button pendingOperations = actionButton("FILES / ANNULER UNE OPÉRATION BLOQUÉE", GOLD);
        tools.addView(pendingOperations);

        LinearLayout pinRow = new LinearLayout(this);
        pinRow.setOrientation(LinearLayout.HORIZONTAL);
        EditText newPin = field("Nouveau PIN (4 chiffres)", "", true);
        newPin.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        Button savePin = actionButton("ENREGISTRER PIN", GOLD);
        pinRow.addView(newPin, weighted());
        pinRow.addView(savePin, weighted());
        if (AppConfig.isRobotMode(this)) tools.addView(pinRow);

        webView = new WebView(this);
        webView.setBackgroundColor(BACKGROUND);
        page.addView(webView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f));
        setContentView(page);

        accounts.setOnClickListener(v -> showAccountManager());
        manageButton.setOnClickListener(v -> {
            boolean opening = managementPanel.getVisibility() != View.VISIBLE;
            managementPanel.setVisibility(opening ? View.VISIBLE : View.GONE);
            manageButton.setText(opening ? "✕ FERMER" : "☰ GÉRER");
        });
        addAccount.setOnClickListener(v -> {
            showPairingScreen(true);
        });
        verifySim.setOnClickListener(v -> confirmAndBindCurrentSim());

        prepare.setOnClickListener(v -> prepareRobotPermissions());
        switchMode.setOnClickListener(v -> showModeSwitcher());
        repairPairing.setOnClickListener(v -> showPairingRepairDialog());
        pendingOperations.setOnClickListener(v -> showPendingOperations());
        toggle.setOnClickListener(v -> {
            if (AppConfig.robotEnabled(this)) {
                if (isActiveUssdForCurrentProfile()) {
                    toast("Une transaction USSD est en cours. Attendez son résultat avant d’arrêter ce Robot.");
                    return;
                }
                RobotService.stop(this);
                toggle.setText("2. DÉMARRER ROBOT");
            } else {
                if (!AppConfig.isRobotMode(this)) {
                    toast("Ce compte est en mode REMOTE. Activez un compte ROBOT pour exécuter l’USSD.");
                    return;
                }
                if (!SecurePinStore.hasPin(this)) {
                    toast("Enregistrez d’abord le PIN Camtel.");
                    return;
                }
                if (!startRobotSafely()) return;
                toggle.setText("ARRÊTER ROBOT");
            }
            applyRobotWindowPolicy();
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
                        .setMessage("Le compte sera retiré uniquement de ce téléphone. Son PIN local chiffré sera effacé.")
                        .setPositiveButton("SUPPRIMER", (confirm, which) -> {
                            RobotService.stop(this);
                            AppConfig.removeActiveProfile(this);
                            recreate();
                        })
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
                            changeActiveMode("REMOTE", "", AppConfig.simSlot(this)))
                    .setNegativeButton("Annuler", null)
                    .show();
            return;
        }

        LinearLayout content = verticalContainer();
        content.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText pin = field("PIN Camtel 4 chiffres", "", true);
        pin.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        Spinner slot = spinner(SimCallManager.slotLabels(this));
        slot.setSelection(Math.min(AppConfig.simSlot(this), slot.getCount() - 1));
        content.addView(help(SecurePinStore.hasPin(this)
                ? "Le PIN déjà chiffré sera conservé. Choisissez seulement la SIM."
                : "Saisissez le PIN une fois et choisissez la SIM à automatiser."));
        if (!SecurePinStore.hasPin(this)) content.addView(pin);
        content.addView(label("SIM utilisée par ce Robot"));
        content.addView(slot);
        new AlertDialog.Builder(this)
                .setTitle("Passer en mode Robot")
                .setView(content)
                .setPositiveButton("PASSER EN ROBOT", (dialog, which) -> {
                    String value = pin.getText().toString().trim();
                    if (!SecurePinStore.hasPin(this) && !value.matches("\\d{4}")) {
                        toast("Le PIN Camtel doit contenir exactement 4 chiffres.");
                        return;
                    }
                    changeActiveMode("ROBOT", value, slot.getSelectedItemPosition());
                })
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

    private void changeActiveMode(String mode, String newPin, int simSlot) {
        toast("Changement de mode en cours…");
        new Thread(() -> {
            try {
                updateDeviceModeCompat(mode);
                if (!newPin.isEmpty()) SecurePinStore.save(this, newPin);
                AppConfig.updateActiveSimSlot(this, simSlot);
                AppConfig.updateActiveMode(this, mode);
                SimIdentityManager.Verification sim = null;
                if ("REMOTE".equals(mode)) {
                    AppConfig.setRobotEnabled(this, false);
                    RobotService.stop(this);
                } else {
                    sim = SimIdentityManager.bindSelectedSim(this, AppConfig.profileId(this));
                    if (!sim.valid) AppConfig.setRobotEnabled(this, false);
                }
                final SimIdentityManager.Verification finalSim = sim;
                runOnUiThread(() -> {
                    String detail = finalSim == null || finalSim.valid ? ""
                            : " SIM non activée : " + finalSim.message;
                    Toast.makeText(this, "Mode " + mode + " activé sur ce compte." + detail,
                            Toast.LENGTH_LONG).show();
                    recreate();
                });
            } catch (Exception error) {
                runOnUiThread(() -> toast("Changement impossible : " + readable(error)));
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
        requestCorePermissions();
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            toast("Accordez Téléphone et État du téléphone, puis touchez de nouveau DÉMARRER ROBOT.");
            return false;
        }
        if (!BlueAccessibilityService.isEnabled(this)) {
            toast("Activez le service d’accessibilité Blue Magic.");
            openAccessibilitySettings();
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
        try {
            SimCallManager.verifyCallRoute(this, AppConfig.profileId(this));
        } catch (Exception error) {
            AppConfig.setRobotEnabled(this, false);
            toast("Robot refusé : " + readable(error));
            refreshNativeStatus();
            return false;
        }
        RobotService.start(this);
        return true;
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
            try {
                AppConfig.clearCallRoute(this, profileId);
                SimCallManager.verifyCallRoute(this, profileId);
                toast("SIM et route d’appel vérifiées pour " + AppConfig.nodeCode(this)
                        + " dans le slot " + (AppConfig.simSlot(this) + 1) + ".");
            } catch (Exception error) {
                AppConfig.setRobotEnabled(this, false);
                toast("SIM présente, mais route d’appel à revérifier : " + readable(error));
            }
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
                    try {
                        AppConfig.clearCallRoute(this, profileId);
                        SimCallManager.verifyCallRoute(this, profileId);
                        toast("SIM liée avec succès. Vous pouvez démarrer le Robot.");
                    } catch (Exception error) {
                        AppConfig.setRobotEnabled(this, false);
                        toast("SIM liée, mais Robot arrêté : " + readable(error));
                    }
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
        boolean simRequired = AppConfig.isRobotMode(this);
        SimIdentityManager.Verification sim = simRequired
                ? SimIdentityManager.verify(this, AppConfig.profileId(this)) : null;
        if (AppConfig.robotEnabled(this) && sim != null && !sim.valid) {
            AppConfig.setRobotEnabled(this, false);
            RobotService.stop(this);
        }
        nativeStatus.setText(AppConfig.nodeCode(this)
                + " • " + AppConfig.displayMode(AppConfig.mode(this))
                + " • SIM " + (AppConfig.simSlot(this) + 1)
                + (!simRequired ? " NON REQUISE" : sim.valid ? " VÉRIFIÉE" : " BLOQUÉE")
                + " • Robot " + (AppConfig.robotEnabled(this) ? "ACTIF" : "ARRÊTÉ")
                + "\nAccessibilité " + (BlueAccessibilityService.isEnabled(this) ? "OK" : "À ACTIVER")
                + " • Robots actifs : " + AppConfig.enabledRobotCount(this)
                + (DeviceLockState.isSecurelyLocked(this)
                ? "\n🔒 VERROU SÉCURISÉ : la commande reprendra après déverrouillage"
                : DeviceLockState.isInsecurelyLocked(this)
                ? "\n✨ VERROU SIMPLE : le dialogue Téléphone sera libéré temporairement" : "")
                + (sim != null && !sim.valid ? "\n⛔ " + sim.message : "")
                + (AppConfig.pinBlocked(this) ? "\n⛔ PIN BLOQUÉ : corriger avant toute nouvelle transaction" : ""));
    }

    @Override
    protected void onResume() {
        super.onResume();
        applyRobotWindowPolicy();
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
                value.put("profile_id", AppConfig.profileId(MainActivity.this));
                value.put("role", AppConfig.role(MainActivity.this));
                value.put("mode", AppConfig.displayMode(AppConfig.mode(MainActivity.this)));
                value.put("sim_slot", AppConfig.simSlot(MainActivity.this));
                value.put("robot_enabled", AppConfig.robotEnabled(MainActivity.this));
                value.put("pin_blocked", AppConfig.pinBlocked(MainActivity.this));
                value.put("accessibility_enabled", BlueAccessibilityService.isEnabled(MainActivity.this));
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
            runOnUiThread(() -> RobotService.stop(MainActivity.this));
        }

        @JavascriptInterface
        public void setFormEditing(boolean editing) {
            runOnUiThread(() -> {
                if (managementPanel != null) managementPanel.setVisibility(View.GONE);
                if (manageButton != null) manageButton.setText("☰ GÉRER");
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
