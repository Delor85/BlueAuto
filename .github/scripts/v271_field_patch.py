from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]

def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')

def write(rel, text):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 occurrence, found {count}')
    return text.replace(old, new, 1)

def sub_once(text, pattern, repl, label, flags=0):
    new, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly 1 regex match, found {count}')
    return new

# -----------------------------------------------------------------------------
# Android identity v2.7.1
# -----------------------------------------------------------------------------
gradle = read('app/build.gradle')
gradle = replace_once(gradle, 'versionCode 51', 'versionCode 52', 'versionCode')
gradle = replace_once(gradle, 'versionName "2.7.0"', 'versionName "2.7.1"', 'versionName')
write('app/build.gradle', gradle)

api = read('app/src/main/java/com/profitloop/blueauto/ApiClient.java')
api = api.replace('payload.put("app_version", "2.7.0")', 'payload.put("app_version", "2.7.1")')
if 'payload.put("app_version", "2.7.1")' not in api:
    raise SystemExit('ApiClient app_version 2.7.1 not installed')
write('app/src/main/java/com/profitloop/blueauto/ApiClient.java', api)

# -----------------------------------------------------------------------------
# Robot reboot durability: the user intent stays enabled through transient SIM
# warm-up states. Only a proven SIM mismatch revokes Robot eligibility.
# -----------------------------------------------------------------------------
appcfg = read('app/src/main/java/com/profitloop/blueauto/AppConfig.java')
appcfg = replace_once(
    appcfg,
    'prefs(context).edit().putBoolean(robotEnabledKey(profileId), enabled).apply();',
    'prefs(context).edit().putBoolean(robotEnabledKey(profileId), enabled).commit();',
    'robot intent synchronous persistence')
write('app/src/main/java/com/profitloop/blueauto/AppConfig.java', appcfg)

sim = read('app/src/main/java/com/profitloop/blueauto/SimIdentityManager.java')
anchor = '    /** Bind after an explicit user choice (pairing, slot selection, or confirmation dialog). */\n'
helper = '''    static boolean isHardMismatch(Verification verification) {
        return verification != null && !verification.valid
                && (NUMBER_MISMATCH.equals(verification.code) || SIM_CHANGED.equals(verification.code));
    }

    static boolean isTransientOrRecoverable(Verification verification) {
        return verification != null && !verification.valid && !isHardMismatch(verification);
    }

'''
sim = replace_once(sim, anchor, helper + anchor, 'SIM mismatch classifier')
sim = sim.replace('Camtel', 'Blue')
write('app/src/main/java/com/profitloop/blueauto/SimIdentityManager.java', sim)

sim_receiver = read('app/src/main/java/com/profitloop/blueauto/SimStateReceiver.java')
old_loop = '''                for (String profileId : AppConfig.enabledRobotProfileIds(app)) {
                    SimIdentityManager.Verification sim = SimIdentityManager.verify(app, profileId);
                    if (sim.valid) continue;
                    AppConfig.setRobotEnabled(app, profileId, false);
                    try {
                        ApiClient.forProfile(app, profileId).heartbeat();
                    } catch (Exception ignored) {
                    }
                }
                if (AppConfig.anyRobotEnabled(app)) RobotService.startEnabled(app);'''
new_loop = '''                for (String profileId : AppConfig.enabledRobotProfileIds(app)) {
                    SimIdentityManager.Verification sim = SimIdentityManager.verify(app, profileId);
                    if (sim.valid || SimIdentityManager.isTransientOrRecoverable(sim)) continue;
                    // A reboot emits SIM_STATE_CHANGED while the modem/subscription database is
                    // still warming up. Never erase the user's Robot intent for that transient
                    // state. Revoke only when Android proves the physical SIM is the wrong one.
                    if (SimIdentityManager.isHardMismatch(sim)) {
                        AppConfig.setRobotEnabled(app, profileId, false);
                        try {
                            ApiClient.forProfile(app, profileId).heartbeat();
                        } catch (Exception ignored) {
                        }
                    }
                }
                if (AppConfig.anyRobotEnabled(app)) {
                    RobotService.startEnabled(app);
                    RobotService.scheduleWatchdog(app, 15_000L);
                }'''
sim_receiver = replace_once(sim_receiver, old_loop, new_loop, 'SIM state reboot guard')
write('app/src/main/java/com/profitloop/blueauto/SimStateReceiver.java', sim_receiver)

boot = read('app/src/main/java/com/profitloop/blueauto/BootReceiver.java')
boot = replace_once(
    boot,
    '    public void onReceive(Context context, Intent intent) {\n        if (!AppConfig.anyRobotEnabled(context)) return;',
    '    public void onReceive(Context context, Intent intent) {\n        AppConfig.migrateLegacyProfile(context);\n        if (!AppConfig.anyRobotEnabled(context)) return;',
    'boot profile migration')
write('app/src/main/java/com/profitloop/blueauto/BootReceiver.java', boot)

robot = read('app/src/main/java/com/profitloop/blueauto/RobotService.java')
robot = robot.replace('disableUnsafeRobot(owner, readiness.message);', 'handleRobotNotReady(owner, readiness);')
robot = robot.replace('disableUnsafeRobot(profileId, readiness.message);', 'handleRobotNotReady(profileId, readiness);')
if 'disableUnsafeRobot(profileId, readiness.message);' in robot or 'disableUnsafeRobot(owner, readiness.message);' in robot:
    raise SystemExit('unpatched unsafe Robot disable call remains')
old_readiness = '''        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, profileId);
        if (!sim.valid) return Readiness.failure(sim.message);
        // La présence de la SIM est le verrou d'éligibilité.'''
new_readiness = '''        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, profileId);
        if (!sim.valid) {
            return SimIdentityManager.isHardMismatch(sim)
                    ? Readiness.hardFailure(sim.message)
                    : Readiness.retryable(sim.message);
        }
        // La présence de la SIM est le verrou d'éligibilité.'''
robot = replace_once(robot, old_readiness, new_readiness, 'Robot SIM readiness classification')
old_disable = '''    private void disableUnsafeRobot(String profileId, String reason) {
        if (profileId == null || profileId.isEmpty()) return;
        AppConfig.setRobotEnabled(this, profileId, false);
        lastHeartbeatByProfile.remove(profileId);
        try {
            ApiClient.forProfile(this, profileId).heartbeat();
        } catch (Exception ignored) {
        }
        updateNotification(robotSummary(AppConfig.nodeCode(this, profileId)
                + " arrêté — " + reason));
    }
'''
new_disable = '''    private void handleRobotNotReady(String profileId, Readiness readiness) {
        if (profileId == null || profileId.isEmpty() || readiness == null) return;
        if (readiness.hardFailure) {
            disableUnsafeRobot(profileId, readiness.message);
            return;
        }
        // Permission/SIM service/slot can be temporarily unavailable during boot. Keep the
        // persisted Robot intent and retry instead of silently turning the Robot off forever.
        lastHeartbeatByProfile.remove(profileId);
        updateNotification(robotSummary(AppConfig.nodeCode(this, profileId)
                + " en attente — " + readiness.message));
        scheduleWatchdog(this, 15_000L);
    }

    private void disableUnsafeRobot(String profileId, String reason) {
        if (profileId == null || profileId.isEmpty()) return;
        AppConfig.setRobotEnabled(this, profileId, false);
        lastHeartbeatByProfile.remove(profileId);
        try {
            ApiClient.forProfile(this, profileId).heartbeat();
        } catch (Exception ignored) {
        }
        updateNotification(robotSummary(AppConfig.nodeCode(this, profileId)
                + " arrêté — " + reason));
    }
'''
robot = replace_once(robot, old_disable, new_disable, 'Robot retryable state handler')
old_class = '''    private static final class Readiness {
        final boolean ready;
        final String message;
        final String simFingerprint;
        final int simSlot;

        private Readiness(boolean ready, String message, String simFingerprint, int simSlot) {
            this.ready = ready;
            this.message = message;
            this.simFingerprint = simFingerprint;
            this.simSlot = simSlot;
        }

        static Readiness ready(SimIdentityManager.Verification sim) {
            return new Readiness(true, sim.message, sim.attestation(), sim.slot);
        }

        static Readiness failure(String message) {
            return new Readiness(false, message, "", -1);
        }
    }
'''
new_class = '''    private static final class Readiness {
        final boolean ready;
        final boolean hardFailure;
        final String message;
        final String simFingerprint;
        final int simSlot;

        private Readiness(boolean ready, boolean hardFailure, String message,
                          String simFingerprint, int simSlot) {
            this.ready = ready;
            this.hardFailure = hardFailure;
            this.message = message;
            this.simFingerprint = simFingerprint;
            this.simSlot = simSlot;
        }

        static Readiness ready(SimIdentityManager.Verification sim) {
            return new Readiness(true, false, sim.message, sim.attestation(), sim.slot);
        }

        static Readiness failure(String message) {
            return retryable(message);
        }

        static Readiness retryable(String message) {
            return new Readiness(false, false, message, "", -1);
        }

        static Readiness hardFailure(String message) {
            return new Readiness(false, true, message, "", -1);
        }
    }
'''
robot = replace_once(robot, old_class, new_class, 'Readiness hard/retryable class')
robot = robot.replace('Camtel', 'Blue')
write('app/src/main/java/com/profitloop/blueauto/RobotService.java', robot)

