import os
import re

print("Bắt đầu vá lỗi chuyên sâu và khôi phục hệ thống...")

def process_file(filepath, processor):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = processor(content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Thành công: Đã xử lý {filepath}")

# =====================================================================
# 1. GỠ BỎ LỆNH CẤM CHỤP MÀN HÌNH (FLAG_SECURE)
# =====================================================================
def remove_flag_secure(content):
    return re.sub(r'window\.addFlags\(WindowManager\.LayoutParams\.FLAG_SECURE\)', '// Removed FLAG_SECURE', content)

process_file("app/src/main/java/com/playtranslate/MainActivity.kt", remove_flag_secure)
process_file("app/src/main/java/com/playtranslate/ui/TranslationResultActivity.kt", remove_flag_secure)
process_file("app/src/main/java/com/playtranslate/ui/WordAnkiReviewActivity.kt", remove_flag_secure)


# =====================================================================
# 2. CẬP NHẬT LỆNH ROOT XUYÊN THỦNG ANDROID 16 & RESET BLACKLIST
# =====================================================================
def upgrade_root_helper(content):
    old_cmds = r'val cmds = arrayOf\([\s\S]*?"settings put secure accessibility_enabled 1"\n\s+\)'
    new_cmds = '''val cmds = arrayOf(
                "appops set $pkg ACCESS_RESTRICTED_SETTINGS allow",
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services null",
                "settings put secure accessibility_enabled 0",
                "sleep 1",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1"
            )'''
    return re.sub(old_cmds, new_cmds, content)

process_file("app/src/main/java/com/playtranslate/root/RootHelper.kt", upgrade_root_helper)


# =====================================================================
# 3. TRỊ CRASH KHI VÀO GAME BẰNG ĐÚNG CHUẨN WINDOW CONTEXT
# =====================================================================
def fix_a11y_service(content):
    # 3.1. Thêm Extension function nếu chưa có
    ext_func = """
fun Context.getSafeWindowContextAndManager(display: android.view.Display): Pair<Context, android.view.WindowManager?> {
    val displayCtx = this.createDisplayContext(display)
    val windowCtx = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
        displayCtx.createWindowContext(android.view.WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY, null)
    } else {
        displayCtx
    }
    return Pair(windowCtx, windowCtx.getSystemService(android.view.WindowManager::class.java))
}
"""
    if "getSafeWindowContextAndManager" not in content:
        content += ext_func

    # 3.2. Dọn rác từ các script lỗi trước (nếu có)
    content = re.sub(r'private fun getSafeWindowManager.*?return null\n\s+\}', '', content, flags=re.DOTALL)
    
    # 3.3. Thay thế toàn bộ các hàm dễ gây crash WindowManager
    replacements = [
        (r'fun updateInspectClickableBoxes\(.*?\).*?clearInspectClickableBoxes\(\)\n\s+if \(\!Prefs\(this\)\.inspectModeEnabled.*?\n\s+\}',
         r'''fun updateInspectClickableBoxes(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int
    ) {
        clearInspectClickableBoxes()
    }'''),

        (r'(fun showTtsZoneEditor\(display: Display\) \{.*?showRegionDragOverlay\(display, initZone\) \{ _ -> \}\n\s+)(?:val ctx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val dp =)',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        \2'),

        (r'(fun showRegionIndicator\(.*?\n\s+if \(region\.isFullScreen\) return\n\s+)(?:val ctx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val dp =)',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        \2'),

        (r'(fun showNoTextPill\(display: Display, message: String\) \{.*?hideNoTextPill\(\)\n\s+)(?:val ctx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val dp =)',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        \2'),

        (r'(fun showRegionDragOverlay\(.*?hideRegionDragOverlay\(\)\n\s+)(?:val wm =.*?|val \w+ = getSafeWindowManager.*?)\n\s+val view = RegionDragView\([^\)]*\)\.apply',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        val view = RegionDragView(ctx).apply'),

        (r'(fun showDebugOverlay\(.*?hideDebugOverlay\(\)\n\s+)(?:val wm =.*?|val \w+ = getSafeWindowManager.*?)\n\s+val view = OcrDebugOverlayView\([^\)]*\)\.apply',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        val view = OcrDebugOverlayView(ctx).apply'),

        (r'(hideTranslationOverlayForDisplay\(displayId\)\n\s+)(?:val displayCtx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val view = TranslationOverlayView\([^\)]*\))',
         r'\1val (displayCtx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        val themedCtx = android.view.ContextThemeWrapper(displayCtx, android.R.style.Theme_DeviceDefault)\n        val view = TranslationOverlayView(themedCtx, pinholeMode = pinholeMode)'),

        (r'(hideFloatingIconForDisplay\(displayId, "recreating"\)\n\s+)(?:val displayCtx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val icon = FloatingOverlayIcon\()[^\)]*(\))',
         r'\1val (displayCtx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n\n        \2displayCtx\3'),

        (r'(fun showFloatingMenu\(display: Display, icon: FloatingOverlayIcon\) \{.*?dismissFloatingMenu\(\)\n\s+)(?:val wm =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val menu = FloatingIconMenu\()[^\)]*(\))',
         r'\1val (displayCtx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        val screenSize = getDisplaySize(display)\n        val themeRes = baseActivityTheme(this)\n        val themedCtx = android.view.ContextThemeWrapper(displayCtx, themeRes)\n        applyAccentOverlay(themedCtx.theme, this)\n        \2themedCtx\3'),

        (r'(fun showHideConfirmAlert\(display: android\.view\.Display\) \{\n\s+)(?:val displayCtx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val appName = getString)',
         r'\1val (displayCtx, overlayWm) = this.getSafeWindowContextAndManager(display)\n        if (overlayWm == null) return\n        \2'),

        (r'(dragView\?\.onDragEnd = \{.*?regionEditorLabel\?\.visibility = View\.VISIBLE\n\s+\}\n\s+// Build floating Use / Cancel button bar\n\s+)(?:val ctx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val dp =)',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        \2'),

        (r'(fun addTouchSentinel\(displayId: Int\) \{.*?val display = dm\.getDisplay\(displayId\) \?\: return\n\s+)(?:val ctx =.*?|val \w+ = getSafeWindowManager.*?)\n.*?(val view = View\()[^\)]*(\))',
         r'\1val (ctx, wm) = this.getSafeWindowContextAndManager(display)\n        if (wm == null) return\n        \2ctx\3')
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
    return content

process_file("app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt", fix_a11y_service)

print("\n--- HOÀN TẤT VÁ LỖI CỰC MẠNH ---")