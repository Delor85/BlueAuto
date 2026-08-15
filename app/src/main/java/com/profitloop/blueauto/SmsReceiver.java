package com.profitloop.blueauto;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.telephony.SmsMessage;
import android.telephony.SubscriptionManager;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class SmsReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (!"android.provider.Telephony.SMS_RECEIVED".equals(intent.getAction())) return;
        Bundle extras = intent.getExtras();
        if (extras == null) return;
        Object[] pdus = (Object[]) extras.get("pdus");
        if (pdus == null || pdus.length == 0) return;
        String format = extras.getString("format");
        StringBuilder body = new StringBuilder();
        for (Object pdu : pdus) {
            SmsMessage sms = android.os.Build.VERSION.SDK_INT >= 23
                    ? SmsMessage.createFromPdu((byte[]) pdu, format)
                    : SmsMessage.createFromPdu((byte[]) pdu);
            if (sms != null && sms.getMessageBody() != null) body.append(sms.getMessageBody());
        }
        String message = body.toString().trim();
        if (message.isEmpty()) return;
        BlueMessageParser.Result parsed = BlueMessageParser.parse(message);
        String profileId = profileForSms(context, intent);
        if (profileId.isEmpty()) return;

        JSONObject active = PendingCommandStore.get(context, profileId);
        if (active != null) {
            String expectedPhone = active.optString("target_phone", "").replaceAll("\\D", "");
            long expectedAmount = active.optLong("amount", 0L);
            boolean correlated = expectedPhone.isEmpty() || parsed.primaryPhone.endsWith(expectedPhone)
                    || message.replaceAll("\\D", "").contains(expectedPhone);
            if (expectedAmount > 0L && parsed.amountFcfa != null && parsed.amountFcfa != expectedAmount) correlated = false;
            if (parsed.wrongPin) {
                AppConfig.setPinBlocked(context, profileId, true);
                RobotService.operatorResult(context, profileId, false, "WRONG_PIN",
                        BlueMessageParser.redactSensitive(message, safePin(context, profileId)), parsed.transactionId);
                return;
            }
            if (correlated && parsed.terminalSuccess()) {
                if ("MODIFY_PIN_LOCAL".equals(UssdCommandFactory.operation(active))) {
                    try { PendingPinChangeStore.commit(context, profileId); } catch (Exception ignored) {}
                }
                RobotService.operatorResult(context, profileId, true, "",
                        BlueMessageParser.redactSensitive(message, safePin(context, profileId)), parsed.transactionId);
                return;
            }
            if (correlated && parsed.terminalFailure()) {
                RobotService.operatorResult(context, profileId, false, "OPERATOR_REJECTED",
                        BlueMessageParser.redactSensitive(message, safePin(context, profileId)), parsed.transactionId);
                return;
            }
        }

        // Passive messages remain valuable even when no Blue Magic command is pending: bank
        // injections, manual USSD, Tchoronko transfers and PIN-reset messages update the model.
        if (parsed.provisionalPin.matches("\\d{4}")) {
            try {
                SecurePinStore.save(context, profileId, parsed.provisionalPin);
                AppConfig.setPinBlocked(context, profileId, false);
            } catch (Exception ignored) {}
        }
        final PendingResult pendingResult = goAsync();
        final String redacted = BlueMessageParser.redactSensitive(message, safePin(context, profileId));
        new Thread(() -> {
            try {
                ApiClient.forProfile(context, profileId).recordOperatorMessage(redacted);
                if (parsed.kind.equals("TRANSFER_RECEIVED") || parsed.kind.equals("MINI_STATEMENT")) {
                    RobotService.requestAudit(context, profileId);
                }
            } catch (Exception ignored) {
            } finally {
                pendingResult.finish();
            }
        }).start();
    }

    private static String profileForSms(Context context, Intent intent) {
        int subscriptionId = intent.getIntExtra(SubscriptionManager.EXTRA_SUBSCRIPTION_INDEX, -1);
        if (subscriptionId < 0) subscriptionId = intent.getIntExtra("subscription", -1);
        int slot = -1;
        if (subscriptionId >= 0) {
            try {
                SubscriptionManager manager = (SubscriptionManager) context.getSystemService(Context.TELEPHONY_SUBSCRIPTION_SERVICE);
                if (manager != null && manager.getActiveSubscriptionInfo(subscriptionId) != null) {
                    slot = manager.getActiveSubscriptionInfo(subscriptionId).getSimSlotIndex();
                }
            } catch (Exception ignored) {}
        }
        List<String> candidates = new ArrayList<>();
        for (String id : AppConfig.profileIds(context)) {
            if (!AppConfig.isRobotMode(context, id)) continue;
            if (slot < 0 || AppConfig.simSlot(context, id) == slot) candidates.add(id);
        }
        if (candidates.size() == 1) return candidates.get(0);
        if (slot < 0 && AppConfig.profileIds(context).length == 1) return AppConfig.profileIds(context)[0];
        return "";
    }

    private static String safePin(Context context, String profileId) {
        try { return SecurePinStore.read(context, profileId); } catch (Exception ignored) { return ""; }
    }
}
