package com.profitloop.blueauto;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Keeps the requested new Camtel PIN only on the Robot until the operator confirms the change. */
final class PendingPinChangeStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "blue_magic_pending_pin_change_v267";
    private PendingPinChangeStore() {}

    static synchronized void save(Context context, String profileId, String pin) throws Exception {
        if (pin == null || !pin.matches("\\d{4}")) throw new IllegalArgumentException("Le nouveau PIN doit contenir 4 chiffres.");
        SecretKey key = key();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] encrypted = cipher.doFinal(pin.getBytes(StandardCharsets.UTF_8));
        String payload = "gcm1:" + Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP) + ":"
                + Base64.encodeToString(encrypted, Base64.NO_WRAP);
        AppConfig.prefs(context).edit().putString(key(profileId), payload).apply();
    }

    static synchronized String read(Context context, String profileId) throws Exception {
        String payload = AppConfig.prefs(context).getString(key(profileId), "");
        if (payload.isEmpty()) return "";
        String[] parts = payload.split(":", 3);
        if (parts.length != 3 || !"gcm1".equals(parts[0])) throw new IllegalStateException("PIN de remplacement invalide.");
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Base64.decode(parts[1], Base64.NO_WRAP)));
        String pin = new String(cipher.doFinal(Base64.decode(parts[2], Base64.NO_WRAP)), StandardCharsets.UTF_8);
        if (!pin.matches("\\d{4}")) throw new IllegalStateException("PIN de remplacement invalide.");
        return pin;
    }

    static synchronized void commit(Context context, String profileId) throws Exception {
        String pin = read(context, profileId);
        if (!pin.isEmpty()) SecurePinStore.save(context, profileId, pin);
        clear(context, profileId);
    }

    static synchronized void clear(Context context, String profileId) {
        AppConfig.prefs(context).edit().remove(key(profileId)).apply();
    }

    private static String key(String profileId) { return "pending_pin_change_" + profileId; }

    private static SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return (SecretKey) store.getKey(KEY_ALIAS, null);
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true).build());
        return generator.generateKey();
    }
}
