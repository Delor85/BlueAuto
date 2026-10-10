package com.profitloop.blueauto;

import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import android.telephony.SubscriptionInfo;
import android.telephony.SubscriptionManager;
import android.telephony.TelephonyManager;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

/**
 * Binds each Robot profile to the physical SIM selected by the user.
 *
 * Android does not expose the same SIM identifiers on every version/vendor. We therefore use the
 * strongest identifier available (verified line number, ICCID, then subscription id) and store only
 * its SHA-256 digest. A missing or changed SIM always fails closed.
 */
final class SimIdentityManager {
    static final String READY = "READY";
    static final String PERMISSION_MISSING = "PERMISSION_MISSING";
    static final String SLOT_MISSING = "SLOT_MISSING";
    static final String NUMBER_MISMATCH = "NUMBER_MISMATCH";
    static final String BINDING_REQUIRED = "BINDING_REQUIRED";
    static final String SIM_CHANGED = "SIM_CHANGED";
    static final String UNAVAILABLE = "UNAVAILABLE";

    private SimIdentityManager() {}

    static Verification verify(Context context, String profileId) {
        Snapshot snapshot = snapshot(context, profileId);
        if (!snapshot.ready()) return snapshot.failure;

        String savedType = AppConfig.simBindingType(context, profileId);
        String savedHash = AppConfig.simBindingHash(context, profileId);
        if (savedType.isEmpty() || savedHash.isEmpty()) {
            // A number read directly from Android and equal to the Camtel number is safe to enroll
            // automatically. Hidden-number SIMs need one explicit confirmation in the UI.
            if ("PHONE".equals(snapshot.identityType)) {
                AppConfig.updateSimBinding(context, profileId, snapshot.identityType,
                        snapshot.identityHash);
                return Verification.ready(snapshot, true);
            }
            return Verification.failure(BINDING_REQUIRED,
                    "Confirmez une fois que la SIM de " + AppConfig.nodeCode(context, profileId)
                            + " est bien dans le slot " + (snapshot.slot + 1) + ".",
                    snapshot);
        }
        if (!savedType.equals(snapshot.identityType) || !savedHash.equals(snapshot.identityHash)) {
            return Verification.failure(SIM_CHANGED,
                    "La SIM du slot " + (snapshot.slot + 1)
                            + " n’est plus celle liée à ce Robot.", snapshot);
        }
        return Verification.ready(snapshot, false);
    }

    /** Bind after an explicit user choice (pairing, slot selection, or confirmation dialog). */
    static Verification bindSelectedSim(Context context, String profileId) {
        Snapshot snapshot = snapshot(context, profileId);
        if (!snapshot.ready()) return snapshot.failure;
        AppConfig.updateSimBinding(context, profileId, snapshot.identityType, snapshot.identityHash);
        return Verification.ready(snapshot, true);
    }

    /** Verify a selected slot without changing the saved Remote/Robot profile. */
    static Verification inspectSelectedSim(Context context, String profileId, int slot) {
        Snapshot snapshot = snapshot(context, profileId, Math.max(0, slot));
        return snapshot.ready() ? Verification.ready(snapshot, false) : snapshot.failure;
    }