# -----------------------------------------------------------------------------
# MainActivity: private MOCK entry, non-invasive switching, simplified pairing,
# local FR/EN preference and larger native secondary text.
# -----------------------------------------------------------------------------
main = read('app/src/main/java/com/profitloop/blueauto/MainActivity.java')
main = replace_once(main,
    '    private static final String MOCK_ROUTE_PROFILE_KEY = "bir_mock_route_profile_v270";\n',
    '    private static final String MOCK_ROUTE_PROFILE_KEY = "bir_mock_route_profile_v270";\n'
    '    private static final String MOCK_RETURN_PROFILE_KEY = "bir_mock_return_profile_v271";\n'
    '    private static final String UI_LANGUAGE_KEY = "bir_ui_language_v271";\n',
    'v271 preference constants')
main = replace_once(main,
    '    private volatile boolean robotStartInProgress;\n',
    '    private volatile boolean robotStartInProgress;\n    private static boolean mockSessionAuthorized;\n',
    'Mock in-memory session gate')
# Rename the old technical form but leave it as a non-reachable diagnostic fallback.
main = replace_once(main,
    '    private void showPairingScreen(boolean addingAccount) {',
    '    private void showPairingScreenLegacy(boolean addingAccount) {',
    'rename legacy pairing form')

new_pairing = r'''
    private String ui(String fr, String en) {
        return "en".equalsIgnoreCase(AppConfig.prefs(this).getString(UI_LANGUAGE_KEY, "fr")) ? en : fr;
    }

    private String inferParentFromNode(String node, String role) {
        if (node == null || "DAE".equalsIgnoreCase(role)) return "";
        String value = node.trim().toUpperCase(Locale.ROOT);
        int separator = value.indexOf('_');
        return separator >= 0 && separator + 1 < value.length() ? value.substring(separator + 1) : "";
    }

    private void showPairingAdminActivation(TextView status, Button button) {
        EditText secret = field(ui("Code d’activation administrateur", "Administrator activation code"), "", true);
        LinearLayout content = verticalContainer();
        content.setPadding(dp(18), dp(8), dp(18), dp(4));
        content.addView(help(ui("Cette étape n’apparaît que sur un téléphone non encore activé. Le code reste chiffré localement.",
                "This step appears only on a phone that has not been activated yet. The code stays encrypted locally.")));
        content.addView(secret);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(ui("Activation administrateur", "Administrator activation"))
                .setView(content)
                .setPositiveButton(ui("ENREGISTRER", "SAVE"), null)
                .setNegativeButton(ui("Annuler", "Cancel"), null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String value = secret.getText().toString().trim();
            if (value.length() < 24) {
                secret.setError(ui("Code incomplet.", "Incomplete code."));
                return;
            }
            try {
                SecurePairingStore.save(this, value);
                secret.setText("");
                status.setText(ui("Téléphone activé. Vous pouvez ajouter le compte.",
                        "Phone activated. You can now add the account."));
                status.setTextColor(CYAN);
                button.setVisibility(View.GONE);
                dialog.dismiss();
            } catch (Exception error) {
                secret.setError(readable(error));
            }
        }));
        dialog.show();
    }

    private void openMockFromPairing(String code, TextView feedback) {
        if (!mockOwnerCodeMatches(code)) {
            feedback.setText(ui("Code MOCK incorrect.", "Incorrect MOCK code."));
            feedback.setTextColor(Color.rgb(255, 139, 152));
            return;
        }
        if (!AppConfig.hasProfiles(this)) {
            feedback.setText(ui("Ajoutez d’abord au moins un compte Blue réel sur ce téléphone.",
                    "Add at least one real Blue account on this phone first."));
            feedback.setTextColor(Color.rgb(255, 139, 152));
            return;
        }
        mockSessionAuthorized = true;
        AppConfig.prefs(this).edit()
                .putString(MOCK_RETURN_PROFILE_KEY, AppConfig.profileId(this))
                .putBoolean(MOCK_OWNER_ENABLED_KEY, false)
                .putBoolean(MOCK_WORKSPACE_KEY, true)
                .commit();
        mockRouteProfile();
        recreate();
    }

    private void showPairingScreen(boolean addingAccount) {
        disposeWebView();
        ScrollView scroll = new ScrollView(this);
        applyMagicBackground(scroll);
        LinearLayout form = verticalContainer();
        scroll.addView(form);

        form.addView(title(ui("B.I.R. — AJOUTER / OUVRIR UN COMPTE", "B.I.R. — ADD / OPEN ACCOUNT")));
        form.addView(help(ui("Renseignez seulement votre identité Blue et le mode de ce téléphone.",
                "Enter only your Blue identity and this phone’s operating mode.")));

        EditText nodeCode = field(ui("Identifiant Blue (ex. OU3, DSM7_OU3, POS16_DSM7_OU3) — ou MOCK",
                "Blue ID (e.g. OU3, DSM7_OU3, POS16_DSM7_OU3) — or MOCK"), "", false);
        form.addView(nodeCode);

        EditText mockCode = field(ui("Code privé MOCK", "Private MOCK code"), "", true);
        mockCode.setVisibility(View.GONE);
        form.addView(mockCode);

        LinearLayout realFields = verticalContainer();
        EditText phone = field(ui("Numéro Blue de la SIM (9 chiffres)", "Blue SIM number (9 digits)"), "", false);
        EditText parent = field(ui("Supérieur direct (laisser vide si l’identifiant complet le contient)",
                "Direct superior (leave blank if included in the full ID)"), "", false);
        Spinner role = spinner(new String[]{"DAE", "DSM", "POS"});
        Spinner mode = spinner(new String[]{"REMOTE", "ROBOT"});
        Spinner simSlot = spinner(SimCallManager.slotLabels(this));
        EditText operatorPin = field(ui("PIN Blue 4 chiffres — uniquement Robot", "4-digit Blue PIN — Robot only"), "", true);
        operatorPin.setInputType(InputType.TYPE_CLASS_NUMBER | InputType.TYPE_NUMBER_VARIATION_PASSWORD);

        realFields.addView(phone);
        realFields.addView(parent);
        realFields.addView(label(ui("Rôle du compte", "Account role")));
        realFields.addView(role);
        realFields.addView(label(ui("Mode de ce téléphone", "This phone mode")));
        realFields.addView(mode);
        LinearLayout robotFields = verticalContainer();
        robotFields.addView(label(ui("SIM utilisée par ce Robot", "SIM used by this Robot")));
        robotFields.addView(simSlot);
        robotFields.addView(operatorPin);
        realFields.addView(robotFields);
        form.addView(realFields);

        TextView feedback = help(ui("Les réglages techniques du serveur sont gérés automatiquement par B.I.R.",
                "B.I.R. manages server technical settings automatically."));
        form.addView(feedback);

        Button adminActivation = actionButton(ui("ACTIVATION ADMINISTRATEUR", "ADMINISTRATOR ACTIVATION"), VIOLET);
        boolean secretReady = false;
        try { secretReady = SecurePairingStore.read(this).trim().length() >= 24; } catch (Exception ignored) {}
        adminActivation.setVisibility(secretReady ? View.GONE : View.VISIBLE);
        adminActivation.setOnClickListener(v -> showPairingAdminActivation(feedback, adminActivation));
        form.addView(adminActivation);

        Button pair = actionButton(ui("CONTINUER", "CONTINUE"), GOLD);
        form.addView(pair);

        nodeCode.addTextChangedListener(new android.text.TextWatcher() {
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            public void onTextChanged(CharSequence s, int start, int before, int count) {}
            public void afterTextChanged(android.text.Editable value) {
                boolean mock = "MOCK".equalsIgnoreCase(value.toString().trim());
                mockCode.setVisibility(mock ? View.VISIBLE : View.GONE);
                realFields.setVisibility(mock ? View.GONE : View.VISIBLE);
                adminActivation.setVisibility(mock ? View.GONE : (hasPairingSecret() ? View.GONE : View.VISIBLE));
                feedback.setText(mock
                        ? ui("Accès propriétaire privé. Le compte MOCK ne sera jamais affiché dans la liste normale des comptes.",
                                "Private owner access. MOCK will never appear in the normal account list.")
                        : ui("Les réglages techniques du serveur sont gérés automatiquement par B.I.R.",
                                "B.I.R. manages server technical settings automatically."));
            }
        });

        mode.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener() {
            public void onItemSelected(android.widget.AdapterView<?> parentView, View view, int position, long id) {
                robotFields.setVisibility("ROBOT".equals(mode.getSelectedItem().toString()) ? View.VISIBLE : View.GONE);
            }
            public void onNothingSelected(android.widget.AdapterView<?> parentView) {}
        });
        robotFields.setVisibility(View.GONE);

        pair.setOnClickListener(v -> {
            String node = nodeCode.getText().toString().trim().toUpperCase(Locale.ROOT);
            if ("MOCK".equals(node)) {
                openMockFromPairing(mockCode.getText().toString().trim(), feedback);
                return;
            }
            if (!node.matches("[A-Z0-9/_-]{3,64}")) {
                nodeCode.setError(ui("Identifiant Blue invalide.", "Invalid Blue ID."));
                nodeCode.requestFocus();
                return;
            }
            String sim = normalizeCameroonPhone(phone.getText().toString());
            if (!sim.matches("6\\d{8}")) {
                phone.setError(ui("Numéro Blue camerounais invalide.", "Invalid Cameroon Blue number."));
                phone.requestFocus();
                return;
            }
            String selectedRole = role.getSelectedItem().toString();
            String selectedMode = mode.getSelectedItem().toString();
            String parentNode = "DAE".equals(selectedRole) ? "" : parent.getText().toString().trim().toUpperCase(Locale.ROOT);
            if (parentNode.isEmpty()) parentNode = inferParentFromNode(node, selectedRole);
            if (!"DAE".equals(selectedRole) && !parentNode.matches("[A-Z0-9/_-]{3,64}")) {
                parent.setError(ui("Indiquez le supérieur direct ou utilisez l’identifiant Blue complet.",
                        "Enter the direct superior or use the full Blue ID."));
                parent.requestFocus();
                return;
            }
            String pin = operatorPin.getText().toString().trim();
            if ("ROBOT".equals(selectedMode) && !pin.matches("\\d{4}")) {
                operatorPin.setError(ui("Le Robot exige le PIN Blue exact à 4 chiffres.",
                        "Robot mode requires the exact 4-digit Blue PIN."));
                operatorPin.requestFocus();
                return;
            }
            String secret;
            try { secret = SecurePairingStore.read(this).trim(); } catch (Exception error) { secret = ""; }
            if (secret.length() < 24) {
                feedback.setText(ui("Activation administrateur requise une seule fois sur ce téléphone.",
                        "One-time administrator activation is required on this phone."));
                feedback.setTextColor(GOLD);
                adminActivation.setVisibility(View.VISIBLE);
                return;
            }
            String apiUrl = AppConfig.pairingApiUrl(this);
            int selectedSlot = simSlot.getSelectedItemPosition();
            pair.setEnabled(false);
            pair.setText(ui("CONNEXION…", "CONNECTING…"));
            feedback.setTextColor(CYAN);
            feedback.setText(ui("Appairage sécurisé Blue en cours…", "Secure Blue pairing in progress…"));
            final String resolvedParent = parentNode;
            final String pairingSecret = secret;
            new Thread(() -> {
                try {
                    JSONObject payload = new JSONObject();
                    payload.put("node_code", node);
                    payload.put("phone_number", sim);
                    payload.put("parent_node_code", resolvedParent);
                    payload.put("role", selectedRole);
                    payload.put("mode", selectedMode);
                    payload.put("pairing_secret", pairingSecret);
                    payload.put("device_name", Build.MANUFACTURER + " " + Build.MODEL);
                    JSONObject data = new ApiClient(this, apiUrl, "").pair(payload);
                    String token = data.optString("device_token", "");
                    String deviceId = data.optString("device_id", "");
                    String canonicalNode = data.optString("node_code", node);
                    String canonicalParent = data.optString("parent_node_code", resolvedParent);
                    if (token.isEmpty()) throw new IllegalStateException(ui("Jeton appareil absent.", "Device token missing."));
                    AppConfig.savePairing(this, deviceId, token, canonicalNode, sim, canonicalParent,
                            selectedRole, selectedMode, apiUrl, selectedSlot);
                    SecurePairingStore.save(this, pairingSecret);
                    String resultMessage;
                    if ("ROBOT".equals(selectedMode)) {
                        SecurePinStore.save(this, pin);
                        SimIdentityManager.Verification verification = SimIdentityManager.bindSelectedSim(this, AppConfig.profileId(this));
                        resultMessage = verification.valid
                                ? ui("Compte Robot ajouté et SIM liée.", "Robot account added and SIM linked.")
                                : ui("Compte ajouté. Vérifiez ensuite la SIM dans Gérer : ", "Account added. Verify the SIM in Manage: ") + verification.message;
                    } else {
                        resultMessage = ui("Compte Remote ajouté.", "Remote account added.");
                    }
                    final String message = resultMessage;
                    runOnUiThread(() -> {
                        toast(message);
                        recreate();
                    });
                } catch (Exception error) {
                    runOnUiThread(() -> {
                        pair.setEnabled(true);
                        pair.setText(ui("RÉESSAYER", "TRY AGAIN"));
                        feedback.setTextColor(Color.rgb(255, 139, 152));
                        feedback.setText(ui("Échec de l’appairage : ", "Pairing failed: ") + readable(error));
                    });
                }
            }, "BIR-Pairing-v271").start();
        });

        if (addingAccount && AppConfig.hasProfiles(this)) {
            Button cancel = actionButton(ui("ANNULER — REVENIR", "CANCEL — GO BACK"), CYAN);
            cancel.setOnClickListener(v -> showControlScreen());
            form.addView(cancel);
        }
        setContentView(scroll);
    }

    private boolean hasPairingSecret() {
        try { return SecurePairingStore.read(this).trim().length() >= 24; }
        catch (Exception ignored) { return false; }
    }

'''
insert_at = '    private void showPairingScreenLegacy(boolean addingAccount) {'
main = replace_once(main, insert_at, new_pairing + insert_at, 'insert simplified v271 pairing')

