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
                    if (sim.valid) continue;
                    AppConfig.setRobotEnabled(app, profileId, false);
                    try {
                        ApiClient.forProfile(app, profileId).heartbeat();
                    } catch (Exception ignored) {
                    }
                }
                if (AppConfig.anyRobotEnabled(app)) RobotService.startEnabled(app);
            } finally {
                pending.finish();
            }
        }, "BlueMagic-SimGuard").start();
    }
}
