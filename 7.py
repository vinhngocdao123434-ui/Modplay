import os
import re

def replace_in_file(filepath, old_str, new_str):
    if not os.path.exists(filepath):
        print(f"Lỗi: Không tìm thấy {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_str not in content:
        # Im lặng bỏ qua nếu đã xóa rồi
        pass
    else:
        content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Thành công: Đã vá {filepath}")

# =====================================================================
# 1. LOẠI BỎ HOÀN TOÀN TÍNH NĂNG CẤM CHỤP MÀN HÌNH (FLAG_SECURE)
# =====================================================================
flag_secure_line = "window.addFlags(WindowManager.LayoutParams.FLAG_SECURE)"

replace_in_file("app/src/main/java/com/playtranslate/MainActivity.kt", flag_secure_line, "// Removed FLAG_SECURE by user request")
replace_in_file("app/src/main/java/com/playtranslate/ui/TranslationResultActivity.kt", flag_secure_line, "// Removed FLAG_SECURE by user request")
replace_in_file("app/src/main/java/com/playtranslate/ui/WordAnkiReviewActivity.kt", flag_secure_line, "// Removed FLAG_SECURE by user request")

print("Đã dỡ bỏ lệnh cấm chụp màn hình trên toàn hệ thống.")

# =====================================================================
# 2. XỬ LÝ DỨT ĐIỂM VÒNG LẶP ROOT VÀ VUỐT ĐA NHIỆM (MainActivity.kt)
# =====================================================================
main_path = "app/src/main/java/com/playtranslate/MainActivity.kt"
if os.path.exists(main_path):
    with open(main_path, 'r', encoding='utf-8') as f:
        main_content = f.read()
    
    # Tìm và thay thế khối code if (prefs.useRootMode...) trong checkOnboardingState
    # Sử dụng Regex để thay thế dù code trước đó ở trạng thái nào
    pattern = r'if \(prefs\.useRootMode && com\.playtranslate\.root\.RootHelper\.isRootAvailable\(\)\) \{.*?(?=val notifGranted)'
    
    new_root_logic = """if (prefs.useRootMode && com.playtranslate.root.RootHelper.isRootAvailable()) {
            onboardingContainer.visibility = View.GONE
            if (!PlayTranslateAccessibilityService.isEnabled(this)) {
                // App thực sự mất quyền trong Settings, dùng Root để cấp lại
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
                // App đã có quyền, chỉ là vuốt đa nhiệm nên load chậm. Đợi kết nối, KHÔNG hiện hộp thoại đòi quyền.
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
    
    main_content = re.sub(pattern, new_root_logic, main_content, flags=re.DOTALL)
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(main_content)
    print("Đã vá lỗi vòng lặp đòi quyền Root khi vuốt đa nhiệm.")

# =====================================================================
# 3. TRỊ CRASH KHI ẤN ICON TRONG GAME (PlayTranslateAccessibilityService.kt)
# =====================================================================
a11y_path = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"
if os.path.exists(a11y_path):
    with open(a11y_path, 'r', encoding='utf-8') as f:
        a11y_content = f.read()
    
    # Chèn hàm getSafeWindowManager vào companion object nếu chưa có
    safe_wm_code = """
        // Hàm lấy WindowManager an toàn tuyệt đối chống Crash BadTokenException trong Game
        private fun getSafeWindowManager(context: Context, displayId: Int): WindowManager? {
            return if (displayId == Display.DEFAULT_DISPLAY || displayId <= 0) {
                context.getSystemService(WindowManager::class.java)
            } else {
                val dm = context.getSystemService(Context.DISPLAY_SERVICE) as DisplayManager
                val display = dm.getDisplay(displayId) ?: return context.getSystemService(WindowManager::class.java)
                context.createDisplayContext(display).getSystemService(WindowManager::class.java)
            }
        }

        @Volatile"""
    
    a11y_content = a11y_content.replace("@Volatile", safe_wm_code, 1)

    # Thay thế tàn dư của các bản vá lỗi trước gây crash
    a11y_content = re.sub(r'val wm = .*getSystemService\(WindowManager::class\.java\) \?\: return', 
                          r'val wm = getSafeWindowManager(this, display.displayId) ?: return', 
                          a11y_content)
    
    a11y_content = re.sub(r'val overlayWm = displayCtx\.getSystemService\(WindowManager::class\.java\) \?\: return', 
                          r'val overlayWm = getSafeWindowManager(this, display.displayId) ?: return', 
                          a11y_content)
    
    a11y_content = re.sub(r'val wm = ctx\.getSystemService\(WindowManager::class\.java\) \?\: return', 
                          r'val wm = getSafeWindowManager(this, display.displayId) ?: return', 
                          a11y_content)

    with open(a11y_path, 'w', encoding='utf-8') as f:
        f.write(a11y_content)
    print("Đã thiết lập WindowManager gốc, chống Crash tuyệt đối khi ở trong game.")

print("\n--- HOÀN TẤT VÁ LỖI TẬN GỐC ---")
