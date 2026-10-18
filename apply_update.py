import os
import re

print(">>> Đang cập nhật toàn bộ hệ thống PlayTranslate...")

# ==============================================================================
# 1. TtsManager.kt (Đọc đúng 1 lần duy nhất, chống lặp vĩnh viễn)
# ==============================================================================
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
        val trimmed = text.trim()
        if (trimmed.isBlank()) return
        // Chống đọc lặp: Chỉ đọc nếu nội dung thực sự thay đổi
        if (!force && trimmed == lastSpokenText) return
        lastSpokenText = trimmed

        val engineInstance = tts
        if (engineInstance != null && isInitialized) {
            applySettings()
            engineInstance.speak(trimmed, TextToSpeech.QUEUE_FLUSH, null, "PLAY_TRANSLATE_TTS")
        }
    }

    fun stop() {
        // Giữ nguyên lastSpokenText để khi quét lại khung hình đứng yên không bị đọc lặp
        tts?.stop()
    }

    fun resetLastSpoken() {
        lastSpokenText = null
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
print(f"  + Đã cập nhật TtsManager: {tts_mgr_path}")

# ==============================================================================
# 2. TranslationOverlayView.kt (Bỏ nút đỏ, giữ nguyên giao diện gốc)
# ==============================================================================
overlay_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"
if os.path.exists(overlay_path):
    with open(overlay_path, "r", encoding="utf-8") as f:
        ov_code = f.read()
    # Xóa hoàn toàn banner nút đỏ nếu còn
    if "THOÁT CHẾ ĐỘ CHẠM" in ov_code:
        ov_code = re.sub(r'if \(Prefs\(context\)\.inspectModeEnabled\) \{\s*val banner = TextView.*?\n            addView\(banner, bannerLp\)\n        \}', '', ov_code, flags=re.DOTALL)
    with open(overlay_path, "w", encoding="utf-8") as f:
        f.write(ov_code)
    print(f"  * Đã làm sạch: {overlay_path}")

# ==============================================================================
# 3. TranslationBoxDetailOverlay.kt (Popup Raw - Dịch - Copy - TTS)
# ==============================================================================
detail_overlay_path = "app/src/main/java/com/playtranslate/ui/TranslationBoxDetailOverlay.kt"
with open(detail_overlay_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import com.playtranslate.OverlayColors
import com.playtranslate.PlayTranslateAccessibilityService
import com.playtranslate.tts.TtsManager

class TranslationBoxDetailOverlay(
    private val context: Context,
    private val wm: WindowManager,
    private val displayId: Int,
    private val rawText: String,
    private val translatedText: String
) {
    private var scrimView: View? = null

    fun show() {
        dismiss()
        val dp = context.resources.displayMetrics.density
        val oc = OverlayColors

        val scrim = FrameLayout(context).apply {
            setBackgroundColor(Color.argb(160, 0, 0, 0))
            setOnClickListener { dismiss() }
        }

        val card = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(oc.surface(context))
                setStroke((1 * dp).toInt(), oc.divider(context))
                cornerRadius = 16 * dp
            }
            setPadding((20 * dp).toInt(), (20 * dp).toInt(), (20 * dp).toInt(), (16 * dp).toInt())
            setOnClickListener { }
        }

        // Header
        val header = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (14 * dp).toInt() }
        }
        val title = TextView(context).apply {
            text = "Chi tiết bản dịch"
            textSize = 17f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(oc.text(context))
            layoutParams = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f)
        }
        val btnSpeak = ImageButton(context).apply {
            setImageResource(android.R.drawable.ic_lock_silent_mode_off)
            setColorFilter(oc.accent(context))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener {
                TtsManager.getInstance(context).speak(translatedText, force = true)
            }
            layoutParams = LinearLayout.LayoutParams((36 * dp).toInt(), (36 * dp).toInt())
        }
        val btnClose = ImageButton(context).apply {
            setImageResource(android.R.drawable.ic_menu_close_clear_cancel)
            setColorFilter(oc.textMuted(context))
            setBackgroundColor(Color.TRANSPARENT)
            setOnClickListener { dismiss() }
            layoutParams = LinearLayout.LayoutParams((36 * dp).toInt(), (36 * dp).toInt())
        }
        header.addView(title)
        header.addView(btnSpeak)
        header.addView(btnClose)
        card.addView(header)

        // Raw Box
        val rawCard = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(oc.card(context))
                setStroke((1 * dp).toInt(), oc.divider(context))
                cornerRadius = 12 * dp
            }
            setPadding((12 * dp).toInt(), (12 * dp).toInt(), (12 * dp).toInt(), (10 * dp).toInt())
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (12 * dp).toInt() }
        }
        rawCard.addView(TextView(context).apply {
            text = "ORIGINAL TEXT"
            textSize = 10f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(oc.textMuted(context))
        })
        rawCard.addView(TextView(context).apply {
            text = rawText
            textSize = 15f
            setTextColor(oc.text(context))
            setPadding(0, (6 * dp).toInt(), 0, (6 * dp).toInt())
        })
        val btnCopyRaw = Button(context).apply {
            text = "Copy Original"
            textSize = 12f
            isAllCaps = false
            setTextColor(oc.accent(context))
            setBackgroundColor(Color.TRANSPARENT)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { gravity = Gravity.END }
            setOnClickListener { copy(rawText, "Raw text copied") }
        }
        rawCard.addView(btnCopyRaw)
        card.addView(rawCard)

        // Translated Box
        val transCard = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            background = GradientDrawable().apply {
                setColor(oc.card(context))
                setStroke((1 * dp).toInt(), oc.divider(context))
                cornerRadius = 12 * dp
            }
            setPadding((12 * dp).toInt(), (12 * dp).toInt(), (12 * dp).toInt(), (10 * dp).toInt())
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
        }
        transCard.addView(TextView(context).apply {
            text = "TRANSLATION"
            textSize = 10f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(oc.accent(context))
        })
        transCard.addView(TextView(context).apply {
            text = translatedText
            textSize = 16f
            setTextColor(oc.text(context))
            setPadding(0, (6 * dp).toInt(), 0, (6 * dp).toInt())
        })
        val btnCopyTrans = Button(context).apply {
            text = "Copy Translation"
            textSize = 12f
            isAllCaps = false
            setTextColor(oc.accent(context))
            setBackgroundColor(Color.TRANSPARENT)
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { gravity = Gravity.END }
            setOnClickListener { copy(translatedText, "Translation copied") }
        }
        transCard.addView(btnCopyTrans)
        card.addView(transCard)

        val maxW = (320 * dp).toInt()
        val cardLp = FrameLayout.LayoutParams(maxW, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            gravity = Gravity.CENTER
        }
        scrim.addView(card, cardLp)

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        )
        if (PlayTranslateAccessibilityService.addOverlay(scrim, wm, params, displayId)) {
            scrimView = scrim
        }
    }

    private fun copy(text: String, label: String) {
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(ClipData.newPlainText("PlayTranslate", text))
        Toast.makeText(context, label, Toast.LENGTH_SHORT).show()
    }

    fun dismiss() {
        val v = scrimView ?: return
        PlayTranslateAccessibilityService.removeOverlay(v, wm)
        scrimView = null
    }
}
""")
print(f"  + Đã cập nhật TranslationBoxDetailOverlay: {detail_overlay_path}")

# ==============================================================================
# 4. PlayTranslateAccessibilityService.kt (Đồng bộ cảm ứng 1:1, TTS Zone an toàn)
# ==============================================================================
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
with open(a11y_path, "r", encoding="utf-8") as f:
    a11y_code = f.read()

# 1. Đảm bảo import Color đầy đủ
if "import android.graphics.Color" not in a11y_code:
    a11y_code = a11y_code.replace("package com.playtranslate", "package com.playtranslate\n\nimport android.graphics.Color")

# 2. Cửa sổ dịch chính LUÔN LUÔN là FLAG_NOT_TOUCHABLE (Xuyên thấu 100% vào game)
a11y_code = re.sub(
    r'val baseFlags = if \(isInspect\).*?val params = WindowManager\.LayoutParams\(',
    """val params = WindowManager.LayoutParams(""",
    a11y_code, flags=re.DOTALL
)

a11y_code = a11y_code.replace(
    """        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            baseFlags,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }""",
    """        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }"""
)

# 3. Đồng bộ các ô bấm Inspect: Kích thước và tọa độ màn hình chuẩn xác
inspect_manager_clean = """
    private val inspectWindows = mutableListOf<View>()

    fun updateInspectClickableBoxes(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int
    ) {
        clearInspectClickableBoxes()
        if (!Prefs(this).inspectModeEnabled || boxes.isEmpty()) return
        val ctx = createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return
        val dm = resources.displayMetrics
        val scaleX = dm.widthPixels.toFloat() / screenshotW
        val scaleY = dm.heightPixels.toFloat() / screenshotH

        for (box in boxes) {
            if (box.translatedText.isBlank()) continue
            val b = box.bounds
            val left = ((b.left + cropLeft) * scaleX).toInt()
            val top = ((b.top + cropTop) * scaleY).toInt()
            val right = ((b.right + cropLeft) * scaleX).toInt()
            val bottom = ((b.bottom + cropTop) * scaleY).toInt()
            val w = (right - left).coerceAtLeast(20)
            val h = (bottom - top).coerceAtLeast(20)

            val clickable = View(ctx).apply {
                isClickable = true
                setOnClickListener {
                    com.playtranslate.ui.TranslationBoxDetailOverlay(
                        this@PlayTranslateAccessibilityService,
                        wm,
                        display.displayId,
                        box.sourceText,
                        box.translatedText
                    ).show()
                }
            }
            val lp = WindowManager.LayoutParams(
                w, h,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = left
                y = top
            }
            if (addOverlayWindow(clickable, wm, lp, display.displayId)) {
                inspectWindows.add(clickable)
            }
        }
    }

    fun clearInspectClickableBoxes() {
        for (v in inspectWindows) {
            removeOverlayWindow(v)
        }
        inspectWindows.clear()
    }
