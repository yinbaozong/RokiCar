package com.rokicar.controller;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

final class SecureStore {
    private static final String KEYSTORE = "AndroidKeyStore";
    private static final String ALIAS = "rokicar.voice.credentials";
    private final SharedPreferences preferences;

    SecureStore(Context context) {
        preferences = context.getSharedPreferences("voice_secure", Context.MODE_PRIVATE);
    }

    synchronized void put(String key, String value) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, getKey());
            byte[] encrypted = cipher.doFinal((value == null ? "" : value).getBytes(StandardCharsets.UTF_8));
            byte[] iv = cipher.getIV();
            ByteBuffer packed = ByteBuffer.allocate(4 + iv.length + encrypted.length);
            packed.putInt(iv.length).put(iv).put(encrypted);
            preferences.edit().putString(key, Base64.encodeToString(packed.array(), Base64.NO_WRAP)).apply();
        } catch (Exception error) {
            throw new IllegalStateException("无法安全保存语音配置", error);
        }
    }

    synchronized String get(String key) {
        String stored = preferences.getString(key, "");
        if (stored == null || stored.isEmpty()) return "";
        try {
            ByteBuffer packed = ByteBuffer.wrap(Base64.decode(stored, Base64.NO_WRAP));
            int ivLength = packed.getInt();
            if (ivLength < 12 || ivLength > 32) return "";
            byte[] iv = new byte[ivLength];
            byte[] encrypted = new byte[packed.remaining() - ivLength];
            packed.get(iv).get(encrypted);
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, getKey(), new GCMParameterSpec(128, iv));
            return new String(cipher.doFinal(encrypted), StandardCharsets.UTF_8);
        } catch (Exception error) {
            return "";
        }
    }

    private SecretKey getKey() throws Exception {
        KeyStore store = KeyStore.getInstance(KEYSTORE);
        store.load(null);
        if (store.containsAlias(ALIAS)) return ((KeyStore.SecretKeyEntry) store.getEntry(ALIAS, null)).getSecretKey();
        KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE);
        generator.init(new KeyGenParameterSpec.Builder(
                ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .build());
        return generator.generateKey();
    }
}
