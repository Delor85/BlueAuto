from pathlib import Path


def read(path):
    return Path(path).read_text()


def write(path, text):
    Path(path).write_text(text)


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'missing patch anchor: {label}')
    return text.replace(old, new, 1)


# -----------------------------------------------------------------------------
# 1) Native GÉRER: replace the fixed-height inline stack by a responsive dialog.
# -----------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/MainActivity.java'
s = read(p)
s = s.replace('    private View managementPanel;\n', '    private AlertDialog managementDialog;\n', 1)

start = s.index('        ScrollView toolsScroll = new ScrollView(this);')
end = s.index('        webView = new WebView(this);', start)
s = s[:start] + s[end:]

start = s.index('        accounts.setOnClickListener(v -> showAccountManager());')
end = s.index('        WebSettings settings = webView.getSettings();', start)
listeners = '''        accounts.setOnClickListener(v -> showAccountManager());
        manageButton.setOnClickListener(v -> setManagementOpen(true));

'''
s = s[:start] + listeners + s[end:]

start = s.index('    private void setManagementOpen(boolean opening) {')
end = s.index('    private void showPinEditorDialog() {', start)
management = '''    private void setManagementOpen(boolean opening) {
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
        addManagementPair(tools, verifySim, repairPairing);
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
            networkPinChange = managementActionButton("🔁 CHANGER PIN CAMTEL", CYAN);
            addManagementPair(tools, pinSettings, networkPinChange);
            networkPinReset = managementActionButton("🆘 DEMANDER RESET PIN", VIOLET);
            addManagementFull(tools, networkPinReset);

            tools.addView(managementSectionTitle("ROBOT & TÉLÉPHONE"));
            prepare = managementActionButton("✓ AUTORISATIONS", GOLD);
            battery = managementActionButton("🔋 BATTERIE SANS RESTRICTION", CYAN);
            addManagementPair(tools, prepare, battery);
            toggle = managementActionButton(AppConfig.robotEnabled(this)
                    ? "■ ARRÊTER ROBOT" : "▶ DÉMARRER ROBOT", VIOLET);
            addManagementFull(tools, toggle);
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

'''
s = s[:start] + management + s[end:]

# Follow-up patch adds the bridge method; route it to the shared native helper.
bridge_old = '''        @JavascriptInterface
        public void openBatteryOptimizationSettings() {
            runOnUiThread(() -> {
                try {
                    startActivity(new Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
                    toast("Choisissez Blue Magic puis « Sans restriction » / « Ne pas optimiser » si disponible.");
                } catch (Exception error) {
                    toast("Ouvrez Batterie > Blue Magic > Sans restriction / Ne pas optimiser.");
                }
            });
        }
'''
bridge_new = '''        @JavascriptInterface
        public void openBatteryOptimizationSettings() {
            runOnUiThread(MainActivity.this::openBatterySettings);
        }
'''
s = replace_once(s, bridge_old, bridge_new, 'battery bridge helper')

# Status copy: secured lock waits for a human; simple lock may receive one bounded assist.
s = s.replace('🔒 ÉCRAN VERROUILLÉ : aucune commande USSD n’est forcée; déverrouillez normalement',
              '🔒 VERROU SÉCURISÉ : aucune tentative automatique; déverrouillage humain requis')
s = s.replace('🔒 VERROU SIMPLE : aucune tentative automatique de déverrouillage',
              '✨ VERROU SIMPLE : assistance ponctuelle autorisée seulement au moment d’une commande')
write(p, s)


# -----------------------------------------------------------------------------
# 2) Lock classification helpers. No credential lock is ever assisted.
# -----------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/DeviceLockState.java'
s = read(p)
anchor = '''    static boolean blocksUssd(Context context) {
        return isKeyguardLocked(context) || !isScreenInteractive(context);
    }
'''
replacement = '''    static boolean hasSecureCredential(Context context) {
        KeyguardManager manager = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        if (manager == null) return false;
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                ? manager.isDeviceSecure() : manager.isKeyguardSecure();
    }

    static boolean canAssistSimpleUnlock(Context context) {
        if (isSecurelyLocked(context)) return false;
        return isInsecurelyLocked(context) || !isScreenInteractive(context);
    }

    static boolean blocksUssd(Context context) {
        return isKeyguardLocked(context) || !isScreenInteractive(context);
    }
'''
s = replace_once(s, anchor, replacement, 'lock classification helpers')
write(p, s)


