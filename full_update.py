import os
import re

print(">>> Đang cập nhật 100% full tính năng vào mã nguồn PlayTranslate...")

# ==============================================================================
# 1. TtsManager.kt (Đọc đúng 1 lần cho câu mới, không bao giờ lặp)
# ==============================================================================
tts_path = "app/src/main/java/com/playtranslate/tts/TtsManager.kt"
os.makedirs(os.path.dirname(tts_path), exist_ok=True)
with open(tts_path, "w", encoding="utf-8") as f:
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
        // Chống đọc lặp: Chỉ đọc đúng 1 lần cho nội dung mới
        if (!force && trimmed == lastSpokenText) return
        lastSpokenText = trimmed

        val engineInstance = tts
        if (engineInstance != null && isInitialized) {
            applySettings()
            engineInstance.speak(trimmed, TextToSpeech.QUEUE_FLUSH, null, "PLAY_TRANSLATE_TTS")
        }
    }

    fun stop() {
        // Giữ nguyên lastSpokenText để không đọc lặp khi màn hình quét lại
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
print(f"  + Cập nhật TtsManager: {tts_path}")

# ==============================================================================
# 2. TtsSettingsDialog.kt (Giao diện Cài đặt TTS đầy đủ)
# ==============================================================================
tts_dialog_path = "app/src/main/java/com/playtranslate/ui/TtsSettingsDialog.kt"
with open(tts_dialog_path, "w", encoding="utf-8") as f:
    f.write("""package com.playtranslate.ui

import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
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
print(f"  + Cập nhật TtsSettingsDialog: {tts_dialog_path}")

# ==============================================================================
# 3. TranslationBoxDetailOverlay.kt (Popup chi tiết Raw - Dịch - Copy - TTS)
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
    