# In-memory MOCK session only; no persistent public enrollment.
old_enrolled = '''    private boolean mockOwnerEnrolled() {
        return AppConfig.prefs(this).getBoolean(MOCK_OWNER_ENABLED_KEY, false);
    }
'''
new_enrolled = '''    private boolean mockOwnerEnrolled() {
        return mockSessionAuthorized;
    }
'''
main = replace_once(main, old_enrolled, new_enrolled, 'private Mock session gate')

# Replace account manager so MOCK never appears and a click always exits MOCK cleanly.
account_pattern = r'    private void showAccountManager\(\) \{.*?\n    \}\n\n    private void showSimSlotChooser\(\) \{'
account_repl = r'''    private void showAccountManager() {
        String[] labels = AppConfig.profileLabels(this);
        String[] ids = AppConfig.profileIds(this);
        final boolean leavingMock = isMockWorkspaceActive();
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(ui("Comptes Blue", "Blue accounts"))
                .setItems(labels, (ignored, index) -> {
                    if (index < 0 || index >= ids.length) return;
                    if (leavingMock) {
                        mockSessionAuthorized = false;
                        AppConfig.prefs(this).edit()
                                .putBoolean(MOCK_WORKSPACE_KEY, false)
                                .putBoolean(MOCK_OWNER_ENABLED_KEY, false)
                                .remove(MOCK_RETURN_PROFILE_KEY)
                                .commit();
                    }
                    if (!ids[index].equals(AppConfig.profileId(this))) {
                        AppConfig.activateProfile(this, ids[index]);
                    }
                    // Even when this was already the hidden routing profile under MOCK, force a
                    // real UI rebuild. The old behavior opened only the SIM picker and visually
                    // trapped the user in MOCK.
                    recreate();
                })
                .setPositiveButton(ui("Ajouter / Ouvrir", "Add / Open"), null)
                .setNeutralButton(ui("Supprimer l’actif", "Delete active"), null)
                .setNegativeButton(ui("Fermer", "Close"), null)
                .create();
        dialog.setOnShowListener(ignored -> {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
                dialog.dismiss();
                showPairingScreen(true);
            });
            if (leavingMock) {
                dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setVisibility(View.GONE);
            } else {
                dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener(v -> {
                    if (!canModifyActiveProfile()) return;
                    new AlertDialog.Builder(this)
                            .setTitle(ui("Supprimer ", "Delete ") + AppConfig.nodeCode(this) + " ?")
                            .setMessage(ui("Le Robot sera arrêté puis le compte et son PIN chiffré seront retirés de ce téléphone.",
                                    "The Robot will be stopped, then the account and encrypted PIN will be removed from this phone."))
                            .setPositiveButton(ui("SUPPRIMER", "DELETE"), (confirm, which) -> deleteActiveProfileSafely())
                            .setNegativeButton(ui("Annuler", "Cancel"), null)
                            .show();
                });
            }
        });
        dialog.show();
    }

    private void showSimSlotChooser() {'''
