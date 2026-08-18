package com.profitloop.blueauto;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;

/** Device-bound signing identity for B.I.R. Relay. No private key leaves AndroidKeyStore. */
final class RelayIdentityStore {
    private static final String STORE = "AndroidKeyStore";
    private static final String ALIAS = "bir_relay_identity_v290";

    private RelayIdentityStore() {}

    private static void ensure() throws Exception {
        KeyStore keyStore = KeyStore.getInstance(STORE);
        keyStore.load(null);
        if (keyStore.containsAlias(ALIAS)) return;
        KeyPairGenerator generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, STORE);
        generator.initialize(new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setKeySize(2048)
                .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                .build());
        generator.generateKeyPair();
    }

    static String publicKeyBase64() throws Exception {
        ensure();
        KeyStore keyStore = KeyStore.getInstance(STORE);
        keyStore.load(null);
        PublicKey key = keyStore.getCertificate(ALIAS).getPublicKey();
        return Base64.encodeToString(key.getEncoded(), Base64.NO_WRAP);
    }

    static String fingerprint() throws Exception {
        return OfflineLedgerDb.sha256(publicKeyBase64());
    }

    static String sign(String text) throws Exception {
        ensure();
        KeyStore keyStore = KeyStore.getInstance(STORE);
        keyStore.load(null);
        PrivateKey key = (PrivateKey) keyStore.getKey(ALIAS, null);
        Signature signature = Signature.getInstance("SHA256withRSA");
        signature.initSign(key);
        signature.update((text == null ? "" : text).getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(signature.sign(), Base64.NO_WRAP);
    }
}
