import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

def main():
    print("Khoi dong Google Chrome voi cong Remote Debugging 9222...")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    user_data = r"C:\temp\chrome_gemini_profile"
    
    subprocess.Popen([chrome_path, "--remote-debugging-port=9222", f"--user-data-dir={user_data}", "https://gemini.google.com/app"])
    time.sleep(4)
    
    print("Ket noi Selenium vao Chrome...")
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("CONNECTED!")
    print("URL:", driver.current_url)
    
    prompt = """Bạn là một chuyên gia hạng nặng VÔ CÙNG NGHIÊM KHẮC VÀ KHÓ TÍNH trong lĩnh vực hệ thống giao dịch tài chính. Đừng ngại chỉ trích. Cùng tôi thực hiện phản biện 2 chiều: VẤN ĐỀ CẦN GIẢI QUYẾT: Review lộ trình 5 giai đoạn đưa AI Quant vào thực chiến (Master Roadmap). ĐỀ XUẤT CỦA TÔI: Giai đoạn 1 (Đào tạo In-sample), Giai đoạn 2 (Kiểm định mù OOS), Giai đoạn 3 (Paper Trading), Giai đoạn 4 (Quản trị vốn & Circuit Breaker), Giai đoạn 5 (Tiền thật & Tái huấn luyện). NHIỆM VỤ CỦA BẠN: 1. Tấn công trực diện vào lỗ hổng của quy trình này. 2. Đưa ra cách tiếp cận tốt hơn. 3. Đặt lại 1 câu hỏi sắc bén."""
    
    print("Vui long dam bao da dang nhap Google. Kich ban se cho 10s...")
    time.sleep(10) 
    
    try:
        print("Dang tim o nhap lieu...")
        editor = driver.find_element(By.CSS_SELECTOR, 'rich-textarea, div[role="textbox"], textarea')
        editor.click()
        driver.execute_script("arguments[0].textContent = arguments[1];", editor, prompt)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        time.sleep(1)
        editor.send_keys(Keys.ENTER)
        print("Da gui prompt thanh cong!")
    except Exception as e:
        print("Khong the gui prompt (co the chua dang nhap Google). Loi:", e)
        
    print("\nHoan tat kich ban. Giu trinh duyet 60s de sep doc ket qua...")
    time.sleep(60)

if __name__ == "__main__":
    main()
