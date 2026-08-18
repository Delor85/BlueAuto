package com.profitloop.blueauto;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.PublicKey;
import java.security.Signature;
import java.security.spec.X509EncodedKeySpec;

final class RelayIdentityStore {
    private static final String STORE = "AndroidKeyStore";
    private static final String ALIAS = "bir_relay_identity_v290";
    private RelayIdentityStore() {}

    private static void ensure() throws Exception {
        KeyStore ks = KeyStore.getInstance(STORE); ks.load(null);
        if (ks.containsAlias(ALIAS)) return;
        KeyPairGenerator g = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_RSA, STORE);
        g.initialize(new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setKeySize(2048)
                .setDigests(KeyProperties.DIGEST_SHA256, KeyProperties.DIGEST_SHA512)
                .setSignaturePaddings(KeyProperties.SIGNATURE_PADDING_RSA_PKCS1)
                .build());
        g.generateKeyPair();
    }

    static String publicKeyBase64() throws Exception {
        ensure(); KeyStore ks = KeyStore.getInstance(STORE); ks.load(null);
        PublicKey key = ks.getCertificate(ALIAS).getPublicKey();
        return Base64.encodeToString(key.getEncoded(), Base64.NO_WRAP);
    }

    static String fingerprint() throws Exception { return sha256(publicKeyBase64()); }

    static String sha256(String value) {
        try {
            java.security.MessageDigest digest = java.security.MessageDigest.getInstance("SHA-256");
            byte[] raw = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder(raw.length * 2);
            for (byte b : raw) out.append(String.format(java.util.Locale.US, "%02x", b & 0xff));
            return out.toString();
        } catch (Exception error) { throw new IllegalStateException("SHA-256 unavailable", error); }
    }

    static String sign(String canonical) throws Exception {
        ensure(); KeyStore ks = KeyStore.getInstance(STORE); ks.load(null);
        PrivateKey key = (PrivateKey) ks.getKey(ALIAS, null);
        Signature sig = Signature.getInstance("SHA256withRSA");
        sig.initSign(key); sig.update(canonical.getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(sig.sign(), Base64.NO_WRAP);
    }

    static boolean verify(String publicKeyBase64, String canonical, String signatureBase64) {
        try {
            byte[] encoded = Base64.decode(publicKeyBase64, Base64.DEFAULT);
            PublicKey key = KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(encoded));
            Signature sig = Signature.getInstance("SHA256withRSA");
            sig.initVerify(key); sig.update(canonical.getBytes(StandardCharsets.UTF_8));
            return sig.verify(Base64.decode(signatureBase64, Base64.DEFAULT));
        } catch (Exception ignored) { return false; }
    }
}
