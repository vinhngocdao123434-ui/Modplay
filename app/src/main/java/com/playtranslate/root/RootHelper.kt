package com.playtranslate.root

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
            "/system/bin/su",
            "/system/xbin/su",
            "/sbin/su",
            "/system/su",
            "/system/bin/.ext/.su",
            "/system/usr/we-need-root/su-backup"
        )
        return paths.any { File(it).exists() }
    }

    suspend fun requestRootPermission(): Boolean = withContext(Dispatchers.IO) {
        try {
            val process = Runtime.getRuntime().exec("su")
            process.outputStream.use { os ->
                os.write("id\nexit\n".toByteArray())
                os.flush()
            }
            process.waitFor() == 0
        } catch (e: Exception) {
            Log.w(TAG, "Root request failed: ${e.message}")
            false
        }
    }

    suspend fun grantOverlayPermission(packageName: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val process = Runtime.getRuntime().exec("su")
            process.outputStream.use { os ->
                os.write("pm grant $packageName android.permission.SYSTEM_ALERT_WINDOW\nexit\n".toByteArray())
                os.flush()
            }
            process.waitFor() == 0
        } catch (e: Exception) {
            Log.w(TAG, "grantOverlayPermission failed: ${e.message}")
            false
        }
    }

    suspend fun captureScreenRoot(displayId: Int): Bitmap? = withContext(Dispatchers.IO) {
        try {
            val cmd = if (displayId > 0) "screencap -d $displayId -p\n" else "screencap -p\n"
            val process = Runtime.getRuntime().exec("su")
            val outputStream = process.outputStream
            outputStream.write(cmd.toByteArray())
            outputStream.write("exit\n".toByteArray())
            outputStream.flush()

            val inputStream = process.inputStream
            val byteBuffer = ByteArrayOutputStream()
            val buffer = ByteArray(32 * 1024)
            var read: Int
            while (inputStream.read(buffer).also { read = it } != -1) {
                byteBuffer.write(buffer, 0, read)
            }
            process.waitFor()

            val bytes = byteBuffer.toByteArray()
            if (bytes.isNotEmpty()) {
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            } else {
                null
            }
        } catch (e: Exception) {
            Log.e(TAG, "captureScreenRoot failed: ${e.message}", e)
            null
        }
    }
}
