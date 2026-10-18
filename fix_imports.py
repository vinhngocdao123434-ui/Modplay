# 1. Sửa PlayTranslateAccessibilityService.kt (Thêm import android.graphics.Color)
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
with open(a11y_path, "r", encoding="utf-8") as f:
    content = f.read()

if "import android.graphics.Color" not in content:
    content = content.replace(
        "package com.playtranslate",
        "package com.playtranslate\n\nimport android.graphics.Color"
    )
    with open(a11y_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  * Đã bổ sung import Color vào PlayTranslateAccessibilityService.kt")

# 2. Sửa TranslationOverlayView.kt (Thêm import Service)
overlay_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"
with open(overlay_path, "r", encoding="utf-8") as f:
    content = f.read()

imports_to_add = """import com.playtranslate.PlayTranslateAccessibilityService
import com.playtranslate.CaptureService
"""
if "import com.playtranslate.CaptureService" not in content:
    content = content.replace(
        "package com.playtranslate.ui",
        "package com.playtranslate.ui\n\n" + imports_to_add
    )
    with open(overlay_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  * Đã bổ sung import Service vào TranslationOverlayView.kt")

print(">>> ĐÃ SỬA XONG TOÀN BỘ!")
