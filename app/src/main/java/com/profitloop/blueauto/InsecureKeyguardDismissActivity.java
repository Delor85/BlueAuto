package com.profitloop.blueauto;

import android.app.Activity;
import android.app.KeyguardManager;
import android.os.Build;
import android.os.Bundle;
import android.view.WindowManager;

/**
 * Transparent, content-free Activity used only because Android 8+ requires an Activity token to
 * dismiss a swipe-only keyguard. The full Blue Magic UI is never brought above the Phone app.
 */
public final class InsecureKeyguardDismissActivity extends Activity {
    private int checks;
    private final Runnable finishWhenReleased = new Runnable() {
        @Override public void run() {
            if (!DeviceLockState.isKeyguardLocked(InsecureKeyguardDismissActivity.this)
                    || DeviceLockState.isSecurelyLocked(InsecureKeyguardDismissActivity.this)
                    || checks++ >= 40) {
                finishAndRemoveTask();
                return;
            }
            getWindow().getDecorView().postDelayed(this, 100L);
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
        }
        if (DeviceLockState.isSecurelyLocked(this) || !DeviceLockState.isKeyguardLocked(this)) {
            finishAndRemoveTask();
            return;
        }
        DeviceLockState.dismissInsecureKeyguard(this);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            KeyguardManager manager = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
            if (manager != null) {
                manager.requestDismissKeyguard(this, new KeyguardManager.KeyguardDismissCallback() {
                    @Override public void onDismissSucceeded() { finishAndRemoveTask(); }
                });
            }
        }
        getWindow().getDecorView().post(finishWhenReleased);
    }
}
