package com.playtranslate.root

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File

object RootHelper {
    private const val TAG = "RootHelper"

    fun isRootAvailable(): Boolean {
        val paths = arrayOf(
            "/system/bin/su", "/system/xbin/su", "/sbin/su",
            "/system/su", "/system/bin/.ext/.su"
        )
        return paths.any { File(it).exists() }
    }

    suspend fun grantAllPermissionsViaRoot(context: Context): Boolean = withContext(Dispatchers.IO) {
        try {
            val pkg = context.packageName
            val a11yComponent = "$pkg/$pkg.PlayTranslateAccessibilityService"
            val cmds = arrayOf(
                "appops set $pkg ACCESS_RESTRICTED_SETTINGS allow",
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services null",
                "settings put secure accessibility_enabled 0",
                "sleep 1",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1"
            )
            val process = Runtime.getRuntime().exec("su")
            process.outputStream.use { os ->
                for (c in cmds) {
                    os.write((c + "\n").toByteArray())
                }
                os.write("exit\n".toByteArray())
                os.flush()
            }
            process.waitFor() == 0
        } catch (e: Exception) {
            Log.e(TAG, "grantAllPermissionsViaRoot failed: ${e.message}")
            false
        }
    }

    suspend fun captureScreenRoot(displayId: Int): Bitmap? = withContext(Dispatchers.IO) {
        try {
            val cmd = if (displayId > 0) "screencap -d $displayId -p\n" else "screencap -p\n"
            val process = Runtime.getRuntime().exec("su")
            process.outputStream.use { os ->
                os.write(cmd.toByteArray())
                os.write("exit\n".toByteArray())
                os.flush()
            }
            val bytes = process.inputStream.use { it.readBytes() }
            process.waitFor()
            if (bytes.isNotEmpty()) BitmapFactory.decodeByteArray(bytes, 0, bytes.size) else null
        } catch (e: Exception) {
            Log.e(TAG, "captureScreenRoot failed: ${e.message}")
            null
        }
    }
}
