import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    
    prompt = """Bạn là một chuyên gia hạng nặng VÔ CÙNG NGHIÊM KHẮC VÀ KHÓ TÍNH trong lĩnh vực hệ thống giao dịch tài chính. Đừng ngại chỉ trích. Cùng tôi thực hiện phản biện 2 chiều: 
VẤN ĐỀ CẦN GIẢI QUYẾT: Review lộ trình 5 giai đoạn đưa AI Quant vào thực chiến (Master Roadmap). 
ĐỀ XUẤT CỦA TÔI: Giai đoạn 1 (Đào tạo In-sample), Giai đoạn 2 (Kiểm định mù OOS), Giai đoạn 3 (Paper Trading), Giai đoạn 4 (Quản trị vốn & Circuit Breaker), Giai đoạn 5 (Tiền thật & Tái huấn luyện). 
NHIỆM VỤ CỦA BẠN: 1. Tấn công trực diện vào lỗ hổng của quy trình này. 2. Đưa ra cách tiếp cận tốt hơn. 3. Đặt lại 1 câu hỏi sắc bén."""

    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.execute_script("""
        var overlays = document.querySelectorAll('.cdk-overlay-container, .tool-tip');
        overlays.forEach(function(e){ e.style.display = 'none'; });
    """)
    
    editor = driver.find_element(By.CSS_SELECTOR, 'rich-textarea, div[role="textbox"]')
    
    driver.execute_script("""
        arguments[0].focus();
        document.execCommand('selectAll', false, null);
        document.execCommand('insertText', false, arguments[1]);
    """, editor, prompt)
    
    time.sleep(1)
    
    driver.execute_script("""
        var btn = document.querySelector('.send-button, button[aria-label="Send message"], button[mattooltip="Send message"], button[aria-label="Gửi tin nhắn"]');
        if(btn && !btn.disabled) { btn.click(); }
    """)
    
    print("Da Paste vao o nhap lieu va gui, cho phan hoi...")
    
    last_text = ""
    stable_count = 0
    for _ in range(60):
        time.sleep(2)
        script_read = """
        var bubbles = document.querySelectorAll('.message-content, model-response, [class*="message-content"]');
        for(var i = bubbles.length - 1; i >= 0; i--) {
            var text = bubbles[i].innerText;
            if (text && text.trim().length > 20 && !text.includes('Bạn là một chuyên gia')) {
                return text.trim();
            }
        }
        return "";
        """
        current_text = driver.execute_script(script_read)
        if current_text and current_text == last_text:
            stable_count += 1
        else:
            stable_count = 0
        last_text = current_text
        
        if stable_count >= 3 and current_text != "":
            break
            
    print("=== GEMINI RESPONSE ===")
    print(last_text)
    print("=======================")

if __name__ == "__main__":
    main()
