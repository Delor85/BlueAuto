package com.profitloop.blueauto;

import android.app.KeyguardManager;
import android.content.Context;
import android.os.Build;
import android.os.PowerManager;

final class DeviceLockState {
    @SuppressWarnings("deprecation")
    private static KeyguardManager.KeyguardLock insecureKeyguardLock;

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

    /**
     * Temporarily removes only a swipe/no-credential keyguard so the Android Phone service can
     * expose its USSD prompt to accessibility. A password, PIN, pattern or biometric keyguard is
     * never bypassed.
     */
    @SuppressWarnings("deprecation")
    static synchronized boolean dismissInsecureKeyguard(Context context) {
        if (!isInsecurelyLocked(context)) return false;
        try {
            KeyguardManager manager = (KeyguardManager) context.getSystemService(
                    Context.KEYGUARD_SERVICE);
            if (manager == null) return false;
            if (insecureKeyguardLock == null) {
                insecureKeyguardLock = manager.newKeyguardLock("BlueMagic:InsecureUssdPrompt");
            }
            insecureKeyguardLock.disableKeyguard();
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    @SuppressWarnings("deprecation")
    static synchronized void restoreInsecureKeyguard() {
        if (insecureKeyguardLock == null) return;
        try {
            insecureKeyguardLock.reenableKeyguard();
        } catch (Exception ignored) {
        }
        insecureKeyguardLock = null;
    }
}
