import sys
import json
import os
import time
from playwright.sync_api import sync_playwright

def main():
    print("Khoi dong Playwright ket noi toi Gemini...")
    user_data_dir = r"C:\temp\playwright_gemini_profile"
    
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 800}
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        conv_file = r"d:\DungLA\client1\.agent\gemini_conversations.json"
        topic = "Review_Master_Roadmap"
        conversations = {}
        if os.path.exists(conv_file):
            with open(conv_file, 'r', encoding='utf-8') as f:
                try: conversations = json.load(f)
                except: pass
                
        if topic in conversations:
            url = conversations[topic]
            print(f"Tiep tuc chu de: {topic}")
            page.goto(url)
        else:
            print("Chu de moi, truy cap trang chu Gemini...")
            page.goto("https://gemini.google.com/app")
            
        print("Vui long dam bao da dang nhap Google. Dang cho 5s...")
        time.sleep(5)
        
        prompt = """Bạn là một chuyên gia hạng nặng VÔ CÙNG NGHIÊM KHẮC VÀ KHÓ TÍNH trong lĩnh vực hệ thống giao dịch tài chính. Đừng ngại chỉ trích. Cùng tôi thực hiện phản biện 2 chiều: VẤN ĐỀ CẦN GIẢI QUYẾT: Review lộ trình 5 giai đoạn đưa AI Quant vào thực chiến (Master Roadmap). ĐỀ XUẤT CỦA TÔI: Giai đoạn 1 (Đào tạo In-sample), Giai đoạn 2 (Kiểm định mù OOS), Giai đoạn 3 (Paper Trading), Giai đoạn 4 (Quản trị vốn & Circuit Breaker), Giai đoạn 5 (Tiền thật & Tái huấn luyện). NHIỆM VỤ CỦA BẠN: 1. Tấn công trực diện vào lỗ hổng của quy trình này. 2. Đưa ra cách tiếp cận tốt hơn. 3. Đặt lại 1 câu hỏi sắc bén."""
        
        try:
            print("Dang tim o nhap van ban (rich-textarea)...")
            editor = page.wait_for_selector('rich-textarea, div[role="textbox"], textarea', timeout=15000)
            if editor:
                print("Da tim thay! Dang nhap prompt...")
                editor.click()
                page.keyboard.insert_text(prompt)
                time.sleep(1)
                
                print("Gui cau hoi...")
                page.keyboard.press("Enter")
                
                print("Da gui! Dang cho phan hoi (15s)...")
                time.sleep(15)
                
                new_url = page.url
                conversations[topic] = new_url
                with open(conv_file, 'w', encoding='utf-8') as f:
                    json.dump(conversations, f, indent=2)
                
                print("Luu URL thanh cong:", new_url)
            else:
                print("Khong tim thay o nhap lieu!")
        except Exception as e:
            print(f"Loi: {e}")
            
        print("\nHoan tat kich ban. Giu trinh duyet them 60s de sep xem...")
        time.sleep(60)
        browser.close()

if __name__ == "__main__":
    main()
