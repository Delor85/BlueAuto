from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def write(rel, text):
    (ROOT / rel).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'v281 patch anchor missing: {label}')
    if text.count(old) != 1:
        raise SystemExit(f'v281 patch anchor not unique ({text.count(old)}): {label}')
    return text.replace(old, new, 1)


def sub_once(text, pattern, replacement, label, flags=0):
    value, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f'v281 regex anchor count={count}: {label}')
    return value


# ---------------------------------------------------------------------------
# Android identity: additive upgrade only. Package/signing identity untouched.
# ---------------------------------------------------------------------------
p = 'app/build.gradle'
s = read(p)
s = replace_once(s, 'versionCode 53\n        versionName "2.8.0"',
                 'versionCode 54\n        versionName "2.8.1"', 'Android version 2.8.1')
write(p, s)

p = 'app/src/main/java/com/profitloop/blueauto/ApiClient.java'
s = read(p)
s = s.replace('payload.put("app_version", "2.8.0");', 'payload.put("app_version", "2.8.1");')
if s.count('payload.put("app_version", "2.8.1");') < 2:
    raise SystemExit('ApiClient app_version replacements incomplete')
write(p, s)

# ---------------------------------------------------------------------------
# AppConfig: Remote profiles are read-only observers. Never lease USSD here.
# ---------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/AppConfig.java'
s = read(p)
anchor = '''    static String[] profileLabels(Context context) {\n'''
insert = '''    static List<String> remoteProfileIds(Context context) {\n        JSONArray all = profiles(context);\n        List<String> result = new ArrayList<>();\n        for (int i = 0; i < all.length(); i++) {\n            JSONObject profile = all.optJSONObject(i);\n            if (profile == null) continue;\n            String id = profile.optString("id", "");\n            if (!id.isEmpty() && "REMOTE".equalsIgnoreCase(profile.optString("device_mode", "REMOTE"))\n                    && isPaired(context, id)) result.add(id);\n        }\n        return result;\n    }\n\n    static boolean anyRemoteProfile(Context context) {\n        return !remoteProfileIds(context).isEmpty();\n    }\n\n    static int remoteProfileCount(Context context) {\n        return remoteProfileIds(context).size();\n    }\n\n'''
s = replace_once(s, anchor, insert + anchor, 'AppConfig remote helpers')
write(p, s)

# ---------------------------------------------------------------------------
# Accessibility: Android remains authority; reconnecting the granted service
# immediately wakes the Robot/Remote control plane instead of leaving it stale.
# ---------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java'
s = read(p)
s = replace_once(s,
'''        liveInstance = this;\n        handler.postDelayed(inspectAgain, 250L);''',
'''        liveInstance = this;\n        AppConfig.prefs(this).edit()\n                .putString("accessibility_runtime_state_v281", "CONNECTED")\n                .putLong("accessibility_runtime_at_v281", System.currentTimeMillis()).apply();\n        // The permission itself is controlled by Android. Once Android reconnects the already\n        // granted service, wake every local queue immediately instead of waiting for a watchdog.\n        RobotService.forceSync(this);\n        handler.postDelayed(inspectAgain, 250L);''', 'Accessibility reconnect wake')
s = replace_once(s,
'''    public void onInterrupt() {\n        resetAutomation();\n    }''',
'''    public void onInterrupt() {\n        AppConfig.prefs(this).edit()\n                .putString("accessibility_runtime_state_v281", "INTERRUPTED")\n                .putLong("accessibility_runtime_at_v281", System.currentTimeMillis()).apply();\n        resetAutomation();\n    }''', 'Accessibility interrupt state')
s = replace_once(s,
'''    public void onDestroy() {\n        if (liveInstance == this) liveInstance = null;\n        resetAutomation();\n        super.onDestroy();\n    }''',
'''    public void onDestroy() {\n        if (liveInstance == this) liveInstance = null;\n        AppConfig.prefs(this).edit()\n                .putString("accessibility_runtime_state_v281", "DISCONNECTED")\n                .putLong("accessibility_runtime_at_v281", System.currentTimeMillis()).apply();\n        resetAutomation();\n        super.onDestroy();\n    }''', 'Accessibility destroy state')
write(p, s)

# ---------------------------------------------------------------------------
# RobotService: keep Remote observer alive without giving it USSD authority.
# Adaptive read-only snapshots are cached locally; Robot polling remains FIFO.
# ---------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/RobotService.java'
s = read(p)
s = replace_once(s,
'''    private static final long WATCHDOG_INTERVAL_MS = 60_000L;\n    private static final long SIMPLE_UNLOCK_WAIT_MS = 3_500L;''',
'''    private static final long WATCHDOG_INTERVAL_MS = 60_000L;\n    private static final long REMOTE_SNAPSHOT_MS = 15_000L;\n    private static final long REMOTE_HEARTBEAT_MS = 60_000L;\n    private static final long REMOTE_MAX_RETRY_MS = 120_000L;\n    private static final String REMOTE_CACHE_PREFIX = "remote_dashboard_cache_v281_";\n    private static final String REMOTE_CACHE_AT_PREFIX = "remote_dashboard_cache_at_v281_";\n    private static final long SIMPLE_UNLOCK_WAIT_MS = 3_500L;''', 'Remote observer constants')
s = replace_once(s,
'''    private final Map<String, Integer> apiFailureCountByProfile = new HashMap<>();\n    private long backoffMs = AppConfig.IDLE_POLL_MS;''',
'''    private final Map<String, Integer> apiFailureCountByProfile = new HashMap<>();\n    private final Map<String, Long> lastRemoteSnapshotByProfile = new HashMap<>();\n    private long backoffMs = AppConfig.IDLE_POLL_MS;''', 'Remote observer state')