main = sub_once(main, account_pattern, account_repl, 'non-invasive account manager', flags=re.S)

# Exit MOCK returns to the account that was active before opening it and locks MOCK again.
old_exit = '''        public void exitMockWorkspace() {
            runOnUiThread(() -> {
                setMockWorkspaceActive(false);
                recreate();
            });
        }
'''
new_exit = '''        public void exitMockWorkspace() {
            runOnUiThread(() -> {
                String returnProfile = AppConfig.prefs(MainActivity.this).getString(MOCK_RETURN_PROFILE_KEY, "");
                mockSessionAuthorized = false;
                AppConfig.prefs(MainActivity.this).edit()
                        .putBoolean(MOCK_WORKSPACE_KEY, false)
                        .putBoolean(MOCK_OWNER_ENABLED_KEY, false)
                        .remove(MOCK_RETURN_PROFILE_KEY)
                        .commit();
                if (!returnProfile.isEmpty()) AppConfig.activateProfile(MainActivity.this, returnProfile);
                recreate();
            });
        }
'''
main = replace_once(main, old_exit, new_exit, 'Mock exit restoration')

# Native bridge language preference used by the web shell.
bridge_anchor = '''        @JavascriptInterface
        public boolean isMockWorkspace() {
            return isMockWorkspaceActive();
        }
'''
bridge_lang = '''        @JavascriptInterface
        public String getUiLanguage() {
            return AppConfig.prefs(MainActivity.this).getString(UI_LANGUAGE_KEY, "fr");
        }

        @JavascriptInterface
        public void setUiLanguage(String value) {
            String language = "en".equalsIgnoreCase(value) ? "en" : "fr";
            AppConfig.prefs(MainActivity.this).edit().putString(UI_LANGUAGE_KEY, language).commit();
        }

'''
main = replace_once(main, bridge_anchor, bridge_lang + bridge_anchor, 'native language bridge')
main = replace_once(main, '        view.setTextSize(13);', '        view.setTextSize(14);', 'secondary native text size')
# User-facing native brand: Blue is the mobile brand. Parser/network matching is untouched.
main = main.replace('Camtel', 'Blue')
write('app/src/main/java/com/profitloop/blueauto/MainActivity.java', main)

# -----------------------------------------------------------------------------
# Commission fallback for production Worker 2.6.7.
# -----------------------------------------------------------------------------
appjs = read('app/src/main/assets/app.js')
old_pending = "pendingPreview={type:type,node:node,phone:phone,amount:amount,argument:argument,request_id:requestId(),capacity_check_id:''};"
new_pending = "pendingPreview={type:type,node:node,phone:phone,amount:amount,argument:argument,request_id:requestId(),capacity_check_id:''};if(type==='SUPPLY_CHILD'&&window.BIRCommissionPolicy&&window.BIRCommissionPolicy.getRateBps){pendingPreview.commission_rate_bps=Number(window.BIRCommissionPolicy.getRateBps(node)||0);pendingPreview.commission_base_amount=Number(amount||0);pendingPreview.original_amount=String(amount||'');}"
appjs = replace_once(appjs, old_pending, new_pending, 'attach local commission policy')

old_preview_guard = '''        clearActionError();
        if(preview.robot_ready===false){showActionProgress((preview.robot_status||'ROBOT_OFFLINE')+' — '+(preview.robot_message||'Le Robot ne communique pas encore. La commande peut être mise en attente.'));}
        var decision=confirmFinancial(preview);'''
new_preview_guard = '''        clearActionError();
        if(pendingPreview.type==='SUPPLY_CHILD'&&typeof pendingPreview.commission_rate_bps==='number'&&!pendingPreview.legacy_commission_mode){
            var expectedBps=Number(pendingPreview.commission_rate_bps||0),serverBps=Number(preview.commission_rate_bps||0);
            if(expectedBps!==serverBps){
                var legacyBase=Number(pendingPreview.commission_base_amount||pendingPreview.original_amount||pendingPreview.amount||0);
                var legacyCommission=Math.floor(legacyBase*expectedBps/10000),legacyTotal=legacyBase+legacyCommission;
                pendingPreview.legacy_commission_mode=true;
                pendingPreview.commission_base_amount=legacyBase;
                pendingPreview.amount=String(legacyTotal);
                showActionProgress('Compatibilité serveur : '+String(expectedBps/100).replace('.',',')+' % appliqué localement, total '+formatMoney(legacyTotal)+' FCFA à certifier une seule fois…');
                window.AndroidBridge.previewCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument);
                return;
            }
        }
        if(preview.robot_ready===false){showActionProgress((preview.robot_status||'ROBOT_OFFLINE')+' — '+(preview.robot_message||'Le Robot ne communique pas encore. La commande peut être mise en attente.'));}
        var decision=confirmFinancial(preview);'''
appjs = replace_once(appjs, old_preview_guard, new_preview_guard, 'legacy commission preview fallback')

old_create = '''        if(pendingPreview.type==='SUPPLY_CHILD'&&typeof pendingPreview.commission_rate_bps==='number'&&window.AndroidBridge.createCommandWithCommissionRate){
            window.AndroidBridge.createCommandWithCommissionRate(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
                pendingPreview.amount,pendingPreview.request_id,fingerprint,pendingPreview.capacity_check_id,pendingPreview.argument,pendingPreview.commission_rate_bps);
        }else{
            window.AndroidBridge.createCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
                pendingPreview.amount,pendingPreview.request_id,fingerprint,pendingPreview.capacity_check_id,pendingPreview.argument);
        }'''
new_create = '''        if(pendingPreview.type==='SUPPLY_CHILD'&&typeof pendingPreview.commission_rate_bps==='number'&&!pendingPreview.legacy_commission_mode&&window.AndroidBridge.createCommandWithCommissionRate){
            window.AndroidBridge.createCommandWithCommissionRate(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
                pendingPreview.amount,pendingPreview.request_id,fingerprint,pendingPreview.capacity_check_id,pendingPreview.argument,pendingPreview.commission_rate_bps);
        }else{
            window.AndroidBridge.createCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,
                pendingPreview.amount,pendingPreview.request_id,fingerprint,pendingPreview.capacity_check_id,pendingPreview.argument);
        }'''
appjs = replace_once(appjs, old_create, new_create, 'legacy standard certified create')