# -----------------------------------------------------------------------------
# 3) Invisible one-shot helper Activity. It never handles PIN/pattern/password/biometric locks.
# -----------------------------------------------------------------------------
assist = r'''package com.profitloop.blueauto;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.WindowManager;

/**
 * One-shot assistance for a swipe/no-credential keyguard or a screen that is simply asleep.
 *
 * This Activity is transparent and short lived. It is launched only when DeviceLockState confirms
 * that no secure credential lock is currently blocking the device. A PIN, pattern, password or
 * biometric-protected lock is never dismissed and never receives an automated credential attempt.
 */
public final class SimpleKeyguardAssistActivity extends Activity {
    private static final long MAX_VISIBLE_MS = 1_200L;

    static boolean launch(Context context) {
        if (context == null || DeviceLockState.isSecurelyLocked(context)
                || !DeviceLockState.canAssistSimpleUnlock(context)) return false;
        try {
            Intent intent = new Intent(context, SimpleKeyguardAssistActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                            | Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
                            | Intent.FLAG_ACTIVITY_NO_ANIMATION
                            | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            context.startActivity(intent);
            return true;
        } catch (RuntimeException ignored) {
            return false;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        overridePendingTransition(0, 0);
        if (DeviceLockState.isSecurelyLocked(this)) {
            finishQuietly();
            return;
        }

        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
        }

        KeyguardManager keyguard = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        if (keyguard != null && keyguard.isKeyguardLocked()
                && !DeviceLockState.hasSecureCredential(this)) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                keyguard.requestDismissKeyguard(this, null);
            } else {
                // Android 6/7: this window flag dismisses only a non-secure keyguard.
                getWindow().addFlags(WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD);
            }
        }

        new Handler(Looper.getMainLooper()).postDelayed(this::finishQuietly, MAX_VISIBLE_MS);
    }

    private void finishQuietly() {
        if (!isFinishing()) finish();
        overridePendingTransition(0, 0);
    }
}
'''
write('app/src/main/java/com/profitloop/blueauto/SimpleKeyguardAssistActivity.java', assist)

p = 'app/src/main/AndroidManifest.xml'
s = read(p)
manifest_anchor = '''        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:launchMode="singleTask"
            android:windowSoftInputMode="adjustResize">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
'''
manifest_new = manifest_anchor + '''
        <activity
            android:name=".SimpleKeyguardAssistActivity"
            android:excludeFromRecents="true"
            android:exported="false"
            android:noHistory="true"
            android:theme="@style/BlueMagicTransparentUnlock" />
'''
s = replace_once(s, manifest_anchor, manifest_new, 'simple keyguard helper activity')
write(p, s)


# -----------------------------------------------------------------------------
# 4) Robot: hold one leased command briefly while the one-shot simple-lock assist runs.
#    Secure locks are released immediately. A cooldown prevents screen shaking/retry storms.
# -----------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/RobotService.java'
s = read(p)
s = s.replace('    private static final long WATCHDOG_INTERVAL_MS = 60_000L;\n',
'''    private static final long WATCHDOG_INTERVAL_MS = 60_000L;
    private static final long SIMPLE_UNLOCK_WAIT_MS = 3_500L;
    private static final long SIMPLE_UNLOCK_COOLDOWN_MS = 30_000L;
''', 1)