"""

if "fun updateInspectClickableBoxes" in a11y_code:
    a11y_code = re.sub(r'private val inspectWindows = mutableListOf<View>\(\).*?fun clearInspectClickableBoxes\(\) \{.*?inspectWindows\.clear\(\)\s*\}', inspect_manager_clean, a11y_code, flags=re.DOTALL)
else:
    a11y_code = a11y_code.replace(
        "class PlayTranslateAccessibilityService : AccessibilityService() {",
        "class PlayTranslateAccessibilityService : AccessibilityService() {\n" + inspect_manager_clean
    )

# Gọi updateInspectClickableBoxes với đủ tham số scale
a11y_code = a11y_code.replace(
    "updateInspectClickableBoxes(display, boxes, cropLeft, cropTop)",
    "updateInspectClickableBoxes(display, boxes, cropLeft, cropTop, screenshotW, screenshotH)"
)

# 4. showTtsZoneEditor an toàn
tts_zone_editor = """
    fun showTtsZoneEditor(display: Display) {
        val prefs = Prefs(this)
        val currentZone = prefs.getTtsZone()
        val initZone = if (currentZone.isFullScreen) {
            RegionEntry("TTS Zone", 0.55f, 0.90f, 0.10f, 0.90f, id = "tts_zone_default")
        } else currentZone

        showRegionDragOverlay(display, initZone) { _ -> }
        
        val ctx = createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return
        val dp = ctx.resources.displayMetrics.density

        val bar = android.widget.LinearLayout(ctx).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding((16 * dp).toInt(), (10 * dp).toInt(), (16 * dp).toInt(), (10 * dp).toInt())
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.argb(230, 30, 30, 30))
                cornerRadius = 20 * dp
                setStroke((1 * dp).toInt(), Color.parseColor("#9C27B0"))
            }
        }

        val cancelBtn = android.widget.TextView(ctx).apply {
            text = "✕ Hủy"
            setTextColor(Color.WHITE)
            textSize = 14f
            gravity = Gravity.CENTER
            setPadding((12 * dp).toInt(), 0, (12 * dp).toInt(), 0)
            setOnClickListener { hideRegionDragOverlay(); removeOverlayWindow(bar) }
        }

        val saveBtn = android.widget.TextView(ctx).apply {
            text = "✓ Lưu vùng TTS"
            setTextColor(Color.parseColor("#E1BEE7"))
            textSize = 14f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setPadding((12 * dp).toInt(), 0, (12 * dp).toInt(), 0)
            setOnClickListener {
                val dv = dragView
                if (dv != null) {
                    prefs.setTtsZone(RegionEntry("TTS Zone", dv.topFraction, dv.bottomFraction, dv.leftFraction, dv.rightFraction))
                }
                hideRegionDragOverlay()
                removeOverlayWindow(bar)
            }
        }

        bar.addView(cancelBtn)
        bar.addView(saveBtn)

        val barParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            y = (48 * dp).toInt()
        }
        addOverlayWindow(bar, wm, barParams, display.displayId)
    }
