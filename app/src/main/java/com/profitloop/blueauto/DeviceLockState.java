package com.profitloop.blueauto;

import android.app.KeyguardManager;
import android.content.Context;
import android.os.Build;
import android.os.PowerManager;

/**
 * Read-only view of Android lock state.
 *
 * Blue Magic must never disable, dismiss or fight the keyguard. A locked screen is a routing
 * condition: the Robot keeps running, but an USSD lease is returned to the queue until the user
 * has unlocked the phone normally. This avoids the screen shaking observed on older Androids.
 */
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

    static boolean isKeyguardLocked(Context context) {
        KeyguardManager manager = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        return manager != null && manager.isKeyguardLocked();
    }

    static boolean isInsecurelyLocked(Context context) {
        KeyguardManager manager = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        if (manager == null || !manager.isKeyguardLocked()) return false;
        boolean secure = Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                ? manager.isDeviceSecure() : manager.isKeyguardSecure();
        return !secure;
    }

    static boolean hasSecureCredential(Context context) {
        KeyguardManager manager = (KeyguardManager) context.getSystemService(Context.KEYGUARD_SERVICE);
        if (manager == null) return false;
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                ? manager.isDeviceSecure() : manager.isKeyguardSecure();
    }

    static boolean canAssistSimpleUnlock(Context context) {
        if (isSecurelyLocked(context)) return false;
        return isInsecurelyLocked(context) || !isScreenInteractive(context);
    }

    static boolean blocksUssd(Context context) {
        return isKeyguardLocked(context) || !isScreenInteractive(context);
    }
}