# Existing leased command: never dial a PIN-required financial flow while Android's
# accessibility service is not actually connected. Release the lease safely.
s = replace_once(s,
'''                    } else if (!DeviceLockState.blocksUssd(this)) {\n                        executeCommand(owner, activeUssd, leasedApi);\n                        nextDelay = 2_000L;''',
'''                    } else if (!accessibilityReadyFor(activeUssd)) {\n                        holdLeaseForAccessibility(owner, activeUssd, leasedApi);\n                        nextDelay = BlueAccessibilityService.isEnabled(this) ? 5_000L : 30_000L;\n                    } else if (!DeviceLockState.blocksUssd(this)) {\n                        executeCommand(owner, activeUssd, leasedApi);\n                        nextDelay = 2_000L;''', 'Existing lease accessibility guard')

s = replace_once(s,
'''                        readiness = checkReadiness(profileId);\n                        if (!readiness.ready) {\n                            releaseUnexecutedLease(profileId, command, api, readiness.message);\n                            handleRobotNotReady(profileId, readiness);\n                            nextDelay = 1_000L;\n                            return;\n                        }\n                        executeCommand(profileId, command, api);''',
'''                        readiness = checkReadiness(profileId);\n                        if (!readiness.ready) {\n                            releaseUnexecutedLease(profileId, command, api, readiness.message);\n                            handleRobotNotReady(profileId, readiness);\n                            nextDelay = 1_000L;\n                            return;\n                        }\n                        if (!accessibilityReadyFor(command)) {\n                            holdLeaseForAccessibility(profileId, command, api);\n                            nextDelay = BlueAccessibilityService.isEnabled(this) ? 5_000L : 30_000L;\n                            return;\n                        }\n                        executeCommand(profileId, command, api);''', 'New lease accessibility guard')

# Remote observer runs after Robot FIFO work. It never leases or creates commands.
s = replace_once(s,
'''            boolean reportOutstanding = retryDueFinalReports(4);\n            if (profiles.isEmpty()) {\n                releaseStandbyWakeLock();\n                if (!reportOutstanding) stopSelf();\n                nextDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;\n                return;\n            }\n\n            backoffMs = AppConfig.IDLE_POLL_MS;\n            nextDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;''',
'''            boolean reportOutstanding = retryDueFinalReports(4);\n            long remoteDelay = observeRemoteProfiles();\n            boolean remoteOutstanding = AppConfig.anyRemoteProfile(this);\n            if (profiles.isEmpty()) {\n                releaseStandbyWakeLock();\n                if (!reportOutstanding && !remoteOutstanding) stopSelf();\n                long baseDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;\n                nextDelay = remoteOutstanding ? Math.min(baseDelay, remoteDelay) : baseDelay;\n                return;\n            }\n\n            backoffMs = AppConfig.IDLE_POLL_MS;\n            nextDelay = Math.min(reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS, remoteDelay);''', 'Remote observer cycle')

