import sys
import argparse
import time
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

def setup_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    return driver

def send_prompt(driver, prompt):
    print("Dang tim o nhap lieu va gui...")
    js_inject = """
        let promptText = arguments[0];
        let editor = document.querySelector('rich-textarea p, rich-textarea div[contenteditable="true"], rich-textarea');
        if (editor) {
            editor.textContent = promptText;
            editor.parentElement.dispatchEvent(new Event('input', { bubbles: true }));
            
            // Enable and click send button
            setTimeout(() => {
                let btn = document.querySelector('button[aria-label="Send message"], button[aria-label="Gửi tin nhắn"]');
                if (btn) {
                    btn.removeAttribute('disabled');
                    btn.click();
                }
            }, 500);
            return "SUCCESS";
        }
        return "FAILED: Editor not found";
    """
    res = driver.execute_script(js_inject, prompt)
    print("SEND STATUS:", res)

def read_response(driver, previous_count=0):
    print(f"Dang cho phan hoi tu Gemini (phai > {previous_count} messages)...")
    last_text = ""
    stable_count = 0
    max_wait = 120
    
    # Wait for the response to start and finish
    for _ in range(max_wait):
        time.sleep(1)
        script = """
        var responses = document.querySelectorAll('message-content');
        if (responses.length > arguments[0]) {
            return {
                count: responses.length,
                text: responses[responses.length - 1].innerText
            };
        }
        return { count: responses.length, text: "" };
        """
        res = driver.execute_script(script, previous_count)
        
        if res['count'] <= previous_count:
            continue # Still waiting for the new response to appear
            
        current_text = res['text']
        
        if current_text and current_text == last_text:
            stable_count += 1
        else:
            stable_count = 0
            
        last_text = current_text
        
        if stable_count >= 4 and current_text != "":
            break
            
    print("=== GEMINI RESPONSE ===")
    print(last_text)
    print("=======================")

def count_responses(driver):
    script = "return document.querySelectorAll('message-content').length;"
    return driver.execute_script(script)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", choices=["send", "read", "chat"])
    parser.add_argument("--prompt", type=str, default="")
    args = parser.parse_args()
    
    # Fix unicode printing in Windows console
    sys.stdout.reconfigure(encoding='utf-8')
    
    try:
        driver = setup_driver()
        if args.action == "send":
            send_prompt(driver, args.prompt)
        elif args.action == "read":
            read_response(driver, 0)
        elif args.action == "chat":
            count = count_responses(driver)
            send_prompt(driver, args.prompt)
            read_response(driver, count)
    except Exception as e:
        print("ERROR:", e)
