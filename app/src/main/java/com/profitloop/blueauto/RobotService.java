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
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import org.json.JSONObject;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public class RobotService extends Service {
    static final String ACTION_START = "com.profitloop.blueauto.START_ROBOT";
    static final String ACTION_STOP = "com.profitloop.blueauto.STOP_ROBOT";
    static final String ACTION_PIN_SUBMITTED = "com.profitloop.blueauto.PIN_SUBMITTED";
    static final String ACTION_OPERATOR_RESULT = "com.profitloop.blueauto.OPERATOR_RESULT";
    static final String EXTRA_SUCCESS = "success";
    static final String EXTRA_MESSAGE = "message";
    static final String EXTRA_ERROR_CODE = "error_code";
    static final String EXTRA_TRANSACTION_ID = "transaction_id";

    private static final String CHANNEL_ID = "blue_magic_robot";
    private static final int NOTIFICATION_ID = 5502;

    private ScheduledExecutorService executor;
    private ApiClient api;
    private final AtomicBoolean cycleRunning = new AtomicBoolean(false);
    private long lastHeartbeatAt = 0L;
    private long backoffMs = AppConfig.IDLE_POLL_MS;
    private PowerManager.WakeLock commandWakeLock;

    @Override
    public void onCreate() {
        super.onCreate();
        api = new ApiClient(this);
        executor = Executors.newSingleThreadScheduledExecutor();
        createNotificationChannel();
        startForeground(NOTIFICATION_ID, notification("Robot en préparation…"));
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_STOP.equals(action)) {
            AppConfig.setRobotEnabled(this, false);
            updateNotification("Robot arrêté");
            stopSelf();
            return START_NOT_STICKY;
        }

        if (ACTION_PIN_SUBMITTED.equals(action)) {
            PendingCommandStore.updateState(this, PendingCommandStore.PIN_SUBMITTED);
            executor.execute(() -> reportProgress("PIN_SUBMITTED", "PIN local injecté et validation envoyée."));
            return START_STICKY;
        }

        if (ACTION_OPERATOR_RESULT.equals(action)) {
            boolean success = intent.getBooleanExtra(EXTRA_SUCCESS, false);
            String message = intent.getStringExtra(EXTRA_MESSAGE);
            String code = intent.getStringExtra(EXTRA_ERROR_CODE);
            String transactionId = intent.getStringExtra(EXTRA_TRANSACTION_ID);
            executor.execute(() -> finishCommand(success, code, message, transactionId));
            return START_STICKY;
        }

        AppConfig.setRobotEnabled(this, true);
        updateNotification(AppConfig.pinBlocked(this) ? "Robot bloqué : vérifier le PIN" : "Robot actif");
        scheduleCycle(0L);
        return START_STICKY;
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void scheduleCycle(long delayMs) {
        if (executor == null || executor.isShutdown() || !AppConfig.robotEnabled(this)) return;
        executor.schedule(this::runCycle, Math.max(0L, delayMs), TimeUnit.MILLISECONDS);
    }

    private void runCycle() {
        if (!cycleRunning.compareAndSet(false, true)) return;
        long nextDelay = AppConfig.IDLE_POLL_MS;
        try {
            if (!AppConfig.isPaired(this) || !AppConfig.isRobotMode(this)) {
                updateNotification("Configuration Robot incomplète");
                nextDelay = 60_000L;
                return;
            }
            if (System.currentTimeMillis() - lastHeartbeatAt >= AppConfig.HEARTBEAT_MS) {
                api.heartbeat();
                lastHeartbeatAt = System.currentTimeMillis();
            }

            JSONObject pending = PendingCommandStore.get(this);
            if (pending != null && PendingCommandStore.REPORT_PENDING.equals(
                    pending.optString("local_state", ""))) {
                retryFinalReport(pending);
                nextDelay = PendingCommandStore.get(this) == null ? 2_000L : 15_000L;
                return;
            }
            if (AppConfig.pinBlocked(this)) {
                updateNotification("ARRÊT D’URGENCE : PIN à corriger");
                nextDelay = 60_000L;
                return;
            }
            if (PendingCommandStore.isExpired(pending)) {
                finishCommand(false, "RESULT_TIMEOUT",
                        "Aucune confirmation fiable reçue dans le délai. Vérification manuelle requise.", "");
                nextDelay = 5_000L;
                return;
            }

            if (pending != null) {
                nextDelay = 3_000L;
                return;
            }

            JSONObject lease = api.leaseCommand();
            if (!lease.optBoolean("available", false)) {
                backoffMs = AppConfig.IDLE_POLL_MS;
                nextDelay = AppConfig.IDLE_POLL_MS;
                updateNotification("Robot actif — aucune commande");
                return;
            }

            JSONObject command = lease.optJSONObject("command");
            if (command == null) throw new IllegalStateException("Commande louée absente.");
            command.put("local_state", PendingCommandStore.LEASED);
            command.put("leased_at", System.currentTimeMillis());
            command.put("state_changed_at", System.currentTimeMillis());
            PendingCommandStore.save(this, command);
            executeCommand(command);
            nextDelay = 3_000L;
            backoffMs = AppConfig.IDLE_POLL_MS;
        } catch (Exception error) {
            updateNotification("Serveur indisponible — nouvelle tentative différée");
            backoffMs = Math.min(60_000L, Math.max(AppConfig.IDLE_POLL_MS, backoffMs * 2L));
            nextDelay = backoffMs;
        } finally {
            cycleRunning.set(false);
            scheduleCycle(nextDelay);
        }
    }

    private void executeCommand(JSONObject command) {
        try {
            String ussd = UssdCommandFactory.buildAndValidate(command);
            boolean requiresPin = UssdCommandFactory.requiresPin(command);
            if (requiresPin && !SecurePinStore.hasPin(this)) {
                finishCommand(false, "PIN_NOT_CONFIGURED", "Aucun PIN opérateur chiffré sur ce Robot.", "");
                return;
            }
            if (requiresPin && !BlueAccessibilityService.isEnabled(this)) {
                finishCommand(false, "ACCESSIBILITY_DISABLED", "Service d’accessibilité Blue Magic désactivé.", "");
                return;
            }
            if (checkSelfPermission(Manifest.permission.CALL_PHONE) != PackageManager.PERMISSION_GRANTED) {
                finishCommand(false, "CALL_PERMISSION_MISSING", "Autorisation Téléphone non accordée.", "");
                return;
            }

            acquireCommandWakeLock();
            PendingCommandStore.updateState(this, PendingCommandStore.DIALING);
            api.sendEvent(command, "DIALING", "Composition USSD déclenchée sur le Robot.", "");
            updateNotification("Commande en cours : " + command.optString("public_id", ""));

            String next = requiresPin ? PendingCommandStore.AWAITING_PIN : PendingCommandStore.AWAITING_RESULT;
            PendingCommandStore.updateState(this, next);
            api.sendEvent(command, next, requiresPin
                    ? "En attente de la fenêtre de confirmation PIN."
                    : "En attente du résultat opérateur.", "");

            String encoded = ussd.replace("#", Uri.encode("#"));
            Intent call = new Intent(Intent.ACTION_CALL, Uri.parse("tel:" + encoded));
            call.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            if (call.resolveActivity(getPackageManager()) == null) {
                finishCommand(false, "NO_DIALER", "Aucune application Téléphone compatible.", "");
                return;
            }
            startActivity(call);
        } catch (SecurityException securityError) {
            finishCommand(false, "COMMAND_INTEGRITY_FAILURE", securityError.getMessage(), "");
        } catch (Exception error) {
            finishCommand(false, "DIAL_FAILURE", safeMessage(error), "");
        }
    }

    private void reportProgress(String state, String message) {
        JSONObject command = PendingCommandStore.get(this);
        if (command == null) return;
        try {
            api.sendEvent(command, state, message, "");
            if ("PIN_SUBMITTED".equals(state)) {
                PendingCommandStore.updateState(this, PendingCommandStore.AWAITING_RESULT);
                api.sendEvent(command, "AWAITING_RESULT", "Validation envoyée; attente confirmation Camtel.", "");
            }
        } catch (Exception ignored) {
        }
    }

    private void finishCommand(boolean success, String errorCode, String message, String transactionId) {
        JSONObject command = PendingCommandStore.get(this);
        if (command == null) return;
        String code = errorCode == null ? "" : errorCode;
        String state;
        if (success) {
            state = "SUCCEEDED";
        } else if ("WRONG_PIN".equals(code)) {
            state = "BLOCKED";
            AppConfig.setPinBlocked(this, true);
        } else if ("RESULT_TIMEOUT".equals(code)) {
            state = "UNKNOWN";
        } else {
            state = "FAILED";
        }

        boolean reported = false;
        try {
            String detail = (message == null ? "" : message);
            if (!code.isEmpty()) detail = code + " — " + detail;
            api.sendEvent(command, state, detail, transactionId == null ? "" : transactionId);
            reported = true;
        } catch (Exception ignored) {
            try {
                command.put("local_state", PendingCommandStore.REPORT_PENDING);
                command.put("final_state", state);
                command.put("final_message", message == null ? "" : message);
                command.put("final_error_code", code);
                command.put("final_transaction_id", transactionId == null ? "" : transactionId);
                command.put("state_changed_at", System.currentTimeMillis());
                PendingCommandStore.save(this, command);
            } catch (Exception ignoredAgain) {
            }
        }
        if (reported) {
            PendingCommandStore.clear(this);
        }
        releaseCommandWakeLock();
        updateNotification(reported
                ? (success ? "Dernière commande réussie" :
                (AppConfig.pinBlocked(this) ? "ARRÊT D’URGENCE : PIN incorrect" : "Dernière commande à vérifier"))
                : "Résultat obtenu — synchronisation serveur en attente");
        scheduleCycle(reported ? 2_000L : 15_000L);
    }

    private void retryFinalReport(JSONObject command) {
        String state = command.optString("final_state", "UNKNOWN");
        String message = command.optString("final_message", "");
        String code = command.optString("final_error_code", "");
        String transactionId = command.optString("final_transaction_id", "");
        try {
            String detail = code.isEmpty() ? message : code + " — " + message;
            api.sendEvent(command, state, detail, transactionId);
            PendingCommandStore.clear(this);
            updateNotification("Résultat synchronisé — Robot prêt");
        } catch (Exception ignored) {
            updateNotification("Résultat en attente de synchronisation");
        }
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

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = getSystemService(NotificationManager.class);
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    getString(R.string.robot_channel_name),
                    NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("État du téléphone Robot Blue Magic");
            manager.createNotificationChannel(channel);
        }
    }

    private Notification notification(String text) {
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(this, 1, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);
        return builder
                .setContentTitle("Blue Magic — " + AppConfig.nodeCode(this))
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setOngoing(true)
                .setContentIntent(pending)
                .build();
    }

    private void updateNotification(String text) {
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        if (manager != null) manager.notify(NOTIFICATION_ID, notification(text));
    }

    static void start(Context context) {
        Intent intent = new Intent(context, RobotService.class).setAction(ACTION_START);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) context.startForegroundService(intent);
        else context.startService(intent);
    }

    static void stop(Context context) {
        AppConfig.setRobotEnabled(context, false);
        context.stopService(new Intent(context, RobotService.class));
    }

    static void pinSubmitted(Context context) {
        sendServiceAction(context, new Intent(context, RobotService.class).setAction(ACTION_PIN_SUBMITTED));
    }

    static void operatorResult(Context context, boolean success, String errorCode,
                               String message, String transactionId) {
        Intent intent = new Intent(context, RobotService.class)
                .setAction(ACTION_OPERATOR_RESULT)
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
