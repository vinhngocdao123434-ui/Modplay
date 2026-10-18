import os

print(">>> Đang sửa chữa triệt để toàn bộ 4 vấn đề...")

# 1. Cập nhật TtsSettingsDialog.kt (Giao diện Cài đặt TTS đầy đủ)
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
        root.addView(buildClickRow(ctx, "TTS Engine", tvEngineVal) {
            val engines = ttsManager.getAvailableEngines()
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
                android.widget.Toast.makeText(ctx, "Không tìm thấy giọng đọc phù hợp", android.widget.Toast.LENGTH_SHORT).show()
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
        tvVoiceVal.text = prefs.ttsVoiceName.ifEmpty { "Tự động" }

        // Tốc độ đọc (Speed rate)
        val tvRateVal = TextView(ctx).apply {
            text = "Tốc độ: %.2fx".format(prefs.ttsSpeechRate)
            textSize = 14f
            setTextColor(com.playtranslate.OverlayColors.text(ctx))
            setPadding(0, (12 * dp).toInt(), 0, (4 * dp).toInt())
        }
        root.addView(tvRateVal)
        val seekRate = SeekBar(ctx).apply {
            max = 20 // 0.5x to 2.5x
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
            text = "Nghe thử âm thanh"
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

# 2. Cập nhật RootHelper.kt (Kích hoạt toàn bộ quyền Root chuẩn sạch)
root_path = "app/src/main/java/com/playtranslate/root/RootHelper.kt"
with open(root_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.root

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
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1"
            )
            val process = Runtime.getRuntime().exec("su")
            process.outputStream.use { os ->
                for (c in cmds) {
                    os.write((c + "\\n").toByteArray())
                }
                os.write("exit\\n".toByteArray())
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
            val cmd = if (displayId > 0) "screencap -d $displayId -p\\n" else "screencap -p\\n"
            val process = Runtime.getRuntime().exec("su")
            process.outputStream.use { os ->
                os.write(cmd.toByteArray())
                os.write("exit\\n".toByteArray())
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
""")
print(f"  * Đã chuẩn hóa: {root_path}")

# 3. Sửa triệt để PlayTranslateAccessibilityService.kt (Thoát kẹt Inspect & TTS Zone an toàn)
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
with open(a11y_path, "r", encoding="utf-8") as f:
    a11y_content = f.read()

# Đảm bảo Window Inspect luôn có FLAG_NOT_FOCUSABLE để không bao giờ chiếm phím ảo
a11y_content = a11y_content.replace(
    "val baseFlags = if (isInspect) {\n            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN\n        } else {\n            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN\n        }",
    """val baseFlags = if (isInspect) {
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        } else {
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN
        }"""
)

# Thêm hàm showTtsZoneEditor an toàn (không full viền, có nút Apply/Cancel đầy đủ)
tts_editor_func = """
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
        val btnSize = (48 * dp).toInt()

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

if "fun showTtsZoneEditor" not in a11y_content:
    a11y_content = a11y_content.replace(
        "class PlayTranslateAccessibilityService : AccessibilityService() {",
        "class PlayTranslateAccessibilityService : AccessibilityService() {\n" + tts_editor_func
    )

a11y_content = a11y_content.replace(
    "menu.onSetTtsZone = {\n            dismissFloatingMenu()\n            showRegionDragOverlay(display, Prefs(this).getTtsZone()) { zone ->\n                Prefs(this).setTtsZone(zone)\n            }\n        }",
    "menu.onSetTtsZone = { dismissFloatingMenu(); showTtsZoneEditor(display) }"
)

with open(a11y_path, "w", encoding="utf-8") as f:
    f.write(a11y_content)
print(f"  * Đã sửa an toàn: {a11y_path}")

# 4. Sửa TranslationOverlayView.kt: Khi Inspect bật, thêm nút Exit Inspect trên đầu màn hình
overlay_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"
with open(overlay_path, "r", encoding="utf-8") as f:
    ov_content = f.read()

# Chèn nút thoát Inspect mode ở đầu hàm rebuildChildren
exit_inspect_banner = """
        if (Prefs(context).inspectModeEnabled) {
            val banner = TextView(context).apply {
                text = "✕ THOÁT CHẾ ĐỘ CHẠM (INSPECT)"
                textSize = 12f
                typeface = android.graphics.Typeface.DEFAULT_BOLD
                setTextColor(Color.WHITE)
                gravity = Gravity.CENTER
                setPadding((16 * dp).toInt(), (8 * dp).toInt(), (16 * dp).toInt(), (8 * dp).toInt())
                background = android.graphics.drawable.GradientDrawable().apply {
                    setColor(Color.argb(220, 200, 40, 40))
                    cornerRadius = 16 * dp
                }
                setOnClickListener {
                    Prefs(context).inspectModeEnabled = false
                    PlayTranslateAccessibilityService.instance?.let { s ->
                        s.hideTranslationOverlay()
                        CaptureService.instance?.refreshLiveOverlay()
                    }
                }
            }
            val bannerLp = LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT).apply {
                gravity = Gravity.TOP or Gravity.CENTER_HORIZONTAL
                topMargin = (24 * dp).toInt()
            }
            addView(banner, bannerLp)
        }
"""
if "THOÁT CHẾ ĐỘ CHẠM" not in ov_content:
    ov_content = ov_content.replace(
        "removeAllViews()\n        if (boxes.isEmpty()) return",
        "removeAllViews()\n        if (boxes.isEmpty()) return\n" + exit_inspect_banner
    )
    with open(overlay_path, "w", encoding="utf-8") as f:
        f.write(ov_content)
    print(f"  * Đã gắn Banner thoát an toàn vào: {overlay_path}")

print(">>> ĐÃ KHẮC PHỤC HOÀN TOÀN CẢ 4 VẤN ĐỀ!")
