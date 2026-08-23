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

final class SecurePairingStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "blue_magic_pairing_v1";
    private static final String VALUE_KEY = "pairing_secret_cipher_v1";

    private SecurePairingStore() {}

    static synchronized void save(Context context, String secret) throws Exception {
        if (secret == null || secret.length() < 24) {
            throw new IllegalArgumentException("Le code d’activation initiale est invalide.");
        }
        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        String payload = "gcm1:"
                + Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP)
                + ":"
                + Base64.encodeToString(
                        cipher.doFinal(secret.getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP);
        AppConfig.prefs(context).edit().putString(VALUE_KEY, payload).commit();
    }

    static synchronized String read(Context context) throws Exception {
        String payload = AppConfig.prefs(context).getString(VALUE_KEY, "");
        if (payload.isEmpty()) return "";
        String[] parts = payload.split(":", 3);
        if (parts.length != 3 || !"gcm1".equals(parts[0])) {
            throw new IllegalStateException("Code d’activation local illisible.");
        }
        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key,
                new GCMParameterSpec(128, Base64.decode(parts[1], Base64.NO_WRAP)));
        return new String(cipher.doFinal(Base64.decode(parts[2], Base64.NO_WRAP)),
                StandardCharsets.UTF_8);
    }

    static boolean hasSecret(Context context) {
        return !AppConfig.prefs(context).getString(VALUE_KEY, "").isEmpty();
    }

    static synchronized void clear(Context context) {
        AppConfig.prefs(context).edit().remove(VALUE_KEY).commit();
    }

    private static SecretKey getOrCreateKey() throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(KEY_ALIAS)) return (SecretKey) store.getKey(KEY_ALIAS, null);

        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
        generator.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build());
        return generator.generateKey();
    }
}
