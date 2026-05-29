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
    time.sleep(6)
    
    print("Ket noi Selenium vao Chrome...")
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    print("CONNECTED!")
    print("URL:", driver.current_url)
    
    prompt = "Xin chào Chuyên gia! Tôi là hệ thống AI Antigravity. Rất vui được hợp tác cùng bạn trong dự án AI Quant Trading này."
    
    print("Vui long dam bao da dang nhap Google. Kich ban se cho 15s...")
    time.sleep(15) 
    
    try:
        print("Dang tim o nhap lieu...")
        editor = driver.find_element(By.CSS_SELECTOR, 'rich-textarea, div[role="textbox"], textarea')
        editor.click()
        driver.execute_script("arguments[0].textContent = arguments[1];", editor, prompt)
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        time.sleep(1)
        editor.send_keys(Keys.ENTER)
        print("Da gui loi chao thanh cong!")
    except Exception as e:
        print("Khong the gui loi chao (co the chua dang nhap Google). Loi:", e)
        
    print("\nHoan tat kich ban. Chrome van se tiep tuc mo. Script tu dong dong sau 5 phut...")
    time.sleep(300)

if __name__ == "__main__":
    main()
