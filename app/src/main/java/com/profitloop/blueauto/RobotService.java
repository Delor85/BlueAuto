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

    private ScheduledExecutorService executor;
    private final AtomicBoolean cycleRunning = new AtomicBoolean(false);
    private final Map<String, Long> lastHeartbeatByProfile = new HashMap<>();
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

        if (ACTION_AUDIT.equals(action)) {
            final String targetProfile = profileId;
            executor.schedule(() -> queueOverlapAudit(targetProfile, true), 1_000L, TimeUnit.MILLISECONDS);
            return START_STICKY;
        }

        if (ACTION_START.equals(action) && !profileId.isEmpty()) {
            AppConfig.setRobotEnabled(this, profileId, true);
            lastHeartbeatByProfile.remove(profileId);
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
            List<JSONObject> activeCommands = PendingCommandStore.getActiveUssdCommands(this);
            // A lease captured before a SIM was removed must be returned to the server before it can
            // block the correct Robot. Once dialing may have started we fail closed as UNKNOWN.
            for (JSONObject active : activeCommands) {
                String owner = active.optString("local_profile_id", "");
                Readiness readiness = checkReadiness(owner);
                if (readiness.ready) continue;
                String state = active.optString("local_state", PendingCommandStore.LEASED);
                if (PendingCommandStore.LEASED.equals(state)) {
                    releaseUnexecutedLease(owner, active, ApiClient.forProfile(this, owner),
                            readiness.message);
                } else {
                    finishCommand(owner, false, "SIM_LOST_DURING_COMMAND",
                            readiness.message + " La transaction doit être vérifiée avant toute reprise.", "");
                }
                disableUnsafeRobot(owner, readiness.message);
            }

            activeCommands = PendingCommandStore.getActiveUssdCommands(this);
            if (activeCommands.size() > 1) {
                for (int index = 1; index < activeCommands.size(); index++) {
                    JSONObject conflict = activeCommands.get(index);
                    String conflictProfile = conflict.optString("local_profile_id", "");
                    if (PendingCommandStore.LEASED.equals(
                            conflict.optString("local_state", PendingCommandStore.LEASED))) {
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

                ApiClient api = ApiClient.forProfile(this, profileId);
                try {
                    Readiness readiness = checkReadiness(profileId);
                    if (!readiness.ready) {
                        disableUnsafeRobot(profileId, readiness.message);
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
                    if (lease.optBoolean("available", false)) {
                        JSONObject command = lease.optJSONObject("command");
                        if (command == null) throw new IllegalStateException("Commande louée absente.");
                        command.put("local_profile_id", profileId);
                        command.put("local_state", PendingCommandStore.LEASED);
                        command.put("leased_at", System.currentTimeMillis());
                        command.put("state_changed_at", System.currentTimeMillis());
                        PendingCommandStore.save(this, profileId, command);
                        roundRobinIndex = (index + 1) % count;
                        if (DeviceLockState.blocksUssd(this)) {
                            releaseLockedLease(profileId, command, api);
                            nextDelay = AppConfig.LOCKED_POLL_MS;
                            return;
                        }
                        readiness = checkReadiness(profileId);
                        if (!readiness.ready) {
                            releaseUnexecutedLease(profileId, command, api, readiness.message);
                            disableUnsafeRobot(profileId, readiness.message);
                            nextDelay = 1_000L;
                            return;
                        }
                        executeCommand(profileId, command, api);
                        nextDelay = 2_000L;
                        backoffMs = AppConfig.IDLE_POLL_MS;
                        return;
                    }

                } catch (ApiClient.ApiException apiError) {
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : " + apiError.code + " — " + safeMessage(apiError);
                } catch (Exception profileError) {
                    lastProfileProblem = AppConfig.nodeCode(this, profileId)
                            + " : réseau — " + safeMessage(profileError);
                }
            }

            boolean reportOutstanding = retryOneDueFinalReport();
            if (profiles.isEmpty()) {
                releaseStandbyWakeLock();
                if (!reportOutstanding) stopSelf();
                nextDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;
                return;
            }

            backoffMs = AppConfig.IDLE_POLL_MS;
            nextDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;
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

    private boolean retryOneDueFinalReport() {
        boolean outstanding = false;
        boolean attempted = false;
        for (String profileId : AppConfig.profileIds(this)) {
            JSONObject pending = PendingCommandStore.get(this, profileId);
            if (pending == null || !PendingCommandStore.REPORT_PENDING.equals(
                    pending.optString("local_state", ""))) continue;
            if (!attempted && PendingCommandStore.isFinalReportRetryDue(pending)) {
                retryFinalReport(profileId, pending);
                attempted = true;
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
                disableUnsafeRobot(profileId, readiness.message);
                return;
            }
            String operation = UssdCommandFactory.operation(command);
            CommandExecutionPolicy.Capability capability = CommandExecutionPolicy.capability(
                    operation,
                    SecurePinStore.hasPin(this, profileId),
                    BlueAccessibilityService.isEnabled(this),
                    AppConfig.pinBlocked(this, profileId));
            if (!capability.ready) {
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
                api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot déverrouillé.", "");
                updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");

                String next = requiresPin ? PendingCommandStore.AWAITING_PIN
                        : PendingCommandStore.AWAITING_RESULT;
                PendingCommandStore.updateState(this, profileId, next);
                api.sendEvent(command, next, requiresPin
                        ? "En attente de la fenêtre de confirmation PIN."
                        : "Commande directe avec PIN local déjà composé; attente du résultat opérateur.", "");
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
            ApiClient api = ApiClient.forProfile(this, profileId);
            api.sendEvent(command, state, message, "");
            if ("PIN_SUBMITTED".equals(state)) {
                PendingCommandStore.updateState(this, profileId, PendingCommandStore.AWAITING_RESULT);
                api.sendEvent(command, "AWAITING_RESULT",
                        "Validation envoyée; attente confirmation Camtel.", "");
            }
        } catch (Exception ignored) {
        }
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

    private void releaseLockedLease(String profileId, JSONObject command, ApiClient api) {
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
        if (!sim.valid) return Readiness.failure(sim.message);
        // La présence de la SIM est le verrou d'éligibilité. Certains dialers Android 6 à 13
        // ne publient leur PhoneAccount qu'au moment de l'appel : exiger cette route ici arrêtait
        // le Robot avant qu'il puisse louer TEST_NUMBER ou une commande financière. La route
        // exacte reste résolue et contrôlée immédiatement avant placeCall().
        return Readiness.ready(sim);
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
        try {
            api.releaseCommand(command, "Robot non éligible avant composition : " + reason);
        } catch (Exception ignored) {
            // Le lease serveur expirera sans DIALING; il pourra alors être repris sans double débit.
        }
        PendingCommandStore.clear(this, profileId);
        releaseCommandWakeLock();
    }

    private static final class Readiness {
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

    private boolean hasServiceWork() {
        return AppConfig.anyRobotEnabled(this) || PendingCommandStore.hasAnyPending(this);
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
                .setContentTitle("Blue Magic — " + AppConfig.enabledRobotCount(this) + " Robot(s) actif(s)")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setOngoing(true)
                .setContentIntent(pending)
                .build();
    }

    private String robotSummary(String detail) {
        return AppConfig.enabledRobotCount(this) + " Robot(s) — " + detail;
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

    static void scheduleWatchdog(Context context, long delayMs) {
        if (!AppConfig.anyRobotEnabled(context)) return;
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