old_quote = '''        var base=Number(preview.requested_base_amount||preview.amount||0), commission=Number(preview.commission_amount||0), rateBps=Number(preview.commission_rate_bps||0), rate=rateBps/100;
        var quote=preview.operation==='DISTRIBUTION_TRANSFER' ? ('\\nMONTANT DE BASE : '+formatMoney(base)+' FCFA\\nCOMMISSION ('+String(rate).replace('.',',')+' %) : '+formatMoney(commission)+' FCFA\\nTOTAL À RECEVOIR : '+formatMoney(preview.amount)+' FCFA') : ('\\nMONTANT : '+formatMoney(preview.amount)+' FCFA');'''
new_quote = '''        var localCommission=pendingPreview&&pendingPreview.type==='SUPPLY_CHILD'&&typeof pendingPreview.commission_rate_bps==='number';
        var base=localCommission?Number(pendingPreview.commission_base_amount||pendingPreview.original_amount||preview.requested_base_amount||0):Number(preview.requested_base_amount||preview.amount||0);
        var rateBps=localCommission?Number(pendingPreview.commission_rate_bps||0):Number(preview.commission_rate_bps||0), rate=rateBps/100;
        var commission=localCommission?Math.floor(base*rateBps/10000):Number(preview.commission_amount||0), total=localCommission?base+commission:Number(preview.amount||0);
        var quote=preview.operation==='DISTRIBUTION_TRANSFER' ? ('\\nMONTANT DE BASE : '+formatMoney(base)+' FCFA\\nCOMMISSION ('+String(rate).replace('.',',')+' %) : '+formatMoney(commission)+' FCFA\\nTOTAL À RECEVOIR : '+formatMoney(total)+' FCFA') : ('\\nMONTANT : '+formatMoney(preview.amount)+' FCFA');'''
appjs = replace_once(appjs, old_quote, new_quote, 'local commission quote')

old_repreview = '''            if(chosenBps!==rateBps){
                pendingPreview.commission_rate_bps=chosenBps;
                showActionProgress('Nouveau taux '+String(chosen).replace('.',',')+' % : recalcul et nouvelle certification serveur…');
                if(window.AndroidBridge.previewCommandWithCommissionRate){
                    window.AndroidBridge.previewCommandWithCommissionRate(pendingPreview.type,pendingPreview.node,pendingPreview.phone,pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument,chosenBps);
                    return 'REPREVIEW';
                }
                showToast('Cette version Android ne sait pas recertifier un taux ponctuel.');return false;
            }'''
new_repreview = '''            if(chosenBps!==rateBps){
                pendingPreview.commission_rate_bps=chosenBps;
                if(window.BIRCommissionPolicy&&window.BIRCommissionPolicy.setOneShotRate){window.BIRCommissionPolicy.setOneShotRate(pendingPreview.node,chosenBps);}
                showActionProgress('Nouveau taux '+String(chosen).replace('.',',')+' % : recalcul et nouvelle certification…');
                if(pendingPreview.legacy_commission_mode){
                    var changedBase=Number(pendingPreview.commission_base_amount||pendingPreview.original_amount||0);
                    pendingPreview.amount=String(changedBase+Math.floor(changedBase*chosenBps/10000));
                    window.AndroidBridge.previewCommand(pendingPreview.type,pendingPreview.node,pendingPreview.phone,pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument);
                    return 'REPREVIEW';
                }
                if(window.AndroidBridge.previewCommandWithCommissionRate){
                    window.AndroidBridge.previewCommandWithCommissionRate(pendingPreview.type,pendingPreview.node,pendingPreview.phone,pendingPreview.amount,pendingPreview.request_id,pendingPreview.capacity_check_id,pendingPreview.argument,chosenBps);
                    return 'REPREVIEW';
                }
                showToast('Cette version Android ne sait pas recertifier un taux ponctuel.');return false;
            }'''
appjs = replace_once(appjs, old_repreview, new_repreview, 'commission re-preview loop fix')
# Client UI branding. Dynamic DOM overlay also catches remaining generated text.
appjs = appjs.replace('Camtel', 'Blue').replace('CAMTEL', 'BLUE')
write('app/src/main/assets/app.js', appjs)