insert_before = '''    private boolean hasServiceWork() {\n        return AppConfig.anyRobotEnabled(this) || PendingCommandStore.hasAnyPending(this);\n    }'''
remote_methods = '''    private boolean accessibilityReadyFor(JSONObject command) {\n        return command == null || !UssdCommandFactory.requiresPin(command)\n                || BlueAccessibilityService.isConnected();\n    }\n\n    private void holdLeaseForAccessibility(String profileId, JSONObject command, ApiClient api) {\n        boolean granted = BlueAccessibilityService.isEnabled(this);\n        String reason = granted\n                ? "Accessibilité Android autorisée mais service en reconnexion; aucune composition financière avant reconnexion."\n                : "Accessibilité Android désactivée; réactivation utilisateur requise avant achat/vente.";\n        releaseUnexecutedLease(profileId, command, api, reason);\n        apiRetryAtByProfile.put(profileId, System.currentTimeMillis() + (granted ? 5_000L : 30_000L));\n        updateNotification(robotSummary(granted\n                ? "Accessibilité en reconnexion — Robot conservé, reprise automatique dès retour du service"\n                : "Accessibilité désactivée — Robot conservé, achat/vente en attente de réactivation"));\n    }\n\n    /**\n     * Read-only Remote observer. Heartbeat keeps the server route fresh; dashboard snapshots\n     * are cached locally so the foreground UI can render immediately without multiplying calls.\n     * No lease_command/create_command/USSD is ever invoked here.\n     */\n    private long observeRemoteProfiles() {\n        List<String> remotes = AppConfig.remoteProfileIds(this);\n        if (remotes.isEmpty()) return Long.MAX_VALUE;\n        long now = System.currentTimeMillis();\n        long nextDue = now + REMOTE_SNAPSHOT_MS;\n        for (String profileId : remotes) {\n            long retryAt = apiRetryAtByProfile.containsKey(profileId)\n                    ? apiRetryAtByProfile.get(profileId) : 0L;\n            if (retryAt > now) {\n                nextDue = Math.min(nextDue, retryAt);\n                continue;\n            }\n            ApiClient api = ApiClient.forProfile(this, profileId);\n            try {\n                long lastHeartbeat = lastHeartbeatByProfile.containsKey(profileId)\n                        ? lastHeartbeatByProfile.get(profileId) : 0L;\n                if (now - lastHeartbeat >= REMOTE_HEARTBEAT_MS) {\n                    api.heartbeat(false);\n                    lastHeartbeatByProfile.put(profileId, now);\n                }\n                long lastSnapshot = lastRemoteSnapshotByProfile.containsKey(profileId)\n                        ? lastRemoteSnapshotByProfile.get(profileId) : 0L;\n                if (now - lastSnapshot >= REMOTE_SNAPSHOT_MS) {\n                    JSONObject dashboard = api.dashboard();\n                    AppConfig.prefs(this).edit()\n                            .putString(REMOTE_CACHE_PREFIX + profileId, dashboard.toString())\n                            .putLong(REMOTE_CACHE_AT_PREFIX + profileId, now).apply();\n                    lastRemoteSnapshotByProfile.put(profileId, now);\n                    updateNotification(robotSummary("Remote synchronisé — "\n                            + AppConfig.nodeCode(this, profileId)));\n                }\n                clearProfileApiFailure(profileId);\n                long hbDue = (lastHeartbeatByProfile.containsKey(profileId)\n                        ? lastHeartbeatByProfile.get(profileId) : now) + REMOTE_HEARTBEAT_MS;\n                long dashDue = (lastRemoteSnapshotByProfile.containsKey(profileId)\n                        ? lastRemoteSnapshotByProfile.get(profileId) : now) + REMOTE_SNAPSHOT_MS;\n                nextDue = Math.min(nextDue, Math.min(hbDue, dashDue));\n            } catch (Exception error) {\n                long failureRetryAt = Math.min(now + REMOTE_MAX_RETRY_MS, markProfileApiFailure(profileId));\n                nextDue = Math.min(nextDue, failureRetryAt);\n                updateNotification(robotSummary("Remote en reprise réseau — "\n                        + AppConfig.nodeCode(this, profileId)));\n            }\n        }\n        return Math.max(1_000L, nextDue - System.currentTimeMillis());\n    }\n\n    static JSONObject cachedRemoteDashboard(Context context, String profileId, long maxAgeMs) {\n        if (profileId == null || profileId.isEmpty()) return null;\n        long at = AppConfig.prefs(context).getLong(REMOTE_CACHE_AT_PREFIX + profileId, 0L);\n        if (at <= 0L || System.currentTimeMillis() - at > Math.max(1_000L, maxAgeMs)) return null;\n        String raw = AppConfig.prefs(context).getString(REMOTE_CACHE_PREFIX + profileId, "");\n        if (raw.isEmpty()) return null;\n        try { return new JSONObject(raw); } catch (Exception ignored) { return null; }\n    }\n\n    private boolean hasServiceWork() {\n        return AppConfig.anyRobotEnabled(this) || PendingCommandStore.hasAnyPending(this)\n                || AppConfig.anyRemoteProfile(this);\n    }'''
s = replace_once(s, insert_before, remote_methods, 'RobotService observer methods')

s = replace_once(s,
'''    static void scheduleWatchdog(Context context, long delayMs) {\n        if (!AppConfig.anyRobotEnabled(context)) return;''',
'''    static void scheduleWatchdog(Context context, long delayMs) {\n        if (!AppConfig.anyRobotEnabled(context) && !AppConfig.anyRemoteProfile(context)) return;''', 'Watchdog Remote support')
s = replace_once(s,
'''        return (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O\n                ? new Notification.Builder(this, CHANNEL_ID) : new Notification.Builder(this))\n                .setContentTitle("Blue Magic — " + AppConfig.enabledRobotCount(this) + " Robot(s) actif(s)")''',
'''        return (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O\n                ? new Notification.Builder(this, CHANNEL_ID) : new Notification.Builder(this))\n                .setContentTitle("B.I.R. — " + AppConfig.enabledRobotCount(this) + " Robot(s) • "\n                        + AppConfig.remoteProfileCount(this) + " Remote(s)")''', 'Notification title')
s = replace_once(s,
'''    private String robotSummary(String detail) {\n        return AppConfig.enabledRobotCount(this) + " Robot(s) — " + detail;\n    }''',
'''    private String robotSummary(String detail) {\n        return AppConfig.enabledRobotCount(this) + " Robot(s) • "\n                + AppConfig.remoteProfileCount(this) + " Remote(s) — " + detail;\n    }''', 'Notification summary')
write(p, s)

