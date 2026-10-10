package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    static final String ACTION_WATCHDOG = "com.profitloop.blueauto.ROBOT_WATCHDOG";
    private static final long WATCHDOG_MS = 60_000L;

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!AppConfig.anyRobotEnabled(context)) return;
        // Robot intent is persistent locally. Boot, package replacement, watchdog and a normal
        // user unlock all wake the same foreground service; none of these silently changes the
        // Android Accessibility setting.
        RobotService.startEnabled(context);
        RobotService.scheduleWatchdog(context, WATCHDOG_MS);
    }
}
