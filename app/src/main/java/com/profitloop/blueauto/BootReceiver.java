package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    static final String ACTION_WATCHDOG = "com.profitloop.blueauto.ROBOT_WATCHDOG";
    private static final long WATCHDOG_MS = 60_000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        AppConfig.migrateLegacyProfile(context);
        if (AppConfig.hasProfiles(context)) RobotService.pollAdministrativeControls(context);
        if (!AppConfig.anyRobotEnabled(context) && !AppConfig.anyRemoteProfile(context)) return;
        // Robot intent and Remote observation are persistent locally. Boot, package replacement,
        // watchdog and normal user unlock wake the same foreground control service; Android remains
        // the sole authority for Accessibility and no financial confirmation is automated here.
        RobotService.startEnabled(context);
        RobotService.scheduleWatchdog(context, WATCHDOG_MS);
    }
}
