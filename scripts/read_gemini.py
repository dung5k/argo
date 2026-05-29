import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    script = """
    var bubbles = document.querySelectorAll('.message-content, model-response');
    for(var i = bubbles.length - 1; i >= 0; i--) {
        var text = bubbles[i].innerText;
        if (text && text.trim().length > 10 && !text.includes('Xin chào Chuyên gia')) {
            return text.trim();
        }
    }
    return "NO_RESPONSE";
    """
    res = driver.execute_script(script)
    print("=== GEMINI RESPONSE ===")
    print(res)
    print("=======================")

if __name__ == "__main__":
    main()
