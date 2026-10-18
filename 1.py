import os
import re

def process_file(filepath, processor):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    new_content = processor(content)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Thành công: Đã đập đi xây lại {filepath}")

# =====================================================================
# 1. ĐẬP ĐI XÂY LẠI CƠ CHẾ CONTEXT VẼ ĐÈ LÊN GAME (Chống Crash tuyệt đối)
# =====================================================================
def rebuild_a11y_service(content):
    # 1.1 Xóa sạch các tàn dư của getSafeWindowContextAndManager cũ
    content = re.sub(r'private fun Context\.getSafeWindowContextAndManager.*?return Pair.*?\n\}', '', content, flags=re.DOTALL)
    
    # 1.2 Thêm hàm Context chuẩn gốc của Accessibility (Kế thừa Token)
    core_context_func = """
    // KIẾN TRÚC MỚI: Dùng trực tiếp Context của Service để giữ nguyên Accessibility Token
    private fun getSafeOverlayContext(display: android.view.Display): Context {
        return if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) {
            this // Bắt buộc dùng 'this' để không mất Token trên Android 16
        } else {
            this.createDisplayContext(display) // Kế thừa token cho màn hình phụ
        }
    }
    """
    if "getSafeOverlayContext" not in content:
        content = content.replace("companion object {", core_context_func + "\n    companion object {")

    # 1.3 Thay máu toàn bộ các nơi lấy WindowManager bị lỗi ở các bản vá trước
    replacements = [
        (r'val \(ctx, wm\) = this\.getSafeWindowContextAndManager\(display\)\n\s+if \(wm == null\) return', 
         r'val ctx = getSafeOverlayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return'),
        
        (r'val \(displayCtx, wm\) = this\.getSafeWindowContextAndManager\(display\)\n\s+if \(wm == null\) return', 
         r'val displayCtx = getSafeOverlayContext(display)\n        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return'),

        (r'val \(displayCtx, overlayWm\) = this\.getSafeWindowContextAndManager\(display\)\n\s+if \(overlayWm == null\) return', 
         r'val displayCtx = getSafeOverlayContext(display)\n        val overlayWm = displayCtx.getSystemService(WindowManager::class.java) ?: return'),
         
        (r'val \(ctx, wm\) = getSafeWindowContextAndManager\(display\)\n\s+if \(wm == null\) return', 
         r'val ctx = getSafeOverlayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return'),
         
        (r'val \(displayCtx, wm\) = getSafeWindowContextAndManager\(display\)\n\s+if \(wm == null\) return', 
         r'val displayCtx = getSafeOverlayContext(display)\n        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return'),
         
        (r'val \(displayCtx, overlayWm\) = getSafeWindowContextAndManager\(display\)\n\s+if \(overlayWm == null\) return', 
         r'val displayCtx = getSafeOverlayContext(display)\n        val overlayWm = displayCtx.getSystemService(WindowManager::class.java) ?: return')
    ]

    for old, new in replacements:
        content = re.sub(old, new, content)

    # 1.4 Khôi phục lại updateInspectClickableBoxes bị xóa nhầm ở bản trước
    if "clearInspectClickableBoxes()" in content and "val ctx = getSafeOverlayContext(display)" not in content:
        content = re.sub(
            r'fun updateInspectClickableBoxes\(.*?clearInspectClickableBoxes\(\)\n\s+\}',
            r'''fun updateInspectClickableBoxes(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int
    ) {
        clearInspectClickableBoxes()
        if (!Prefs(this).inspectModeEnabled || boxes.isEmpty()) return
        val ctx = getSafeOverlayContext(display)
        val wm = ctx.getSystemService(WindowManager::class.java) ?: return
        val dm = resources.displayMetrics
        val scaleX = dm.widthPixels.toFloat() / screenshotW
        val scaleY = dm.heightPixels.toFloat() / screenshotH

        for (box in boxes) {
            if (box.translatedText.isBlank()) continue
            val b = box.bounds
            val left = ((b.left + cropLeft) * scaleX).toInt()
            val top = ((b.top + cropTop) * scaleY).toInt()
            val right = ((b.right + cropLeft) * scaleX).toInt()
            val bottom = ((b.bottom + cropTop) * scaleY).toInt()
            val w = (right - left).coerceAtLeast(20)
            val h = (bottom - top).coerceAtLeast(20)

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
            val lp = WindowManager.LayoutParams(
                w, h,
                WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
                PixelFormat.TRANSLUCENT
            ).apply {
                gravity = Gravity.TOP or Gravity.START
                x = left
                y = top
            }
            if (addOverlayWindow(clickable, wm, lp, display.displayId)) {
                inspectWindows.add(clickable)
            }
        }
    }''', content, flags=re.DOTALL)

    return content

process_file("app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt", rebuild_a11y_service)


# =====================================================================
# 2. ĐẬP ĐI XÂY LẠI LUỒNG ROOT: ÉP XUYÊN MÀN HÌNH ONBOARDING
# =====================================================================
def rebuild_main_activity(content):
    # Dọn dẹp cục nợ if (prefs.useRootMode...) cũ rích
    content = re.sub(r'if \(prefs\.useRootMode && com\.playtranslate\.root\.RootHelper\.isRootAvailable\(\)\) \{.*?(?=val notifGranted =)', '', content, flags=re.DOTALL)
    
    # Ép Root ngay từ đầu hàm checkOnboardingState
    root_force_code = """
        // KIẾN TRÚC MỚI: Bạo lực vượt qua màn hình Onboarding nếu có Root
        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            onboardingContainer.visibility = View.GONE
            lifecycleScope.launch {
                com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
                // Ép UI tin rằng Accessibility đã mở
                updateActionButtonState()
            }
            return
        }
        
        val notifGranted ="""
    
    content = content.replace("val notifGranted =", root_force_code)
    return content

process_file("app/src/main/java/com/playtranslate/MainActivity.kt", rebuild_main_activity)


# =====================================================================
# 3. LỆNH ROOT "CỨNG NHẤT" ĐỂ VƯỢT QUA ANDROID 16 BLACKLIST
# =====================================================================
def rebuild_root_helper(content):
    old_cmds = r'val cmds = arrayOf\([\s\S]*?"settings put secure accessibility_enabled 1"\n\s+\)'
    # Lệnh Root dọn sạch rác, tắt service, cấp appops, rồi ép bật lại
    new_cmds = '''val cmds = arrayOf(
                "appops set $pkg ACCESS_RESTRICTED_SETTINGS allow",
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services null",
                "settings put secure accessibility_enabled 0",
                "sleep 0.5",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1",
                "am force-stop com.android.settings" // Ép hệ thống reset UI Settings để nhận Service
            )'''
    return re.sub(old_cmds, new_cmds, content)

process_file("app/src/main/java/com/playtranslate/root/RootHelper.kt", rebuild_root_helper)

print("\n--- XONG! HỆ THỐNG ĐÃ ĐƯỢC XÂY LẠI TỪ MÓNG ---")