# -----------------------------------------------------------------------------
# v2.7.1 additive overlay: bilingual core UI, Blue branding, local commission
# policy, compact transaction journal, chronology-first balance cache.
# -----------------------------------------------------------------------------
v271js = r'''(function(){
'use strict';
function id(x){return document.getElementById(x);}function bridge(){return typeof window.AndroidBridge==='undefined'?null:window.AndroidBridge;}
function cfg(){try{return JSON.parse((bridge()&&bridge().getConfiguration&&bridge().getConfiguration())||'{}');}catch(e){return {};}}
function esc(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#39;'}[c];});}
function profileKey(){var c=cfg();return String(c.profile_id||c.node_code||'default');}
function safeParse(raw,fallback){try{return JSON.parse(raw);}catch(e){return fallback;}}
function upper(v){return String(v||'').toUpperCase();}
function stamp(v){var n=Date.parse(v||'');return isNaN(n)?0:n;}
function formatMoney(v){var n=Number(v);if(!isFinite(n))return '—';return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}

/* ---------- language + Blue branding ---------- */
var language='fr';try{if(bridge()&&bridge().getUiLanguage)language=bridge().getUiLanguage()==='en'?'en':'fr';}catch(e){}
var EN={
'Accueil':'Home','Piloter':'Control','Fournir':'Supply','Vendre':'Sell','Réseau':'Network','Activité':'Activity','Gérer':'Manage',
'COMPTE ACTIF':'ACTIVE ACCOUNT','MODULES B.I.R.':'B.I.R. MODULES','Soldes & preuves':'Balances & evidence','Robot intelligent':'Smart Robot',
'Activité & SAV':'Activity & Support','Centre Gérer':'Manage Center','ACTIVITÉ EN COURS':'LIVE ACTIVITY','Voir tout':'View all',
'ACHAT DE CRÉDIT':'CREDIT PURCHASE','Demander à mon supérieur':'Request from my superior','Montant (FCFA)':'Amount (FCFA)',
'Envoyer la demande':'Send request','APPROVISIONNEMENT':'SUPPLY','Recharger un enfant direct':'Supply a direct child','Programmer la recharge':'Schedule supply',
'VENTE CLIENT':'CUSTOMER SALE','Recharger un client final':'Top up a customer','Exécuter la vente':'Execute sale','Comptes et slots':'Accounts & SIM slots',
'Actualiser':'Refresh','Actualiser par USSD':'Refresh via USSD','Aucune commande sur ce téléphone.':'No command on this phone.',
'Commandes récentes':'Recent commands','REGISTRE LOCAL':'LOCAL REGISTER','FLOTTE & RÉSEAU':'FLEET & NETWORK','État du nœud actif':'Active node status',
'Commissions':'Commissions','Taux par défaut (%)':'Default rate (%)','ENREGISTRER':'SAVE','PERSONNALISER':'CUSTOMIZE','REVENIR AU DÉFAUT':'RESET TO DEFAULT',
'REVENIR AU RÉSEAU':'BACK TO NETWORK','FIABILITÉ DU SOLDE':'BALANCE RELIABILITY','Preuve avant priorité':'Evidence before priority'
};
function blueText(value){return String(value||'').replace(/CAMTEL/g,'BLUE').replace(/Camtel/g,'Blue').replace(/camtel/g,'Blue');}
function translateText(value){var original=blueText(value),trim=original.replace(/^\s+|\s+$/g,'');if(language==='en'&&EN[trim])return original.replace(trim,EN[trim]);return original;}
function applyLanguage(root){var walker,node,i,els,attrs=['placeholder','title','aria-label'];root=root||document.body;if(!root)return;walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null,false);while((node=walker.nextNode())){if(node.parentNode&&/^(SCRIPT|STYLE)$/.test(node.parentNode.tagName))continue;var changed=translateText(node.nodeValue);if(changed!==node.nodeValue)node.nodeValue=changed;}els=root.querySelectorAll?root.querySelectorAll('input,button,select,textarea,[title],[aria-label]'):[];for(i=0;i<els.length;i+=1){for(var a=0;a<attrs.length;a+=1){var val=els[i].getAttribute&&els[i].getAttribute(attrs[a]);if(val){var nv=translateText(val);if(nv!==val)els[i].setAttribute(attrs[a],nv);}}}}
function languageButton(){var top=document.querySelector('.bir-topbar');if(!top||id('v271Language'))return;var b=document.createElement('button');b.id='v271Language';b.type='button';b.className='v271-language';b.textContent=language==='en'?'FR':'EN';b.title=language==='en'?'Passer en français':'Switch to English';b.onclick=function(){language=language==='en'?'fr':'en';try{if(bridge()&&bridge().setUiLanguage)bridge().setUiLanguage(language);}catch(e){};window.location.reload();};top.appendChild(b);}
function observeBrand(){if(!window.MutationObserver)return;var busy=false;new MutationObserver(function(m){if(busy)return;busy=true;try{for(var i=0;i<m.length;i+=1){for(var j=0;j<m[i].addedNodes.length;j+=1){var n=m[i].addedNodes[j];if(n.nodeType===1)applyLanguage(n);else if(n.nodeType===3)n.nodeValue=translateText(n.nodeValue);}}}finally{busy=false;}}).observe(document.body,{childList:true,subtree:true});}

/* ---------- local commission policy + legacy Worker fallback ---------- */
var commissionServerSupport=null,oneShot={};
function commissionKey(){return 'bir_commission_policy_v271_'+profileKey();}
function commissionPolicy(){var c=cfg(),fallback=upper(c.role)==='DAE'?1000:upper(c.role)==='DSM'?800:0,p=safeParse(localStorage.getItem(commissionKey())||'{}',{});if(typeof p.default_bps!=='number')p.default_bps=fallback;if(!p.children)p.children={};return p;}
function saveCommission(p){try{localStorage.setItem(commissionKey(),JSON.stringify(p));}catch(e){}}
function effectiveRate(child){var key=upper(child),p=commissionPolicy();if(Object.prototype.hasOwnProperty.call(oneShot,key))return Number(oneShot[key]||0);if(Object.prototype.hasOwnProperty.call(p.children,key))return Number(p.children[key]||0);return Number(p.default_bps||0);}
window.BIRCommissionPolicy={getRateBps:effectiveRate,setOneShotRate:function(child,bps){oneShot[upper(child)]=Number(bps||0);},serverSupportsPersistent:function(){return commissionServerSupport===true;}};
function rateStatus(text,kind){var out=id('ctRateList');if(out){out.className='bir-rate-list '+(kind||'');out.textContent=text;}}
function bindCommission(){var def=id('ctDefaultRate'),saveDef=id('ctSaveDefault'),child=id('ctChild'),rate=id('ctChildRate'),saveChild=id('ctSaveChild'),reset=id('ctResetChild'),p=commissionPolicy();if(!def||!saveDef)return;def.value=String(Number(p.default_bps||0)/100).replace('.',',');function parse(v){var n=Number(String(v||'').replace(',','.').replace(/^\s+|\s+$/g,''));return isFinite(n)&&n>=0&&n<=50?Math.round(n*100):null;}saveDef.onclick=function(){var bps=parse(def.value);if(bps===null){rateStatus(language==='en'?'Invalid rate (0–50%).':'Taux invalide (0 à 50 %).','error');return;}p=commissionPolicy();p.default_bps=bps;saveCommission(p);rateStatus((language==='en'?'Local default saved: ':'Taux par défaut local enregistré : ')+String(bps/100).replace('.',',')+' %.','ok');if(commissionServerSupport===true&&bridge()&&bridge().platformAction)bridge().platformAction('commission_set_default',JSON.stringify({rate_bps:bps}));};if(saveChild)saveChild.onclick=function(){var code=upper(child.value),bps=parse(rate.value);if(!code||bps===null){rateStatus(language==='en'?'Enter a direct child and a valid rate.':'Indiquez un enfant direct et un taux valide.','error');return;}p=commissionPolicy();p.children[code]=bps;saveCommission(p);rateStatus(code+' : '+String(bps/100).replace('.',',')+' % '+(language==='en'?'saved locally.':'enregistré localement.'),'ok');if(commissionServerSupport===true&&bridge()&&bridge().platformAction)bridge().platformAction('commission_set_child',JSON.stringify({child_node_code:code,rate_bps:bps}));};if(reset)reset.onclick=function(){var code=upper(child.value);if(!code)return;p=commissionPolicy();delete p.children[code];saveCommission(p);rateStatus(code+' : '+(language==='en'?'back to default ':'retour au défaut ')+String(Number(p.default_bps||0)/100).replace('.',',')+' %.','ok');if(commissionServerSupport===true&&bridge()&&bridge().platformAction)bridge().platformAction('commission_set_child',JSON.stringify({child_node_code:code,use_default:true}));};rateStatus((language==='en'?'Local policy active. Default: ':'Politique locale active. Défaut : ')+String(Number(p.default_bps||0)/100).replace('.',',')+' %.'+(commissionServerSupport===false?(language==='en'?' Current production server does not persist it yet.':' Le serveur de production actuel ne la persiste pas encore.'):''),'ok');}

/* ---------- compact durable transaction journal ---------- */
var journalLimit=100;
function journalKey(){return 'bir_transaction_journal_v271_'+profileKey();}
function isFinancial(c){var op=upper(c&&c.operation),rt=upper(c&&c.request_type);return op.indexOf('TRANSFER')>=0||rt==='SUPPLY_CHILD'||rt==='REQUEST_SUPPLY'||rt==='RETAIL_SALE';}
function journalLoad(){var v=safeParse(localStorage.getItem(journalKey())||'[]',[]);return Object.prototype.toString.call(v)==='[object Array]'?v:[];}
function journalSave(items){items=items.slice(0,5000);var raw=JSON.stringify(items);while(raw.length>1900000&&items.length>100){items.length=Math.max(100,Math.floor(items.length*.9));raw=JSON.stringify(items);}try{localStorage.setItem(journalKey(),raw);}catch(e){while(items.length>100){items.length=Math.floor(items.length*.75);try{localStorage.setItem(journalKey(),JSON.stringify(items));break;}catch(ignored){}}}return items;}
function commandTime(c){return c.operator_event_at||c.completed_at||c.updated_at||c.created_at||new Date().toISOString();}
function compact(c){return {id:String(c.public_id||c.id||''),op:String(c.operation||c.request_type||''),state:String(c.state||''),amount:Number(c.amount||c.total_amount||0),base:Number(c.requested_base_amount||c.base_amount||0),commission:Number(c.commission_amount||0),rate:Number(c.commission_rate_bps||0),target:String(c.target_node_code||''),phone:String(c.target_phone||''),tx:String(c.transaction_id||''),at:commandTime(c),msg:String(c.result_message||'').slice(0,220)};}
function journalCapture(c){if(!c||!isFinancial(c))return;var item=compact(c),items=journalLoad(),i,index=-1;for(i=0;i<items.length;i+=1){if(item.id&&items[i].id===item.id){index=i;break;}}if(index>=0)items.splice(index,1);items.unshift(item);items.sort(function(a,b){return stamp(b.at)-stamp(a.at);});journalSave(items);renderJournal();}
function seedJournal(){var old=safeParse(localStorage.getItem('blue_magic_embedded_commands_'+profileKey())||'[]',[]);if(!journalLoad().length&&old&&old.length){for(var i=old.length-1;i>=0;i-=1)journalCapture(old[i]);}}
function journalPanel(){var support=document.querySelector('[data-tab-panel="support"]');if(!support||id('v271Journal'))return;var card=document.createElement('article');card.id='v271Journal';card.className='panel v271-journal';card.innerHTML='<p class="eyebrow">'+(language==='en'?'TRANSACTION JOURNAL':'JOURNAL DES TRANSACTIONS')+'</p><h3>'+(language==='en'?'Purchases & sales — newest first':'Achats & ventes — plus récent en haut')+'</h3><div class="v271-journal-tools"><input id="v271JournalSearch" placeholder="'+(language==='en'?'Search node, phone, ID…':'Rechercher nœud, numéro, ID…')+'"><button id="v271JournalMore" type="button">'+(language==='en'?'SHOW MORE':'AFFICHER PLUS')+'</button></div><div class="v271-journal-wrap"><table><thead><tr><th>'+(language==='en'?'Date':'Date')+'</th><th>'+(language==='en'?'Operation':'Opération')+'</th><th>'+(language==='en'?'Amount':'Montant')+'</th><th>'+(language==='en'?'Target':'Cible')+'</th><th>'+(language==='en'?'Status':'État')+'</th></tr></thead><tbody id="v271JournalRows"></tbody></table></div><p id="v271JournalMeta" class="small muted"></p>';support.insertBefore(card,support.firstChild);id('v271JournalSearch').oninput=renderJournal;id('v271JournalMore').onclick=function(){journalLimit+=100;renderJournal();};}
function renderJournal(){var rows=id('v271JournalRows'),meta=id('v271JournalMeta');if(!rows)return;var items=journalLoad(),q=upper(id('v271JournalSearch')&&id('v271JournalSearch').value),out=[],shown=0,i,x,hay;for(i=0;i<items.length&&shown<journalLimit;i+=1){x=items[i];hay=upper([x.id,x.op,x.target,x.phone,x.tx,x.state,x.msg].join(' '));if(q&&hay.indexOf(q)<0)continue;out.push('<tr><td>'+esc(new Date(x.at).toLocaleString(language==='en'?'en-GB':'fr-FR'))+'</td><td>'+esc(x.op)+'</td><td>'+esc(formatMoney(x.amount||x.base))+' F</td><td>'+esc(x.target||x.phone||'—')+'</td><td>'+esc(x.state||'—')+'</td></tr>');shown+=1;}rows.innerHTML=out.join('')||'<tr><td colspan="5">'+(language==='en'?'No saved purchase/sale yet.':'Aucun achat/vente sauvegardé pour l’instant.')+'</td></tr>';if(meta)meta.textContent=(language==='en'?'Saved locally: ':'Sauvegardées localement : ')+items.length+' • '+(language==='en'?'compact limit 5,000 entries / ~1.9 MB.':'limite compacte 5 000 entrées / ~1,9 Mo.');}

/* ---------- chronology-first local balance guard ---------- */
function balanceKey(){return 'bir_balance_guard_v271_'+profileKey();}
function balanceLoad(){return safeParse(localStorage.getItem(balanceKey())||'null',null);}
function balanceSave(proof){if(!proof||proof.balance===null||typeof proof.balance==='undefined')return;var old=balanceLoad(),next=Number(proof.ts||stamp(proof.operator_event_at||proof.observed_at));if(old&&Number(old.ts||0)>next)return;proof.ts=next||Date.now();try{localStorage.setItem(balanceKey(),JSON.stringify(proof));}catch(e){}}
function ownNode(data){var c=cfg(),nodes=data&&data.nodes||[],i;for(i=0;i<nodes.length;i+=1){if(upper(nodes[i].node_code)===upper(c.node_code))return nodes[i];}return null;}
function guardDashboard(data){if(!data||data.error)return data;var own=ownNode(data),cached=balanceLoad(),incoming;if(!own||!cached)return data;incoming=stamp(own.operator_event_at||own.observed_at);if(own.balance===null||typeof own.balance==='undefined'||!incoming||incoming<Number(cached.ts||0)){own.balance=cached.balance;own.available_balance=cached.available_balance;own.reserved_amount=cached.reserved_amount;own.balance_quality=cached.balance_quality||'EXACT';own.evidence_kind=cached.evidence_kind||'LOCAL_NEWER_PROOF';own.observed_at=cached.observed_at;own.operator_event_at=cached.operator_event_at||cached.observed_at;own.balance_reusable=true;own.client_balance_guard=true;}else{balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,ts:incoming});}return data;}
function parseBalance(msg,requireCurrent){var s=String(msg||''),re=requireCurrent?/(?:Current\s*Balance|CurrentBalance)[^0-9]{0,25}([0-9][0-9 .,_]*)/i:/(?:Current\s*Balance|CurrentBalance|Solde(?:\s+actuel)?|Balance)[^0-9]{0,25}([0-9][0-9 .,_]*)/i,m=s.match(re);if(!m)return null;var raw=m[1].replace(/[\s,_]/g,'');if(raw.indexOf('.')>=0&&raw.indexOf('.')<raw.length-3)raw=raw.replace(/\./g,'');var n=Number(raw.replace(',','.'));return isFinite(n)?n:null;}
function proofFromCommand(c){if(!c||upper(c.state)!=='SUCCEEDED')return;var op=upper(c.operation),value=null,eventAt=c.operator_event_at||'';if(op==='BALANCE_OWN'||op==='CHECK_BALANCE')value=parseBalance(c.result_message,false);else if(op==='LAST_TRANSACTIONS')value=parseBalance(c.result_message,true);else if(op.indexOf('TRANSFER')>=0&&eventAt)value=parseBalance(c.result_message,true);if(value===null)return;var when=eventAt||c.updated_at||c.completed_at||c.created_at||new Date().toISOString();balanceSave({balance:value,available_balance:value,reserved_amount:0,balance_quality:'EXACT',evidence_kind:op==='LAST_TRANSACTIONS'?'HISTORY_CURRENTBALANCE':'LOCAL_BLUE_PROOF',observed_at:when,operator_event_at:eventAt||when,ts:stamp(when)||Date.now()});showCachedBalance();}
function showCachedBalance(){var p=balanceLoad();if(!p)return;var a=id('ownBalance'),b=id('birCamtelBalance'),f=id('birBalanceFreshness');if(a&&(!a.textContent||/actualiser|refresh/i.test(a.textContent)))a.textContent=formatMoney(p.balance)+' FCFA';if(b&&(!b.textContent||/actualiser|refresh/i.test(b.textContent)))b.textContent=formatMoney(p.balance);if(f)f.textContent=(language==='en'?'Last reliable Blue proof • ':'Dernière preuve Blue fiable • ')+new Date(Number(p.ts||Date.now())).toLocaleString(language==='en'?'en-GB':'fr-FR');}

function wrapCallbacks(){window.BlueMagicNative=window.BlueMagicNative||{};var oldDash=window.BlueMagicNative.onDashboard,oldCreated=window.BlueMagicNative.onCommandCreated,oldStatus=window.BlueMagicNative.onCommandStatus,oldHealth=window.BlueMagicNative.onServerHealth;window.BlueMagicNative.onDashboard=function(data){data=guardDashboard(data||{});if(typeof oldDash==='function')oldDash(data);var own=ownNode(data);if(own&&own.balance!==null&&typeof own.balance!=='undefined'){balanceSave({balance:own.balance,available_balance:own.available_balance,reserved_amount:own.reserved_amount,balance_quality:own.balance_quality,evidence_kind:own.evidence_kind,observed_at:own.observed_at,operator_event_at:own.operator_event_at,ts:stamp(own.operator_event_at||own.observed_at)||Date.now()});}showCachedBalance();applyLanguage(document.body);};window.BlueMagicNative.onCommandCreated=function(data){if(typeof oldCreated==='function')oldCreated(data);if(data&&data.command)journalCapture(data.command);};window.BlueMagicNative.onCommandStatus=function(data){if(typeof oldStatus==='function')oldStatus(data);if(data&&data.command){journalCapture(data.command);proofFromCommand(data.command);}applyLanguage(document.body);};window.BlueMagicNative.onServerHealth=function(data){if(data&&!data.error){var caps=data.capabilities||{},v=String(data.version||''),m=v.match(/(\d+)\.(\d+)\.(\d+)/),ok=caps.commissions===true;if(!ok&&m){ok=Number(m[1])>2||(Number(m[1])===2&&(Number(m[2])>6||(Number(m[2])===6&&Number(m[3])>=10)));}commissionServerSupport=ok;}if(typeof oldHealth==='function')oldHealth(data);bindCommission();};}
function boot(){languageButton();applyLanguage(document.body);observeBrand();journalPanel();seedJournal();renderJournal();showCachedBalance();wrapCallbacks();window.setTimeout(bindCommission,80);var b=bridge();if(b&&b.loadDashboard){try{b.loadDashboard();}catch(e){}}}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
}());
'''
write('app/src/main/assets/control-tower-v271.js', v271js)

