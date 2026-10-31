package com.shanmukhan.agentictrader

import android.content.Context
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyInfo
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import androidx.biometric.BiometricManager
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import java.io.File
import java.nio.ByteBuffer
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec

/** Cipher use itself requires a fresh Class 3 biometric. UI success alone never unlocks data. */
class SecureVault(private val context: Context) {
    private val alias = "agentic-trader.phone.v1"
    private val file = AtomicFile(File(context.noBackupFilesDir, "phone.vault"))
    private val store get() = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
    fun paired() = file.baseFile.exists() && store.containsAlias(alias)

    fun enrollmentCipher(): Cipher {
        check(BiometricManager.from(context).canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            == BiometricManager.BIOMETRIC_SUCCESS) {
            "Set up a strong fingerprint or supported strong biometric in Android settings first."
        }
        if (!store.containsAlias(alias)) {
            KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
                init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                    .setKeySize(256).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                    .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                    .setUserAuthenticationRequired(true)
                    .setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG)
                    .setInvalidatedByBiometricEnrollment(true).setUnlockedDeviceRequired(true).build())
            }.generateKey()
        }
        return Cipher.getInstance("AES/GCM/NoPadding").apply { init(Cipher.ENCRYPT_MODE, hardwareKey()) }
    }

    @Suppress("DEPRECATION")
    private fun hardwareKey(): SecretKey {
        val key = store.getKey(alias, null) as SecretKey
        val info = SecretKeyFactory.getInstance(key.algorithm, "AndroidKeyStore")
            .getKeySpec(key, KeyInfo::class.java) as KeyInfo
        val hardware = if (Build.VERSION.SDK_INT >= 31)
            info.securityLevel in listOf(KeyProperties.SECURITY_LEVEL_TRUSTED_ENVIRONMENT, KeyProperties.SECURITY_LEVEL_STRONGBOX)
            else info.isInsideSecureHardware
        check(hardware && info.isUserAuthenticationRequired && info.isUserAuthenticationRequirementEnforcedBySecureHardware) {
            "This phone cannot provide the hardware-backed biometric protection required by Agentic Trader."
        }
        return key
    }

    fun decryptCipher(): Cipher {
        val value = file.readFully()
        check(value.size in 32..4096) { "Phone pairing is damaged. Pair this phone again." }
        return Cipher.getInstance("AES/GCM/NoPadding").apply {
            init(Cipher.DECRYPT_MODE, hardwareKey(), GCMParameterSpec(128, value.copyOfRange(0, 12)))
        }
    }
    fun save(cipher: Cipher, plaintext: ByteArray) {
        val output = file.startWrite()
        try {
            check(cipher.iv.size == 12)
            output.write(ByteBuffer.allocate(12 + plaintext.size + 16).put(cipher.iv).put(cipher.doFinal(plaintext)).array())
            file.finishWrite(output)
        } catch (error: Exception) { file.failWrite(output); throw error }
        finally { plaintext.fill(0) }
    }
    fun open(cipher: Cipher): ByteArray {
        val encrypted = file.readFully()
        return cipher.doFinal(encrypted.copyOfRange(12, encrypted.size))
    }
    fun forget() { file.delete(); store.deleteEntry(alias) }
}

class BiometricGate(private val activity: FragmentActivity) {
    private var prompt: BiometricPrompt? = null
    fun authenticate(cipher: Cipher, title: String, success: (Cipher) -> Unit, error: (String) -> Unit) {
        prompt?.cancelAuthentication()
        prompt = BiometricPrompt(activity, ContextCompat.getMainExecutor(activity),
            object : BiometricPrompt.AuthenticationCallback() {
                override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                    val authorized = result.cryptoObject?.cipher
                    if (authorized != null) success(authorized) else error("Biometric protection was not authorized.")
                }
                override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                    error("Biometric unlock was cancelled or is unavailable. Try again when ready.")
                }
            })
        prompt?.authenticate(BiometricPrompt.PromptInfo.Builder().setTitle(title)
            .setSubtitle("Your fingerprint stays on your phone")
            .setAllowedAuthenticators(BiometricManager.Authenticators.BIOMETRIC_STRONG)
            .setNegativeButtonText("Cancel").build(), BiometricPrompt.CryptoObject(cipher))
    }
    fun cancel() { prompt?.cancelAuthentication(); prompt = null }
}
