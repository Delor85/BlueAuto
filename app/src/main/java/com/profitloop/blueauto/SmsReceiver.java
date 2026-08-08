package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;

import org.json.JSONObject;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SmsReceiver extends BroadcastReceiver {
    private static final Pattern TX_ID = Pattern.compile("(?i)(?:transaction\\s*id|transactionid)(?:\\s+is)?\\s*[:#-]?\\s*(\\d{6,})");

    @Override
    public void onReceive(Context context, Intent intent) {
        if (!"android.provider.Telephony.SMS_RECEIVED".equals(intent.getAction())) return;
        JSONObject command = PendingCommandStore.get(context);
        if (command == null) return;

        Bundle extras = intent.getExtras();
        if (extras == null) return;
        Object[] pdus = (Object[]) extras.get("pdus");
        String format = extras.getString("format");
        if (pdus == null) return;

        StringBuilder body = new StringBuilder();
        for (Object pdu : pdus) {
            SmsMessage sms = SmsMessage.createFromPdu((byte[]) pdu, format);
            if (sms != null && sms.getMessageBody() != null) body.append(sms.getMessageBody());
        }
        evaluate(context, command, body.toString());
    }

    private void evaluate(Context context, JSONObject command, String message) {
        String lower = message.toLowerCase(Locale.ROOT);
        if (containsAny(lower, "wrong pin code", "pin incorrect", "code pin incorrect", "code erroné")) {
            AppConfig.setPinBlocked(context, true);
            RobotService.operatorResult(context, false, "WRONG_PIN", redact(context, message), transactionId(message));
            return;
        }

        String expectedPhone = command.optString("target_phone", "").replaceAll("\\D", "");
        String expectedAmount = command.optString("amount", "").replaceFirst("\\.0+$", "").replaceAll("\\D", "");
        String compact = lower.replaceAll("[\\s,._-]", "");
        boolean correlated = (!expectedPhone.isEmpty() && compact.contains(expectedPhone))
                || !transactionId(message).isEmpty();
        if (!correlated) return;
        if (!expectedAmount.isEmpty() && !containsAmount(lower, expectedAmount)) return;

        if (containsAny(lower, "successfully", "processed successfully", "received", "you transfer")) {
            RobotService.operatorResult(context, true, "", redact(context, message), transactionId(message));
        } else if (containsAny(lower, "failed", "insufficient", "not enough", "frozen", "suspended", "invalid")) {
            RobotService.operatorResult(context, false, "OPERATOR_REJECTED", redact(context, message), transactionId(message));
        }
    }

    private static String redact(Context context, String value) {
        try {
            String pin = SecurePinStore.read(context);
            if (!pin.isEmpty()) value = value.replace(pin, "****");
        } catch (Exception ignored) {
        }
        return value.length() <= 1800 ? value : value.substring(0, 1800);
    }

    private static String transactionId(String text) {
        Matcher matcher = TX_ID.matcher(text);
        return matcher.find() ? matcher.group(1) : "";
    }

    private static boolean containsAmount(String message, String expectedAmount) {
        String normalized = message.replace(",", "");
        Pattern pattern = Pattern.compile("(?i)(?<!\\d)" + Pattern.quote(expectedAmount)
                + "(?:\\.00)?\\s*FCFA(?!\\w)");
        return pattern.matcher(normalized).find();
    }

    private static boolean containsAny(String value, String... needles) {
        for (String needle : needles) if (value.contains(needle)) return true;
        return false;
    }
}
