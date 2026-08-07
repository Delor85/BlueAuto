package com.profitloop.blueauto;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class SecurePinStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "blue_magic_operator_pin_v2";
    private static final String PREF_CIPHER = "operator_pin_cipher";

    private SecurePinStore() {}

    static synchronized void save(Context context, String pin) throws Exception {
        if (pin == null || !pin.matches("\\d{4}")) {
            throw new IllegalArgumentException("Le PIN opérateur doit contenir exactement 4 chiffres.");
        }

        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        byte[] encrypted = cipher.doFinal(pin.getBytes(StandardCharsets.UTF_8));
        String payload = "gcm1:"
                + Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP)
                + ":"
                + Base64.encodeToString(encrypted, Base64.NO_WRAP);
        AppConfig.prefs(context).edit().putString(PREF_CIPHER, payload).apply();
    }

    static synchronized String read(Context context) throws Exception {
        String payload = AppConfig.prefs(context).getString(PREF_CIPHER, "");
        if (payload.isEmpty()) return "";

        String[] parts = payload.split(":", 3);
        if (parts.length != 3 || !"gcm1".equals(parts[0])) {
            throw new IllegalStateException("Format PIN chiffré inconnu.");
        }

        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(128, Base64.decode(parts[1], Base64.NO_WRAP));
        cipher.init(Cipher.DECRYPT_MODE, key, spec);
        byte[] clear = cipher.doFinal(Base64.decode(parts[2], Base64.NO_WRAP));
        String pin = new String(clear, StandardCharsets.UTF_8);
        if (!pin.matches("\\d{4}")) throw new IllegalStateException("PIN local invalide.");
        return pin;
    }

    static boolean hasPin(Context context) {
        return !AppConfig.prefs(context).getString(PREF_CIPHER, "").isEmpty();
    }

    static synchronized void clear(Context context) {
        AppConfig.prefs(context).edit().remove(PREF_CIPHER).apply();
    }

    private static SecretKey getOrCreateKey() throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) {
            return (SecretKey) store.getKey(KEY_ALIAS, null);
        }

        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
        generator.init(new KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build());
        return generator.generateKey();
    }
}
