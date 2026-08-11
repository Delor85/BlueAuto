package com.profitloop.blueauto;

import android.Manifest;
import android.content.Context;
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
                    ? manager.getSupportedModemCount()
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

    static void verifyCallRoute(Context context, String profileId) {
        resolveRoute(context, profileId);
    }

    static void placeUssdCall(Context context, String ussd, String profileId) throws Exception {
        Route route = resolveRoute(context, profileId);
        Uri address = Uri.parse("tel:" + ussd.replace("#", Uri.encode("#")));
        Bundle extras = new Bundle();
        extras.putParcelable(TelecomManager.EXTRA_PHONE_ACCOUNT_HANDLE, route.account);
        route.telecom.placeCall(address, extras);
    }

    private static Route resolveRoute(Context context, String profileId) {
        int requestedSlot = AppConfig.simSlot(context, profileId);
        int count = slotCount(context);
        if (requestedSlot < 0 || requestedSlot >= count) {
            throw new IllegalStateException("Le slot SIM " + (requestedSlot + 1) + " n’existe pas sur ce téléphone.");
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
                telecom, telephony, subscriptions, target, AppConfig.phoneNumber(context, profileId));
        if (account == null) {
            throw new IllegalStateException("Route d’appel ambiguë pour le slot "
                    + (requestedSlot + 1) + ". Blue Magic refuse de choisir une autre SIM.");
        }
        return new Route(telecom, target, account);
    }

    private static PhoneAccountHandle resolvePhoneAccount(
            TelecomManager telecom, TelephonyManager telephony,
            SubscriptionManager subscriptions, SubscriptionInfo target, String configuredPhone) {
        List<PhoneAccountHandle> all = telecom.getCallCapablePhoneAccounts();
        List<PhoneAccountHandle> cellular = new ArrayList<>();
        for (PhoneAccountHandle handle : all) {
            PhoneAccount account = telecom.getPhoneAccount(handle);
            if (account != null && account.supportsUriScheme(PhoneAccount.SCHEME_TEL)) cellular.add(handle);
        }
        if (cellular.isEmpty()) return null;

        int targetSubscription = target.getSubscriptionId();
        if (Build.VERSION.SDK_INT >= 30) {
            List<PhoneAccountHandle> exact = new ArrayList<>();
            for (PhoneAccountHandle handle : cellular) {
                try {
                    if (telephony.getSubscriptionId(handle) == targetSubscription) exact.add(handle);
                } catch (Exception ignored) {
                }
            }
            if (exact.size() == 1) return exact.get(0);
            if (exact.size() > 1) return null;
        }

        String expectedPhone = digits(configuredPhone);
        if (expectedPhone.length() >= 9) {
            String suffix = expectedPhone.substring(expectedPhone.length() - 9);
            List<PhoneAccountHandle> phoneMatches = new ArrayList<>();
            for (PhoneAccountHandle handle : cellular) {
                try {
                    String line = digits(telecom.getLine1Number(handle));
                    PhoneAccount account = telecom.getPhoneAccount(handle);
                    String address = account == null || account.getAddress() == null
                            ? "" : digits(account.getAddress().getSchemeSpecificPart());
                    if (line.endsWith(suffix) || address.endsWith(suffix)) phoneMatches.add(handle);
                } catch (Exception ignored) {
                }
            }
            if (phoneMatches.size() == 1) return phoneMatches.get(0);
            if (phoneMatches.size() > 1) return null;
        }

        String subscriptionToken = String.valueOf(targetSubscription);
        List<PhoneAccountHandle> idMatches = new ArrayList<>();
        for (PhoneAccountHandle handle : cellular) {
            String id = handle.getId() == null ? "" : handle.getId().toLowerCase(Locale.ROOT);
            if (id.matches(".*(?:^|\\D)" + subscriptionToken + "(?:\\D|$).*$")) {
                idMatches.add(handle);
            }
        }
        if (idMatches.size() == 1) return idMatches.get(0);
        if (idMatches.size() > 1) return null;

        // The sole active subscription and sole TEL account are unambiguous. No list-index or
        // default-SIM fallback is allowed on multi-SIM devices.
        try {
            List<SubscriptionInfo> active = subscriptions.getActiveSubscriptionInfoList();
            if (active != null && active.size() == 1 && cellular.size() == 1
                    && active.get(0).getSubscriptionId() == targetSubscription) {
                return cellular.get(0);
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private static String digits(String value) {
        return value == null ? "" : value.replaceAll("\\D", "");
    }

    private static final class Route {
        final TelecomManager telecom;
        final SubscriptionInfo subscription;
        final PhoneAccountHandle account;

        Route(TelecomManager telecom, SubscriptionInfo subscription, PhoneAccountHandle account) {
            this.telecom = telecom;
            this.subscription = subscription;
            this.account = account;
        }
    }
}
