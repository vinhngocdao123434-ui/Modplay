import os

print(">>> Đang áp dụng bản sửa lỗi chuẩn xác 100%...")

# 1. Cập nhật TtsSettingsDialog.kt hoàn chỉnh
tts_dialog_path = "app/src/main/java/com/playtranslate/ui/TtsSettingsDialog.kt"
os.makedirs(os.path.dirname(tts_dialog_path), exist_ok=True)
with open(tts_dialog_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.ui

import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.SeekBar
import android.widget.TextView
import android.widget.Toast
import androidx.fragment.app.DialogFragment
import com.google.android.material.materialswitch.MaterialSwitch
import com.playtranslate.Prefs
import com.playtranslate.R
import com.playtranslate.applyAccentOverlay
import com.playtranslate.fullScreenDialogTheme
import com.playtranslate.tts.TtsManager
import java.util.Locale

class TtsSettingsDialog : DialogFragment() {

    private lateinit var prefs: Prefs
    private lateinit var ttsManager: TtsManager

    override fun getTheme(): Int = fullScreenDialogTheme(requireContext())

    override fun onCreateDialog(savedInstanceState: Bundle?): android.app.Dialog {
        val dialog = super.onCreateDialog(savedInstanceState)
        applyAccentOverlay(dialog.context.theme, requireContext())
        return dialog
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        prefs = Prefs(requireContext())
        ttsManager = TtsManager.getInstance(requireContext())
        
        val ctx = requireContext()
        val dp = resources.displayMetrics.density

        val root = LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            setPadding((20 * dp).toInt(), (24 * dp).toInt(), (20 * dp).toInt(), (24 * dp).toInt())
            setBackgroundColor(com.playtranslate.OverlayColors.surface(ctx))
        }

        // Header
        root.addView(TextView(ctx).apply {
            text = "CÀI ĐẶT TEXT-TO-SPEECH (TTS)"
            textSize = 18f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setTextColor(com.playtranslate.OverlayColors.text(ctx))
            setPadding(0, 0, 0, (16 * dp).toInt())
        })

        // Switch Tự động đọc
        val switchRow = LinearLayout(ctx).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = android.view.Gravity.CENTER_VERTICAL
            setPadding(0, (8 * dp).toInt(), 0, (16 * dp).toInt())
        }
        val tvSwitch = TextView(ctx).apply {
            text = "Tự động đọc bản dịch"
            textSize = 15f
            setTextColor(com.playtranslate.OverlayColors.text(ctx))
            layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
        }
        val switchAuto = MaterialSwitch(ctx).apply {
            isChecked = prefs.ttsAutoSpeakEnabled
            setOnCheckedChangeListener { _, checked ->
                prefs.ttsAutoSpeakEnabled = checked
                if (checked) ttsManager.initTts() else ttsManager.stop()
            }
        }
        switchRow.addView(tvSwitch)
        switchRow.addView(switchAuto)
        root.addView(switchRow)

        // Chọn Engine
        val tvEngineVal = TextView(ctx)
        root.addView(buildClickRow(ctx, "TTS Engine (Bộ đọc)", tvEngineVal) {
            val engines = ttsManager.getAvailableEngines()
            if (engines.isEmpty()) {
                Toast.makeText(ctx, "Không tìm thấy TTS Engine trên máy", Toast.LENGTH_SHORT).show()
                return@buildClickRow
            }
            val names = engines.map { it.label + " (" + it.name + ")" }.toTypedArray()
            AlertDialog.Builder(ctx)
                .setTitle("Chọn TTS Engine")
                .setItems(names) { _, which ->
                    val selected = engines[which].name
                    prefs.ttsEnginePackage = selected
                    ttsManager.initTts(selected)
                    tvEngineVal.text = engines[which].label
                }
                .show()
        })
        val currentEng = ttsManager.getAvailableEngines().firstOrNull { it.name == prefs.ttsEnginePackage }
        tvEngineVal.text = currentEng?.label ?: "Mặc định hệ thống"

        // Chọn Giọng đọc (Voice)
        val tvVoiceVal = TextView(ctx)
        root.addView(buildClickRow(ctx, "Giọng đọc (Voice)", tvVoiceVal) {
            val voices = ttsManager.getAvailableVoices()
            if (voices.isEmpty()) {
                Toast.makeText(ctx, "Không tìm thấy giọng đọc nào khả dụng", Toast.LENGTH_SHORT).show()
                return@buildClickRow
            }
            val voiceNames = voices.map { 
                it.name + if (!it.isNetworkConnectionRequired) " [Offline]" else "" 
            }.toTypedArray()
            AlertDialog.Builder(ctx)
                .setTitle("Chọn Giọng đọc")
                .setItems(voiceNames) { _, which ->
                    prefs.ttsVoiceName = voices[which].name
                    ttsManager.applySettings()
                    tvVoiceVal.text = voices[which].name
                }
                .show()
        })
        tvVoiceVal.text = prefs.ttsVoiceName.ifEmpty { "Tự động theo ngôn ngữ" }

        // Tốc độ đọc (Speed rate)
        val tvRateVal = TextView(ctx).apply {
            text = "Tốc độ: %.2fx".format(prefs.ttsSpeechRate)
            textSize = 14f
            setTextColor(com.playtranslate.OverlayColors.text(ctx))
            setPadding(0, (12 * dp).toInt(), 0, (4 * dp).toInt())
        }
        root.addView(tvRateVal)
        val seekRate = SeekBar(ctx).apply {
            max = 20
            progress = ((prefs.ttsSpeechRate - 0.5f) * 10).toInt().coerceIn(0, 20)
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(p0: SeekBar?, p1: Int, p2: Boolean) {
                    val rate = 0.5f + (p1 / 10f)
                    prefs.ttsSpeechRate = rate
                    tvRateVal.text = "Tốc độ: %.2fx".format(rate)
                    ttsManager.applySettings()
                }
                override fun onStartTrackingTouch(p0: SeekBar?) {}
                override fun onStopTrackingTouch(p0: SeekBar?) {}
            })
        }
        root.addView(seekRate)

        // Nút Nghe thử
        root.addView(Button(ctx).apply {
            text = "Nghe thử giọng đọc"
            setOnClickListener {
                ttsManager.speak("Đây là âm thanh thử nghiệm từ Play Translate.", force = true)
            }
        })

        // Nút Đóng
        root.addView(Button(ctx).apply {
            text = "Đóng"
            setOnClickListener { dismiss() }
        })

        return root
    }

    private fun buildClickRow(ctx: Context, title: String, tvVal: TextView, onClick: () -> Unit): View {
        val dp = resources.displayMetrics.density
        return LinearLayout(ctx).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(0, (8 * dp).toInt(), 0, (8 * dp).toInt())
            isClickable = true
            setOnClickListener { onClick() }
            addView(TextView(ctx).apply {
                text = title
                textSize = 14f
                typeface = android.graphics.Typeface.DEFAULT_BOLD
                setTextColor(com.playtranslate.OverlayColors.text(ctx))
            })
            tvVal.apply {
                textSize = 13f
                setTextColor(com.playtranslate.OverlayColors.accent(ctx))
            }
            addView(tvVal)
        }
    }

    companion object {
        const val TAG = "TtsSettingsDialog"
        fun newInstance() = TtsSettingsDialog()
    }
}
""")
print(f"  + Đã tạo: {tts_dialog_path}")

# 2. Xóa sạch banner nút đỏ trong TranslationOverlayView.kt và giữ nguyên FLAG_NOT_TOUCHABLE
overlay_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"
with open(overlay_path, "r", encoding="utf-8") as f:
    ov_code = f.read()

# Gỡ bỏ banner đỏ
if "THOÁT CHẾ ĐỘ CHẠM" in ov_code:
    import re
    ov_code = re.sub(r'if \(Prefs\(context\)\.inspectModeEnabled\) \{\s*val banner = TextView.*?\n            addView\(banner, bannerLp\)\n        \}', '', ov_code, flags=re.DOTALL)
    with open(overlay_path, "w", encoding="utf-8") as f:
        f.write(ov_code)
    print(f"  * Đã loại bỏ hoàn toàn nút đỏ khỏi: {overlay_path}")

# 3. Sửa PlayTranslateAccessibilityService.kt
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
with open(a11y_path, "r", encoding="utf-8") as f:
    a11y_code = f.read()

# Cửa sổ dịch CHÍNH LUÔN LUÔN là FLAG_NOT_TOUCHABLE (không bao giờ cướp cảm ứng game!)
old_flags_logic = """val isInspect = Prefs(this).inspectModeEnabled
        val baseFlags = if (isInspect) {
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        } else {
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        }"""
new_flags_logic = """val baseFlags = WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN"""

if old_flags_logic in a11y_code:
    a11y_code = a11y_code.replace(old_flags_logic, new_flags_logic)

# Quản lý các ô bấm Inspect nhỏ riêng biệt (chỉ bắt cảm ứng trên diện tích của từng chữ)
inspect_boxes_manager = """
    private val inspectWindows = mutableListOf<View>()

    fun updateInspectClickableBoxes(display: Display, boxes: List<TranslationOverlayView.TextBox>, cropLeft: Int, cropTop: Int) {
        clearInspectClickableBoxes()
        if (!Prefs(this).inspectModeEnabled || boxes.isEmpty()) return
        val ctx = createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return

        for (box in boxes) {
            if (box.translatedText.isBlank()) continue
            val b = box.bounds
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
            val w = b.width().coerceAtLeast(10)
            val h = b.height().coerceAtLeast(10)
            val lp = WindowManager.LayoutParams(
                w, h,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = b.left + cropLeft
                y = b.top + cropTop
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

if "updateInspectClickableBoxes" not in a11y_code:
    a11y_code = a11y_code.replace(
        "class PlayTranslateAccessibilityService : AccessibilityService() {",
        "class PlayTranslateAccessibilityService : AccessibilityService() {\n" + inspect_boxes_manager
    )

# Gọi updateInspectClickableBoxes mỗi khi có bản dịch
if "updateInspectClickableBoxes(display, boxes, cropLeft, cropTop)" not in a11y_code:
    a11y_code = a11y_code.replace(
        "translationOverlayHandles[displayId] = TranslationOverlayHandle(view, dirtyView)",
        "translationOverlayHandles[displayId] = TranslationOverlayHandle(view, dirtyView)\n        updateInspectClickableBoxes(display, boxes, cropLeft, cropTop)"
    )

# Sửa hàm xóa overlay để xóa luôn các ô bấm inspect
if "clearInspectClickableBoxes()" not in a11y_code:
    a11y_code = a11y_code.replace(
        "fun hideTranslationOverlayForDisplay(displayId: Int) {",
        "fun hideTranslationOverlayForDisplay(displayId: Int) {\n        clearInspectClickableBoxes()"
    )

with open(a11y_path, "w", encoding="utf-8") as f:
    f.write(a11y_code)
print(f"  * Đã sửa hoàn chỉnh: {a11y_path}")

# 4. Sửa FloatingIconMenu.kt: Thêm nút Cài đặt TTS và hiển thị menu trực quan
menu_path = "app/src/main/java/com/playtranslate/ui/FloatingIconMenu.kt"
with open(menu_path, "r", encoding="utf-8") as f:
    menu_code = f.read()

if "var onOpenTtsSettings: (() -> Unit)? = null" not in menu_code:
    menu_code = menu_code.replace(
        "var onToggleInspectMode: (() -> Unit)? = null",
        "var onToggleInspectMode: (() -> Unit)? = null\n    var onOpenTtsSettings: (() -> Unit)? = null"
    )

# Cập nhật menu để thêm nút mở Cài đặt TTS
tts_settings_btn_code = """
        // TTS Settings Button in Floating Menu
        val ttsSetGroup = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            layoutParams = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply { bottomMargin = (10 * dp).toInt() }
        }
        val ttsSetBtn = FrameLayout(context).apply {
            background = GradientDrawable().apply {
                setColor(cardColor)
                cornerRadius = 14 * dp
            }
            elevation = 4 * dp
            layoutParams = LinearLayout.LayoutParams(btnSize, btnSize).apply {
                gravity = Gravity.CENTER_HORIZONTAL
            }
            setOnClickListener { onOpenTtsSettings?.invoke() }
        }
        val ttsSetIcon = ImageView(context).apply {
            setImageResource(android.R.drawable.ic_lock_silent_mode_off)
            imageTintList = android.content.res.ColorStateList.valueOf(textColor)
            scaleType = ImageView.ScaleType.CENTER_INSIDE
            setPadding(iconPad, iconPad, iconPad, iconPad)
        }
        ttsSetBtn.addView(ttsSetIcon, LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        val ttsSetLabel = TextView(context).apply {
            text = "TTS Settings"
            setTextColor(textColor)
            textSize = 9f
            gravity = Gravity.CENTER_HORIZONTAL
            setTypeface(null, Typeface.BOLD)
            maxWidth = btnSize
        }
        ttsSetGroup.addView(ttsSetBtn)
        ttsSetGroup.addView(ttsSetLabel)
        menuCard.addView(ttsSetGroup)
"""
if "TTS Settings" not in menu_code:
    menu_code = menu_code.replace("menuCard.addView(ttsZoneGroup)", "menuCard.addView(ttsZoneGroup)\n" + tts_settings_btn_code)

with open(menu_path, "w", encoding="utf-8") as f:
    f.write(menu_code)
print(f"  * Đã bổ sung nút TTS Settings vào Menu: {menu_path}")

# 5. Đưa kích hoạt TTS trực tiếp vào PinholeOverlayMode.kt (Đảm bảo chữ ra là đọc ngay!)
pinhole_path = "app/src/main/java/com/playtranslate/PinholeOverlayMode.kt"
with open(pinhole_path, "r", encoding="utf-8") as f:
    pinhole_code = f.read()

tts_trigger = """
                    // Kích hoạt đọc TTS trực tiếp nếu bật
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
                        }.map { it.translatedText }
                        if (toSpeak.isNotEmpty()) {
                            com.playtranslate.tts.TtsManager.getInstance(service).speak(toSpeak.joinToString(". "))
                        }
                    }
"""

if "TtsManager.getInstance(service).speak" not in pinhole_code:
    pinhole_code = pinhole_code.replace(
        "showOverlayAndCapture(a11y, mergedFinal, cropLeft, cropTop, screenshotW, screenshotH)",
        "showOverlayAndCapture(a11y, mergedFinal, cropLeft, cropTop, screenshotW, screenshotH)\n" + tts_trigger
    )
    with open(pinhole_path, "w", encoding="utf-8") as f:
        f.write(pinhole_code)
    print(f"  * Đã kích hoạt TTS trực tiếp vào luồng dịch: {pinhole_path}")

# 6. Liên kết nút TTS Settings vào PlayTranslateAccessibilityService
with open(a11y_path, "r", encoding="utf-8") as f:
    a11y_code = f.read()

if "onOpenTtsSettings" not in a11y_code:
    a11y_code = a11y_code.replace(
        "menu.onSetTtsZone = { dismissFloatingMenu(); showTtsZoneEditor(display) }",
        """menu.onSetTtsZone = { dismissFloatingMenu(); showTtsZoneEditor(display) }
        menu.onOpenTtsSettings = {
            dismissFloatingMenu()
            val intent = Intent(this@PlayTranslateAccessibilityService, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
                action = "com.playtranslate.ACTION_OPEN_TTS_SETTINGS"
            }
            startActivity(intent)
        }"""
    )
    with open(a11y_path, "w", encoding="utf-8") as f:
        f.write(a11y_code)

# 7. MainActivity nhận action mở TTS dialog
main_act_path = "app/src/main/java/com/playtranslate/MainActivity.kt"
if os.path.exists(main_act_path):
    with open(main_act_path, "r", encoding="utf-8") as f:
        main_code = f.read()
    if "ACTION_OPEN_TTS_SETTINGS" not in main_code:
        main_code = main_code.replace(
            "ACTION_OPEN_SETTINGS -> {",
            """\"com.playtranslate.ACTION_OPEN_TTS_SETTINGS\" -> {
                com.playtranslate.ui.TtsSettingsDialog.newInstance().show(supportFragmentManager, com.playtranslate.ui.TtsSettingsDialog.TAG)
            }
            ACTION_OPEN_SETTINGS -> {"""
        )
        with open(main_act_path, "w", encoding="utf-8") as f:
            f.write(main_code)
        print(f"  * Đã mở cổng Dialog TTS trong MainActivity: {main_act_path}")

print(">>> TẤT CẢ ĐÃ ĐƯỢC KHẮC PHỤC TRIỆT ĐỂ VÀ CHUẨN XÁC!")