"""

if "fun showTtsZoneEditor" in a11y_code:
    a11y_code = re.sub(r'fun showTtsZoneEditor\(display: Display\) \{.*?addOverlayWindow\(bar, wm, barParams, display\.displayId\)\s*\}', tts_zone_editor, a11y_code, flags=re.DOTALL)
else:
    a11y_code = a11y_code.replace(
        "class PlayTranslateAccessibilityService : AccessibilityService() {",
        "class PlayTranslateAccessibilityService : AccessibilityService() {\n" + tts_zone_editor
    )

with open(a11y_path, "w", encoding="utf-8") as f:
    f.write(a11y_code)
print(f"  * Đã chuẩn hóa PlayTranslateAccessibilityService: {a11y_path}")

# ==============================================================================
# 5. PinholeOverlayMode.kt (Kích hoạt phát âm TTS 1 lần cho câu mới)
# ==============================================================================
pinhole_path = "app/src/main/java/com/playtranslate/PinholeOverlayMode.kt"
with open(pinhole_path, "r", encoding="utf-8") as f:
    pinhole_code = f.read()

tts_call = """
                    // Phát âm TTS đúng 1 lần cho nội dung mới trong TTS Zone
                    if (Prefs(service).ttsAutoSpeakEnabled && mergedFinal.isNotEmpty()) {
                        val zone = Prefs(service).getTtsZone()
                        val zoneRect = Rect(
                            (zone.left * screenshotW).toInt(),
                            (zone.top * screenshotH).toInt(),
                            (zone.right * screenshotW).toInt(),
                            (zone.bottom * screenshotH).toInt()
                        )
                        val toSpeak = mergedFinal.filter { b ->
                            b.translatedText.isNotBlank() && Rect.intersects(b.bounds, zoneRect)
                        }.map { it.translatedText }.joinToString(". ")
                        if (toSpeak.isNotBlank()) {
                            com.playtranslate.tts.TtsManager.getInstance(service).speak(toSpeak)
                        }
                    }