# ---------------------------------------------------------------------------
# Boot/package/watchdog: Remote observers also come back after boot/replacement.
# ---------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/BootReceiver.java'
s = read(p)
s = replace_once(s,
'''        if (AppConfig.hasProfiles(context)) RobotService.pollAdministrativeControls(context);\n        if (!AppConfig.anyRobotEnabled(context)) return;\n        // Robot intent is persistent locally. Boot, package replacement, watchdog and a normal\n        // user unlock all wake the same foreground service; none of these silently changes the\n        // Android Accessibility setting.\n        RobotService.startEnabled(context);\n        RobotService.scheduleWatchdog(context, WATCHDOG_MS);''',
'''        if (AppConfig.hasProfiles(context)) RobotService.pollAdministrativeControls(context);\n        if (!AppConfig.anyRobotEnabled(context) && !AppConfig.anyRemoteProfile(context)) return;\n        // Robot intent and Remote observation are persistent locally. Boot, package replacement,\n        // watchdog and normal user unlock wake the same foreground control service; Android remains\n        // the sole authority for Accessibility and no financial confirmation is automated here.\n        RobotService.startEnabled(context);\n        RobotService.scheduleWatchdog(context, WATCHDOG_MS);''', 'Boot Remote observer')
write(p, s)

# ---------------------------------------------------------------------------
# MainActivity: old-Android native Manage safety net, owner account switching,
# 30-minute owner inactivity lock, clearer accessibility/runtime recovery.
# ---------------------------------------------------------------------------
p = 'app/src/main/java/com/profitloop/blueauto/MainActivity.java'
s = read(p)
s = replace_once(s,
'''    private static final String OWNER_ADMIN_WORKSPACE_KEY = "bir_owner_admin_workspace_v280";\n    private static final String OWNER_ADMIN_RETURN_PROFILE_KEY = "bir_owner_admin_return_profile_v280";''',
'''    private static final String OWNER_ADMIN_WORKSPACE_KEY = "bir_owner_admin_workspace_v280";\n    private static final String OWNER_ADMIN_RETURN_PROFILE_KEY = "bir_owner_admin_return_profile_v280";\n    private static final String OWNER_SESSION_LAST_ACTIVITY_KEY = "bir_owner_session_last_activity_v281";\n    private static final long OWNER_SESSION_IDLE_MS = 30L * 60_000L;\n    private static final String ADMIN_PROFILE_ID = "__BIR_OWNER_ADMIN__";''', 'Owner timeout constants')

s = replace_once(s,
'''    private boolean isOwnerAdminWorkspaceActive() {\n        return adminSessionAuthorized && AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                && SecureOwnerStore.has(this, "OWNER_ADMIN");\n    }''',
'''    private boolean isOwnerAdminWorkspaceActive() {\n        return adminSessionAuthorized && !ownerSessionExpired()\n                && AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                && SecureOwnerStore.has(this, "OWNER_ADMIN");\n    }\n\n    private boolean ownerSessionExpired() {\n        long last = AppConfig.prefs(this).getLong(OWNER_SESSION_LAST_ACTIVITY_KEY, 0L);\n        return last > 0L && System.currentTimeMillis() - last >= OWNER_SESSION_IDLE_MS;\n    }\n\n    private void touchOwnerSession() {\n        AppConfig.prefs(this).edit().putLong(OWNER_SESSION_LAST_ACTIVITY_KEY,\n                System.currentTimeMillis()).apply();\n    }\n\n    private boolean expireOwnerSessionIfIdle() {\n        if (!ownerSessionExpired()) return false;\n        String returnProfile = AppConfig.prefs(this).getString(OWNER_ADMIN_RETURN_PROFILE_KEY, "");\n        if (returnProfile.isEmpty()) {\n            returnProfile = AppConfig.prefs(this).getString(MOCK_RETURN_PROFILE_KEY, "");\n        }\n        boolean hadOwnerSession = mockSessionAuthorized || adminSessionAuthorized\n                || AppConfig.prefs(this).getBoolean(MOCK_WORKSPACE_KEY, false)\n                || AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false);\n        mockSessionAuthorized = false;\n        adminSessionAuthorized = false;\n        AppConfig.prefs(this).edit()\n                .putBoolean(MOCK_WORKSPACE_KEY, false)\n                .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                .remove(MOCK_RETURN_PROFILE_KEY)\n                .remove(OWNER_ADMIN_RETURN_PROFILE_KEY)\n                .remove(OWNER_SESSION_LAST_ACTIVITY_KEY).commit();\n        if (!returnProfile.isEmpty()) AppConfig.activateProfile(this, returnProfile);\n        return hadOwnerSession;\n    }\n\n    @Override\n    public void onUserInteraction() {\n        super.onUserInteraction();\n        if (ownerSessionExpired()) {\n            if (expireOwnerSessionIfIdle()) recreate();\n            return;\n        }\n        if (mockSessionAuthorized || adminSessionAuthorized) touchOwnerSession();\n    }''', 'Owner timeout mechanics')

