package com.profitloop.blueauto;

import android.Manifest;
import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.SystemClock;

import org.json.JSONObject;

import java.util.Calendar;
import java.util.HashMap;
import java.util.Locale;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public class RobotService extends Service {
    static final String ACTION_START = "com.profitloop.blueauto.START_ROBOT";
    static final String ACTION_WAKE = "com.profitloop.blueauto.WAKE_ROBOTS";
    static final String ACTION_STOP = "com.profitloop.blueauto.STOP_ROBOT";
    static final String ACTION_CANCEL = "com.profitloop.blueauto.CANCEL_PENDING";
    static final String ACTION_PIN_SUBMITTED = "com.profitloop.blueauto.PIN_SUBMITTED";
    static final String ACTION_OPERATOR_RESULT = "com.profitloop.blueauto.OPERATOR_RESULT";
    static final String ACTION_AUDIT = "com.profitloop.blueauto.REQUEST_AUDIT";
    static final String ACTION_FORCE_SYNC = "com.profitloop.blueauto.FORCE_SYNC";
    static final String ACTION_CONTROL_POLL = "com.profitloop.blueauto.ADMIN_CONTROL_POLL";
    static final String EXTRA_PROFILE_ID = "profile_id";
    static final String EXTRA_SUCCESS = "success";
    static final String EXTRA_MESSAGE = "message";
    static final String EXTRA_ERROR_CODE = "error_code";
    static final String EXTRA_TRANSACTION_ID = "transaction_id";

    private static final String CHANNEL_ID = "blue_magic_robot";
    private static final int NOTIFICATION_ID = 5502;
    private static final int WATCHDOG_REQUEST_CODE = 5503;
    private static final long STANDBY_WAKE_MS = 30 * 60_000L;
    private static final long WATCHDOG_INTERVAL_MS = 60_000L;
    private static final long REMOTE_SNAPSHOT_MS = 5_000L;
    private static final long REMOTE_HEARTBEAT_MS = 20_000L;
    private static final long REMOTE_MAX_RETRY_MS = 30_000L;
    private static final String REMOTE_CACHE_PREFIX = "remote_dashboard_cache_v281_";
    private static final String REMOTE_CACHE_AT_PREFIX = "remote_dashboard_cache_at_v281_";
    private static final long SIMPLE_UNLOCK_WAIT_MS = 3_500L;
    private static final long SIMPLE_UNLOCK_COOLDOWN_MS = 30_000L;

    private ScheduledExecutorService executor;
    private final AtomicBoolean cycleRunning = new AtomicBoolean(false);
    private final Map<String, Long> lastHeartbeatByProfile = new HashMap<>();
    private final Map<String, Long> apiRetryAtByProfile = new HashMap<>();
    private final Map<String, Integer> apiFailureCountByProfile = new HashMap<>();
    private final Map<String, Long> lastRemoteSnapshotByProfile = new HashMap<>();
    private long backoffMs = AppConfig.IDLE_POLL_MS;
    private int roundRobinIndex = 0;
    private PowerManager.WakeLock commandWakeLock;
    private PowerManager.WakeLock standbyWakeLock;
    private long standbyWakeRenewAt = 0L;
    private long lastCommandFinishedAt = 0L;

    @Override
    public void onCreate() {
        super.onCreate();
        executor = Executors.newSingleThreadScheduledExecutor();
        createNotificationChannel();
        enterForeground(notification("Robots en préparation…"));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_WAKE : intent.getAction();
        String profileId = profileId(intent);

        if (ACTION_CANCEL.equals(action)) {
            final String targetProfile = profileId;
            executor.execute(() -> cancelPendingCommand(targetProfile));
            return START_STICKY;
        }

        if (ACTION_STOP.equals(action)) {
            if (!profileId.isEmpty()) {
                AppConfig.setRobotEnabled(this, profileId, false);
                lastHeartbeatByProfile.remove(profileId);
                clearProfileApiFailure(profileId);
            }
            if (!AppConfig.anyRobotEnabled(this)) releaseStandbyWakeLock();
            final String stoppedProfile = profileId;
            final boolean stopAfterRelease = !hasServiceWork();
            executor.execute(() -> {
                try {
                    if (!stoppedProfile.isEmpty()) {
                        ApiClient.forProfile(this, stoppedProfile).heartbeat();
                    }
                } catch (Exception ignored) {
                    // Local stop remains authoritative; no other phone is elected automatically.
                } finally {
                    if (stopAfterRelease) {
                        updateNotification("Tous les Robots sont arrêtés");
                        stopSelf();
                    }
                }
            });
            if (stopAfterRelease) {
                updateNotification("Arrêt du Robot en cours de confirmation…");
                return START_NOT_STICKY;
            }
            updateNotification(robotSummary("Robot arrêté; autres Robots actifs"));
            scheduleCycle(0L);
            return START_STICKY;
        }

        if (ACTION_PIN_SUBMITTED.equals(action)) {
            final String targetProfile = profileId;
            executor.execute(() -> reportProgress(targetProfile, "PIN_SUBMITTED",
                    "PIN local injecté et validation envoyée."));
            return START_STICKY;
        }

        if (ACTION_OPERATOR_RESULT.equals(action)) {
            boolean success = intent.getBooleanExtra(EXTRA_SUCCESS, false);
            String message = intent.getStringExtra(EXTRA_MESSAGE);
            String code = intent.getStringExtra(EXTRA_ERROR_CODE);
            String transactionId = intent.getStringExtra(EXTRA_TRANSACTION_ID);
            final String targetProfile = profileId;
            executor.execute(() -> finishCommand(targetProfile, success, code, message, transactionId));
            return START_STICKY;
        }

        if (ACTION_FORCE_SYNC.equals(action)) {
            apiRetryAtByProfile.clear();
            apiFailureCountByProfile.clear();
            lastHeartbeatByProfile.clear();
            lastRemoteSnapshotByProfile.clear();
            backoffMs = 250L;
            updateNotification(robotSummary("Auto-Réveil — reprise immédiate de la synchronisation"));
            executor.execute(() -> {
                OfflineSyncManager.syncSome(this, 25);
                retryDueFinalReports(8);
            });
            scheduleCycle(0L);
            scheduleWatchdog(this, 5_000L);
            return START_STICKY;
        }

        if (ACTION_CONTROL_POLL.equals(action)) {
            executor.execute(() -> {
                pollAdministrativeControlsInternal();
                if (!hasServiceWork()) stopSelf();
            });
            return START_NOT_STICKY;
        }

        if (ACTION_AUDIT.equals(action)) {
            final String targetProfile = profileId;
            executor.schedule(() -> queueOverlapAudit(targetProfile, true), 1_000L, TimeUnit.MILLISECONDS);
            return START_STICKY;
        }

        if (ACTION_START.equals(action) && !profileId.isEmpty()) {
            AppConfig.setRobotEnabled(this, profileId, true);
            lastHeartbeatByProfile.remove(profileId);
            clearProfileApiFailure(profileId);
        }
        if (!hasServiceWork()) {
            stopSelf();
            return START_NOT_STICKY;
        }
        acquireStandbyWakeLock();
        scheduleWatchdog(this, WATCHDOG_INTERVAL_MS);
        updateNotification(robotSummary("Surveillance active"));
        scheduleCycle(0L);
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void scheduleCycle(long delayMs) {
        if (executor == null || executor.isShutdown() || !hasServiceWork()) return;
        executor.schedule(this::runCycle, Math.max(0L, delayMs), TimeUnit.MILLISECONDS);
    }

    private void runCycle() {
        if (!cycleRunning.compareAndSet(false, true)) return;
        long nextDelay = AppConfig.IDLE_POLL_MS;
        try {
            List<String> profiles = AppConfig.enabledRobotProfileIds(this);
            if (!profiles.isEmpty()) acquireStandbyWakeLock();
            // Synchronization is secondary to execution: failures here never block local USSD.
            OfflineSyncManager.syncSome(this, 4);
            List<JSONObject> activeCommands = PendingCommandStore.getActiveUssdCommands(this);
            // A lease captured before a SIM was removed must be returned to the server before it can
            // block the correct Robot. Once dialing may have started we fail closed as UNKNOWN.
            for (JSONObject active : activeCommands) {
                String owner = active.optString("local_profile_id", "");
                Readiness readiness = checkReadiness(owner);
                if (readiness.ready) continue;
                String state = active.optString("local_state", PendingCommandStore.LEASED);
                if (PendingCommandStore.LEASED.equals(state)) {
                    if (active.optBoolean("local_origin", false)) {
                        if (readiness.hardFailure) finishCommand(owner, false, "LOCAL_ROBOT_NOT_READY", readiness.message, "");
                        else handleRobotNotReady(owner, readiness);
                    } else {
                        releaseUnexecutedLease(owner, active, ApiClient.forProfile(this, owner), readiness.message);
                    }
                } else {
                    finishCommand(owner, false, "SIM_LOST_DURING_COMMAND",
                            readiness.message + " La transaction doit être vérifiée avant toute reprise.", "");
                }
                handleRobotNotReady(owner, readiness);
            }

            activeCommands = PendingCommandStore.getActiveUssdCommands(this);
            if (activeCommands.size() > 1) {
                for (int index = 1; index < activeCommands.size(); index++) {
                    JSONObject conflict = activeCommands.get(index);
                    String conflictProfile = conflict.optString("local_profile_id", "");
                    if (PendingCommandStore.LEASED.equals(
                            conflict.optString("local_state", PendingCommandStore.LEASED))) {
                        if (conflict.optBoolean("local_origin", false)) continue;
                        releaseUnexecutedLease(conflictProfile, conflict,
                                ApiClient.forProfile(this, conflictProfile),
                                "Une autre session USSD utilise déjà ce téléphone.");
                    } else {
                        finishCommand(conflictProfile, false, "CONCURRENT_COMMAND_RECOVERY",
                                "Plusieurs sessions USSD déjà composées ont été détectées. Vérification manuelle requise.", "");
                    }
                }
            }

            JSONObject activeUssd = activeCommands.isEmpty() ? null : activeCommands.get(0);
            if (activeUssd != null) {
                String owner = activeUssd.optString("local_profile_id", "");
                String localState = activeUssd.optString("local_state", PendingCommandStore.LEASED);
                if (PendingCommandStore.LEASED.equals(localState)) {
                    ApiClient leasedApi = activeUssd.optBoolean("local_origin", false) ? null : ApiClient.forProfile(this, owner);
                    if (DeviceLockState.isSecurelyLocked(this)) {
                        releaseLockedLease(owner, activeUssd, leasedApi);
                        nextDelay = AppConfig.LOCKED_POLL_MS;
                    } else if (!accessibilityReadyFor(activeUssd)) {
                        holdLeaseForAccessibility(owner, activeUssd, leasedApi);
                        nextDelay = BlueAccessibilityService.isEnabled(this) ? 5_000L : 30_000L;
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

            long sinceLastCommand = System.currentTimeMillis() - lastCommandFinishedAt;
            if (lastCommandFinishedAt > 0L && sinceLastCommand < AppConfig.NEXT_COMMAND_GAP_MS) {
                nextDelay = AppConfig.NEXT_COMMAND_GAP_MS - sinceLastCommand;
                return;
            }

            profiles = AppConfig.enabledRobotProfileIds(this);
            String lastProfileProblem = "";
            int count = profiles.size();
            for (int offset = 0; offset < count; offset++) {
                int index = (roundRobinIndex + offset) % count;
                String profileId = profiles.get(index);
                if (!AppConfig.isPaired(this, profileId) || !AppConfig.isRobotMode(this, profileId)) continue;
                if (PendingCommandStore.get(this, profileId) != null) continue;
                long retryAt = apiRetryAtByProfile.containsKey(profileId)
                        ? apiRetryAtByProfile.get(profileId) : 0L;
                if (retryAt > System.currentTimeMillis()) {
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : réseau en reprise; autres SIM prioritaires";
                    continue;
                }

                ApiClient api = ApiClient.forProfile(this, profileId);
                try {
                    Readiness readiness = checkReadiness(profileId);
                    if (!readiness.ready) {
                        handleRobotNotReady(profileId, readiness);
                        try {
                            api.heartbeat();
                            lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                        } catch (Exception ignored) {
                        }
                        lastProfileProblem = AppConfig.nodeCode(this, profileId)
                                + " : " + readiness.message;
                        continue;
                    }

                    long lastHeartbeat = lastHeartbeatByProfile.containsKey(profileId)
                            ? lastHeartbeatByProfile.get(profileId) : 0L;
                    if (System.currentTimeMillis() - lastHeartbeat >= AppConfig.HEARTBEAT_MS) {
                        api.heartbeat(lastHeartbeat == 0L);
                        lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                    }

                    maybeQueueNightlyNetworkAudit(profileId, api);
                    JSONObject lease = api.leaseCommand();
                    clearProfileApiFailure(profileId);
                    if (lease.optBoolean("force_sync", false)) {
                        apiRetryAtByProfile.remove(profileId);
                        lastHeartbeatByProfile.remove(profileId);
                        OfflineSyncManager.syncSome(this, 25);
                        retryDueFinalReports(8);
                        try {
                            api.heartbeat(false);
                            lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                        } catch (Exception ignored) {}
                        updateNotification(robotSummary("Auto-Réveil distant reçu — synchronisation reprise"));
                        nextDelay = 500L;
                        continue;
                    }
                    if (lease.optBoolean("available", false)) {
                        JSONObject command = lease.optJSONObject("command");
                        if (command == null) throw new IllegalStateException("Commande louée absente.");
                        command.put("local_profile_id", profileId);
                        command.put("local_state", PendingCommandStore.LEASED);
                        command.put("leased_at", System.currentTimeMillis());
                        command.put("state_changed_at", System.currentTimeMillis());
                        PendingCommandStore.save(this, profileId, command);
                        try { JSONObject received = new JSONObject(command.toString()); received.remove("lease_token");
                            LocalEventStore.append(this, profileId, command.optString("public_id"), "REMOTE_ORDER_RECEIVED", received);
                        } catch (Exception ignored) {}
                        roundRobinIndex = (index + 1) % count;
                        if (DeviceLockState.blocksUssd(this)) {
                            if (DeviceLockState.isSecurelyLocked(this)
                                    || !beginSimpleUnlockAssist(profileId, command)) {
                                releaseLockedLease(profileId, command, api);
                                nextDelay = AppConfig.LOCKED_POLL_MS;
                            } else {
                                nextDelay = 750L;
                            }
                            return;
                        }
                        readiness = checkReadiness(profileId);
                        if (!readiness.ready) {
                            releaseUnexecutedLease(profileId, command, api, readiness.message);
                            handleRobotNotReady(profileId, readiness);
                            nextDelay = 1_000L;
                            return;
                        }
                        if (!accessibilityReadyFor(command)) {
                            holdLeaseForAccessibility(profileId, command, api);
                            nextDelay = BlueAccessibilityService.isEnabled(this) ? 5_000L : 30_000L;
                            return;
                        }
                        executeCommand(profileId, command, api);
                        nextDelay = 2_000L;
                        backoffMs = AppConfig.IDLE_POLL_MS;
                        return;
                    }

                } catch (ApiClient.ApiException apiError) {
                    // API business/auth errors are explicit server answers, not transport stalls.
                    clearProfileApiFailure(profileId);
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : " + apiError.code + " — " + safeMessage(apiError);
                } catch (Exception profileError) {
                    long failureRetryAt = markProfileApiFailure(profileId);
                    long seconds = Math.max(1L, (failureRetryAt - System.currentTimeMillis() + 999L) / 1000L);
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : réseau lent; nouvelle tentative dans ~" + seconds
                            + " s, autres SIM non bloquées";
                }
            }

            boolean reportOutstanding = retryDueFinalReports(4);
            long remoteDelay = observeRemoteProfiles();
            boolean remoteOutstanding = AppConfig.anyRemoteProfile(this);
            if (profiles.isEmpty()) {
                releaseStandbyWakeLock();
                if (!reportOutstanding && !remoteOutstanding) stopSelf();
                long baseDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;
                nextDelay = remoteOutstanding ? Math.min(baseDelay, remoteDelay) : baseDelay;
                return;
            }

            backoffMs = AppConfig.IDLE_POLL_MS;
            nextDelay = Math.min(reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS, remoteDelay);
            if (!lastProfileProblem.isEmpty()) {
                updateNotification(robotSummary("Une SIM signale « " + lastProfileProblem
                        + " »; les autres files continuent"));
            } else {
                updateNotification(robotSummary(reportOutstanding
                        ? "Une synchronisation reste à reprendre; les autres files continuent"
                        : "Aucune commande en attente"));
            }
        } catch (Exception error) {
            updateNotification(robotSummary("Cycle interne interrompu — nouvelle tentative"));
            backoffMs = Math.min(60_000L, Math.max(AppConfig.IDLE_POLL_MS, backoffMs * 2L));
            nextDelay = backoffMs;
        } finally {
            cycleRunning.set(false);
            scheduleCycle(nextDelay);
        }
    }

    private void pollAdministrativeControlsInternal() {
        String[] ids = AppConfig.profileIds(this);
        for (String profileId : ids) {
            if (!AppConfig.isPaired(this, profileId)) continue;
            try {
                JSONObject data = ApiClient.forProfile(this, profileId).controlPoll();
                org.json.JSONArray actions = data.optJSONArray("actions");
                if (actions == null) continue;
                for (int i = 0; i < actions.length(); i++) {
                    JSONObject action = actions.optJSONObject(i);
                    if (action == null) continue;
                    long actionId = action.optLong("id", 0L);
                    String command = action.optString("action", "");
                    boolean ok = applyAdministrativeControl(profileId, command);
                    try { ApiClient.forProfile(this, profileId).controlAck(actionId, ok,
                            ok ? "Action appliquée localement." : "Action refusée par les contrôles locaux."); }
                    catch (Exception ignored) {}
                }
            } catch (ApiClient.ApiException unsupported) {
                // Production v2.6.7 does not expose this endpoint yet. Silent fail keeps the old app path cheap.
                if (!"UNKNOWN_ACTION".equals(unsupported.code)) markProfileApiFailure(profileId);
            } catch (Exception ignored) { markProfileApiFailure(profileId); }
        }
    }

    private boolean applyAdministrativeControl(String profileId, String command) {
        if ("STOP_ROBOT".equals(command)) {
            AppConfig.setRobotEnabled(this, profileId, false);
            return true;
        }
        if ("SET_REMOTE".equals(command)) {
            AppConfig.setRobotEnabled(this, profileId, false);
            return AppConfig.updateMode(this, profileId, "REMOTE");
        }
        if ("SET_ROBOT".equals(command)) return AppConfig.updateMode(this, profileId, "ROBOT");
        if ("SYNC_NOW".equals(command)) {
            apiRetryAtByProfile.remove(profileId); lastHeartbeatByProfile.remove(profileId); return true;
        }
        if ("CANCEL_PENDING".equals(command)) { cancelPendingCommand(profileId); return true; }
        if ("START_ROBOT".equals(command)) {
            if (!AppConfig.isRobotMode(this, profileId)) AppConfig.updateMode(this, profileId, "ROBOT");
            Readiness readiness = checkReadiness(profileId);
            if (!readiness.ready) return false;
            AppConfig.setRobotEnabled(this, profileId, true);
            lastHeartbeatByProfile.remove(profileId);
            return true;
        }
        return false;
    }

    private void maybeQueueNightlyNetworkAudit(String profileId, ApiClient api) {
        String role = AppConfig.role(this, profileId).toUpperCase(Locale.ROOT);
        int startMinute;
        int spanMinutes;
        if ("POS".equals(role)) { startMinute = 2 * 60; spanMinutes = 60; }
        else if ("DSM".equals(role)) { startMinute = 3 * 60; spanMinutes = 60; }
        else if ("DAE".equals(role)) { startMinute = 4 * 60; spanMinutes = 60; }
        else return;

        Calendar now = Calendar.getInstance();
        int minuteOfDay = now.get(Calendar.HOUR_OF_DAY) * 60 + now.get(Calendar.MINUTE);
        if (minuteOfDay >= 7 * 60) return;
        String dayKey = String.format(Locale.US, "%04d-%03d",
                now.get(Calendar.YEAR), now.get(Calendar.DAY_OF_YEAR));
        String node = AppConfig.nodeCode(this, profileId);
        int slot = deterministicNightSlot(node + "|" + dayKey + "|PRIMARY", spanMinutes);
        int dueMinute = startMinute + slot;
        android.content.SharedPreferences prefs =
                getSharedPreferences("blue_magic_night_audit", MODE_PRIVATE);
        String primaryKey = profileId + "_" + role + "_primary";
        String finalKey = profileId + "_" + role + "_final";
        String retryKey = profileId + "_" + role + "_retry_at";
        long retryAt = prefs.getLong(retryKey, 0L);
        if (System.currentTimeMillis() < retryAt) return;

        String phase = "";
        if (minuteOfDay >= dueMinute && !dayKey.equals(prefs.getString(primaryKey, ""))) {
            phase = "PRIMARY";
        } else if ("DAE".equals(role)) {
            // A small second DAE sweep before 06:00 catches post-audit activity without waking
            // every PoS a second time. Reports themselves remain live and never freeze at this hour.
            int finalDue = 5 * 60 + 15
                    + deterministicNightSlot(node + "|" + dayKey + "|FINAL", 40);
            if (minuteOfDay >= finalDue && !dayKey.equals(prefs.getString(finalKey, ""))) {
                phase = "FINAL";
            }
        }
        if (phase.isEmpty()) return;

        try {
            JSONObject result = api.networkBalanceAudit();
            boolean complete = result.optBoolean("complete", false);
            android.content.SharedPreferences.Editor edit = prefs.edit();
            if (complete) {
                edit.putString("FINAL".equals(phase) ? finalKey : primaryKey, dayKey)
                        .remove(retryKey).apply();
            } else {
                edit.putLong(retryKey, System.currentTimeMillis() + 5 * 60_000L).apply();
            }
            updateNotification(robotSummary("Audit " + phase.toLowerCase(Locale.ROOT) + " " + role + " : "
                    + result.optInt("queued", 0) + " requête(s), "
                    + result.optInt("reused", 0) + " preuve(s), "
                    + result.optInt("deferred", 0) + " différée(s)"));
        } catch (Exception ignored) {
            prefs.edit().putLong(retryKey, System.currentTimeMillis() + 5 * 60_000L).apply();
        }
    }

    private static int deterministicNightSlot(String key, int spanMinutes) {
        int hash = key == null ? 0 : key.hashCode();
        if (hash == Integer.MIN_VALUE) hash = 0;
        return Math.abs(hash) % Math.max(1, spanMinutes);
    }

    private boolean retryDueFinalReports(int maxAttempts) {
        boolean outstanding = false;
        int attempted = 0;
        for (String profileId : AppConfig.profileIds(this)) {
            JSONObject pending = PendingCommandStore.get(this, profileId);
            if (pending == null || !PendingCommandStore.REPORT_PENDING.equals(
                    pending.optString("local_state", ""))) continue;
            if (attempted < Math.max(1, maxAttempts) && PendingCommandStore.isFinalReportRetryDue(pending)) {
                retryFinalReport(profileId, pending);
                attempted += 1;
                pending = PendingCommandStore.get(this, profileId);
            }
            if (pending != null && PendingCommandStore.REPORT_PENDING.equals(
                    pending.optString("local_state", ""))) outstanding = true;
        }
        return outstanding;
    }

    private void executeCommand(String profileId, JSONObject command, ApiClient api) {
        try {
            Readiness readiness = checkReadiness(profileId);
            if (!readiness.ready) {
                releaseUnexecutedLease(profileId, command, api, readiness.message);
                handleRobotNotReady(profileId, readiness);
                return;
            }
            String operation = UssdCommandFactory.operation(command);
            CommandExecutionPolicy.Capability capability = CommandExecutionPolicy.capability(
                    operation,
                    SecurePinStore.hasPin(this, profileId),
                    BlueAccessibilityService.isEnabled(this),
                    AppConfig.pinBlocked(this, profileId));
            if (!capability.ready) {
                if ("ACCESSIBILITY_DISABLED".equals(capability.code)) {
                    releaseUnexecutedLease(profileId, command, api,
                            "Accessibilité Blue Magic désactivée; transaction financière conservée en file.");
                    updateNotification(robotSummary("Robot actif — Accessibilité à réactiver; achats/ventes restent en file"));
                    return;
                }
                finishCommand(profileId, false, capability.code, capability.message, "");
                return;
            }
            String ussd = UssdCommandFactory.buildAndValidate(this, profileId, command);
            boolean requiresPin = UssdCommandFactory.requiresPin(command);
            if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
                finishCommand(profileId, false, "CALL_PERMISSION_MISSING",
                        "Autorisation Téléphone non accordée.", "");
                return;
            }
            if (SimCallManager.slotCount(this) > 1
                    && checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
                finishCommand(profileId, false, "SIM_PERMISSION_MISSING",
                        "Autorisation État du téléphone requise pour sélectionner la SIM.", "");
                return;
            }
            if (DeviceLockState.blocksUssd(this)) {
                releaseLockedLease(profileId, command, api);
                return;
            }
            acquireCommandWakeLock();
            try {
                PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);
                if (api != null) {
                    // This single fence is intentionally kept: it prevents another Robot from
                    // re-leasing a transaction after physical USSD may have started.
                    api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot.", "");
                }
                updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");

                String next = requiresPin ? PendingCommandStore.AWAITING_PIN
                        : PendingCommandStore.AWAITING_RESULT;
                PendingCommandStore.updateState(this, profileId, next);
                SimCallManager.placeUssdCall(this, ussd, profileId);
                if (requiresPin) BlueAccessibilityService.kick(this);
            } catch (SecurityException permissionError) {
                finishCommand(profileId, false, "SIM_PERMISSION_MISSING", safeMessage(permissionError), "");
            } catch (IllegalStateException slotError) {
                finishCommand(profileId, false, "SIM_SELECTION_FAILED", safeMessage(slotError), "");
            }
        } catch (SecurityException securityError) {
            finishCommand(profileId, false, "COMMAND_INTEGRITY_FAILURE", securityError.getMessage(), "");
        } catch (Exception error) {
            finishCommand(profileId, false, "DIAL_FAILURE", safeMessage(error), "");
        }
    }


    private void reportProgress(String profileId, String state, String message) {
        if (profileId == null || profileId.isEmpty()) return;
        JSONObject command = PendingCommandStore.get(this, profileId);
        if (command == null) return;
        try {
            if ("PIN_SUBMITTED".equals(state)) {
                PendingCommandStore.updateState(this, profileId, PendingCommandStore.AWAITING_RESULT);
            }
            JSONObject progress = new JSONObject(); progress.put("state", state); progress.put("message", message == null ? "" : message);
            LocalEventStore.append(this, profileId, command.optString("public_id"), "LOCAL_PROGRESS", progress);
        } catch (Exception ignored) {}
    }

    private void finishCommand(String profileId, boolean success, String errorCode,
                               String message, String transactionId) {
        if (profileId == null || profileId.isEmpty()) return;
        JSONObject command = PendingCommandStore.get(this, profileId);
        if (command == null) return;
        String code = errorCode == null ? "" : errorCode;
        String state;
        if (success) {
            state = "SUCCEEDED";
        } else if ("WRONG_PIN".equals(code) || "PIN_BLOCKED".equals(code)) {
            state = "BLOCKED";
            if ("WRONG_PIN".equals(code)) AppConfig.setPinBlocked(this, profileId, true);
        } else if ("RESULT_TIMEOUT".equals(code)
                || "USER_CANCELLED_UNCERTAIN".equals(code)
                || "CONCURRENT_COMMAND_RECOVERY".equals(code)) {
            state = "UNKNOWN";
        } else {
            state = "FAILED";
        }

        boolean localOrigin = command.optBoolean("local_origin", false);
        if (localOrigin) {
            try {
                JSONObject result = new JSONObject(command.toString());
                result.remove("lease_token"); result.put("state", state); result.put("error_code", code);
                result.put("result_message", message == null ? "" : message);
                result.put("operator_transaction_id", transactionId == null ? "" : transactionId);
                result.put("completed_at_ms", System.currentTimeMillis());
                LocalEventStore.append(this, profileId, command.optString("public_id"), "LOCAL_COMMAND_RESULT", result);
            } catch (Exception ignored) {}
            if (success && "MODIFY_PIN_LOCAL".equals(UssdCommandFactory.operation(command))) {
                try { PendingPinChangeStore.commit(this, profileId); } catch (Exception ignored) {}
            }
            PendingCommandStore.clear(this, profileId);
            lastCommandFinishedAt = System.currentTimeMillis(); releaseCommandWakeLock(); BlueAccessibilityService.kick(this);
            executor.execute(() -> OfflineSyncManager.syncProfile(this, profileId, 8));
            updateNotification(success ? "Commande locale réussie — synchronisation asynchrone" : "Commande locale terminée — preuve conservée");
            scheduleCycle(1_000L); return;
        }

        boolean reported = false;
        try {
            String detail = message == null ? "" : message;
            if (!code.isEmpty()) detail = code + " — " + detail;
            ApiClient.forProfile(this, profileId).sendEvent(
                    command, state, detail, transactionId == null ? "" : transactionId);
            reported = true;
        } catch (Exception ignored) {
            try {
                command.put("local_state", PendingCommandStore.REPORT_PENDING);
                command.put("final_state", state);
                command.put("final_message", message == null ? "" : message);
                command.put("final_error_code", code);
                command.put("final_transaction_id", transactionId == null ? "" : transactionId);
                command.put("state_changed_at", System.currentTimeMillis());
                PendingCommandStore.save(this, profileId, command);
            } catch (Exception ignoredAgain) {
            }
        }
        if (reported && success && "MODIFY_PIN_LOCAL".equals(UssdCommandFactory.operation(command))) {
            try { PendingPinChangeStore.commit(this, profileId); } catch (Exception ignored) {}
        }
        if (reported && success && CommandExecutionPolicy.isFinancial(UssdCommandFactory.operation(command))) {
            scheduleOverlapAuditAfterFinancial(profileId);
        }
        if (reported) PendingCommandStore.clear(this, profileId);
        lastCommandFinishedAt = System.currentTimeMillis();
        releaseCommandWakeLock();
        BlueAccessibilityService.kick(this);
        updateNotification(reported
                ? (success ? "Dernière commande réussie — " + AppConfig.nodeCode(this, profileId)
                : (AppConfig.pinBlocked(this, profileId) ? "PIN incorrect — Robot bloqué"
                : "Dernière commande à vérifier — " + AppConfig.nodeCode(this, profileId)))
                : "Résultat obtenu — synchronisation en attente");
        scheduleCycle(reported ? 1_000L : 15_000L);
    }

    private void scheduleOverlapAuditAfterFinancial(String profileId) {
        String key = "overlap_tx_count_" + profileId;
        int count = AppConfig.prefs(this).getInt(key, 0) + 1;
        if (count < 4) {
            AppConfig.prefs(this).edit().putInt(key, count).apply();
            return;
        }
        AppConfig.prefs(this).edit().putInt(key, 0).apply();
        executor.schedule(() -> queueOverlapAudit(profileId, false), 15_000L, TimeUnit.MILLISECONDS);
    }

    private void queueOverlapAudit(String profileId, boolean forced) {
        if (profileId == null || profileId.isEmpty() || !AppConfig.robotEnabled(this, profileId)) return;
        if (PendingCommandStore.get(this, profileId) != null) {
            if (forced) executor.schedule(() -> queueOverlapAudit(profileId, true), 5_000L, TimeUnit.MILLISECONDS);
            return;
        }
        try {
            JSONObject payload = new JSONObject();
            payload.put("request_type", "LAST_TRANSACTIONS");
            payload.put("client_request_id", "audit_" + java.util.UUID.randomUUID().toString().replace("-", ""));
            ApiClient.forProfile(this, profileId).createCommand(payload);
            updateNotification(robotSummary("Audit Blue des 5 dernières transactions programmé"));
            scheduleCycle(0L);
        } catch (Exception ignored) {
            if (forced) executor.schedule(() -> queueOverlapAudit(profileId, true), 30_000L, TimeUnit.MILLISECONDS);
        }
    }

    private void retryFinalReport(String profileId, JSONObject command) {
        String state = command.optString("final_state", "UNKNOWN");
        String message = command.optString("final_message", "");
        String code = command.optString("final_error_code", "");
        String transactionId = command.optString("final_transaction_id", "");
        ApiClient api = ApiClient.forProfile(this, profileId);
        try {
            String detail = code.isEmpty() ? message : code + " — " + message;
            api.sendEvent(command, state, detail, transactionId);
            PendingCommandStore.clear(this, profileId);
            updateNotification(robotSummary("Résultat synchronisé"));
        } catch (Exception error) {
            PendingCommandStore.incrementReportRetries(this, profileId);
            try {
                JSONObject status = api.commandStatus(command.optString("public_id", ""));
                JSONObject remote = status.optJSONObject("command");
                if (remote != null && isTerminalState(remote.optString("state", ""))) {
                    PendingCommandStore.clear(this, profileId);
                    updateNotification(robotSummary("Résultat déjà confirmé par le serveur"));
                    return;
                }
            } catch (Exception ignored) {
            }
            updateNotification(robotSummary("Résultat en attente de synchronisation"));
        }
    }

    private void cancelPendingCommand(String profileId) {
        if (profileId == null || profileId.isEmpty()) return;
        JSONObject command = PendingCommandStore.get(this, profileId);
        if (command == null) {
            updateNotification(robotSummary("Aucune opération à annuler pour cette SIM"));
            return;
        }
        String localState = command.optString("local_state", PendingCommandStore.LEASED);
        if (PendingCommandStore.REPORT_PENDING.equals(localState)) {
            retryFinalReport(profileId, command);
            scheduleCycle(0L);
            if (PendingCommandStore.get(this, profileId) != null) {
                updateNotification(robotSummary("Preuve conservée; autres files toujours libérées"));
            }
            return;
        }
        BlueAccessibilityService.cancelVisiblePrompt(this, profileId);
        if (PendingCommandStore.LEASED.equals(localState)) {
            finishCommand(profileId, false, "USER_CANCELLED_BEFORE_DIAL",
                    "Commande annulée localement avant la composition USSD.", "");
        } else {
            finishCommand(profileId, false, "USER_CANCELLED_UNCERTAIN",
                    "Annulation demandée après le début possible de la session; vérification manuelle requise.", "");
        }
    }

    private boolean beginSimpleUnlockAssist(String profileId, JSONObject command) {
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
        if (command != null && command.optBoolean("local_origin", false)) {
            releaseCommandWakeLock();
            updateNotification(robotSummary(secure ? "Écran sécurisé — commande locale conservée jusqu’au déverrouillage humain" : "Écran verrouillé — commande locale conservée et reprise automatique"));
            scheduleWatchdog(this, 15_000L); return;
        }
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

    private Readiness checkReadiness(String profileId) {
        if (profileId == null || profileId.isEmpty()) {
            return Readiness.failure("Profil Robot local absent.");
        }
        if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
            return Readiness.failure("Autorisation Téléphone absente; Robot arrêté sans louer de commande.");
        }
        if (checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            return Readiness.failure("Autorisation État du téléphone absente; SIM invérifiable.");
        }
        SimIdentityManager.Verification sim = SimIdentityManager.verify(this, profileId);
        if (!sim.valid) {
            return SimIdentityManager.isHardMismatch(sim)
                    ? Readiness.hardFailure(sim.message)
                    : Readiness.retryable(sim.message);
        }
        // La présence de la SIM est le verrou d'éligibilité. Certains dialers Android 6 à 13
        // ne publient leur PhoneAccount qu'au moment de l'appel : exiger cette route ici arrêtait
        // le Robot avant qu'il puisse louer TEST_NUMBER ou une commande financière. La route
        // exacte reste résolue et contrôlée immédiatement avant placeCall().
        return Readiness.ready(sim);
    }

    private void handleRobotNotReady(String profileId, Readiness readiness) {
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

    private void releaseUnexecutedLease(String profileId, JSONObject command, ApiClient api,
                                        String reason) {
        if (command != null && command.optBoolean("local_origin", false)) {
            updateNotification(robotSummary("Commande locale conservée — " + reason));
            scheduleWatchdog(this, 15_000L); return;
        }
        try {
            if (api != null) api.releaseCommand(command, "Robot non éligible avant composition : " + reason);
        } catch (Exception ignored) {
            // Le lease serveur expirera sans DIALING; il pourra alors être repris sans double débit.
        }
        PendingCommandStore.clear(this, profileId);
        releaseCommandWakeLock();
    }

    private static final class Readiness {
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

    private static boolean isTerminalState(String state) {
        return "SUCCEEDED".equals(state) || "FAILED".equals(state)
                || "UNKNOWN".equals(state) || "BLOCKED".equals(state)
                || "CANCELLED".equals(state);
    }

    private void acquireCommandWakeLock() {
        releaseCommandWakeLock();
        PowerManager manager = (PowerManager) getSystemService(POWER_SERVICE);
        if (manager != null) {
            commandWakeLock = manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,
                    "BlueMagic:ActiveUssdCommand");
            commandWakeLock.acquire(AppConfig.COMMAND_TIMEOUT_MS + 15_000L);
        }
    }


    private void releaseCommandWakeLock() {
        if (commandWakeLock != null && commandWakeLock.isHeld()) commandWakeLock.release();
        commandWakeLock = null;
    }

    private void acquireStandbyWakeLock() {
        if (!AppConfig.anyRobotEnabled(this)) return;
        long now = System.currentTimeMillis();
        if (standbyWakeLock != null && standbyWakeLock.isHeld() && now < standbyWakeRenewAt) return;
        releaseStandbyWakeLock();
        PowerManager manager = (PowerManager) getSystemService(POWER_SERVICE);
        if (manager == null) return;
        standbyWakeLock = manager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "BlueMagic:RobotStandbyCpu");
        standbyWakeLock.acquire(STANDBY_WAKE_MS);
        standbyWakeRenewAt = now + STANDBY_WAKE_MS / 2L;
    }

    private void releaseStandbyWakeLock() {
        if (standbyWakeLock != null && standbyWakeLock.isHeld()) standbyWakeLock.release();
        standbyWakeLock = null;
        standbyWakeRenewAt = 0L;
    }

    private boolean accessibilityReadyFor(JSONObject command) {
        return command == null || !UssdCommandFactory.requiresPin(command)
                || BlueAccessibilityService.isConnected();
    }

    private void holdLeaseForAccessibility(String profileId, JSONObject command, ApiClient api) {
        boolean granted = BlueAccessibilityService.isEnabled(this);
        if (command != null && command.optBoolean("local_origin", false)) {
            updateNotification(robotSummary(granted ? "Accessibilité autorisée, service Android en reconnexion — commande locale conservée" : "Accessibilité désactivée par Android/utilisateur — commande locale conservée, réactivation requise"));
            scheduleWatchdog(this, granted ? 5_000L : 30_000L); return;
        }
        String reason = granted
                ? "Accessibilité Android autorisée mais service en reconnexion; aucune composition financière avant reconnexion."
                : "Accessibilité Android désactivée; réactivation utilisateur requise avant achat/vente.";
        releaseUnexecutedLease(profileId, command, api, reason);
        apiRetryAtByProfile.put(profileId, System.currentTimeMillis() + (granted ? 5_000L : 30_000L));
        updateNotification(robotSummary(granted
                ? "Accessibilité en reconnexion — Robot conservé, reprise automatique dès retour du service"
                : "Accessibilité désactivée — Robot conservé, achat/vente en attente de réactivation"));
    }

    /**
     * Read-only Remote observer. Heartbeat keeps the server route fresh; dashboard snapshots
     * are cached locally so the foreground UI can render immediately without multiplying calls.
     * No lease_command/create_command/USSD is ever invoked here.
     */
    private long observeRemoteProfiles() {
        List<String> remotes = AppConfig.remoteProfileIds(this);
        if (remotes.isEmpty()) return Long.MAX_VALUE;
        long now = System.currentTimeMillis();
        long nextDue = now + REMOTE_SNAPSHOT_MS;
        for (String profileId : remotes) {
            long retryAt = apiRetryAtByProfile.containsKey(profileId)
                    ? apiRetryAtByProfile.get(profileId) : 0L;
            if (retryAt > now) {
                nextDue = Math.min(nextDue, retryAt);
                continue;
            }
            ApiClient api = ApiClient.forProfile(this, profileId);
            try {
                long lastHeartbeat = lastHeartbeatByProfile.containsKey(profileId)
                        ? lastHeartbeatByProfile.get(profileId) : 0L;
                if (now - lastHeartbeat >= REMOTE_HEARTBEAT_MS) {
                    api.heartbeat(false);
                    lastHeartbeatByProfile.put(profileId, now);
                }
                long lastSnapshot = lastRemoteSnapshotByProfile.containsKey(profileId)
                        ? lastRemoteSnapshotByProfile.get(profileId) : 0L;
                if (now - lastSnapshot >= REMOTE_SNAPSHOT_MS) {
                    JSONObject dashboard = api.dashboard();
                    AppConfig.prefs(this).edit()
                            .putString(REMOTE_CACHE_PREFIX + profileId, dashboard.toString())
                            .putLong(REMOTE_CACHE_AT_PREFIX + profileId, now).apply();
                    lastRemoteSnapshotByProfile.put(profileId, now);
                    updateNotification(robotSummary("Remote synchronisé — "
                            + AppConfig.nodeCode(this, profileId)));
                }
                clearProfileApiFailure(profileId);
                long hbDue = (lastHeartbeatByProfile.containsKey(profileId)
                        ? lastHeartbeatByProfile.get(profileId) : now) + REMOTE_HEARTBEAT_MS;
                long dashDue = (lastRemoteSnapshotByProfile.containsKey(profileId)
                        ? lastRemoteSnapshotByProfile.get(profileId) : now) + REMOTE_SNAPSHOT_MS;
                nextDue = Math.min(nextDue, Math.min(hbDue, dashDue));
            } catch (Exception error) {
                long failureRetryAt = Math.min(now + REMOTE_MAX_RETRY_MS, markProfileApiFailure(profileId));
                nextDue = Math.min(nextDue, failureRetryAt);
                updateNotification(robotSummary("Remote en reprise réseau — "
                        + AppConfig.nodeCode(this, profileId)));
            }
        }
        return Math.max(1_000L, nextDue - System.currentTimeMillis());
    }

    static JSONObject cachedRemoteDashboard(Context context, String profileId, long maxAgeMs) {
        if (profileId == null || profileId.isEmpty()) return null;
        long at = AppConfig.prefs(context).getLong(REMOTE_CACHE_AT_PREFIX + profileId, 0L);
        if (at <= 0L || System.currentTimeMillis() - at > Math.max(1_000L, maxAgeMs)) return null;
        String raw = AppConfig.prefs(context).getString(REMOTE_CACHE_PREFIX + profileId, "");
        if (raw.isEmpty()) return null;
        try { return new JSONObject(raw); } catch (Exception ignored) { return null; }
    }

    private boolean hasServiceWork() {
        return AppConfig.anyRobotEnabled(this) || PendingCommandStore.hasAnyPending(this)
                || AppConfig.anyRemoteProfile(this);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = getSystemService(NotificationManager.class);
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID, getString(R.string.robot_channel_name), NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("État des téléphones Robots Blue Magic");
            manager.createNotificationChannel(channel);
        }
    }

    private void enterForeground(Notification value) {
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(NOTIFICATION_ID, value,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
            } else if (Build.VERSION.SDK_INT >= 29) {
                // Android 10 à 13 reçoivent uniquement un type connu de leur framework.
                startForeground(NOTIFICATION_ID, value,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(NOTIFICATION_ID, value);
            }
        } catch (RuntimeException primaryFailure) {
            // Certains constructeurs Android 10/11 interprètent mal un manifeste compilé avec un
            // type Android 14. Le type dataSync déclaré sert de repli et empêche le service de
            // fermer tout le processus au moment où l’activité s’ouvre.
            if (Build.VERSION.SDK_INT >= 29) {
                startForeground(NOTIFICATION_ID, value,
                        ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(NOTIFICATION_ID, value);
            }
        }
    }

    private Notification notification(String text) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(this, 1, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        return (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID) : new Notification.Builder(this))
                .setContentTitle("B.I.R. — " + AppConfig.enabledRobotCount(this) + " Robot(s) • "
                        + AppConfig.remoteProfileCount(this) + " Remote(s)")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setOngoing(true)
                .setContentIntent(pending)
                .build();
    }

    private String robotSummary(String detail) {
        return AppConfig.enabledRobotCount(this) + " Robot(s) • "
                + AppConfig.remoteProfileCount(this) + " Remote(s) — " + detail;
    }

    private void updateNotification(String text) {
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (manager != null) manager.notify(NOTIFICATION_ID, notification(text));
    }

    static void start(Context context) {
        String profileId = AppConfig.profileId(context);
        sendServiceAction(context, new Intent(context, RobotService.class)
                .setAction(ACTION_START).putExtra(EXTRA_PROFILE_ID, profileId));
    }

    static void startEnabled(Context context) {
        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_WAKE));
    }

    static void forceSync(Context context) {
        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_FORCE_SYNC));
    }

    static void pollAdministrativeControls(Context context) {
        if (!AppConfig.hasProfiles(context)) return;
        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_CONTROL_POLL));
    }

    static void scheduleWatchdog(Context context, long delayMs) {
        if (!AppConfig.anyRobotEnabled(context) && !AppConfig.anyRemoteProfile(context)) return;
        AlarmManager manager = (AlarmManager) context.getSystemService(ALARM_SERVICE);
        if (manager == null) return;
        Intent intent = new Intent(context, BootReceiver.class)
                .setAction(BootReceiver.ACTION_WATCHDOG);
        PendingIntent pending = PendingIntent.getBroadcast(context, WATCHDOG_REQUEST_CODE, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        long triggerAt = SystemClock.elapsedRealtime() + Math.max(1_000L, delayMs);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            manager.setAndAllowWhileIdle(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerAt, pending);
        } else {
            manager.set(AlarmManager.ELAPSED_REALTIME_WAKEUP, triggerAt, pending);
        }
    }

    static void stop(Context context) {
        stop(context, AppConfig.profileId(context));
    }

    static void stop(Context context, String profileId) {
        sendServiceAction(context, new Intent(context, RobotService.class)
                .setAction(ACTION_STOP).putExtra(EXTRA_PROFILE_ID, profileId));
    }

    static void cancelPending(Context context, String profileId) {
        sendServiceAction(context, new Intent(context, RobotService.class)
                .setAction(ACTION_CANCEL).putExtra(EXTRA_PROFILE_ID, profileId));
    }

    static void pinSubmitted(Context context, String profileId) {
        sendServiceAction(context, new Intent(context, RobotService.class)
                .setAction(ACTION_PIN_SUBMITTED).putExtra(EXTRA_PROFILE_ID, profileId));
    }

    static void operatorResult(Context context, String profileId, boolean success, String errorCode,
                               String message, String transactionId) {
        Intent intent = new Intent(context, RobotService.class)
                .setAction(ACTION_OPERATOR_RESULT)
                .putExtra(EXTRA_PROFILE_ID, profileId)
                .putExtra(EXTRA_SUCCESS, success)
                .putExtra(EXTRA_ERROR_CODE, errorCode)
                .putExtra(EXTRA_MESSAGE, message)
                .putExtra(EXTRA_TRANSACTION_ID, transactionId);
        sendServiceAction(context, intent);
    }

    static void requestAudit(Context context, String profileId) {
        sendServiceAction(context, new Intent(context, RobotService.class)
                .setAction(ACTION_AUDIT).putExtra(EXTRA_PROFILE_ID, profileId));
    }

    private static void sendServiceAction(Context context, Intent intent) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent);
            else context.startService(intent);
        } catch (RuntimeException ignored) {
            // Android 12+ peut refuser un démarrage reçu en arrière-plan. Le prochain retour dans
            // l'app ou le watchdog relancera le même service sans faire planter l'interface.
            scheduleWatchdog(context, 5_000L);
        }
    }

    private static String profileId(Intent intent) {
        if (intent == null) return "";
        String profileId = intent.getStringExtra(EXTRA_PROFILE_ID);
        return profileId == null ? "" : profileId;
    }

    private long markProfileApiFailure(String profileId) {
        int count = apiFailureCountByProfile.containsKey(profileId)
                ? apiFailureCountByProfile.get(profileId) + 1 : 1;
        count = Math.min(4, count);
        apiFailureCountByProfile.put(profileId, count);
        long delay = Math.min(30_000L, 5_000L * (1L << (count - 1)));
        long retryAt = System.currentTimeMillis() + delay;
        apiRetryAtByProfile.put(profileId, retryAt);
        return retryAt;
    }

    private void clearProfileApiFailure(String profileId) {
        if (profileId == null || profileId.isEmpty()) return;
        apiFailureCountByProfile.remove(profileId);
        apiRetryAtByProfile.remove(profileId);
    }

    private static String safeMessage(Exception error) {
        String message = error.getMessage();
        return message == null || message.trim().isEmpty() ? error.getClass().getSimpleName() : message;
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        scheduleWatchdog(this, 2_000L);
        super.onTaskRemoved(rootIntent);
    }

    @Override
    public void onDestroy() {
        scheduleWatchdog(this, 3_000L);
        if (executor != null) executor.shutdownNow();
        releaseCommandWakeLock();
        releaseStandbyWakeLock();
        super.onDestroy();
    }
}