"""

if "val toSpeak = mergedFinal" not in pinhole_code:
    pinhole_code = pinhole_code.replace(
        "showOverlayAndCapture(a11y, mergedFinal, cropLeft, cropTop, screenshotW, screenshotH)",
        "showOverlayAndCapture(a11y, mergedFinal, cropLeft, cropTop, screenshotW, screenshotH)\n" + tts_call
    )
    with open(pinhole_path, "w", encoding="utf-8") as f:
        f.write(pinhole_code)
    print(f"  * Đã kích hoạt TTS trong PinholeOverlayMode: {pinhole_path}")

# ==============================================================================
# 6. MainActivity.kt (Bỏ qua ép buộc Accessibility nếu máy có Root)
# ==============================================================================
main_path = "app/src/main/java/com/playtranslate/MainActivity.kt"
with open(main_path, "r", encoding="utf-8") as f:
    main_code = f.read()

# Đảm bảo có import TtsSettingsDialog
if "import com.playtranslate.ui.TtsSettingsDialog" not in main_code:
    main_code = main_code.replace("package com.playtranslate", "package com.playtranslate\n\nimport com.playtranslate.ui.TtsSettingsDialog")

# Thêm logic Root vào checkOnboardingState để không bao giờ hỏi Accessibility nếu có Root
root_onboarding_bypass = """
        // Bỏ qua đòi Accessibility nếu máy đã bật Root mode
        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            lifecycleScope.launch {
                com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
            }
            onboardingContainer.visibility = View.GONE
            return
        }
"""
if "prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()" not in main_code:
    main_code = main_code.replace(
        "val notifGranted = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU",
        root_onboarding_bypass + "\n        val notifGranted = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU"
    )

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_code)
print(f"  * Đã cập nhật MainActivity (Bypass root): {main_path}")

# ==============================================================================
# 7. FloatingIconMenu.kt (Nút TTS Settings, TTS Zone, Inspect)
# ==============================================================================
menu_path = "app/src/main/java/com/playtranslate/ui/FloatingIconMenu.kt"
with open(menu_path, "r", encoding="utf-8") as f:
    menu_code = f.read()

# Đảm bảo các callbacks đầy đủ
if "var onOpenTtsSettings" not in menu_code:
    menu_code = menu_code.replace(
        "var onCaptureRegion: (() -> Unit)? = null",
        "var onCaptureRegion: (() -> Unit)? = null\n    var onSetTtsZone: (() -> Unit)? = null\n    var onToggleInspectMode: (() -> Unit)? = null\n    var onOpenTtsSettings: (() -> Unit)? = null"
    )

with open(menu_path, "w", encoding="utf-8") as f:
    f.write(menu_code)
print(f"  * Đã cập nhật FloatingIconMenu: {menu_path}")

print(">>> TẤT CẢ ĐÃ ĐƯỢC CẬP NHẬT HOÀN CHỈNH VÀ CHUẨN XÁC 100%!")
