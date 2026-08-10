package com.profitloop.blueauto;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import org.json.JSONObject;

import java.util.HashMap;
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
    static final String ACTION_PIN_SUBMITTED = "com.profitloop.blueauto.PIN_SUBMITTED";
    static final String ACTION_OPERATOR_RESULT = "com.profitloop.blueauto.OPERATOR_RESULT";
    static final String EXTRA_PROFILE_ID = "profile_id";
    static final String EXTRA_SUCCESS = "success";
    static final String EXTRA_MESSAGE = "message";
    static final String EXTRA_ERROR_CODE = "error_code";
    static final String EXTRA_TRANSACTION_ID = "transaction_id";

    private static final String CHANNEL_ID = "blue_magic_robot";
    private static final int NOTIFICATION_ID = 5502;

    private ScheduledExecutorService executor;
    private final AtomicBoolean cycleRunning = new AtomicBoolean(false);
    private final Map<String, Long> lastHeartbeatByProfile = new HashMap<>();
    private long backoffMs = AppConfig.IDLE_POLL_MS;
    private int roundRobinIndex = 0;
    private PowerManager.WakeLock commandWakeLock;
    private PowerManager.WakeLock commandScreenWakeLock;
    private long lastCommandFinishedAt = 0L;

    @Override
    public void onCreate() {
        super.onCreate();
        executor = Executors.newSingleThreadScheduledExecutor();
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, notification("Robots en préparation…"));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_WAKE : intent.getAction();
        String profileId = profileId(intent);

        if (ACTION_STOP.equals(action)) {
            if (!profileId.isEmpty()) AppConfig.setRobotEnabled(this, profileId, false);
            if (!hasServiceWork()) {
                updateNotification("Tous les Robots sont arrêtés");
                stopSelf();
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

        if (ACTION_START.equals(action) && !profileId.isEmpty()) {
            AppConfig.setRobotEnabled(this, profileId, true);
        }
        if (!hasServiceWork()) {
            stopSelf();
            return START_NOT_STICKY;
        }
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
            List<JSONObject> activeCommands = PendingCommandStore.getActiveUssdCommands(this);
            if (activeCommands.size() > 1) {
                for (int index = 1; index < activeCommands.size(); index++) {
                    JSONObject conflict = activeCommands.get(index);
                    finishCommand(conflict.optString("local_profile_id", ""), false,
                            "CONCURRENT_COMMAND_RECOVERY",
                            "Plusieurs sessions USSD locales ont été détectées. Cette opération doit être vérifiée manuellement.", "");
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

            boolean reportOutstanding = false;
            for (String profileId : AppConfig.profileIds(this)) {
                JSONObject pending = PendingCommandStore.get(this, profileId);
                if (pending != null && PendingCommandStore.REPORT_PENDING.equals(
                        pending.optString("local_state", ""))) {
                    retryFinalReport(profileId, pending);
                    if (PendingCommandStore.get(this, profileId) != null) reportOutstanding = true;
                }
            }

            if (profiles.isEmpty()) {
                if (!reportOutstanding) stopSelf();
                nextDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;
                return;
            }

            if (DeviceLockState.isSecurelyLocked(this)) {
                updateNotification(robotSummary("En pause — déverrouillez le téléphone"));
                nextDelay = AppConfig.LOCKED_POLL_MS;
                return;
            }

            long sinceLastCommand = System.currentTimeMillis() - lastCommandFinishedAt;
            if (lastCommandFinishedAt > 0L && sinceLastCommand < AppConfig.NEXT_COMMAND_GAP_MS) {
                nextDelay = AppConfig.NEXT_COMMAND_GAP_MS - sinceLastCommand;
                return;
            }

            int count = profiles.size();
            for (int offset = 0; offset < count; offset++) {
                int index = (roundRobinIndex + offset) % count;
                String profileId = profiles.get(index);
                if (!AppConfig.isPaired(this, profileId) || !AppConfig.isRobotMode(this, profileId)) continue;

                ApiClient api = ApiClient.forProfile(this, profileId);
                long lastHeartbeat = lastHeartbeatByProfile.containsKey(profileId)
                        ? lastHeartbeatByProfile.get(profileId) : 0L;
                if (System.currentTimeMillis() - lastHeartbeat >= AppConfig.HEARTBEAT_MS) {
                    api.heartbeat();
                    lastHeartbeatByProfile.put(profileId, System.currentTimeMillis());
                }

                if (AppConfig.pinBlocked(this, profileId)) continue;
                if (PendingCommandStore.get(this, profileId) != null) continue;

                JSONObject lease = api.leaseCommand();
                if (!lease.optBoolean("available", false)) continue;

                JSONObject command = lease.optJSONObject("command");
                if (command == null) throw new IllegalStateException("Commande louée absente.");
                command.put("local_profile_id", profileId);
                command.put("local_state", PendingCommandStore.LEASED);
                command.put("leased_at", System.currentTimeMillis());
                command.put("state_changed_at", System.currentTimeMillis());
                PendingCommandStore.save(this, profileId, command);
                roundRobinIndex = (index + 1) % count;
                if (DeviceLockState.isSecurelyLocked(this)) {
                    releaseLockedLease(profileId, command, api);
                    nextDelay = AppConfig.LOCKED_POLL_MS;
                    return;
                }
                executeCommand(profileId, command, api);
                nextDelay = 2_000L;
                backoffMs = AppConfig.IDLE_POLL_MS;
                return;
            }

            backoffMs = AppConfig.IDLE_POLL_MS;
            nextDelay = reportOutstanding ? 15_000L : AppConfig.IDLE_POLL_MS;
            updateNotification(robotSummary(reportOutstanding
                    ? "Une synchronisation reste à reprendre; les autres files continuent"
                    : "Aucune commande en attente"));
        } catch (Exception error) {
            updateNotification(robotSummary("Serveur indisponible — nouvelle tentative"));
            backoffMs = Math.min(60_000L, Math.max(AppConfig.IDLE_POLL_MS, backoffMs * 2L));
            nextDelay = backoffMs;
        } finally {
            cycleRunning.set(false);
            scheduleCycle(nextDelay);
        }
    }

    private void executeCommand(String profileId, JSONObject command, ApiClient api) {
        try {
            String ussd = UssdCommandFactory.buildAndValidate(command);
            boolean requiresPin = UssdCommandFactory.requiresPin(command);
            if (requiresPin && !SecurePinStore.hasPin(this, profileId)) {
                finishCommand(profileId, false, "PIN_NOT_CONFIGURED",
                        "Aucun PIN opérateur chiffré sur ce Robot.", "");
                return;
            }
            if (requiresPin && !BlueAccessibilityService.isEnabled(this)) {
                finishCommand(profileId, false, "ACCESSIBILITY_DISABLED",
                        "Service d’accessibilité Blue Magic désactivé.", "");
                return;
            }
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
            if (DeviceLockState.isSecurelyLocked(this)) {
                releaseLockedLease(profileId, command, api);
                return;
            }

            acquireCommandWakeLock();
            PendingCommandStore.updateState(this, profileId, PendingCommandStore.DIALING);
            api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot.", "");
            updateNotification("Commande " + AppConfig.nodeCode(this, profileId) + " en cours");

            String next = requiresPin ? PendingCommandStore.AWAITING_PIN : PendingCommandStore.AWAITING_RESULT;
            PendingCommandStore.updateState(this, profileId, next);
            api.sendEvent(command, next, requiresPin
                    ? "En attente de la fenêtre de confirmation PIN."
                    : "En attente du résultat opérateur.", "");

            try {
                SimCallManager.placeUssdCall(this, ussd, AppConfig.simSlot(this, profileId));
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
        } else if ("WRONG_PIN".equals(code)) {
            state = "BLOCKED";
            AppConfig.setPinBlocked(this, profileId, true);
        } else if ("RESULT_TIMEOUT".equals(code)
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

    private void releaseLockedLease(String profileId, JSONObject command, ApiClient api) {
        try {
            api.releaseCommand(command,
                    "Téléphone verrouillé par un mot de passe ou schéma; exécution différée.");
        } catch (Exception ignored) {
            // Un ancien serveur relâchera lui-même le lease à son expiration.
        }
        PendingCommandStore.clear(this, profileId);
        releaseCommandWakeLock();
        updateNotification(robotSummary("Commande différée — déverrouillez le téléphone"));
    }

    private static boolean isTerminalState(String state) {
        return "SUCCEEDED".equals(state) || "FAILED".equals(state)
                || "UNKNOWN".equals(state) || "BLOCKED".equals(state);
    }

    private void acquireCommandWakeLock() {
        releaseCommandWakeLock();
        PowerManager manager = (PowerManager) getSystemService(POWER_SERVICE);
        if (manager != null) {
            commandWakeLock = manager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,
                    "BlueMagic:ActiveUssdCommand");
            commandWakeLock.acquire(AppConfig.COMMAND_TIMEOUT_MS + 15_000L);
            if (!DeviceLockState.isSecurelyLocked(this)) {
                commandScreenWakeLock = manager.newWakeLock(
                        PowerManager.SCREEN_BRIGHT_WAKE_LOCK
                                | PowerManager.ACQUIRE_CAUSES_WAKEUP
                                | PowerManager.ON_AFTER_RELEASE,
                        "BlueMagic:VisibleUssdPrompt");
                commandScreenWakeLock.acquire(AppConfig.COMMAND_TIMEOUT_MS + 15_000L);
            }
        }
    }

    private void releaseCommandWakeLock() {
        if (commandWakeLock != null && commandWakeLock.isHeld()) commandWakeLock.release();
        commandWakeLock = null;
        if (commandScreenWakeLock != null && commandScreenWakeLock.isHeld()) {
            commandScreenWakeLock.release();
        }
        commandScreenWakeLock = null;
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

    static void stop(Context context) {
        String profileId = AppConfig.profileId(context);
        sendServiceAction(context, new Intent(context, RobotService.class)
                .setAction(ACTION_STOP).putExtra(EXTRA_PROFILE_ID, profileId));
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

    private static void sendServiceAction(Context context, Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent);
        else context.startService(intent);
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
    public void onDestroy() {
        if (executor != null) executor.shutdownNow();
        releaseCommandWakeLock();
        super.onDestroy();
    }
}
