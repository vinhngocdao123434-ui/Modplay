import os

print(">>> Đang áp dụng các cập nhật tính năng vào mã nguồn...")

# 1. Tạo file Workflow GitHub Actions
workflow_path = ".github/workflows/build-debug.yml"
os.makedirs(os.path.dirname(workflow_path), exist_ok=True)
with open(workflow_path, "w", encoding="utf-8") as f:
    f.write("""name: Build Debug APK

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: gradle

      - name: Prepare local config files
        run: |
          touch local.properties
          echo "deepl.api.key=" >> local.properties
          chmod +x gradlew || true

      - name: Build Debug APK
        run: ./gradlew assembleDebug -x test -x lint --no-daemon --stacktrace

      - name: Upload Debug APK
        uses: actions/upload-artifact@v4
        with:
          name: PlayTranslate-debug-apk
          path: app/build/outputs/apk/debug/*.apk
          if-no-files-found: error
""")
print(f"  + Đã tạo: {workflow_path}")

# 2. Tạo RootHelper.kt
root_helper_path = "app/src/main/java/com/playtranslate/root/RootHelper.kt"
os.makedirs(os.path.dirname(root_helper_path), exist_ok=True)
with open(root_helper_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.root

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
                os.write("id\\nexit\\n".toByteArray())
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
                os.write("pm grant $packageName android.permission.SYSTEM_ALERT_WINDOW\\nexit\\n".toByteArray())
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
            val cmd = if (displayId > 0) "screencap -d $displayId -p\\n" else "screencap -p\\n"
            val process = Runtime.getRuntime().exec("su")
            val outputStream = process.outputStream
            outputStream.write(cmd.toByteArray())
            outputStream.write("exit\\n".toByteArray())
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
""")
print(f"  + Đã tạo: {root_helper_path}")

# 3. Tạo TtsManager.kt
tts_mgr_path = "app/src/main/java/com/playtranslate/tts/TtsManager.kt"
os.makedirs(os.path.dirname(tts_mgr_path), exist_ok=True)
with open(tts_mgr_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.tts

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.Voice
import android.util.Log
import com.playtranslate.Prefs
import java.util.Locale

class TtsManager private constructor(private val context: Context) {

    private var tts: TextToSpeech? = null
    private var isInitialized = false
    private var lastSpokenText: String? = null

    init {
        initTts()
    }

    fun initTts(customEnginePkg: String? = null) {
        val prefs = Prefs(context)
        val engine = customEnginePkg ?: prefs.ttsEnginePackage.takeIf { it.isNotBlank() }
        isInitialized = false
        tts?.stop()
        tts?.shutdown()

        val initListener = TextToSpeech.OnInitListener { status ->
            if (status == TextToSpeech.SUCCESS) {
                isInitialized = true
                applySettings()
                Log.i(TAG, "TTS initialized with engine: $engine")
            } else {
                Log.e(TAG, "TTS initialization failed: $status")
            }
        }

        tts = if (!engine.isNullOrBlank()) {
            TextToSpeech(context.applicationContext, initListener, engine)
        } else {
            TextToSpeech(context.applicationContext, initListener)
        }
    }

    fun applySettings() {
        val engineInstance = tts ?: return
        if (!isInitialized) return
        val prefs = Prefs(context)
        engineInstance.setSpeechRate(prefs.ttsSpeechRate.coerceIn(0.5f, 2.5f))

        val targetLang = prefs.targetLang
        val loc = Locale.forLanguageTag(targetLang)
        try {
            engineInstance.language = loc
        } catch (_: Exception) {}

        val savedVoice = prefs.ttsVoiceName
        if (savedVoice.isNotBlank()) {
            try {
                val match = engineInstance.voices?.firstOrNull { it.name == savedVoice }
                if (match != null) engineInstance.voice = match
            } catch (_: Exception) {}
        }
    }

    fun getAvailableEngines(): List<TextToSpeech.EngineInfo> {
        return tts?.engines ?: emptyList()
    }

    fun getAvailableVoices(): List<Voice> {
        return try {
            val engineInstance = tts ?: return emptyList()
            val prefs = Prefs(context)
            val targetLocale = Locale.forLanguageTag(prefs.targetLang)
            engineInstance.voices
                ?.filter { it.locale.language == targetLocale.language }
                ?.sortedBy { it.name }
                ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun speak(text: String, force: Boolean = false) {
        if (text.isBlank()) return
        if (!force && text == lastSpokenText) return
        lastSpokenText = text

        val engineInstance = tts
        if (engineInstance != null && isInitialized) {
            applySettings()
            engineInstance.speak(text, TextToSpeech.QUEUE_FLUSH, null, "PLAY_TRANSLATE_TTS")
        }
    }

    fun stop() {
        lastSpokenText = null
        tts?.stop()
    }

    companion object {
        private const val TAG = "TtsManager"
        @Volatile private var instance: TtsManager? = null

        fun getInstance(context: Context): TtsManager =
            instance ?: synchronized(this) {
                instance ?: TtsManager(context.applicationContext).also { instance = it }
            }
    }
}
""")
print(f"  + Đã tạo: {tts_mgr_path}")

