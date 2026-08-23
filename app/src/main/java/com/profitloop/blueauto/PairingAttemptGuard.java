package com.profitloop.blueauto;

import android.content.Context;

/** Five activation-code attempts per window, without forcing an Android data reset. */
final class PairingAttemptGuard {
    static final int MAX_ATTEMPTS = 5;
    static final long LOCK_MS = 15L * 60_000L;
    private static final String FAILURES = "pairing_activation_failures_v296";
    private static final String LOCKED_UNTIL = "pairing_activation_locked_until_v296";

    private PairingAttemptGuard() {}

    static synchronized long lockedForMs(Context context) {
        long until = AppConfig.prefs(context).getLong(LOCKED_UNTIL, 0L);
        long remaining = until - System.currentTimeMillis();
        if (remaining > 0L) return remaining;
        if (until > 0L) reset(context);
        return 0L;
    }

    static synchronized int remaining(Context context) {
        if (lockedForMs(context) > 0L) return 0;
        int failures = Math.max(0, AppConfig.prefs(context).getInt(FAILURES, 0));
        return Math.max(0, MAX_ATTEMPTS - failures);
    }

    static synchronized int recordDenied(Context context) {
        if (lockedForMs(context) > 0L) return 0;
        int failures = AppConfig.prefs(context).getInt(FAILURES, 0) + 1;
        if (failures >= MAX_ATTEMPTS) {
            AppConfig.prefs(context).edit()
                    .putInt(FAILURES, MAX_ATTEMPTS)
                    .putLong(LOCKED_UNTIL, System.currentTimeMillis() + LOCK_MS)
                    .commit();
            return 0;
        }
        AppConfig.prefs(context).edit().putInt(FAILURES, failures).commit();
        return MAX_ATTEMPTS - failures;
    }

    static synchronized void reset(Context context) {
        AppConfig.prefs(context).edit().remove(FAILURES).remove(LOCKED_UNTIL).commit();
    }
}
