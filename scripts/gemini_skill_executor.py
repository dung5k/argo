import sys
import os
import io
import json
import time
import argparse
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def setup_driver():
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(EdgeChromiumDriverManager().install())
    return webdriver.Edge(service=service, options=options)

def human_typing(driver, text):
    editor = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'rich-textarea p, rich-textarea div[contenteditable="true"], rich-textarea'))
    )
    editor.click()
    time.sleep(0.5)
    
    actions = ActionChains(driver)
    for char in text:
        actions.send_keys(char)
        actions.perform()
        time.sleep(0.01) # Simulate fast human typing
    time.sleep(0.5)

def import_codebase(driver):
    print("Finding + button to import code...")
    js_find_plus = """
        let inputArea = document.querySelector('rich-textarea')?.closest('.input-area') || document.querySelector('rich-textarea')?.parentElement?.parentElement?.parentElement;
        if (!inputArea) return null;
        let buttons = Array.from(inputArea.querySelectorAll('button'));
        return buttons.find(b => (b.getAttribute('aria-label') || '').includes('Upload') || (b.getAttribute('aria-label') || '').includes('Tải') || (b.getAttribute('aria-label') || '').includes('Add'));
    """
    plus_btn = driver.execute_script(js_find_plus)
    if not plus_btn:
        print("Could not find + button!")
        return False
        
    ActionChains(driver).move_to_element(plus_btn).click().perform()
    time.sleep(1)
    
    js_find_more = """
        let all = Array.from(document.querySelectorAll('*'));
        return all.find(e => e.children.length <= 1 && e.innerText && e.innerText.trim() === 'More uploads' && e.offsetWidth > 0) || 
               all.find(e => e.children.length <= 1 && e.innerText && e.innerText.trim().includes('More uploads') && e.offsetWidth > 0);
    """
    more_uploads = driver.execute_script(js_find_more)
    if more_uploads:
        ActionChains(driver).move_to_element(more_uploads).perform()
        time.sleep(1)
        
    js_find_import = """
        let all = Array.from(document.querySelectorAll('*'));
        return all.find(e => e.children.length === 0 && e.innerText && e.innerText.includes('Import code') && e.offsetWidth > 0) || 
               all.find(e => e.children.length <= 1 && e.innerText && e.innerText.includes('Import code') && e.offsetWidth > 0);
    """
    import_code = driver.execute_script(js_find_import)
    if not import_code:
        print("Could not find 'Import code' in menu!")
        driver.execute_script("document.body.click();") # Close menu
        return False
        
    ActionChains(driver).move_to_element(import_code).click().perform()
    time.sleep(2)
    
    print("Waiting for dialog and typing Github repo URL...")
    repo_url = "https://github.com/dung5k/forex_predictor.git"
    
    js_type_repo = f"""
        let dialog = document.querySelector('dialog, [role="dialog"], .mat-mdc-dialog-container');
        if (!dialog) return false;
        let inputs = Array.from(dialog.querySelectorAll('input'));
        let input = inputs.find(i => i.getBoundingClientRect().width > 0 && i.getBoundingClientRect().height > 0);
        if (input) {{
            input.value = '{repo_url}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            return true;
        }}
        return false;
    """
    
    found = False
    for _ in range(5):
        if driver.execute_script(js_type_repo):
            found = True
            break
        time.sleep(1)
        
    if not found:
        print("Could not find input box for repo URL")
        ActionChains(driver).send_keys(Keys.ESCAPE).perform() # Try to escape dialog
        return False
        
    time.sleep(1)
    
    print("Clicking Import button...")
    js_click_add = """
        let dialog = document.querySelector('dialog, [role="dialog"], .mat-mdc-dialog-container');
        if (!dialog) return false;
        let buttons = Array.from(dialog.querySelectorAll('button'));
        let addBtn = buttons.find(b => b.innerText && (b.innerText.toLowerCase().includes('import') || b.innerText.toLowerCase().includes('add') || b.innerText.toLowerCase().includes('nhập')));
        if (addBtn) {
            addBtn.removeAttribute('disabled');
            // Try different types of clicks
            addBtn.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
            addBtn.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
            addBtn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
            addBtn.click();
            return true;
        }
        return false;
    """
    clicked = driver.execute_script(js_click_add)
    if clicked:
        print("Import button clicked via JS.")
    else:
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        print("Pressed Enter to submit import.")
        
    time.sleep(4)
    
    # Wait for dialog to disappear naturally
    js_wait_dialog = "return !!document.querySelector('dialog, [role=\"dialog\"], .mat-mdc-dialog-container');"
    for i in range(10):
        if not driver.execute_script(js_wait_dialog):
            print("Dialog closed.")
            break
        print(f"Waiting for dialog to close ({i+1}/10)...")
        time.sleep(1)
        
    if driver.execute_script(js_wait_dialog):
        print("Dialog still open, pressing Escape...")
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
    time.sleep(1)
    return True

def execute_skill(driver, prompt_text):
    print("Importing codebase as required by skill...")
    import_codebase(driver)
    
    print("Typing prompt...")
    human_typing(driver, prompt_text)
    
    print("Clicking send...")
    js_click_send = """
        let btn = document.querySelector('button[aria-label="Send message"], button[aria-label="Gửi tin nhắn"]');
        if (btn) {
            btn.removeAttribute('disabled');
            btn.click();
            return true;
        }
        return false;
    """
    driver.execute_script(js_click_send)
    print("Prompt sent successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", type=str, required=True)
    args = parser.parse_args()
    
    try:
        driver = setup_driver()
        execute_skill(driver, args.prompt)
    except Exception as e:
        print("ERROR:", e)