# 4. Sửa AndroidManifest.xml
manifest_path = "app/src/main/AndroidManifest.xml"
if os.path.exists(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "android.permission.SYSTEM_ALERT_WINDOW" not in content:
        content = content.replace(
            '<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />',
            '<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />\n    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />'
        )
    if "android.intent.action.TTS_SERVICE" not in content:
        content = content.replace(
            '<package android:name="com.ichi2.anki" />',
            '<package android:name="com.ichi2.anki" />\n        <intent>\n            <action android:name="android.intent.action.TTS_SERVICE" />\n        </intent>'
        )
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  * Đã cập nhật: {manifest_path}")

# 5. Sửa Prefs.kt
prefs_path = "app/src/main/java/com/playtranslate/Prefs.kt"
if os.path.exists(prefs_path):
    with open(prefs_path, "r", encoding="utf-8") as f:
        content = f.read()

    tts_props = """
    // ── Root Mode ────────────────────────────────────────────────────────
    var useRootMode: Boolean
        get() = sp.getBoolean(KEY_USE_ROOT_MODE, false)
        set(v) = sp.edit().putBoolean(KEY_USE_ROOT_MODE, v).apply()

    // ── Inspect Mode (Tap translation box for details) ───────────────────
    var inspectModeEnabled: Boolean
        get() = sp.getBoolean(KEY_INSPECT_MODE_ENABLED, false)
        set(v) = sp.edit().putBoolean(KEY_INSPECT_MODE_ENABLED, v).apply()

    // ── Text-To-Speech (TTS) ─────────────────────────────────────────────
    var ttsAutoSpeakEnabled: Boolean
        get() = sp.getBoolean(KEY_TTS_AUTO_SPEAK, false)
        set(v) = sp.edit().putBoolean(KEY_TTS_AUTO_SPEAK, v).apply()

    var ttsEnginePackage: String
        get() = sp.getString(KEY_TTS_ENGINE_PKG, "") ?: ""
        set(v) = sp.edit().putString(KEY_TTS_ENGINE_PKG, v).apply()

    var ttsVoiceName: String
        get() = sp.getString(KEY_TTS_VOICE_NAME, "") ?: ""
        set(v) = sp.edit().putString(KEY_TTS_VOICE_NAME, v).apply()

    var ttsSpeechRate: Float
        get() = sp.getFloat(KEY_TTS_SPEECH_RATE, 1.0f)
        set(v) = sp.edit().putFloat(KEY_TTS_SPEECH_RATE, v).apply()

    // ── TTS Zone ─────────────────────────────────────────────────────────
    fun getTtsZone(): RegionEntry {
        val json = sp.getString(KEY_TTS_ZONE, null) ?: return DEFAULT_TTS_ZONE
        return try {
            val o = JSONObject(json)
            RegionEntry(
                label = o.optString("label", "TTS Zone"),
                top = o.getDouble("top").toFloat(),
                bottom = o.getDouble("bottom").toFloat(),
                left = o.optDouble("left", 0.0).toFloat(),
                right = o.optDouble("right", 1.0).toFloat(),
                id = o.optString("id", "tts_zone_default")
            )
        } catch (_: Exception) {
            DEFAULT_TTS_ZONE
        }
    }

    fun setTtsZone(zone: RegionEntry) {
        val o = JSONObject().apply {
            put("label", "TTS Zone")
            put("top", zone.top.toDouble())
            put("bottom", zone.bottom.toDouble())
            put("left", zone.left.toDouble())
            put("right", zone.right.toDouble())
            put("id", zone.id)
        }
        sp.edit().putString(KEY_TTS_ZONE, o.toString()).apply()
    }
"""
    target_anchor = "set(v) = sp.edit().putString(KEY_TARGET_LANG, v).apply()\n"
    if "useRootMode" not in content and target_anchor in content:
        content = content.replace(target_anchor, target_anchor + tts_props)

    keys_insert = """
        private const val KEY_USE_ROOT_MODE = "use_root_mode"
        private const val KEY_INSPECT_MODE_ENABLED = "inspect_mode_enabled"
        private const val KEY_TTS_AUTO_SPEAK = "tts_auto_speak"
        private const val KEY_TTS_ENGINE_PKG = "tts_engine_pkg"
        private const val KEY_TTS_VOICE_NAME = "tts_voice_name"
        private const val KEY_TTS_SPEECH_RATE = "tts_speech_rate"
        private const val KEY_TTS_ZONE = "tts_zone"
        val DEFAULT_TTS_ZONE = RegionEntry("TTS Zone", 0.00f, 1.00f, 0.00f, 1.00f, id = "tts_zone_default")
"""
    key_anchor = 'private const val KEY_SELECTED_REGION_BY_DISPLAY = "selected_region_by_display"\n'
    if "KEY_USE_ROOT_MODE" not in content and key_anchor in content:
        content = content.replace(key_anchor, key_anchor + keys_insert)

    with open(prefs_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  * Đã cập nhật: {prefs_path}")

# 6. Sửa CaptureService.kt
capture_path = "app/src/main/java/com/playtranslate/CaptureService.kt"
if os.path.exists(capture_path):
    with open(capture_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_capture = """    internal suspend fun captureScreen(displayId: Int): Bitmap? {
        val mgr = PlayTranslateAccessibilityService.instance?.screenshotManager
        return mgr?.requestClean(displayId)
    }"""
    new_capture = """    internal suspend fun captureScreen(displayId: Int): Bitmap? {
        val prefs = Prefs(this)
        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            return com.playtranslate.root.RootHelper.captureScreenRoot(displayId)
        }
        val mgr = PlayTranslateAccessibilityService.instance?.screenshotManager
        return mgr?.requestClean(displayId)
    }"""
    if old_capture in content:
        content = content.replace(old_capture, new_capture)

    tts_speak_block = """
        // Lọc đọc TTS theo vùng TTS Zone
        val prefs = Prefs(this)
        if (prefs.ttsAutoSpeakEnabled) {
            val ttsZone = prefs.getTtsZone()
            val displayW = (ocrResult.groupBounds.maxOfOrNull { it.right } ?: 1000).toFloat()
            val displayH = (ocrResult.groupBounds.maxOfOrNull { it.bottom } ?: 1000).toFloat()
            val zoneRect = Rect(
                (ttsZone.left * displayW).toInt(),
                (ttsZone.top * displayH).toInt(),
                (ttsZone.right * displayW).toInt(),
                (ttsZone.bottom * displayH).toInt()
            )
            val eligibleTexts = ocrResult.groupBounds.indices.filter { idx ->
                Rect.intersects(ocrResult.groupBounds[idx], zoneRect)
            }.mapNotNull { perGroup.getOrNull(it)?.first }
            if (eligibleTexts.isNotEmpty()) {
                com.playtranslate.tts.TtsManager.getInstance(this).speak(eligibleTexts.joinToString(". "))
            }
        }
"""
    emit_anchor = "emitResult(\n            com.playtranslate.model.TranslationResult("
    if "ttsAutoSpeakEnabled" not in content and emit_anchor in content:
        content = content.replace(emit_anchor, tts_speak_block + "\n        " + emit_anchor)

    with open(capture_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  * Đã cập nhật: {capture_path}")

# 7. Sửa PlayTranslateAccessibilityService.kt
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
if os.path.exists(a11y_path):
    with open(a11y_path, "r", encoding="utf-8") as f:
        content = f.read()

    old_view_setup = """        val view = TranslationOverlayView(themedCtx, pinholeMode = pinholeMode).apply {
            setBoxes(boxes, cropLeft, cropTop, screenshotW, screenshotH)
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }"""

    new_view_setup = """        val view = TranslationOverlayView(themedCtx, pinholeMode = pinholeMode).apply {
            setBoxes(boxes, cropLeft, cropTop, screenshotW, screenshotH)
            onBoxClicked = { box ->
                val intent = Intent(this@PlayTranslateAccessibilityService, com.playtranslate.ui.WordAnkiReviewActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    putExtra(com.playtranslate.ui.WordAnkiReviewActivity.EXTRA_WORD, box.sourceText)
                    putExtra(com.playtranslate.ui.WordAnkiReviewActivity.EXTRA_DEFINITION, box.translatedText)
                }
                startActivity(intent)
            }
        }
        val isInspect = Prefs(this).inspectModeEnabled
        val baseFlags = if (isInspect) {
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        } else {
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        }
        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            baseFlags,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }"""
    if old_view_setup in content:
        content = content.replace(old_view_setup, new_view_setup)

    menu_wiring_anchor = "menu.onCaptureRegion = {"
    new_menu_wiring = """menu.onToggleInspectMode = {
            val p = Prefs(this)
            p.inspectModeEnabled = !p.inspectModeEnabled
            dismissFloatingMenu()
            hideTranslationOverlay()
            CaptureService.instance?.refreshLiveOverlay()
        }
        menu.onSetTtsZone = {
            dismissFloatingMenu()
            showRegionDragOverlay(display, Prefs(this).getTtsZone()) { zone ->
                Prefs(this).setTtsZone(zone)
            }
        }
        menu.onCaptureRegion = {"""
    if "onToggleInspectMode" not in content and menu_wiring_anchor in content:
        content = content.replace(menu_wiring_anchor, new_menu_wiring)

    with open(a11y_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  * Đã cập nhật: {a11y_path}")

# 8. Sửa TranslationOverlayView.kt
overlay_view_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"
if os.path.exists(overlay_view_path):
    with open(overlay_view_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "var onBoxClicked" not in content:
        content = content.replace(
            "val pinholeMode: Boolean = false,\n) : FrameLayout(context) {",
            "val pinholeMode: Boolean = false,\n) : FrameLayout(context) {\n\n    var onBoxClicked: ((TextBox) -> Unit)? = null"
        )
    old_child_tag = "child.setTag(R.id.tag_bg_color, box.bgColor)"
    new_child_tag = """if (Prefs(context).inspectModeEnabled && box.translatedText.isNotEmpty()) {
                    child.isClickable = true
                    child.isFocusable = true
                    child.setOnClickListener {
                        onBoxClicked?.invoke(box)
                    }
                }
                child.setTag(R.id.tag_bg_color, box.bgColor)"""
    if old_child_tag in content and "inspectModeEnabled" not in content:
        content = content.replace(old_child_tag, new_child_tag)

    with open(overlay_view_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  * Đã cập nhật: {overlay_view_path}")

# 9. Sửa FloatingIconMenu.kt
menu_path = "app/src/main/java/com/playtranslate/ui/FloatingIconMenu.kt"
if os.path.exists(menu_path):
    with open(menu_path, "r", encoding="utf-8") as f:
        content = f.read()

    callbacks_anchor = "var onCaptureRegion: (() -> Unit)? = null\n"
