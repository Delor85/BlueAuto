package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (AppConfig.isPaired(context)
                && AppConfig.isRobotMode(context)
                && AppConfig.robotEnabled(context)
                && !AppConfig.pinBlocked(context)) {
            RobotService.start(context);
        }
    }
}