s = replace_once(s,
'''        mockSessionAuthorized = true;\n        AppConfig.prefs(this).edit()''',
'''        mockSessionAuthorized = true;\n        touchOwnerSession();\n        AppConfig.prefs(this).edit()''', 'Mock session touch')
s = replace_once(s,
'''                adminSessionAuthorized = true;\n                AppConfig.prefs(this).edit()''',
'''                adminSessionAuthorized = true;\n                touchOwnerSession();\n                AppConfig.prefs(this).edit()''', 'Admin session touch')

s = replace_once(s,
'''                        ? ui("Accès propriétaire privé. Le compte MOCK ne sera jamais affiché dans la liste normale des comptes.",\n                                "Private owner access. MOCK will never appear in the normal account list.")''',
'''                        ? ui("Accès propriétaire privé. Après enrôlement, MOCK apparaît dans la liste des comptes avec verrouillage après 30 minutes d’inactivité.",\n                                "Private owner access. Once enrolled, MOCK appears in the account list and locks after 30 minutes of inactivity.")''', 'Mock account list wording')

# Replace the complete account manager with a combined real + protected virtual list.
new_account_manager = r'''    private void showAccountManager() {
        String[] realLabels = AppConfig.profileLabels(this);
        String[] realIds = AppConfig.profileIds(this);
        final List<String> labels = new ArrayList<>();
        final List<String> ids = new ArrayList<>();
        for (int i = 0; i < realIds.length; i++) {
            labels.add(realLabels[i]);
            ids.add(realIds[i]);
        }
        boolean mockKnown = SecureOwnerStore.has(this, "MOCK_OWNER") || mockSessionAuthorized;
        boolean adminKnown = SecureOwnerStore.has(this, "OWNER_ADMIN") || adminSessionAuthorized;
        if (mockKnown) {
            labels.add("MOCK • PROPRIÉTAIRE • " + ((mockSessionAuthorized && !ownerSessionExpired())
                    ? ui("SESSION ACTIVE", "SESSION ACTIVE") : ui("VERROUILLÉ", "LOCKED")));
            ids.add(MOCK_PROFILE_ID);
        }
        if (adminKnown) {
            labels.add("ADMIN • PROPRIÉTAIRE • " + ((adminSessionAuthorized && !ownerSessionExpired())
                    ? ui("SESSION ACTIVE", "SESSION ACTIVE") : ui("VERROUILLÉ", "LOCKED")));
            ids.add(ADMIN_PROFILE_ID);
        }
        final boolean leavingOwnerWorkspace = isMockWorkspaceActive()
                || AppConfig.prefs(this).getBoolean(OWNER_ADMIN_WORKSPACE_KEY, false);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(ui("Tous les comptes B.I.R.", "All B.I.R. accounts"))
                .setItems(labels.toArray(new String[0]), (ignored, index) -> {
                    if (index < 0 || index >= ids.size()) return;
                    String selected = ids.get(index);
                    if (MOCK_PROFILE_ID.equals(selected)) {
                        openOwnerVirtualAccount("MOCK_OWNER");
                        return;
                    }
                    if (ADMIN_PROFILE_ID.equals(selected)) {
                        openOwnerVirtualAccount("OWNER_ADMIN");
                        return;
                    }
                    // Leaving an owner workspace does NOT destroy its 30-minute authenticated
                    // session. This makes DAE/DSM/PoS <-> MOCK/ADMIN switching immediate while
                    // inactivity still forces the code again.
                    AppConfig.prefs(this).edit()
                            .putBoolean(MOCK_WORKSPACE_KEY, false)
                            .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)
                            .remove(MOCK_RETURN_PROFILE_KEY)
                            .remove(OWNER_ADMIN_RETURN_PROFILE_KEY).commit();
                    if (!selected.equals(AppConfig.profileId(this))) AppConfig.activateProfile(this, selected);
                    if (mockSessionAuthorized || adminSessionAuthorized) touchOwnerSession();
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
            if (leavingOwnerWorkspace) {
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

    private void openOwnerVirtualAccount(String kind) {
        boolean mock = "MOCK_OWNER".equals(kind);
        boolean authorized = mock ? mockSessionAuthorized : adminSessionAuthorized;
        if (authorized && !ownerSessionExpired()) {
            String returnProfile = AppConfig.profileId(this);
            AppConfig.prefs(this).edit()
                    .putString(mock ? MOCK_RETURN_PROFILE_KEY : OWNER_ADMIN_RETURN_PROFILE_KEY, returnProfile)
                    .putBoolean(MOCK_WORKSPACE_KEY, mock)
                    .putBoolean(OWNER_ADMIN_WORKSPACE_KEY, !mock).commit();
            touchOwnerSession();
            recreate();
            return;
        }
        LinearLayout content = verticalContainer();
        content.setPadding(dp(16), dp(8), dp(16), dp(8));
        EditText code = field(mock ? ui("Code privé MOCK", "Private MOCK code")
                : ui("Code privé ADMIN propriétaire", "Private owner ADMIN code"), "", true);
        TextView feedback = help(ui("Session propriétaire verrouillée. Le code est requis après 30 minutes d’inactivité.",
                "Owner session is locked. The code is required after 30 minutes of inactivity."));
        content.addView(feedback);
        content.addView(code);
        AlertDialog dialog = new AlertDialog.Builder(this)
                .setTitle(mock ? ui("Ouvrir MOCK", "Open MOCK") : ui("Ouvrir ADMIN", "Open ADMIN"))
                .setView(content)
                .setPositiveButton(ui("OUVRIR", "OPEN"), null)
                .setNegativeButton(ui("Annuler", "Cancel"), null)
                .create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE)
                .setOnClickListener(v -> {
                    String value = code.getText().toString().trim();
                    if (mock) openMockFromPairing(value, feedback);
                    else openOwnerAdminFromPairing(value, feedback);
                    code.setText("");
                    if ((mock && mockSessionAuthorized) || (!mock && adminSessionAuthorized)) dialog.dismiss();
                }));
        dialog.show();
    }

'''
s = sub_once(s, r'    private void showAccountManager\(\) \{.*?\n    private void showSimSlotChooser\(\) \{',
             new_account_manager + '    private void showSimSlotChooser() {',
             'Combined owner account manager', flags=re.S)

