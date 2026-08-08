package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (AppConfig.anyRobotEnabled(context)) RobotService.startEnabled(context);
    }
}
