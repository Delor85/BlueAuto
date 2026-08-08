package com.profitloop.blueauto;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.telecom.PhoneAccount;
import android.telecom.PhoneAccountHandle;
import android.telecom.TelecomManager;
import android.telephony.SubscriptionInfo;
import android.telephony.SubscriptionManager;
import android.telephony.TelephonyManager;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

final class SimCallManager {
    private SimCallManager() {}

    static int slotCount(Context context) {
        try {
            TelephonyManager manager = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
            if (manager == null) return 1;
            int count = Build.VERSION.SDK_INT >= 30
                    ? manager.getActiveModemCount()
                    : manager.getPhoneCount();
            return Math.max(1, Math.min(4, count));
        } catch (Exception ignored) {
            return 1;
        }
    }

    static String[] slotLabels(Context context) {
        int count = slotCount(context);
        String[] labels = new String[count];
        for (int i = 0; i < count; i++) labels[i] = "SIM " + (i + 1) + " (slot " + (i + 1) + ")";
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            return labels;
        }
        try {
            SubscriptionManager subscriptions = (SubscriptionManager) context.getSystemService(
                    Context.TELEPHONY_SUBSCRIPTION_SERVICE);
            if (subscriptions == null) return labels;
            for (int slot = 0; slot < count; slot++) {
                SubscriptionInfo info = subscriptions.getActiveSubscriptionInfoForSimSlotIndex(slot);
                if (info == null) continue;
                CharSequence name = info.getDisplayName();
                if (name == null || name.toString().trim().isEmpty()) name = info.getCarrierName();
                if (name != null && !name.toString().trim().isEmpty()) {
                    labels[slot] += " — " + name.toString().trim();
                }
            }
        } catch (Exception ignored) {
        }
        return labels;
    }

    static void placeUssdCall(Context context, String ussd, int requestedSlot) throws Exception {
        int count = slotCount(context);
        if (requestedSlot < 0 || requestedSlot >= count) {
            throw new IllegalStateException("Le slot SIM " + (requestedSlot + 1) + " n’existe pas sur ce téléphone.");
        }
        Uri address = Uri.parse("tel:" + ussd.replace("#", Uri.encode("#")));

        if (count == 1 && context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            startLegacyCall(context, address, null);
            return;
        }
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            throw new SecurityException("Autorisation État du téléphone requise pour sélectionner la SIM.");
        }

        TelecomManager telecom = (TelecomManager) context.getSystemService(Context.TELECOM_SERVICE);
        SubscriptionManager subscriptions = (SubscriptionManager) context.getSystemService(
                Context.TELEPHONY_SUBSCRIPTION_SERVICE);
        TelephonyManager telephony = (TelephonyManager) context.getSystemService(Context.TELEPHONY_SERVICE);
        if (telecom == null || subscriptions == null || telephony == null) {
            throw new IllegalStateException("Services Téléphone Android indisponibles.");
        }

        SubscriptionInfo target = subscriptions.getActiveSubscriptionInfoForSimSlotIndex(requestedSlot);
        if (target == null) {
            throw new IllegalStateException("Aucune SIM active dans le slot " + (requestedSlot + 1) + ".");
        }
        PhoneAccountHandle account = resolvePhoneAccount(
                context, telecom, telephony, subscriptions, target, AppConfig.phoneNumber(context));
        if (account == null) {
            throw new IllegalStateException("Android ne permet pas d’associer le slot "
                    + (requestedSlot + 1) + " à un compte d’appel actif.");
        }

        Bundle extras = new Bundle();
        extras.putParcelable(TelecomManager.EXTRA_PHONE_ACCOUNT_HANDLE, account);
        telecom.placeCall(address, extras);
    }

    private static PhoneAccountHandle resolvePhoneAccount(
            Context context, TelecomManager telecom, TelephonyManager telephony,
            SubscriptionManager subscriptions, SubscriptionInfo target, String configuredPhone) {
        List<PhoneAccountHandle> all = telecom.getCallCapablePhoneAccounts();
        List<PhoneAccountHandle> cellular = new ArrayList<>();
        for (PhoneAccountHandle handle : all) {
            PhoneAccount account = telecom.getPhoneAccount(handle);
            if (account == null || account.supportsUriScheme(PhoneAccount.SCHEME_TEL)) cellular.add(handle);
        }
        if (cellular.isEmpty()) return null;

        int targetSubscription = target.getSubscriptionId();
        if (Build.VERSION.SDK_INT >= 30) {
            for (PhoneAccountHandle handle : cellular) {
                try {
                    if (telephony.getSubscriptionId(handle) == targetSubscription) return handle;
                } catch (Exception ignored) {
                }
            }
        }

        String expectedPhone = digits(configuredPhone);
        if (expectedPhone.length() >= 9) {
            for (PhoneAccountHandle handle : cellular) {
                try {
                    String line = digits(telecom.getLine1Number(handle));
                    if (line.endsWith(expectedPhone.substring(expectedPhone.length() - 9))) return handle;
                } catch (Exception ignored) {
                }
            }
        }

        String subscriptionToken = String.valueOf(targetSubscription);
        for (PhoneAccountHandle handle : cellular) {
            String id = handle.getId() == null ? "" : handle.getId().toLowerCase(Locale.ROOT);
            if (id.matches(".*(?:^|\\D)" + subscriptionToken + "(?:\\D|$).*$")) return handle;
        }

        try {
            List<SubscriptionInfo> active = subscriptions.getActiveSubscriptionInfoList();
            if (active != null) {
                for (int i = 0; i < active.size(); i++) {
                    if (active.get(i).getSubscriptionId() == targetSubscription && i < cellular.size()) {
                        return cellular.get(i);
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return cellular.size() == 1 ? cellular.get(0) : null;
    }

    private static void startLegacyCall(Context context, Uri address, PhoneAccountHandle account) {
        Intent call = new Intent(Intent.ACTION_CALL, address);
        call.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        if (account != null) call.putExtra(TelecomManager.EXTRA_PHONE_ACCOUNT_HANDLE, account);
        if (call.resolveActivity(context.getPackageManager()) == null) {
            throw new IllegalStateException("Aucune application Téléphone compatible.");
        }
        context.startActivity(call);
    }

    private static String digits(String value) {
        return value == null ? "" : value.replaceAll("\\D", "");
    }
}
