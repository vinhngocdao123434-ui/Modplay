package com.playtranslate.tts

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
