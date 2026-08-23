package com.profitloop.blueauto;

import android.app.Application;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;

/**
 * Lightweight field-safety observer for Remote terminals and local Robot health.
 *
 * It never creates a financial command. RobotService maintains the authenticated Remote dashboard
 * cache; this observer checks that state every 10 seconds for urgent Remote alerts. On a Robot it
 * only detects an Accessibility state transition and wakes the existing sync engine so the Remote
 * receives that state promptly instead of waiting for a normal heartbeat.
 */
public final class BirApplication extends Application {
    private static final String CHANNEL = "bir_remote_urgent_v297";
    private static final int NOTIFICATION_ID = 5597;
    private static final long CHECK_MS = 10_000L;
    private static final long ROBOT_SILENCE_ALERT_SECONDS = 60L;
    private static final long CACHE_MAX_AGE_MS = 90_000L;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private Boolean lastAccessibilityEnabled;
    private Boolean lastAccessibilityConnected;
    private final Runnable observer = new Runnable() {
        @Override public void run() {
            try {
                publishLocalAccessibilityTransition();
                inspectRemoteHealth();
            } catch (Exception ignored) {}
            handler.postDelayed(this, CHECK_MS);
        }
    };

    @Override public void onCreate() {
        super.onCreate();
        createUrgencyChannel();
        handler.postDelayed(observer, 1_500L);
    }

    private void publishLocalAccessibilityTransition() {
        if (!AppConfig.anyRobotEnabled(this)) {
            lastAccessibilityEnabled = null;
            lastAccessibilityConnected = null;
            return;
        }
        boolean enabled = BlueAccessibilityService.isEnabled(this);
        boolean connected = BlueAccessibilityService.isConnected();
        if (lastAccessibilityEnabled == null || lastAccessibilityConnected == null) {
            lastAccessibilityEnabled = enabled;
            lastAccessibilityConnected = connected;
            return;
        }
        if (lastAccessibilityEnabled != enabled || lastAccessibilityConnected != connected) {
            lastAccessibilityEnabled = enabled;
            lastAccessibilityConnected = connected;
            // Safe control-plane wake only: clears heartbeat backoff and publishes fresh telemetry.
            // No command is created and no USSD is dialled by this observer.
            RobotService.forceSync(this);
        }
    }

    private void inspectRemoteHealth() {
        String[] remotes = AppConfig.remoteProfileIds(this).toArray(new String[0]);
        String urgentTitle = "";
        String urgentText = "";
        for (String profileId : remotes) {
            JSONObject dashboard = RobotService.cachedRemoteDashboard(this, profileId, CACHE_MAX_AGE_MS);
            if (dashboard == null) continue;
            JSONObject row = ownNode(dashboard, AppConfig.nodeCode(this, profileId));
            if (row == null) continue;
            String node = row.optString("official_node_code", row.optString("node_code",
                    AppConfig.nodeCode(this, profileId)));
            boolean robotExpected = row.optBoolean("robot_enabled", false)
                    || "ONLINE".equalsIgnoreCase(row.optString("robot_status", ""))
                    || "STALE".equalsIgnoreCase(row.optString("robot_status", ""));
            if (!robotExpected) continue;

            // Accessibility is a direct operational fault and remains immediately actionable.
            if (row.has("accessibility_enabled") && !row.optBoolean("accessibility_enabled", true)) {
                urgentTitle = "URGENT — Accessibilité " + node;
                urgentText = "Le Robot a perdu l’Accessibilité. Achats/ventes doivent rester en file. Ouvrez B.I.R. et intervenez sur le téléphone Robot.";
                break;
            }
            if (row.has("accessibility_connected") && !row.optBoolean("accessibility_connected", true)) {
                urgentTitle = "URGENT — Robot " + node;
                urgentText = "Accessibilité autorisée mais service Android déconnecté. Ne recréez pas la transaction; B.I.R. attend la reconnexion.";
                break;
            }

            double age = row.optDouble("robot_age_seconds", -1d);
            String status = row.optString("robot_status", "").toUpperCase(Locale.ROOT);
            boolean serverStale = row.optBoolean("robot_stale", false)
                    || "OFFLINE".equals(status) || "STALE".equals(status);
            boolean silentForSixtySeconds = age >= ROBOT_SILENCE_ALERT_SECONDS;
            // Prefer the measured age. If an older server does not expose age_seconds, keep its
            // explicit STALE/OFFLINE verdict as a compatibility fallback instead of hiding danger.
            if (silentForSixtySeconds || (age < 0d && serverStale)) {
                urgentTitle = "URGENT — Robot " + node + " injoignable";
                urgentText = silentForSixtySeconds
                        ? "Aucun signal fiable depuis " + Math.round(age) + " s. Ne recréez pas une opération déjà en file."
                        : "La télémétrie du Robot est déclarée en retard par le serveur. Ne recréez pas une opération déjà en file.";
                break;
            }
        }
        if (urgentTitle.isEmpty()) clearUrgency();
        else publishUrgency(urgentTitle, urgentText);
    }

    private static JSONObject ownNode(JSONObject dashboard, String nodeCode) {
        JSONArray nodes = dashboard.optJSONArray("nodes");
        if (nodes == null) return null;
        for (int i = 0; i < nodes.length(); i++) {
            JSONObject row = nodes.optJSONObject(i);
            if (row != null && nodeCode.equalsIgnoreCase(row.optString("node_code", ""))) return row;
        }
        return null;
    }

    private void createUrgencyChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager == null) return;
        NotificationChannel channel = new NotificationChannel(CHANNEL,
                "Alertes urgentes B.I.R.", NotificationManager.IMPORTANCE_HIGH);
        channel.setDescription("Robot injoignable, Accessibilité perdue et incidents terrain prioritaires");
        channel.enableVibration(true);
        manager.createNotificationChannel(channel);
    }

    private void publishUrgency(String title, String text) {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return;
        Intent open = new Intent(this, MainActivity.class);
        PendingIntent pending = PendingIntent.getActivity(this, 97, open,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL) : new Notification.Builder(this);
        Notification notification = builder.setContentTitle(title)
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setSmallIcon(android.R.drawable.stat_notify_error)
                .setAutoCancel(false)
                .setOnlyAlertOnce(true)
                .setContentIntent(pending)
                .build();
        manager.notify(NOTIFICATION_ID, notification);
    }

    private void clearUrgency() {
        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.cancel(NOTIFICATION_ID);
    }
}
