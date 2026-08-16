package com.profitloop.blueauto;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Keeps owner/admin entitlement tokens outside JavaScript and outside clear-text preferences.
 * The server stores only token hashes; Android stores the clear token encrypted by AndroidKeyStore.
 */
final class SecureOwnerStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String KEY_ALIAS = "bir_owner_entitlements_v1";
    private static final String PREFIX = "owner_entitlement_cipher_v1_";

    private SecureOwnerStore() {}

    static synchronized void save(Context context, String kind, String entitlementId, String token) throws Exception {
        String normalized = normalizeKind(kind);
        if (token == null || token.length() < 32 || entitlementId == null || entitlementId.trim().isEmpty()) {
            throw new IllegalArgumentException("Entitlement propriétaire incomplet.");
        }
        JSONObject clear = new JSONObject();
        clear.put("kind", normalized);
        clear.put("entitlement_id", entitlementId.trim());
        clear.put("token", token.trim());
        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE, key);
        String payload = "gcm1:"
                + Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP)
                + ":"
                + Base64.encodeToString(cipher.doFinal(clear.toString().getBytes(StandardCharsets.UTF_8)), Base64.NO_WRAP);
        AppConfig.prefs(context).edit().putString(PREFIX + normalized, payload).commit();
    }

    static synchronized JSONObject read(Context context, String kind) throws Exception {
        String normalized = normalizeKind(kind);
        String payload = AppConfig.prefs(context).getString(PREFIX + normalized, "");
        if (payload.isEmpty()) return new JSONObject();
        String[] parts = payload.split(":", 3);
        if (parts.length != 3 || !"gcm1".equals(parts[0])) {
            throw new IllegalStateException("Entitlement propriétaire local illisible.");
        }
        SecretKey key = getOrCreateKey();
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE, key,
                new GCMParameterSpec(128, Base64.decode(parts[1], Base64.NO_WRAP)));
        return new JSONObject(new String(cipher.doFinal(Base64.decode(parts[2], Base64.NO_WRAP)),
                StandardCharsets.UTF_8));
    }

    static String token(Context context, String kind) {
        try { return read(context, kind).optString("token", ""); }
        catch (Exception ignored) { return ""; }
    }

    static String entitlementId(Context context, String kind) {
        try { return read(context, kind).optString("entitlement_id", ""); }
        catch (Exception ignored) { return ""; }
    }

    static boolean has(Context context, String kind) {
        return !AppConfig.prefs(context).getString(PREFIX + normalizeKind(kind), "").isEmpty();
    }

    static void clear(Context context, String kind) {
        AppConfig.prefs(context).edit().remove(PREFIX + normalizeKind(kind)).commit();
    }

    private static String normalizeKind(String kind) {
        return "MOCK_OWNER".equalsIgnoreCase(kind) ? "MOCK_OWNER" : "OWNER_ADMIN";
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
