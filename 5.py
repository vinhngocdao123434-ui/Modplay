import os

def replace_in_file(filepath, old_str, new_str):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy file {filepath}")
        return
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if old_str not in content:
        print(f"Cảnh báo: Không tìm thấy đoạn code cũ trong {filepath}. Có thể file đã được vá.")
    else:
        content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Thành công: Đã vá lỗi file {filepath}")

# =========================================================
# 1. Vá lỗi vòng lặp cấp quyền Root (MainActivity.kt)
# =========================================================
main_path = "app/src/main/java/com/playtranslate/MainActivity.kt"

old_check = """        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
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

new_check = """        if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            onboardingContainer.visibility = View.GONE
            if (!PlayTranslateAccessibilityService.isEnabled(this)) {
                lifecycleScope.launch {
                    com.playtranslate.root.RootHelper.grantAllPermissionsViaRoot(this@MainActivity)
                    var retries = 0
                    while (!PlayTranslateAccessibilityService.isConnected && retries < 20) {
                        kotlinx.coroutines.delay(150)
                        retries++
                    }
                    updateActionButtonState()
                }
            } else {
                updateActionButtonState()
            }
            return
        }"""

replace_in_file(main_path, old_check, new_check)

# =========================================================
# 2. Vá lỗi Crash WindowManager khi ở trong Game (PlayTranslateAccessibilityService.kt)
# =========================================================
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"

if not os.path.exists(a11y_path):
    print(f"Lỗi: Không tìm thấy {a11y_path}")
else:
    with open(a11y_path, 'r', encoding='utf-8') as f:
        a11y_content = f.read()

    # Thay thế toàn bộ hàm lấy Display Context lỏng lẻo bằng Window Context an toàn tuyệt đối
    a11y_content = a11y_content.replace("createDisplayContext(display)", "getSafeWindowContext(display)")

    # Chèn hàm helper getSafeWindowContext vào cuối class (trước companion object)
    if "private fun getSafeWindowContext" not in a11y_content:
        safe_context_code = """
    private fun getSafeWindowContext(display: Display): Context {
        val displayCtx = createDisplayContext(display)
        return if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S) {
            displayCtx.createWindowContext(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY, null)
        } else {
            displayCtx
        }
    }

    companion object {"""
        a11y_content = a11y_content.replace("    companion object {", safe_context_code)

    with open(a11y_path, 'w', encoding='utf-8') as f:
        f.write(a11y_content)
    print(f"Thành công: Đã vá lỗi WindowManager trong {a11y_path}")

print("\n--- HOÀN TẤT VÁ LỖI ---")
print("Bạn đã có thể đẩy (push) code mới lên Github hoặc Build lại app.")
