import os
import time
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def send_to_gemini(prompt_text):
    print("Connecting to Chrome on port 9222...")
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    pyperclip.copy(prompt_text)
    print("Copied prompt to clipboard.")
    
    try:
        # Find the input box
        input_box = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "rich-textarea, .text-input-field, div[contenteditable='true']"))
        )
        print("Found input box. Clicking to focus...")
        input_box.click()
        time.sleep(0.5)
        
        # Select all and delete (to clear previous text)
        print("Clearing previous text...")
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        
        # Paste new text
        print("Sending Ctrl+V...")
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        time.sleep(1)
        
        # Take screenshot before click
        driver.save_screenshot("d:/DungLA/client1/temp/before_click_send.png")
        
        # Look for send button specifically by class or aria-label
        # Sometimes the button is disabled until some input event fires.
        # Sending a space at the end to trigger input event just in case
        ActionChains(driver).send_keys(" ").perform()
        time.sleep(0.5)
        
        print("Trying to click Send button...")
        send_clicked = False
        try:
            send_btn = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='Send'], button.send-button, .bottom-right-container button")
            if send_btn and send_btn.is_displayed():
                send_btn.click()
                send_clicked = True
                print("Clicked Send button!")
        except Exception as e:
            print(f"Could not click button directly: {e}")
            
        if not send_clicked:
            print("Sending Enter...")
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(0.5)
            ActionChains(driver).key_down(Keys.CONTROL).send_keys(Keys.ENTER).key_up(Keys.CONTROL).perform()
            
        time.sleep(2)
        driver.save_screenshot("d:/DungLA/client1/temp/after_click_send.png")
        print("Prompt submitted successfully!")
    except Exception as e:
        print(f"Error during Gemini automation: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    prompt = """BỐI CẢNH (HỆ THỐNG GIAO DỊCH LÕI - PHIÊN BẢN 6):
Chúng tôi đang tinh chỉnh mô hình Neural Network (Transformer MTF) cho bot giao dịch.
Hiện tại, WinRate đang ở mức 0.0% trong quá trình Test. Hãy đóng vai một chuyên gia nghiêm khắc và phân tích mã nguồn/cấu hình để tìm ra lỗ hổng, đề xuất phương án và đặt 1 câu hỏi phản biện sắc bén."""
    send_to_gemini(prompt)
