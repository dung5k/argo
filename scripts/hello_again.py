import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

def main():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        print("URL hien tai:", driver.current_url)
        
        prompt = "Xin chào Chuyên gia! Tôi là hệ thống AI Antigravity. Rất vui được hợp tác cùng bạn trong dự án AI Quant Trading này."
        
        print("Dang tim o nhap lieu...")
        editor = driver.find_element(By.CSS_SELECTOR, 'rich-textarea, div[role="textbox"]')
        
        print("Dang focus vao o nhap lieu bang JS...")
        driver.execute_script("arguments[0].click();", editor)
        driver.execute_script("arguments[0].focus();", editor)
        time.sleep(1)
        
        print("Dang go phim...")
        actions = ActionChains(driver)
        actions.send_keys(prompt)
        actions.pause(1)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        
        print("Da gui thanh cong bang ActionChains!")
    except Exception as e:
        print("Loi:", e)

if __name__ == "__main__":
    main()
