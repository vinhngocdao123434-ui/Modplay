import os
import re

print("Bắt đầu dọn dẹp và vá lỗi hệ thống...")

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
# 2. SỬA LỆNH ROOT ĐỂ TẨY TRẮNG BLACKLIST TRÊN ANDROID 16
# =====================================================================
def fix_root_helper(content):
    old_cmds = r'val cmds = arrayOf\([\s\S]*?"settings put secure accessibility_enabled 1"\n\s+\)'
    new_cmds = '''val cmds = arrayOf(
                "appops set $pkg ACCESS_RESTRICTED_SETTINGS allow",
                "pm grant $pkg android.permission.SYSTEM_ALERT_WINDOW",
                "pm grant $pkg android.permission.POST_NOTIFICATIONS",
                "settings put secure enabled_accessibility_services \\"\\"",
                "settings put secure accessibility_enabled 0",
                "sleep 0.5",
                "settings put secure enabled_accessibility_services $a11yComponent",
                "settings put secure accessibility_enabled 1"
            )'''
    return re.sub(old_cmds, new_cmds, content)

process_file("app/src/main/java/com/playtranslate/root/RootHelper.kt", fix_root_helper)


# =====================================================================
# 3. FIX LỖI BUILD GITHUB VÀ CRASH WINDOWMANAGER
# (Dọn rác cũ và dùng Context gốc)
# =====================================================================
def fix_a11y_service(content):
    # Dọn dẹp sạch sẽ các hàm rác từ bản script trước
    content = re.sub(r'private fun getSafeWindowContextAndManager.*?\n\}', '', content, flags=re.DOTALL)
    content = re.sub(r'private fun Context\.getSafeWindowContextAndManager.*?\n\}', '', content, flags=re.DOTALL)
    content = re.sub(r'private fun getSafeWindowManager.*?\n\s+\}', '', content, flags=re.DOTALL)
    content = re.sub(r'private fun getSafeOverlayContext.*?\n\s+\}', '', content, flags=re.DOTALL)
    content = re.sub(r'fun Context\.getSafeWindowContextAndManager.*?\n\}', '', content, flags=re.DOTALL)

    # Vá nội tuyến (Inline) từng hàm để đảm bảo 100% không bị Unresolved Reference
    # 3.1: updateInspectClickableBoxes
    content = re.sub(
        r'(clearInspectClickableBoxes\(\)\n\s+if \(\!Prefs\(this\)\.inspectModeEnabled \|\| boxes\.isEmpty\(\)\) return\n\s+).*?(val dm = resources\.displayMetrics)',
        r'\1val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.2: showTtsZoneEditor
    content = re.sub(
        r'(showRegionDragOverlay\(display, initZone\) \{ _ -> \}\n\s+).*?(val dp = )',
        r'\1val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.3: showRegionIndicator
    content = re.sub(
        r'(if \(region\.isFullScreen\) return\n\s+).*?(val dp = )',
        r'\1val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.4: showNoTextPill
    content = re.sub(
        r'(hideNoTextPill\(\)\n\s+).*?(val dp = )',
        r'\1val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.5: showRegionDragOverlay
    content = re.sub(
        r'(hideRegionDragOverlay\(\)\n\s+).*?(val view = RegionDragView)',
        r'\1val wm = (if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)).getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.6: showDebugOverlay
    content = re.sub(
        r'(hideDebugOverlay\(\)\n\s+).*?(val view = OcrDebugOverlayView)',
        r'\1val wm = (if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)).getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.7: showTranslationOverlay
    content = re.sub(
        r'(hideTranslationOverlayForDisplay\(displayId\)\n\s+).*?(val view = TranslationOverlayView)',
        r'\1val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val themedCtx = android.view.ContextThemeWrapper(displayCtx, android.R.style.Theme_DeviceDefault)\n        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.8: installFloatingIconForDisplay
    content = re.sub(
        r'(hideFloatingIconForDisplay\(displayId, "recreating"\)\n\s+).*?(val icon = FloatingOverlayIcon)',
        r'\1val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return\n\n        \2',
        content, flags=re.DOTALL
    )

    # 3.9: showFloatingMenu
    content = re.sub(
        r'(dismissFloatingMenu\(\)\n\s+).*?(val screenSize = getDisplaySize\(display\))',
        r'\1val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = displayCtx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )
    content = re.sub(
        r'val themedCtx = android\.view\.ContextThemeWrapper\(.*?, themeRes\)',
        r'val themedCtx = android.view.ContextThemeWrapper(displayCtx, themeRes)',
        content
    )

    # 3.10: showHideConfirmAlert
    content = re.sub(
        r'(fun showHideConfirmAlert\(display: android\.view\.Display\) \{\n\s+).*?(val appName = getString)',
        r'\1val displayCtx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val overlayWm = displayCtx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.11: showRegionEditor
    content = re.sub(
        r'(dragView\?\.onDragEnd = \{.*?regionEditorLabel\?\.visibility = View\.VISIBLE\n\s+\}\n\s+// Build floating Use / Cancel button bar\n\s+).*?(val dp = )',
        r'\1val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    # 3.12: addTouchSentinel
    content = re.sub(
        r'(val display = dm\.getDisplay\(displayId\) \?\: return\n\s+).*?(val view = View)',
        r'\1val ctx = if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) this else this.createDisplayContext(display)\n        val wm = ctx.getSystemService(WindowManager::class.java) ?: return\n        \2',
        content, flags=re.DOTALL
    )

    return content

process_file("app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt", fix_a11y_service)


# =====================================================================
# 4. FIX NÚT BẬT TRONG SETTINGS: DÙNG ROOT KHÔI PHỤC NGAY LẬP TỨC
# =====================================================================
def fix_settings_renderer(content):
    pattern = r'switchOverlayIcon\.setOnCheckedChangeListener \{ _, checked ->.*?(?=rowOverlayIcon\.setOnClickListener)'
    new_logic = '''switchOverlayIcon.setOnCheckedChangeListener { _, checked ->
            if (checked && !PlayTranslateAccessibilityService.isConnected) {
                if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
                    android.widget.Toast.makeText(ctx, "Khôi phục Service bằng Root...", android.widget.Toast.LENGTH_SHORT).show()
                    lifecycleScope.launch {
                        com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(ctx)
                        var retries = 0
                        while (!PlayTranslateAccessibilityService.isConnected && retries < 25) {
                            kotlinx.coroutines.delay(100)
                            retries++
                        }
                        if (PlayTranslateAccessibilityService.isConnected) {
                            prefs.showOverlayIcon = true
                            PlayTranslateAccessibilityService.instance?.reconcileFloatingIcons()
                            try { com.playtranslate.PlayTranslateTileService.TileSync.refresh(ctx) } catch (e: Exception) {}
                            refreshOnScreenControlsTint(isSingle)
                        } else {
                            switchOverlayIcon.isChecked = false
                            android.widget.Toast.makeText(ctx, "Root thất bại, vui lòng khởi động lại app", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    }
                    return@setOnCheckedChangeListener
                } else {
                    switchOverlayIcon.isChecked = false
                    try {
                        androidx.appcompat.app.AlertDialog.Builder(ctx)
                            .setTitle(if (!PlayTranslateAccessibilityService.isEnabled(ctx)) R.string.overlay_icon_a11y_required_title else R.string.app_name)
                            .setMessage(if (!PlayTranslateAccessibilityService.isEnabled(ctx)) R.string.overlay_icon_a11y_required_message else R.string.accessibility_dialog_message)
                            .setPositiveButton(R.string.btn_open_a11y_settings) { _, _ ->
                                ctx.startActivity(android.content.Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS).apply { addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK) })
                            }
                            .setNegativeButton(android.R.string.cancel, null)
                            .show()
                    } catch (e: Exception) {}
                    return@setOnCheckedChangeListener
                }
            }

            if (checked) {
                prefs.showOverlayIcon = true
                PlayTranslateAccessibilityService.instance?.reconcileFloatingIcons()
                try { com.playtranslate.PlayTranslateTileService.TileSync.refresh(ctx) } catch (e: Exception) {}
            } else {
                PlayTranslateAccessibilityService.disable(ctx, "settings_toggle_off")
            }
            refreshOnScreenControlsTint(isSingle)
        }\n        '''
    return re.sub(pattern, new_logic, content, flags=re.DOTALL)

process_file("app/src/main/java/com/playtranslate/ui/SettingsRenderer.kt", fix_settings_renderer)


# =====================================================================
# 5. SỬA LẠI LOGIC CHỜ QUYỀN ROOT MÀN HÌNH CHÍNH (MainActivity.kt)
# =====================================================================
def fix_main_activity(content):
    pattern = r'if \(prefs\.useRootMode && com\.playtranslate\.root\.RootHelper\.isRootAvailable\(\)\) \{.*?(?=val notifGranted =)'
    new_logic = '''if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
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
        
        '''
    return re.sub(pattern, new_logic, content, flags=re.DOTALL)

process_file("app/src/main/java/com/playtranslate/MainActivity.kt", fix_main_activity)

print("\n--- HOÀN TẤT VÁ LỖI TOÀN DIỆN ---")