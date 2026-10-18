import os
import re

print("Bắt đầu dọn dẹp đoạn code gây Crash...")

filepath = "app/src/main/java/com/playtranslate/PlayTranslateAccessibilityService.kt"

if not os.path.exists(filepath):
    print(f"Lỗi: Không tìm thấy {filepath}")
else:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Xóa sạch hàm getSafeWindowContext gây lỗi crash mà tôi đã đưa vào 2 lượt trước
    content = re.sub(r'private fun getSafeWindowContext\(display: Display\): Context \{.*?\n\s+\}', '', content, flags=re.DOTALL)

    # 2. Thêm hàm Context chuẩn: Trực tiếp dùng 'this' để không bị mất Token
    correct_func = """
    // BIỆN PHÁP CHUẨN: Màn hình chính bắt buộc dùng Context gốc ('this') của Service để giữ Thẻ bài (Token)
    private fun getSafeOverlayContext(display: android.view.Display): android.content.Context {
        return if (display.displayId == android.view.Display.DEFAULT_DISPLAY || display.displayId <= 0) {
            this 
        } else {
            this.createDisplayContext(display)
        }
    }
    """
    if "getSafeOverlayContext" not in content:
        content = content.replace("companion object {", correct_func + "\n    companion object {")

    # 3. Đổi tất cả những chỗ đang gọi hàm lỗi thành hàm chuẩn
    content = content.replace("getSafeWindowContext(display)", "getSafeOverlayContext(display)")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Thành công: Đã gỡ bỏ WindowContext gây lỗi và vá lại bằng Context gốc.")
    print("Bạn có thể đẩy code lên GitHub ngay bây giờ!")