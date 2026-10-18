import os

print(">>> Đang sửa các lỗi biên dịch...")

# 1. Sửa TranslationOverlayView.kt (Thêm import Prefs)
view_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"
if os.path.exists(view_path):
    with open(view_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "import com.playtranslate.Prefs" not in content:
        content = content.replace(
            "package com.playtranslate.ui",
            "package com.playtranslate.ui\n\nimport com.playtranslate.Prefs"
        )
        with open(view_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  * Đã sửa: {view_path}")

# 2. Sửa CaptureService.kt (Thêm import android.graphics.Rect)
capture_path = "app/src/main/java/com/playtranslate/CaptureService.kt"
if os.path.exists(capture_path):
    with open(capture_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "import android.graphics.Rect\n" not in content:
        content = content.replace(
            "package com.playtranslate",
            "package com.playtranslate\n\nimport android.graphics.Rect"
        )
        with open(capture_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  * Đã sửa: {capture_path}")

# 3. Sửa PlayTranslateAccessibilityService.kt (Thêm TYPE_ACCESSIBILITY_OVERLAY vào LayoutParams)
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
if os.path.exists(a11y_path):
    with open(a11y_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    old_lp = """        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            baseFlags,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }"""
    
    new_lp = """        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            baseFlags,
            PixelFormat.TRANSLUCENT
        ).apply { windowAnimations = 0 }"""
    
    if old_lp in content:
        content = content.replace(old_lp, new_lp)
        with open(a11y_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  * Đã sửa: {a11y_path}")

# 4. Sửa Prefs.kt (Bổ sung KEY_* vào companion object)
prefs_path = "app/src/main/java/com/playtranslate/Prefs.kt"
if os.path.exists(prefs_path):
    with open(prefs_path, "r", encoding="utf-8") as f:
        content = f.read()

    missing_keys = """
        const val KEY_USE_ROOT_MODE = "use_root_mode"
        const val KEY_INSPECT_MODE_ENABLED = "inspect_mode_enabled"
        const val KEY_TTS_AUTO_SPEAK = "tts_auto_speak"
        const val KEY_TTS_ENGINE_PKG = "tts_engine_pkg"
        const val KEY_TTS_VOICE_NAME = "tts_voice_name"
        const val KEY_TTS_SPEECH_RATE = "tts_speech_rate"
        const val KEY_TTS_ZONE = "tts_zone"
        val DEFAULT_TTS_ZONE = RegionEntry("TTS Zone", 0.00f, 1.00f, 0.00f, 1.00f, id = "tts_zone_default")
"""
    if "KEY_USE_ROOT_MODE" not in content:
        content = content.replace(
            "companion object {",
            "companion object {" + missing_keys
        )
        with open(prefs_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  * Đã sửa: {prefs_path}")

print(">>> Đã sửa xong toàn bộ các lỗi tham chiếu!")