v271css = r'''/* B.I.R. v2.7.1 — field stabilization overlay. */
.v271-language{min-width:44px;height:34px;padding:0 10px;border:1px solid rgba(255,255,255,.28);border-radius:999px;background:rgba(255,255,255,.1);color:#fff;font-size:.72rem;font-weight:900;letter-spacing:.05em}
.muted,.small,.bir-tagline,.bir-modules-grid small,.bir-balance-note,.command-time,.v270-evidence-grid span,.v270-business-grid span{font-size:max(.76rem,12.5px)!important;line-height:1.43!important}
.v271-journal{margin:8px 0 14px!important}.v271-journal-tools{display:flex;gap:8px;margin:8px 0}.v271-journal-tools input{flex:1;min-width:0}.v271-journal-tools button{white-space:nowrap}.v271-journal-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}.v271-journal table{width:100%;border-collapse:collapse;font-size:.72rem}.v271-journal th,.v271-journal td{padding:8px 6px;border-bottom:1px solid #dbe5ef;text-align:left;vertical-align:top}.v271-journal th{color:#0b3567;font-size:.67rem;text-transform:uppercase;letter-spacing:.03em}.v271-journal td{color:#304f6d}.v271-journal td:nth-child(3){white-space:nowrap;font-weight:800}
/* Preserve the validated keyboard behavior: the bottom dock may compact/move, never disappear. */
body.form-editing .module-tabs{opacity:.97!important;visibility:visible!important;pointer-events:auto!important}
@media(max-width:520px){.v271-journal-tools{align-items:stretch;flex-direction:column}.v271-journal-tools button{width:100%}.v271-language{height:32px;padding:0 8px}}
'''
write('app/src/main/assets/control-tower-v271.css', v271css)

