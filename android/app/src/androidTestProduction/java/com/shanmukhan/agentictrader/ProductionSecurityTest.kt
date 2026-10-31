package com.shanmukhan.agentictrader

import android.view.WindowManager
import androidx.biometric.BiometricManager
import androidx.compose.ui.test.*
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test

/** Negative device checks only; no credentials, pairing or network request is supplied. */
class ProductionSecurityTest {
    @get:Rule val ui = createAndroidComposeRule<MainActivity>()
    @Test fun productionLaunchIsLockedAndUsesSecureWindow() {
        assertFalse(BuildConfig.DEMO)
        assertTrue(ui.activity.window.attributes.flags and WindowManager.LayoutParams.FLAG_SECURE != 0)
        ui.onNodeWithText("Pair and protect this phone").assertIsNotEnabled()
        ui.onNodeWithText("Server operator token").assertExists()
        ui.onNodeWithText("Available cash").assertDoesNotExist()
    }
    @Test fun missingStrongBiometricsFailClosedBeforeEnrollment() {
        val context = ui.activity
        val available = BiometricManager.from(context).canAuthenticate(BiometricManager.Authenticators.BIOMETRIC_STRONG)
        org.junit.Assume.assumeTrue("Negative test requires no enrolled strong biometric", available != BiometricManager.BIOMETRIC_SUCCESS)
        val vault = SecureVault(context)
        try { vault.enrollmentCipher(); fail("Must refuse unsupported/unenrolled biometrics") } catch (_: IllegalStateException) { }
        assertFalse(vault.paired())
    }
}
