package com.playtranslate.ui

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
