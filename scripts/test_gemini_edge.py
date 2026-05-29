import time
import subprocess
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager

def main():
    print("Starting Edge with Remote Debugging...")
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    
    # Khởi động Edge (nếu chưa chạy) với port 9222
    subprocess.Popen([edge_path, "--remote-debugging-port=9222", "https://gemini.google.com/"])
    time.sleep(3) # Chờ Edge lên
    
    print("Connecting Selenium to Edge...")
    options = Options()
    options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    
    # Sử dụng webdriver_manager để tự tải driver phù hợp
    service = Service(EdgeChromiumDriverManager().install())
    
    driver = webdriver.Edge(service=service, options=options)
    
    print("CONNECTED!")
    print("URL:", driver.current_url)
    print("Title:", driver.title)
    
    print("Ready to execute Peer-Review Protocol.")
    
    # Giữ cửa sổ để sếp xem
    # input("Press Enter to exit...")
    
if __name__ == "__main__":
    main()
