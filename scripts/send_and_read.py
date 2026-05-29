import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    prompt = """Bạn là một chuyên gia hạng nặng VÔ CÙNG NGHIÊM KHẮC VÀ KHÓ TÍNH trong lĩnh vực hệ thống giao dịch tài chính. Đừng ngại chỉ trích. Cùng tôi thực hiện phản biện 2 chiều: 
VẤN ĐỀ CẦN GIẢI QUYẾT: Review lộ trình 5 giai đoạn đưa AI Quant vào thực chiến (Master Roadmap). 
ĐỀ XUẤT CỦA TÔI: Giai đoạn 1 (Đào tạo In-sample), Giai đoạn 2 (Kiểm định mù OOS), Giai đoạn 3 (Paper Trading), Giai đoạn 4 (Quản trị vốn & Circuit Breaker), Giai đoạn 5 (Tiền thật & Tái huấn luyện). 
NHIỆM VỤ CỦA BẠN: 1. Tấn công trực diện vào lỗ hổng của quy trình này. 2. Đưa ra cách tiếp cận tốt hơn. 3. Đặt lại 1 câu hỏi sắc bén."""

    script_send = """
    var editor = document.querySelector('rich-textarea, div[role="textbox"]');
    if(editor) {
        editor.textContent = arguments[0];
        editor.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
    }
    return false;
    """
    
    success = driver.execute_script(script_send, prompt)
    if not success:
        print("Khong tim thay editor")
        return
        
    time.sleep(1)
    
    try:
        editor = driver.find_element(By.CSS_SELECTOR, 'rich-textarea, div[role="textbox"]')
        ActionChains(driver).click(editor).send_keys(Keys.END).send_keys(Keys.ENTER).perform()
    except Exception as e:
        print("ActionChains Error:", e)
        script_click = """
        var btn = document.querySelector('.send-button, button[aria-label="Send message"]');
        if(btn) { btn.click(); return true; }
        return false;
        """
        driver.execute_script(script_click)
            
    print("Da gui prompt, dang cho phan hoi...")
    
    last_text = ""
    stable_count = 0
    for _ in range(60):
        time.sleep(1.5)
        script_read = """
        var bubbles = document.querySelectorAll('.message-content, model-response');
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
