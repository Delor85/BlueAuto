package com.profitloop.blueauto;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.WindowManager;

/**
 * One-shot assistance for a swipe/no-credential keyguard or a screen that is simply asleep.
 *
 * This Activity is transparent and short lived. It is launched only when DeviceLockState confirms
 * that no secure credential lock is currently blocking the device. A PIN, pattern, password or
 * biometric-protected lock is never dismissed and never receives an automated credential attempt.
 */
public final class SimpleKeyguardAssistActivity extends Activity {
    private static final long MAX_VISIBLE_MS = 1_200L;

    static boolean launch(Context context) {
        if (context == null || DeviceLockState.isSecurelyLocked(context)
                || !DeviceLockState.canAssistSimpleUnlock(context)) return false;
        try {
            Intent intent = new Intent(context, SimpleKeyguardAssistActivity.class)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                            | Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
                            | Intent.FLAG_ACTIVITY_NO_ANIMATION
                            | Intent.FLAG_ACTIVITY_SINGLE_TOP);
            context.startActivity(intent);
            return true;
        } catch (RuntimeException ignored) {
            return false;
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        overridePendingTransition(0, 0);
        if (DeviceLockState.isSecurelyLocked(this)) {
            finishQuietly();
            return;
        }

        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
        }

        KeyguardManager keyguard = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
        if (keyguard != null && keyguard.isKeyguardLocked()
                && !DeviceLockState.hasSecureCredential(this)) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                keyguard.requestDismissKeyguard(this, null);
            } else {
                // Android 6/7: this window flag dismisses only a non-secure keyguard.
                getWindow().addFlags(WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD);
            }
        }

        new Handler(Looper.getMainLooper()).postDelayed(this::finishQuietly, MAX_VISIBLE_MS);
    }

    private void finishQuietly() {
        if (!isFinishing()) finish();
        overridePendingTransition(0, 0);
    }
}