old_active = '''            JSONObject activeUssd = activeCommands.isEmpty() ? null : activeCommands.get(0);
            if (activeUssd != null) {
                String owner = activeUssd.optString("local_profile_id", "");
                if (PendingCommandStore.isExpired(activeUssd)) {
                    finishCommand(owner, false, "RESULT_TIMEOUT",
                            "Aucune confirmation fiable reçue dans le délai. Vérification manuelle requise.", "");
                    nextDelay = 5_000L;
                } else {
                    nextDelay = 2_000L;
                }
                return;
            }
'''
new_active = '''            JSONObject activeUssd = activeCommands.isEmpty() ? null : activeCommands.get(0);
            if (activeUssd != null) {
                String owner = activeUssd.optString("local_profile_id", "");
                String localState = activeUssd.optString("local_state", PendingCommandStore.LEASED);
                if (PendingCommandStore.LEASED.equals(localState)) {
                    ApiClient leasedApi = ApiClient.forProfile(this, owner);
                    if (DeviceLockState.isSecurelyLocked(this)) {
                        releaseLockedLease(owner, activeUssd, leasedApi);
                        nextDelay = AppConfig.LOCKED_POLL_MS;
                    } else if (!DeviceLockState.blocksUssd(this)) {
                        executeCommand(owner, activeUssd, leasedApi);
                        nextDelay = 2_000L;
                    } else {
                        long assistAt = activeUssd.optLong("simple_unlock_assist_at", 0L);
                        if (assistAt <= 0L) {
                            if (beginSimpleUnlockAssist(owner, activeUssd)) {
                                nextDelay = 750L;
                            } else {
                                releaseLockedLease(owner, activeUssd, leasedApi);
                                nextDelay = AppConfig.LOCKED_POLL_MS;
                            }
                        } else if (System.currentTimeMillis() - assistAt >= SIMPLE_UNLOCK_WAIT_MS) {
                            releaseLockedLease(owner, activeUssd, leasedApi);
                            nextDelay = AppConfig.LOCKED_POLL_MS;
                        } else {
                            nextDelay = 750L;
                        }
                    }
                    return;
                }
                if (PendingCommandStore.isExpired(activeUssd)) {
                    finishCommand(owner, false, "RESULT_TIMEOUT",
                            "Aucune confirmation fiable reçue dans le délai. Vérification manuelle requise.", "");
                    nextDelay = 5_000L;
                } else {
                    nextDelay = 2_000L;
                }
                return;
            }
'''
s = replace_once(s, old_active, new_active, 'leased simple-lock wait')

old_new_lease = '''                        if (DeviceLockState.blocksUssd(this)) {
                            releaseLockedLease(profileId, command, api);
                            nextDelay = AppConfig.LOCKED_POLL_MS;
                            return;
                        }
'''
new_new_lease = '''                        if (DeviceLockState.blocksUssd(this)) {
                            if (DeviceLockState.isSecurelyLocked(this)
                                    || !beginSimpleUnlockAssist(profileId, command)) {
                                releaseLockedLease(profileId, command, api);
                                nextDelay = AppConfig.LOCKED_POLL_MS;
                            } else {
                                nextDelay = 750L;
                            }
                            return;
                        }
'''
s = replace_once(s, old_new_lease, new_new_lease, 'initial simple-lock assist')