# Old Android WebView safety net: visible native Manage/Accounts bar on Android 6/8.
s = replace_once(s,
'''        Button accounts = actionButton("COMPTES (" + AppConfig.profileCount(this) + ")", GOLD);\n        manageButton = actionButton("☰ GÉRER", VIOLET);\n        compactBar.addView(accounts, weighted());\n        compactBar.addView(manageButton, weighted());\n        page.addView(compactBar);\n        compactBar.setVisibility(View.GONE);''',
'''        int visibleAccountCount = AppConfig.profileCount(this)\n                + (SecureOwnerStore.has(this, "MOCK_OWNER") ? 1 : 0)\n                + (SecureOwnerStore.has(this, "OWNER_ADMIN") ? 1 : 0);\n        Button accounts = actionButton(ui("COMPTES (" + visibleAccountCount + ")",\n                "ACCOUNTS (" + visibleAccountCount + ")"), GOLD);\n        manageButton = actionButton(ui("☰ GÉRER", "☰ MANAGE"), VIOLET);\n        compactBar.addView(manageButton, weighted());\n        compactBar.addView(accounts, weighted());\n        page.addView(compactBar);\n        compactBar.setVisibility(Build.VERSION.SDK_INT <= Build.VERSION_CODES.O\n                ? View.VISIBLE : View.GONE);''', 'Android 6/8 native Manage bar')

# Runtime status differentiates granted-but-disconnected from actually disabled.
s = replace_once(s,
'''        boolean accessibility = BlueAccessibilityService.isEnabled(this);''',
'''        boolean accessibility = BlueAccessibilityService.isEnabled(this);\n        boolean accessibilityConnected = BlueAccessibilityService.isConnected();''', 'Accessibility runtime status variable')
s = replace_once(s,
'''        } else if (robotEnabled && !accessibility) {\n            status.append("\\n⚠ Accessibilité à activer avant achat/vente • TEST_NUMBER reste direct");''',
'''        } else if (robotEnabled && !accessibility) {\n            status.append("\\n⚠ Accessibilité désactivée par Android • Robot conservé • achat/vente en attente");\n        } else if (robotEnabled && !accessibilityConnected) {\n            status.append("\\n↻ Accessibilité autorisée mais service en reconnexion • reprise automatique");''', 'Accessibility reconnect status')
s = replace_once(s,
'''        nativeStatus.setTextColor((!sim.valid || AppConfig.pinBlocked(this)\n                || (robotEnabled && !accessibility)) ? GOLD : CYAN);''',
'''        nativeStatus.setTextColor((!sim.valid || AppConfig.pinBlocked(this)\n                || (robotEnabled && (!accessibility || !accessibilityConnected))) ? GOLD : CYAN);''', 'Accessibility status color')

# Resume wakes both Robot and Remote observer and enforces owner idle lock.
s = replace_once(s,
'''    protected void onResume() {\n        super.onResume();\n        applyRobotWindowPolicy();\n        RobotService.pollAdministrativeControls(this);\n        if (AppConfig.anyRobotEnabled(this)) {''',
'''    protected void onResume() {\n        super.onResume();\n        if (expireOwnerSessionIfIdle()) {\n            recreate();\n            return;\n        }\n        applyRobotWindowPolicy();\n        RobotService.pollAdministrativeControls(this);\n        if (AppConfig.anyRobotEnabled(this) || AppConfig.anyRemoteProfile(this)) {''', 'Resume Remote + owner timeout')