index = read('app/src/main/assets/index.html')
index = replace_once(index,
    '    <link rel="stylesheet" href="control-tower-v270.css">',
    '    <link rel="stylesheet" href="control-tower-v270.css">\n    <link rel="stylesheet" href="control-tower-v271.css">',
    'v271 CSS wiring')
index = replace_once(index,
    '  <script src="control-tower-v270.js"></script>',
    '  <script src="control-tower-v270.js"></script>\n  <script src="control-tower-v271.js"></script>',
    'v271 JS wiring')
# Static visible branding only. JS runtime handles all later generated nodes.
index = index.replace('Camtel', 'Blue').replace('CAMTEL', 'BLUE')
write('app/src/main/assets/index.html', index)

# -----------------------------------------------------------------------------
# Contract test + recovery state.
# -----------------------------------------------------------------------------
test = r'''import fs from 'node:fs';
function read(p){return fs.readFileSync(p,'utf8');}
function ok(v,m){if(!v)throw new Error(m);}
const gradle=read('app/build.gradle');
const app=read('app/src/main/assets/app.js');
const v271=read('app/src/main/assets/control-tower-v271.js');
const css=read('app/src/main/assets/control-tower-v271.css');
const html=read('app/src/main/assets/index.html');
const main=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const cfg=read('app/src/main/java/com/profitloop/blueauto/AppConfig.java');
const sim=read('app/src/main/java/com/profitloop/blueauto/SimIdentityManager.java');
const simRx=read('app/src/main/java/com/profitloop/blueauto/SimStateReceiver.java');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
ok(gradle.includes('versionCode 52')&&gradle.includes('versionName "2.7.1"'),'v2.7.1 identity');
ok(main.includes('Identifiant Blue')&&main.includes('"MOCK".equals(node)')&&main.includes('Code privé MOCK'),'MOCK only through add/open form');
ok(!main.includes('labelsList.add((mockActive'),'MOCK must not be inserted into normal account list');
ok(main.includes('mockSessionAuthorized = false')&&main.includes('recreate();'),'MOCK must exit/rebuild cleanly');
ok(main.includes('ACTIVATION ADMINISTRATEUR')&&!main.substring(main.indexOf('private void showPairingScreen(boolean'),main.indexOf('private void showPairingScreenLegacy')).includes('Adresse du serveur'),'normal pairing hides server URL');
ok(cfg.includes('putBoolean(robotEnabledKey(profileId), enabled).commit()'),'Robot intent must persist synchronously');
ok(sim.includes('isHardMismatch')&&simRx.includes('isTransientOrRecoverable'),'transient SIM boot state must not disable Robot');
ok(robot.includes('handleRobotNotReady')&&robot.includes('scheduleWatchdog(this, 15_000L)'),'Robot retry path after boot');
ok(app.includes('legacy_commission_mode')&&app.includes('commission_base_amount'),'legacy commission fallback');
ok(v271.includes('bir_commission_policy_v271_')&&v271.includes('default_bps'),'local default/custom commission policy');
ok(v271.includes('slice(0,5000)')&&v271.includes('1900000'),'compact durable journal');
ok(v271.includes('bir_balance_guard_v271_')&&v271.includes('incoming<Number(cached.ts||0)'),'chronology-first balance guard');
ok(v271.includes('replace(/CAMTEL/g,\'BLUE\')')&&v271.includes("getUiLanguage"),'Blue branding + bilingual switch');
ok(html.includes('control-tower-v271.css')&&html.includes('control-tower-v271.js'),'v271 assets wired');
ok(!/form-editing[^}]*display\s*:\s*none/.test(css),'dock must not disappear while typing');
console.log('B.I.R. v2.7.1 field stabilization contract OK');
'''
write('app/src/test/v271-field-stabilization-contract.mjs', test)

doc = '''# B.I.R. v2.7.1 — stabilisation terrain\n\nDate : 2026-08-16\n\n## Base\n\nCette étape part du HEAD documentaire v2.7.0 `b3db1e3b2baac3424f4d7192ecb62d8b61020e8c` et conserve comme APK terrain précédente le SHA applicatif `c92e62e5f3a22369f99c3c2bfe04592abe18cb16`.\n\n## Corrections v2.7.1\n\n- Reprise Robot après reboot : le souhait Robot est persisté synchroniquement. Les états transitoires de la radio/SIM au démarrage ne désactivent plus le Robot. Seuls `NUMBER_MISMATCH` et `SIM_CHANGED` révoquent automatiquement le Robot.\n- MOCK privé : il n'est plus listé dans les comptes normaux. Il se découvre uniquement dans Ajouter/Ouvrir en saisissant `MOCK` puis le code propriétaire. L'autorisation MOCK est une session mémoire, perdue à la fermeture du processus.\n- MOCK non invasif : quitter MOCK ou choisir un vrai compte reconstruit immédiatement l'interface réelle, même si ce compte était déjà le profil de routage sous-jacent.\n- Appairage simplifié : serveur et secret sont masqués du parcours normal; un téléphone vierge affiche seulement une activation administrateur ponctuelle.\n- Commissions : politique locale compacte par acteur (défaut DAE 10 %, DSM 8 %, exceptions enfant). Avec le Worker production 2.6.7, un taux non nul est converti en total base+commission puis ce total est recertifié une seule fois par le serveur, supprimant la boucle 0 %.\n- Limite commissions : un `REQUEST_SUPPLY` initié sur un autre téléphone ne peut pas partager automatiquement la politique locale du supérieur tant que Worker/D1 0005 ne sont pas déployés. Aucun déploiement serveur n'est inclus ici.\n- Solde : cache local chronologique. Une preuve plus vieille ou sans horodatage sûr ne peut pas écraser une preuve locale plus récente. La dernière preuve fiable s'affiche immédiatement au lieu de laisser le solde vide pendant plusieurs minutes.\n- Journal : achats/ventes sauvegardés localement, plus récents en premier, jusqu'à 5 000 entrées et environ 1,9 Mo avant élagage. Une mise à jour APK conserve ce journal; une désinstallation/effacement des données le supprime.\n- Marque : les textes visibles utilisent Blue. Les parseurs/protocoles ne sont pas renommés aveuglément.\n- Bilingue : bouton FR/EN dans la barre supérieure pour le cœur de l'interface, avec préférence locale; les diagnostics profonds gardent le français comme langue de repli.\n- Ergonomie : textes secondaires légèrement agrandis; le dock reste visible/compact lors de la saisie.\n\n## Interdictions conservées\n\n- ne pas fusionner PR #4;\n- ne pas déployer Worker;\n- ne pas appliquer D1 0005;\n- ne pas utiliser la clé permanente pendant la CI normale;\n- ne pas modifier le package `com.profitloop.blueauto`;\n- ne pas contourner un verrou sécurisé Android.\n'''
write('docs/BIR_V271_FIELD_STABILIZATION_STATE.md', doc)

# Release-time server source must remain byte-for-byte outside this Android/client patch.
print('v2.7.1 field patch prepared')
