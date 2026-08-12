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
import java.util.Collections;
import java.util.Comparator;
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
        if (route.account == null) {
            startVerifiedSingleSimCall(context, address);
            return;
        }
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
        AccountResolution resolution = resolvePhoneAccount(context, profileId, requestedSlot,
                telecom, telephony, subscriptions, target,
                AppConfig.phoneNumber(context, profileId));
        if (resolution == null) {
            throw new IllegalStateException("Route d’appel ambiguë pour le slot "
                    + (requestedSlot + 1) + ". Vérifiez puis liez de nouveau cette SIM.");
        }
        if (resolution.account != null) {
            String component = resolution.account.getComponentName() == null ? ""
                    : resolution.account.getComponentName().flattenToString();
            AppConfig.updateCallRoute(context, profileId, resolution.account.getId(), component,
                    resolution.confidence);
        }
        return new Route(telecom, target, resolution.account);
    }

    private static AccountResolution resolvePhoneAccount(
            Context context, String profileId, int requestedSlot,
            TelecomManager telecom, TelephonyManager telephony,
            SubscriptionManager subscriptions, SubscriptionInfo target, String configuredPhone) {
        List<PhoneAccountHandle> all = telecom.getCallCapablePhoneAccounts();
        List<PhoneAccountHandle> cellular = new ArrayList<>();
        for (PhoneAccountHandle handle : all) {
            PhoneAccount account = telecom.getPhoneAccount(handle);
            if (account != null && account.supportsUriScheme(PhoneAccount.SCHEME_TEL)) cellular.add(handle);
        }
        if (cellular.isEmpty()) {
            return isOnlyActiveSubscription(subscriptions, target)
                    && verifiedPhysicalSim(context, profileId, target)
                    ? new AccountResolution(null, "VERIFIED_SINGLE_SIM_DEFAULT") : null;
        }

        int targetSubscription = target.getSubscriptionId();
        if (Build.VERSION.SDK_INT >= 30) {
            List<PhoneAccountHandle> exact = new ArrayList<>();
            for (PhoneAccountHandle handle : cellular) {
                try {
                    if (telephony.getSubscriptionId(handle) == targetSubscription) exact.add(handle);
                } catch (Exception ignored) {
                }
            }
            if (exact.size() == 1) return new AccountResolution(exact.get(0), "SUBSCRIPTION_EXACT");
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
            if (phoneMatches.size() == 1) {
                return new AccountResolution(phoneMatches.get(0), "PHONE_EXACT");
            }
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
        if (idMatches.size() == 1) {
            return new AccountResolution(idMatches.get(0), "SUBSCRIPTION_HANDLE");
        }
        if (idMatches.size() > 1) return null;

        // Once the physical SIM has been verified, reuse the exact call account selected for it.
        // This is essential on Android 6 OEM dialers that never expose a subscription id through
        // TelecomManager, while still preventing a default-SIM switch after a reboot.
        String rememberedId = AppConfig.callAccountId(context, profileId);
        String rememberedComponent = AppConfig.callAccountComponent(context, profileId);
        if (!rememberedId.isEmpty() && !rememberedComponent.isEmpty()) {
            List<PhoneAccountHandle> remembered = new ArrayList<>();
            for (PhoneAccountHandle handle : cellular) {
                String component = handle.getComponentName() == null ? ""
                        : handle.getComponentName().flattenToString();
                if (rememberedId.equals(handle.getId()) && rememberedComponent.equals(component)) {
                    remembered.add(handle);
                }
            }
            if (remembered.size() == 1) {
                return new AccountResolution(remembered.get(0), "MEMORIZED_VERIFIED_SLOT");
            }
            if (remembered.size() > 1) return null;
            AppConfig.clearCallRoute(context, profileId);
        }

        // Some Android 6 dialers identify their accounts only as SIM 1 / SIM 2. Use that explicit
        // slot label before the controlled ordering fallback.
        List<PhoneAccountHandle> slotHints = new ArrayList<>();
        for (PhoneAccountHandle handle : cellular) {
            PhoneAccount account = telecom.getPhoneAccount(handle);
            String label = account == null || account.getLabel() == null
                    ? "" : account.getLabel().toString();
            String description = account == null || account.getShortDescription() == null
                    ? "" : account.getShortDescription().toString();
            if (hasSlotHint(handle.getId() + " " + label + " " + description, requestedSlot)) {
                slotHints.add(handle);
            }
        }
        if (slotHints.size() == 1 && verifiedPhysicalSim(context, profileId, target)) {
            return new AccountResolution(slotHints.get(0), "VERIFIED_SLOT_LABEL");
        }
        if (slotHints.size() > 1) return null;

        // Une seule SIM active rend la route système non ambiguë, même lorsque le dialer publie
        // plusieurs PhoneAccount techniques (urgence, IMS, VoLTE). C'était le comportement utile
        // de la 2.4.5; l'identité physique de la SIM reste contrôlée juste avant ce choix.
        try {
            List<SubscriptionInfo> active = subscriptions.getActiveSubscriptionInfoList();
            if (active != null && active.size() == 1
                    && active.get(0).getSubscriptionId() == targetSubscription
                    && verifiedPhysicalSim(context, profileId, target)) {
                if (cellular.size() == 1) {
                    return new AccountResolution(cellular.get(0), "SOLE_ACTIVE_SIM");
                }
                return new AccountResolution(null, "VERIFIED_SINGLE_SIM_DEFAULT");
            }
        } catch (Exception ignored) {
        }

        // Controlled Android 6 fallback: only after the SIM identity was explicitly linked and is
        // still valid, pair the ordered active-slot list with the stable Telecom account list. The
        // chosen account is persisted above, so later calls never drift to Android's default SIM.
        try {
            if (!verifiedPhysicalSim(context, profileId, target)) return null;
            List<SubscriptionInfo> active = subscriptions.getActiveSubscriptionInfoList();
            if (active == null) return null;
            List<SubscriptionInfo> ordered = new ArrayList<>();
            for (SubscriptionInfo info : active) {
                if (info != null && info.getSimSlotIndex() >= 0) ordered.add(info);
            }
            Collections.sort(ordered, Comparator.comparingInt(SubscriptionInfo::getSimSlotIndex));
            int position = -1;
            for (int index = 0; index < ordered.size(); index++) {
                if (ordered.get(index).getSubscriptionId() == targetSubscription) {
                    position = index;
                    break;
                }
            }
            if (position >= 0 && position < cellular.size()) {
                return new AccountResolution(cellular.get(position), "VERIFIED_SLOT_ORDER");
            }
        } catch (Exception ignored) {
        }
        return null;
    }

    private static boolean isOnlyActiveSubscription(SubscriptionManager subscriptions,
                                                     SubscriptionInfo target) {
        try {
            List<SubscriptionInfo> active = subscriptions.getActiveSubscriptionInfoList();
            return active != null && active.size() == 1
                    && active.get(0).getSubscriptionId() == target.getSubscriptionId();
        } catch (Exception ignored) {
            return false;
        }
    }

    private static void startVerifiedSingleSimCall(Context context, Uri address) {
        Intent call = new Intent(Intent.ACTION_CALL, address);
        call.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        if (call.resolveActivity(context.getPackageManager()) == null) {
            throw new IllegalStateException("Aucune application Téléphone compatible.");
        }
        context.startActivity(call);
    }

    private static boolean verifiedPhysicalSim(Context context, String profileId,
                                               SubscriptionInfo target) {
        SimIdentityManager.Verification verification = SimIdentityManager.verify(context, profileId);
        return verification.valid && verification.subscriptionId == target.getSubscriptionId()
                && verification.slot == target.getSimSlotIndex();
    }

    private static boolean hasSlotHint(String value, int zeroBasedSlot) {
        String normalized = value == null ? "" : value.toLowerCase(Locale.ROOT)
                .replaceAll("[_-]+", " ").replaceAll("\\s+", " ").trim();
        int humanSlot = zeroBasedSlot + 1;
        return normalized.matches(".*(?:sim|slot|card|phone)\\s*" + humanSlot + "(?:\\D.*|$)");
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

    private static final class AccountResolution {
        final PhoneAccountHandle account;
        final String confidence;

        AccountResolution(PhoneAccountHandle account, String confidence) {
            this.account = account;
            this.confidence = confidence;
        }
    }
}