# Dashboard UI first consumes a fresh background Remote cache; stale/missing cache falls through.
s = replace_once(s,
'''        public void loadDashboard() {\n            new Thread(() -> {\n                try {\n                    callback("onDashboard", new ApiClient(MainActivity.this).dashboard());''',
'''        public void loadDashboard() {\n            new Thread(() -> {\n                try {\n                    if (!AppConfig.isRobotMode(MainActivity.this)) {\n                        RobotService.startEnabled(MainActivity.this);\n                        JSONObject cached = RobotService.cachedRemoteDashboard(MainActivity.this,\n                                AppConfig.profileId(MainActivity.this), 20_000L);\n                        if (cached != null) {\n                            cached.put("_bir_remote_cache", true);\n                            callback("onDashboard", cached);\n                            return;\n                        }\n                    }\n                    callback("onDashboard", new ApiClient(MainActivity.this).dashboard());''', 'Remote dashboard cache')

# Owner exit keeps the authenticated session warm until its shared 30-minute idle deadline.
s = replace_once(s,
'''                adminSessionAuthorized = false;\n                AppConfig.prefs(MainActivity.this).edit().putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                        .remove(OWNER_ADMIN_RETURN_PROFILE_KEY).commit();''',
'''                AppConfig.prefs(MainActivity.this).edit().putBoolean(OWNER_ADMIN_WORKSPACE_KEY, false)\n                        .remove(OWNER_ADMIN_RETURN_PROFILE_KEY).commit();\n                touchOwnerSession();''', 'Admin exit session persistence')
s = replace_once(s,
'''                mockSessionAuthorized = false;\n                AppConfig.prefs(MainActivity.this).edit()\n                        .putBoolean(MOCK_WORKSPACE_KEY, false)\n                        .putBoolean(MOCK_OWNER_ENABLED_KEY, false)\n                        .remove(MOCK_RETURN_PROFILE_KEY)\n                        .commit();''',
'''                AppConfig.prefs(MainActivity.this).edit()\n                        .putBoolean(MOCK_WORKSPACE_KEY, false)\n                        .remove(MOCK_RETURN_PROFILE_KEY)\n                        .commit();\n                touchOwnerSession();''', 'Mock exit session persistence')
write(p, s)

# ---------------------------------------------------------------------------
# Existing JS UI: distinguish accessibility grant from runtime connection.
# ---------------------------------------------------------------------------
p = 'app/src/main/assets/app.js'
s = read(p)
s = replace_once(s,
'''        else if(configuration.mode==='ROBOT'&&!configuration.accessibility_enabled){showActionError({code:'FINANCE_ACCESSIBILITY_REQUIRED',message:'TEST_NUMBER reste disponible. Activez l’Accessibilité Blue Magic avant un achat ou une vente.'});}''',
'''        else if(configuration.mode==='ROBOT'&&!configuration.accessibility_enabled){showActionError({code:'FINANCE_ACCESSIBILITY_REQUIRED',message:'TEST_NUMBER reste disponible. Activez l’Accessibilité B.I.R. avant un achat ou une vente. Le Robot reste mémorisé et reprendra après réactivation.'});}\n        else if(configuration.mode==='ROBOT'&&configuration.accessibility_enabled&&!configuration.accessibility_connected){showActionProgress('Accessibilité autorisée mais service Android en reconnexion. Le Robot reste actif logiquement et reprendra automatiquement sans perdre la file.');}''', 'JS accessibility runtime message')
write(p, s)

# ---------------------------------------------------------------------------
# v2.8 overlay: account switch in ADMIN + expanded pragmatic English coverage.
# ---------------------------------------------------------------------------
p = 'app/src/main/assets/control-tower-v280.js'
s = read(p)
s = replace_once(s,
'''<button id="v280AdminAudit">'+t('JOURNAL ADMIN','ADMIN AUDIT')+'</button><button id="v280AdminExit" class="secondary">''',
'''<button id="v280AdminAudit">'+t('JOURNAL ADMIN','ADMIN AUDIT')+'</button><button id="v280AdminAccounts" class="secondary">'+t('CHANGER DE COMPTE','SWITCH ACCOUNT')+'</button><button id="v280AdminExit" class="secondary">''', 'Admin account switch button')
s = replace_once(s,
'''bind('v280TchoSave',function(){request('owner_tchoronko_save',{role:val('v280TchoRole'),node_code:val('v280TchoNode'),parent_node_code:val('v280TchoParent'),phone_number:val('v280TchoPhone'),display_name:val('v280TchoName'),zone:val('v280TchoZone')});});bind('v280AdminRefresh' ''',
'''bind('v280TchoSave',function(){request('owner_tchoronko_save',{role:val('v280TchoRole'),node_code:val('v280TchoNode'),parent_node_code:val('v280TchoParent'),phone_number:val('v280TchoPhone'),display_name:val('v280TchoName'),zone:val('v280TchoZone')});});bind('v280AdminAccounts',function(){var b=bridge();if(b&&b.openAccounts)b.openAccounts();});bind('v280AdminRefresh' ''', 'Admin account switch binding')
# Expand exact-match dictionary while keeping protected operator/protocol terms unchanged.
s = replace_once(s,
''' 'Actualiser tout':'Refresh all','Aucune donnée':'No data'\n};''',
''' 'Actualiser tout':'Refresh all','Aucune donnée':'No data',\n'En attente':'Pending','Réservée au Robot':'Leased to Robot','Composition USSD':'USSD dialing','Vérification du pop-up':'Prompt verification','PIN validé':'PIN submitted','Confirmation Blue':'Blue confirmation','Réussie':'Successful','Échec':'Failed','À vérifier':'Needs review','Annulée':'Cancelled',\n'Compte inconnu':'Unknown account','Tous les comptes B.I.R.':'All B.I.R. accounts','Ajouter / Ouvrir':'Add / Open','Supprimer l’actif':'Delete active','Fermer':'Close','Verrouillé':'Locked','Session active':'Active session',\n'Autorisations':'Permissions','Batterie':'Battery','Synchroniser':'Synchronize','Démarrer Robot':'Start Robot','Arrêter Robot':'Stop Robot','Changer de mode':'Change mode','Vérifier / réparer l’appairage':'Verify / repair pairing',\n'Solde recalculé':'Recalculated balance','preuve certifiée':'certified evidence','mouvement(s) confirmé(s)':'confirmed movement(s)','Disponible':'Available','Réservé confirmé':'Confirmed reserved','Composante commission':'Commission component',\n'Compte actif':'Active account','Tour de contrôle':'Control tower','Serveur en ligne':'Server online','Dernière synchronisation':'Last synchronization','Reprise automatique':'Automatic recovery','Aucune activité':'No activity',\n'Gestion avancée des enfants':'Advanced child management','Demande utilisateur':'User request','Confirmation utilisateur requise':'User confirmation required','Aucune opération financière silencieuse':'No silent financial operation',\n'Code privé MOCK':'Private MOCK code','Code privé ADMIN propriétaire':'Private owner ADMIN code','Session propriétaire verrouillée. Le code est requis après 30 minutes d’inactivité.':'Owner session is locked. The code is required after 30 minutes of inactivity.',\n'Ouvrir MOCK':'Open MOCK','Ouvrir ADMIN':'Open ADMIN','Changer de compte':'Switch account','Comptes Blue':'Blue accounts','Tous les comptes':'All accounts'\n};''', 'Expanded bilingual dictionary')
write(p, s)

