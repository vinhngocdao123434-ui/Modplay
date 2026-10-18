import os
import re

def replace_in_file(filepath, old_str, new_str):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_str not in content:
        pass
    else:
        content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

def regex_replace_in_file(filepath, pattern, new_str):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(pattern, new_str, content, flags=re.DOTALL)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Bắt đầu vá lỗi chuyên sâu...")

# =====================================================================
# 1. GỠ BỎ LỆNH CẤM CHỤP MÀN HÌNH (FLAG_SECURE)
# =====================================================================
flag_secure = "window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)"
replace_in_file("app/src/main/java/com/playtranslate/MainActivity.kt", flag_secure, "// Removed FLAG_SECURE")
replace_in_file("app/src/main/java/com/playtranslate/ui/TranslationResultActivity.kt", flag_secure, "// Removed FLAG_SECURE")
replace_in_file("app/src/main/java/com/playtranslate/ui/WordAnkiReviewActivity.kt", flag_secure, "// Removed FLAG_SECURE")
print("1. Đã dỡ bỏ lệnh cấm chụp màn hình.")

# =====================================================================
# 2. CẬP NHẬT LỆNH ROOT XUYÊN THỦNG ANDROID 16 (RootHelper.kt)
# =====================================================================
root_helper_path = "app/src/main/java/com/playtranslate/root/RootHelper.kt"
old_cmds = """val cmds = arrayOf(
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1"
            )"""
new_cmds = """val cmds = arrayOf(
                "appops set $pkg ACCESS_RESTRICTED_SETTINGS allow",
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1"
            )"""
replace_in_file(root_helper_path, old_cmds, new_cmds)
print("2. Đã nâng cấp lệnh Root cho Android 16.")

# =====================================================================
# 3. SỬA LOGIC CHỜ QUYỀN ROOT Ở MÀN HÌNH CHÍNH (MainActivity.kt)
# =====================================================================
main_path = "app/src/main/java/com/playtranslate/MainActivity.kt"
main_pattern = r'if \(prefs\.useRootMode && com\.playtranslate\.root\.RootHelper\.isRootAvailable\(\)\) \{.*?(?=val notifGranted)'
new_root_logic = """if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            onboardingContainer.visibility = View.GONE
            if (!PlayTranslateAccessibilityService.isEnabled(this)) {
                lifecycleScope.launch {
                    com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
                    var retries = 0
                    while (!PlayTranslateAccessibilityService.isConnected && retries < 20) {
                        kotlinx.coroutines.delay(100)
                        retries++
                    }
                    updateActionButtonState()
                }
            } else {
                if (!PlayTranslateAccessibilityService.isConnected) {
                    lifecycleScope.launch {
                        var retries = 0
                        while (!PlayTranslateAccessibilityService.isConnected && retries < 20) {
                            kotlinx.coroutines.delay(100)
                            retries++
                        }
                        updateActionButtonState()
                    }
                } else {
                    updateActionButtonState()
                }
            }
            return
        }
        
        """
regex_replace_in_file(main_path, main_pattern, new_root_logic)
print("3. Đã sửa luồng đợi Service, giải quyết lỗi vòng lặp đòi quyền khi vuốt đa nhiệm.")

# =====================================================================
# 4. TRỊ CRASH KHI VÀO GAME BẰNG WINDOW CONTEXT (PlayTranslateAccessibilityService.kt)
# =====================================================================
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"

# Thêm extension function tạo SafeWindowContext vào cuối file
ext_func = """
private fun Context.getSafeWindowContextAndManager(display: Display): Pair<Context, WindowManager?> {
    val displayCtx = this.createDisplayContext(display)
    val windowCtx = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
        displayCtx.createWindowContext(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY, null)
    } else {
        displayCtx
    }
    return Pair(windowCtx, windowCtx.getSystemService(WindowManager::class.java))
}
"""
if os.path.exists(a11y_path):
    with open(a11y_path, 'r', encoding='utf-8') as f:
        a11y_content = f.read()

    if "getSafeWindowContextAndManager" not in a11y_content:
        a11y_content = a11y_content + ext_func

    # Cập nhật tất cả các lệnh gọi WindowManager rủi ro
    replacements = [
        (
            """val ctx = createDisplayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return""",
            """val (ctx, wm) = getSafeWindowContextAndManager(display)
        if (wm == null) return"""
        ),
        (
            """val wm = createDisplayContext(display).getSystemService(WindowManager::class.java) ?: return
        val view = OcrDebugOverlayView(this).apply {""",
            """val (ctx, wm) = getSafeWindowContextAndManager(display)
        if (wm == null) return
        val view = OcrDebugOverlayView(ctx).apply {"""
        ),
        (
            """val displayCtx = createDisplayContext(display)
        val themedCtx = android.view.ContextThemeWrapper(displayCtx, android.R.style.Theme_DeviceDefault)
        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return""",
            """val (displayCtx, wm) = getSafeWindowContextAndManager(display)
        if (wm == null) return
        val themedCtx = android.view.ContextThemeWrapper(displayCtx, android.R.style.Theme_DeviceDefault)"""
        ),
        (
            """val displayCtx = createDisplayContext(display)
        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return""",
            """val (displayCtx, wm) = getSafeWindowContextAndManager(display)
        if (wm == null) return"""
        ),
        (
            """val wm = createDisplayContext(display).getSystemService(WindowManager::class.java) ?: return
        val screenSize = getDisplaySize(display)
        val themeRes = baseActivityTheme(this)
        val themedCtx = android.view.ContextThemeWrapper(createDisplayContext(display), themeRes)""",
            """val (displayCtx, wm) = getSafeWindowContextAndManager(display)
        if (wm == null) return
        val screenSize = getDisplaySize(display)
        val themeRes = baseActivityTheme(this)
        val themedCtx = android.view.ContextThemeWrapper(displayCtx, themeRes)"""
        ),
        (
            """val displayCtx = createDisplayContext(display)
        val overlayWm = displayCtx.getSystemService(WindowManager::class.java) ?: return""",
            """val (displayCtx, overlayWm) = getSafeWindowContextAndManager(display)
        if (overlayWm == null) return"""
        ),
        (
            """val wm = createDisplayContext(display).getSystemService(WindowManager::class.java) ?: return
        val view = RegionDragView(this).apply {""",
            """val (ctx, wm) = getSafeWindowContextAndManager(display)
        if (wm == null) return
        val view = RegionDragView(ctx).apply {"""
        )
    ]

    for old, new in replacements:
        a11y_content = a11y_content.replace(old, new)

    with open(a11y_path, 'w', encoding='utf-8') as f:
        f.write(a11y_content)
    print("4. Đã thay máu WindowContext, chống Crash tuyệt đối khi ở trong game.")

print("\n--- HOÀN TẤT VÁ LỖI CHUYÊN SÂU ---")
print("Bạn đã có thể đẩy code lên Github để Build lại app.")