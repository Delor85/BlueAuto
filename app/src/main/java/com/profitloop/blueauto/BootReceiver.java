package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    static final String ACTION_WATCHDOG = "com.profitloop.blueauto.ROBOT_WATCHDOG";

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!AppConfig.anyRobotEnabled(context)) return;
        RobotService.startEnabled(context);
        RobotService.scheduleWatchdog(context, 15 * 60_000L);
    }
}