    static SubscriptionInfo activeSubscription(Context context, String profileId) {
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) return null;
        try {
            SubscriptionManager manager = (SubscriptionManager) context.getSystemService(
                    Context.TELEPHONY_SUBSCRIPTION_SERVICE);
            return manager == null ? null : manager.getActiveSubscriptionInfoForSimSlotIndex(
                    AppConfig.simSlot(context, profileId));
        } catch (Exception ignored) {
            return null;
        }
    }

    private static Snapshot snapshot(Context context, String profileId) {
        return snapshot(context, profileId, AppConfig.simSlot(context, profileId));
    }

    private static Snapshot snapshot(Context context, String profileId, int slot) {
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED) {
            return Snapshot.failed(slot, Verification.failure(PERMISSION_MISSING,
                    "Autorisez l’état du téléphone pour vérifier la SIM avant toute transaction.", null));
        }

        SubscriptionManager subscriptions = (SubscriptionManager) context.getSystemService(
                Context.TELEPHONY_SUBSCRIPTION_SERVICE);
        if (subscriptions == null) {
            return Snapshot.failed(slot, Verification.failure(UNAVAILABLE,
                    "Le service SIM Android est indisponible.", null));
        }

        final SubscriptionInfo info;
        try {
            info = subscriptions.getActiveSubscriptionInfoForSimSlotIndex(slot);
        } catch (Exception error) {
            return Snapshot.failed(slot, Verification.failure(UNAVAILABLE,
                    "Android n’a pas pu vérifier la SIM du slot " + (slot + 1) + ".", null));
        }
        if (info == null) {
            return Snapshot.failed(slot, Verification.failure(SLOT_MISSING,
                    "Aucune SIM active dans le slot " + (slot + 1) + ".", null));
        }

        String configured = lastNine(AppConfig.phoneNumber(context, profileId));
        String observed = lastNine(readPhoneNumber(context, subscriptions, info));
        if (!observed.isEmpty() && !observed.equals(configured)) {
            Snapshot mismatch = new Snapshot(slot, info, "", "", observed, "");
            mismatch.failure = Verification.failure(NUMBER_MISMATCH,
                    "La SIM du slot " + (slot + 1) + " porte le numéro " + mask(observed)
                            + ", pas celui de " + AppConfig.nodeCode(context, profileId) + ".", mismatch);
            return mismatch;
        }

        String type;
        String rawIdentity;
        if (!observed.isEmpty()) {
            type = "PHONE";
            rawIdentity = observed;
        } else {
            String iccId = safeIccId(info);
            if (!iccId.isEmpty()) {
                type = "ICCID";
                rawIdentity = iccId;
            } else {
                type = "SUBSCRIPTION";
                rawIdentity = String.valueOf(info.getSubscriptionId());
            }
        }
        return new Snapshot(slot, info, type, sha256(type + ":" + rawIdentity), observed,
                carrierLabel(info));
    }

    @SuppressWarnings("deprecation")
    private static String readPhoneNumber(Context context, SubscriptionManager subscriptions,
                                          SubscriptionInfo info) {
        String number = "";
        try {
            if (Build.VERSION.SDK_INT >= 33
                    && context.checkSelfPermission(Manifest.permission.READ_PHONE_NUMBERS)
                    == PackageManager.PERMISSION_GRANTED) {
                number = subscriptions.getPhoneNumber(info.getSubscriptionId());
            }
        } catch (Exception ignored) {
        }
        if (digits(number).isEmpty() && Build.VERSION.SDK_INT >= 24) {
            try {
                number = info.getNumber();
            } catch (Exception ignored) {
            }
        }
        if (digits(number).isEmpty()) {
            try {
                TelephonyManager telephony = (TelephonyManager) context.getSystemService(
                        Context.TELEPHONY_SERVICE);
                if (telephony != null) {
                    number = telephony.createForSubscriptionId(info.getSubscriptionId())
                            .getLine1Number();
                }
            } catch (Exception ignored) {
            }
        }
        return number == null ? "" : number;
    }

    private static String safeIccId(SubscriptionInfo info) {
        try {
            return digits(info.getIccId());
        } catch (Exception ignored) {
            return "";
        }
    }

    private static String carrierLabel(SubscriptionInfo info) {
        CharSequence value = info.getDisplayName();
        if (value == null || value.toString().trim().isEmpty()) value = info.getCarrierName();
        return value == null ? "SIM" : value.toString().trim();
    }

    private static String lastNine(String value) {
        String normalized = digits(value);
        return normalized.length() < 9 ? "" : normalized.substring(normalized.length() - 9);
    }

    private static String digits(String value) {
        return value == null ? "" : value.replaceAll("\\D", "");
    }

    private static String mask(String number) {
        if (number == null || number.length() < 4) return "inconnu";
        return "*****" + number.substring(number.length() - 4);
    }

    private static String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder();
            for (byte item : digest) result.append(String.format(Locale.ROOT, "%02x", item & 0xff));
            return result.toString();
        } catch (Exception error) {
            throw new IllegalStateException("Empreinte SIM indisponible.", error);
        }
    }

    static final class Verification {
        final boolean valid;
        final boolean newlyBound;
        final String code;
        final String message;
        final int slot;
        final int subscriptionId;
        final String fingerprint;
        final String identityType;
        final String carrier;

        private Verification(boolean valid, boolean newlyBound, String code, String message,
                             Snapshot snapshot) {
            this.valid = valid;
            this.newlyBound = newlyBound;
            this.code = code;
            this.message = message;
            this.slot = snapshot == null ? -1 : snapshot.slot;
            this.subscriptionId = snapshot == null || snapshot.info == null
                    ? SubscriptionManager.INVALID_SUBSCRIPTION_ID : snapshot.info.getSubscriptionId();
            this.fingerprint = snapshot == null ? "" : snapshot.identityHash;
            this.identityType = snapshot == null ? "" : snapshot.identityType;
            this.carrier = snapshot == null ? "" : snapshot.carrier;
        }

        static Verification ready(Snapshot snapshot, boolean newlyBound) {
            return new Verification(true, newlyBound, READY,
                    "SIM vérifiée dans le slot " + (snapshot.slot + 1) + ".", snapshot);
        }

        static Verification failure(String code, String message, Snapshot snapshot) {
            return new Verification(false, false, code, message, snapshot);
        }

        String attestation() {
            return valid ? fingerprint : "";
        }
    }

    private static final class Snapshot {
        final int slot;
        final SubscriptionInfo info;
        final String identityType;
        final String identityHash;
        final String observedPhone;
        final String carrier;
        Verification failure;

        Snapshot(int slot, SubscriptionInfo info, String identityType, String identityHash,
                 String observedPhone, String carrier) {
            this.slot = slot;
            this.info = info;
            this.identityType = identityType;
            this.identityHash = identityHash;
            this.observedPhone = observedPhone;
            this.carrier = carrier;
        }

        static Snapshot failed(int slot, Verification failure) {
            Snapshot result = new Snapshot(slot, null, "", "", "", "");
            result.failure = failure;
            return result;
        }

        boolean ready() {
            return failure == null;
        }
    }
}
