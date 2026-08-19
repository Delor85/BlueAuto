package com.profitloop.blueauto;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Durable device-local cache for the newest trusted Blue balance evidence.
 *
 * Only evidence parsed from a trusted telephony accessibility root is accepted.
 * No PIN, raw USSD payload or pairing secret is ever stored here.
 */
final class CertifiedBalanceStore {
    private static final String PREFS = "bir_certified_balance_v293";

    private CertifiedBalanceStore() {}

    static void observeTrusted(Context context, String profileId, BlueMessageParser.Result parsed) {
        if (context == null || profileId == null || profileId.isEmpty() || parsed == null) return;
        if (parsed.currentBalanceFcfa == null || !parsed.terminalSuccess()) return;
        long capturedAt = System.currentTimeMillis();
        long operatorAt = operatorMillis(parsed.date, parsed.time);
        long chronology = operatorAt > 0L ? operatorAt : capturedAt;
        try {
            JSONObject next = new JSONObject();
            next.put("balance", parsed.currentBalanceFcfa.longValue());
            next.put("transaction_id", parsed.transactionId == null ? "" : parsed.transactionId);
            next.put("receipt_number", parsed.receiptNumber == null ? "" : parsed.receiptNumber);
            next.put("kind", parsed.kind == null ? "BLUE_PROOF" : parsed.kind);
            next.put("source", "TRUSTED_TELEPHONY");
            next.put("operator_event_at_ms", operatorAt);
            next.put("captured_at_ms", capturedAt);
            next.put("chronology_ms", chronology);
            next.put("operator_event_at", iso(operatorAt > 0L ? operatorAt : capturedAt));
            next.put("observed_at", iso(capturedAt));

            JSONObject old = get(context, profileId);
            long oldChronology = old == null ? 0L : old.optLong("chronology_ms", 0L);
            long oldCaptured = old == null ? 0L : old.optLong("captured_at_ms", 0L);
            if (old != null && chronology < oldChronology) return;
            if (old != null && chronology == oldChronology && capturedAt <= oldCaptured) return;

            prefs(context).edit().putString(key(profileId), next.toString()).commit();
        } catch (Exception ignored) {
        }
    }

    static JSONObject get(Context context, String profileId) {
        if (context == null || profileId == null || profileId.isEmpty()) return null;
        String raw = prefs(context).getString(key(profileId), "");
        if (raw == null || raw.isEmpty()) return null;
        try {
            return new JSONObject(raw);
        } catch (Exception ignored) {
            return null;
        }
    }

    static String json(Context context, String profileId) {
        JSONObject value = get(context, profileId);
        return value == null ? "{}" : value.toString();
    }

    private static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static String key(String profileId) {
        return "proof_" + profileId;
    }

    private static long operatorMillis(String date, String time) {
        if (date == null || time == null || date.trim().isEmpty() || time.trim().isEmpty()) return 0L;
        String value = date.trim() + " " + time.trim();
        String[] patterns = {"dd-MM-yy HH:mm:ss", "dd/MM/yy HH:mm:ss", "dd-MM-yyyy HH:mm:ss",
                "dd/MM/yyyy HH:mm:ss", "dd-MM-yy HH:mm", "dd/MM/yy HH:mm"};
        for (String pattern : patterns) {
            SimpleDateFormat parser = new SimpleDateFormat(pattern, Locale.ROOT);
            parser.setLenient(false);
            parser.setTimeZone(TimeZone.getTimeZone("GMT+01:00"));
            try {
                Date parsed = parser.parse(value);
                if (parsed != null) return parsed.getTime();
            } catch (ParseException ignored) {
            }
        }
        return 0L;
    }

    private static String iso(long millis) {
        SimpleDateFormat format = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.ROOT);
        format.setTimeZone(TimeZone.getTimeZone("UTC"));
        return format.format(new Date(millis));
    }
}
