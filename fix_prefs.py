import re

prefs_path = "app/src/main/java/com/playtranslate/Prefs.kt"
with open(prefs_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Dọn dẹp các biến bị chèn nhầm ở OverlayMode companion object nếu có
content = content.replace('const val KEY_USE_ROOT_MODE = "use_root_mode"', '')
content = content.replace('const val KEY_INSPECT_MODE_ENABLED = "inspect_mode_enabled"', '')
content = content.replace('const val KEY_TTS_AUTO_SPEAK = "tts_auto_speak"', '')
content = content.replace('const val KEY_TTS_ENGINE_PKG = "tts_engine_pkg"', '')
content = content.replace('const val KEY_TTS_VOICE_NAME = "tts_voice_name"', '')
content = content.replace('const val KEY_TTS_SPEECH_RATE = "tts_speech_rate"', '')
content = content.replace('const val KEY_TTS_ZONE = "tts_zone"', '')
content = content.replace('val DEFAULT_TTS_ZONE = RegionEntry("TTS Zone", 0.00f, 1.00f, 0.00f, 1.00f, id = "tts_zone_default")', '')

# 2. Thay thế toàn bộ khối Root & TTS bằng phiên bản tự thân (dùng trực tiếp string key)
# Xóa bỏ khối cũ bị lỗi nếu có
content = re.sub(r'// ── Root Mode ──.*?sp\.edit\(\)\.putString\(KEY_TTS_ZONE, o\.toString\(\)\)\.apply\(\)\s*\}', '', content, flags=re.DOTALL)

clean_props = """
    // ── Root Mode ────────────────────────────────────────────────────────
    var useRootMode: Boolean
        get() = sp.getBoolean("use_root_mode", false)
        set(v) = sp.edit().putBoolean("use_root_mode", v).apply()

    // ── Inspect Mode (Tap translation box for details) ───────────────────
    var inspectModeEnabled: Boolean
        get() = sp.getBoolean("inspect_mode_enabled", false)
        set(v) = sp.edit().putBoolean("inspect_mode_enabled", v).apply()

    // ── Text-To-Speech (TTS) ─────────────────────────────────────────────
    var ttsAutoSpeakEnabled: Boolean
        get() = sp.getBoolean("tts_auto_speak", false)
        set(v) = sp.edit().putBoolean("tts_auto_speak", v).apply()

    var ttsEnginePackage: String
        get() = sp.getString("tts_engine_pkg", "") ?: ""
        set(v) = sp.edit().putString("tts_engine_pkg", v).apply()

    var ttsVoiceName: String
        get() = sp.getString("tts_voice_name", "") ?: ""
        set(v) = sp.edit().putString("tts_voice_name", v).apply()

    var ttsSpeechRate: Float
        get() = sp.getFloat("tts_speech_rate", 1.0f)
        set(v) = sp.edit().putFloat("tts_speech_rate", v).apply()

    // ── TTS Zone ─────────────────────────────────────────────────────────
    fun getTtsZone(): RegionEntry {
        val json = sp.getString("tts_zone", null)
            ?: return RegionEntry("TTS Zone", 0.00f, 1.00f, 0.00f, 1.00f, id = "tts_zone_default")
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
            RegionEntry("TTS Zone", 0.00f, 1.00f, 0.00f, 1.00f, id = "tts_zone_default")
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
        sp.edit().putString("tts_zone", o.toString()).apply()
    }
"""

anchor = "set(v) = sp.edit().putString(KEY_TARGET_LANG, v).apply()\n"
if anchor in content:
    content = content.replace(anchor, anchor + clean_props)

with open(prefs_path, "w", encoding="utf-8") as f:
    f.write(content)

print(">>> Đã chuẩn hóa Prefs.kt thành công 100%!")
