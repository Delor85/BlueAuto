package com.profitloop.blueauto;

import android.app.KeyguardManager;
import android.content.Context;
import android.os.Build;
import android.os.PowerManager;

final class DeviceLockState {
    private DeviceLockState() {}

    static boolean isSecurelyLocked(Context context) {
        KeyguardManager manager = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        if (manager == null) return false;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return manager.isDeviceSecure() && manager.isDeviceLocked();
        }
        return manager.isKeyguardSecure() && manager.isKeyguardLocked();
    }

    static boolean isScreenInteractive(Context context) {
        PowerManager manager = (PowerManager) context.getSystemService(Context.POWER_SERVICE);
        return manager == null || manager.isInteractive();
    }
}
