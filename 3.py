import os

def replace_in_file(filepath, old_str, new_str):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy file {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old_str not in content:
        print(f"Cảnh báo: Không tìm thấy đoạn code cũ trong {filepath}. Có thể file đã được sửa.")
    else:
        content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Thành công: Đã vá lỗi file {filepath}")

# ---------------------------------------------------------
# 1. Vá lỗi Root Accessibility (MainActivity.kt)
# ---------------------------------------------------------
main_activity_path = "app/src/main/java/com/playtranslate/MainActivity.kt"

old_with_accessibility = """    private fun withAccessibility(action: () -> Unit) {
        when {
            PlayTranslateAccessibilityService.isConnected -> {
                ensureConfigured()
                action()
            }
            // Enabled in Settings but Android hasn't bound the service to our
            // process yet (cold-start window, or post-unbind rebinding). Silent
            // no-op — the next tap will catch the bound state. Crucially, we
            // do NOT fall through to showAccessibilityDialog() here: the user
            // has already granted accessibility, prompting again is the bug
            // this routing exists to prevent.
            PlayTranslateAccessibilityService.isEnabled(this) -> {}
            else -> showAccessibilityDialog()
        }
    }"""

new_with_accessibility = """    private fun withAccessibility(action: () -> Unit) {
        when {
            PlayTranslateAccessibilityService.isConnected -> {
                ensureConfigured()
                action()
            }
            Prefs(this).useRootMode && com.playtranslate.root.RootHelper.isRootAvailable() -> {
                Toast.makeText(this, "Starting Root Service...", Toast.LENGTH_SHORT).show()
                lifecycleScope.launch {
                    com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
                    kotlinx.coroutines.delay(1000)
                    if (PlayTranslateAccessibilityService.isConnected) {
                        ensureConfigured()
                        action()
                    }
                }
            }
            PlayTranslateAccessibilityService.isEnabled(this) -> {}
            else -> showAccessibilityDialog()
        }
    }"""

old_check_onboarding = """        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            lifecycleScope.launch {
                com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
            }
            onboardingContainer.visibility = View.GONE
            return
        }"""

new_check_onboarding = """        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            lifecycleScope.launch {
                com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
            }
            onboardingContainer.visibility = View.GONE
            lifecycleScope.launch {
                var retries = 0
                while (!PlayTranslateAccessibilityService.isConnected && retries < 15) {
                    kotlinx.coroutines.delay(100)
                    retries++
                }
                updateActionButtonState()
            }
            return
        }"""

replace_in_file(main_activity_path, old_with_accessibility, new_with_accessibility)
replace_in_file(main_activity_path, old_check_onboarding, new_check_onboarding)

# ---------------------------------------------------------
# 2. Vá lỗi Nháy hình & Độ nhạy Pinhole (PinholeCalibration.kt & PinholeOverlayMode.kt)
# ---------------------------------------------------------
pinhole_calib_path = "app/src/main/java/com/playtranslate/PinholeCalibration.kt"
replace_in_file(pinhole_calib_path, "const val SPLATTER_THRESHOLD = 60", "const val SPLATTER_THRESHOLD = 85")
replace_in_file(pinhole_calib_path, "const val PINHOLE_DIRTY_PCT = 0.03f", "const val PINHOLE_DIRTY_PCT = 0.06f")
replace_in_file(pinhole_calib_path, "const val PINHOLE_CHANGE_PCT = 0.10f", "const val PINHOLE_CHANGE_PCT = 0.18f")

pinhole_mode_path = "app/src/main/java/com/playtranslate/PinholeOverlayMode.kt"
replace_in_file(pinhole_mode_path, "private val SCENE_CHANGE_THRESHOLD = 0.40f", "private val SCENE_CHANGE_THRESHOLD = 0.55f")
replace_in_file(pinhole_mode_path, "private val OVERLAY_CHANGE_THRESHOLD = 0.10f", "private val OVERLAY_CHANGE_THRESHOLD = 0.20f")

# ---------------------------------------------------------
# 3. Vá lỗi Inspect Mode bị kẹt / bấm xuyên (PlayTranslateAccessibilityService.kt)
# ---------------------------------------------------------
a11y_service_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"

old_inspect_func = """    fun updateInspectClickableBoxes(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int
    ) {
        clearInspectClickableBoxes()
        if (!Prefs(this).inspectModeEnabled || boxes.isEmpty()) return
        val ctx = createDisplayContext(display)
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
    }"""

new_inspect_func = """    fun updateInspectClickableBoxes(
        display: Display,
        boxes: List<TranslationOverlayView.TextBox>,
        cropLeft: Int, cropTop: Int,
        screenshotW: Int, screenshotH: Int
    ) {
        // Logic moved entirely to TranslationOverlayView to fix z-order and touch issues.
        clearInspectClickableBoxes()
    }"""

replace_in_file(a11y_service_path, old_inspect_func, new_inspect_func)

# ---------------------------------------------------------
# 4. Trả lại nền tự nhiên mờ mờ cho khung dịch (TranslationOverlayView.kt)
# ---------------------------------------------------------
overlay_view_path = "app/src/main/java/com/playtranslate/ui/TranslationOverlayView.kt"

old_bg_line = "setBackgroundColor(if (pinholeMode) box.bgColor or 0xFF000000.toInt() else box.bgColor)"
new_bg_line = "setBackgroundColor(box.bgColor) // Removed hard opacity to keep translations looking natural"

replace_in_file(overlay_view_path, old_bg_line, new_bg_line)

print("\n--- HOÀN TẤT VÁ LỖI TỰ ĐỘNG ---")
print("Vui lòng Build lại app bằng Android Studio hoặc Gradle để trải nghiệm bản vá.")
