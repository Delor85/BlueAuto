package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Immediately revokes Robot eligibility when Android reports a SIM change. */
public class SimStateReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        final BroadcastReceiver.PendingResult pending = goAsync();
        final Context app = context.getApplicationContext();
        new Thread(() -> {
            try {
                for (String profileId : AppConfig.enabledRobotProfileIds(app)) {
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
                }
            } finally {
                pending.finish();
            }
        }, "BlueMagic-SimGuard").start();
    }
}