# ---------------------------------------------------------------------------
# v2.8.1 contract: exact requested field fixes + security boundaries.
# ---------------------------------------------------------------------------
test = r'''import fs from 'node:fs';
function read(p){return fs.readFileSync(p,'utf8');}
function need(v, token, label){if(!v.includes(token)) throw new Error('Missing '+label+': '+token);}
const gradle=read('app/build.gradle');
const main=read('app/src/main/java/com/profitloop/blueauto/MainActivity.java');
const appConfig=read('app/src/main/java/com/profitloop/blueauto/AppConfig.java');
const robot=read('app/src/main/java/com/profitloop/blueauto/RobotService.java');
const boot=read('app/src/main/java/com/profitloop/blueauto/BootReceiver.java');
const access=read('app/src/main/java/com/profitloop/blueauto/BlueAccessibilityService.java');
const js=read('app/src/main/assets/control-tower-v280.js');
need(gradle,'versionCode 54','vc54'); need(gradle,'versionName "2.8.1"','v2.8.1');
need(main,'OWNER_SESSION_IDLE_MS = 30L * 60_000L','30-minute owner timeout');
need(main,'MOCK_PROFILE_ID.equals(selected)','MOCK virtual account row');
need(main,'ADMIN_PROFILE_ID.equals(selected)','ADMIN virtual account row');
need(main,'openOwnerVirtualAccount','owner reauthentication');
need(main,'Build.VERSION.SDK_INT <= Build.VERSION_CODES.O','Android 6/8 native Manage fallback');
need(main,'compactBar.addView(manageButton, weighted())','Manage top-left first');
need(main,'AppConfig.anyRobotEnabled(this) || AppConfig.anyRemoteProfile(this)','Remote resume observer');
need(main,'RobotService.cachedRemoteDashboard','Remote local cache');
need(appConfig,'remoteProfileIds','Remote profile selection');
need(robot,'REMOTE_SNAPSHOT_MS = 15_000L','adaptive Remote snapshot');
need(robot,'api.dashboard()','Remote read-only dashboard');
need(robot,'accessibilityReadyFor','Accessibility runtime guard');
need(robot,'Accessibilité en reconnexion','automatic accessibility recovery status');
need(robot,'|| AppConfig.anyRemoteProfile(this)','Remote service persistence');
need(boot,'!AppConfig.anyRobotEnabled(context) && !AppConfig.anyRemoteProfile(context)','boot Remote observer');
need(access,'RobotService.forceSync(this)','accessibility reconnect wake');
need(js,'v280AdminAccounts','ADMIN account switch');
need(js,'30 minutes d’inactivité','owner bilingual lock wording');
if(robot.includes('Settings.Secure.put')||access.includes('Settings.Secure.put')) throw new Error('Forbidden accessibility privilege escalation');
if(robot.includes('leaseCommand();') && !robot.includes('Read-only Remote observer')) { throw new Error('Remote observer boundary missing'); }
console.log('BIR v2.8.1 field-quality contract: OK');
'''
write('app/src/test/v281-field-quality-contract.mjs', test)

print('BIR v2.8.1 field-quality patch applied')