release_anchor = '''    private void releaseLockedLease(String profileId, JSONObject command, ApiClient api) {
        try {
            api.releaseCommand(command,
                    "Écran verrouillé. Le titulaire doit déverrouiller normalement le téléphone; aucune tentative de déverrouillage automatique n’est effectuée.");
        } catch (Exception ignored) {
            // Un ancien serveur relâchera lui-même le lease à son expiration.
        }
        PendingCommandStore.clear(this, profileId);
        releaseCommandWakeLock();
        updateNotification(robotSummary("Écran verrouillé — déverrouillez le téléphone puis Blue Magic reprendra la file"));
    }
'''
release_new = '''    private boolean beginSimpleUnlockAssist(String profileId, JSONObject command) {
        if (!DeviceLockState.canAssistSimpleUnlock(this) || DeviceLockState.isSecurelyLocked(this)) {
            return false;
        }
        long now = System.currentTimeMillis();
        String key = "simple_unlock_assist_at_" + profileId;
        long last = AppConfig.prefs(this).getLong(key, 0L);
        if (now - last < SIMPLE_UNLOCK_COOLDOWN_MS) return false;
        if (!SimpleKeyguardAssistActivity.launch(this)) return false;
        try {
            command.put("simple_unlock_assist_at", now);
            PendingCommandStore.save(this, profileId, command);
        } catch (Exception ignored) {
            return false;
        }
        AppConfig.prefs(this).edit().putLong(key, now).apply();
        updateNotification(robotSummary("Verrou simple — tentative unique de libération avant l’USSD"));
        return true;
    }

    private void releaseLockedLease(String profileId, JSONObject command, ApiClient api) {
        boolean secure = DeviceLockState.isSecurelyLocked(this);
        String reason = secure
                ? "Écran protégé par un verrou sécurisé. Déverrouillage humain obligatoire."
                : "Le verrou simple n’a pas pu être libéré proprement lors de la tentative ponctuelle.";
        try {
            api.releaseCommand(command, reason + " La commande reste dans la file et pourra être reprise.");
        } catch (Exception ignored) {
            // Un ancien serveur relâchera lui-même le lease à son expiration.
        }
        PendingCommandStore.clear(this, profileId);
        releaseCommandWakeLock();
        updateNotification(robotSummary(secure
                ? "Écran sécurisé — déverrouillez ou contactez le titulaire/supérieur; la file reprendra ensuite"
                : "Écran verrouillé — déverrouillez ou contactez le titulaire/supérieur; Blue Magic reprendra la file"));
    }
'''
s = replace_once(s, release_anchor, release_new, 'lock release and bounded assist')
write(p, s)


# -----------------------------------------------------------------------------
# 5) Tests: keep the stronger label and verify the responsive/lock contracts.
# -----------------------------------------------------------------------------
p = 'app/src/test/v268-field-contract.mjs'
s = read(p)
s = s.replace("if(!ui.includes('Réservé : ')||!ui.includes('Solde Camtel : '))",
              "if(!ui.includes('Réservé après confirmation : ')||!ui.includes('Solde Camtel : '))")
write(p, s)

responsive_test = r'''import fs from 'node:fs';
const main=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/MainActivity.java','utf8');
const lock=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/DeviceLockState.java','utf8');
const assist=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/SimpleKeyguardAssistActivity.java','utf8');
const robot=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/RobotService.java','utf8');
const manifest=fs.readFileSync('app/src/main/AndroidManifest.xml','utf8');
if(main.includes('MATCH_PARENT, dp(260)')) throw new Error('legacy fixed 260dp management panel still present');
for(const needle of ['showManagementCenter','COMPTE & SIM','PIN CAMTEL','ROBOT & TÉLÉPHONE','FILES & SÉCURITÉ','addManagementPair']){
  if(!main.includes(needle)) throw new Error('responsive management contract missing: '+needle);
}
if(!main.includes('widthDp < 290f')) throw new Error('ultra-narrow management fallback missing');
if(!manifest.includes('.SimpleKeyguardAssistActivity')) throw new Error('simple lock assist activity not registered');
if(manifest.includes('android.permission.DISABLE_KEYGUARD')) throw new Error('deprecated DISABLE_KEYGUARD permission must stay absent');
for(const banned of ['disableKeyguard','SCREEN_BRIGHT_WAKE_LOCK','ACQUIRE_CAUSES_WAKEUP']){
  if(assist.includes(banned)||robot.includes(banned)||lock.includes(banned)) throw new Error('unsafe repeated lock mechanism: '+banned);
}
if(!assist.includes('DeviceLockState.isSecurelyLocked(this)')) throw new Error('secure-lock gate missing in assist activity');
if(!assist.includes('requestDismissKeyguard')||!assist.includes('FLAG_DISMISS_KEYGUARD')) throw new Error('versioned simple-lock dismissal path missing');
if(!robot.includes('SIMPLE_UNLOCK_COOLDOWN_MS')||!robot.includes('beginSimpleUnlockAssist')) throw new Error('bounded/cooldown simple-lock policy missing');
if(!robot.includes('contactez le titulaire/supérieur')) throw new Error('human-unlock notification missing');
console.log('v2.6.8 responsive management + bounded simple-lock assist contract OK');
'''
write('app/src/test/v268-responsive-management.mjs', responsive_test)
