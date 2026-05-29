import time
import json
import os
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

def main():
    print("Connecting to Edge on port 9222...")
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Edge(options=options)
    
    print(f"Current URL: {driver.current_url}")
    if "gemini.google.com" not in driver.current_url:
        driver.get("https://gemini.google.com/app")
        time.sleep(5)
    
    # 1. Read conversations history
    conv_file = "d:\\DungLA\\client1\\.agent\\gemini_conversations.json"
    topic = "Review_Master_Roadmap"
    conversations = {}
    if os.path.exists(conv_file):
        with open(conv_file, 'r', encoding='utf-8') as f:
            try:
                conversations = json.load(f)
            except:
                pass
                
    if topic in conversations:
        url = conversations[topic]
        print(f"Topic exists. Navigating to {url}")
        if driver.current_url != url:
            driver.get(url)
            time.sleep(4)
    else:
        print("New topic. Proceeding in current chat.")

    prompt = """Ban la mot chuyen gia hang nang VO CUNG NGHIEM KHAC VA KHO TINH trong linh vuc he thong giao dich tai chinh. Dung ngai chi trich. Cung toi thuc hien phan bien 2 chieu: VAN DE CAN GIAI QUYET: Review lo trinh 5 giai doan dua AI Quant vao thuc chien (Master Roadmap). DE XUAT CUA TOI: Giai doan 1 (Dao tao In-sample), Giai doan 2 (Kiem dinh mu OOS), Giai doan 3 (Paper Trading), Giai doan 4 (Quan tri von & Circuit Breaker), Giai doan 5 (Tien that & Tai huan luyen). NHIEM VU CUA BAN: 1. Tan cong truc dien vao lo hong cua quy trinh nay. 2. Dua ra cach tiep can tot hon. 3. Dat lai 1 cau hoi sac ben."""
    
    # Try to find the input box
    print("Finding text input...")
    try:
        # Gemini uses rich-textarea with contenteditable="true"
        editor = driver.find_element(By.CSS_SELECTOR, "rich-textarea p, div[contenteditable='true'], textarea")
        # Click it
        editor.click()
        # Paste the text
        print("Sending prompt...")
        # Since it's a contenteditable, we can execute JS to set text, or use send_keys
        driver.execute_script("arguments[0].textContent = arguments[1];", editor, prompt)
        
        # Trigger input event so React/Angular registers it
        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", editor)
        time.sleep(1)
        
        # Press Enter or find send button
        editor.send_keys(Keys.ENTER)
        print("Prompt sent!")
        
        # Wait for response (just wait a bit and save URL)
        time.sleep(5)
        new_url = driver.current_url
        conversations[topic] = new_url
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2)
            
        print("Done. Saved URL:", new_url)
    except Exception as e:
        print("Error interacting with Gemini:", e)

if __name__ == "__main__":
    main()
