import time
import pyperclip
import pyautogui
import os

def send_prompt_to_gemini(prompt):
    print("Preparing to send prompt to Gemini using PyAutoGUI...")
    
    # Minimize IDE if it is Antigravity
    # Looking at the screen, the Antigravity IDE is currently active.
    # We can try to Alt+Tab or just click the Chrome taskbar icon.
    # The Chrome taskbar icon is at roughly x=675, y=1055.
    print("Activating Chrome window from taskbar...")
    pyautogui.click(675, 1055)
    time.sleep(1)
    
    # We are now presumably in Chrome. Let's make sure it's focused.
    # We'll click in the middle of the screen where the Gemini input box typically is.
    print("Clicking near center (assuming input box is there)...")
    pyautogui.click(960, 520) # Center of 1080p screen
    time.sleep(0.5)
    
    # 3. Copy to clipboard
    pyperclip.copy(prompt)
    print("Prompt copied to clipboard.")
    time.sleep(0.5)
    
    # 4. PyAutoGUI Paste
    print("Pasting with PyAutoGUI...")
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1)
    
    # 5. PyAutoGUI Enter
    print("Pressing Enter with PyAutoGUI...")
    pyautogui.press('enter')
    time.sleep(2)
    print("Done")

if __name__ == "__main__":
    prompt = """BỐI CẢNH (HỆ THỐNG GIAO DỊCH LÕI - PHIÊN BẢN 6):
Chúng tôi đang tinh chỉnh mô hình Neural Network (Transformer MTF) cho bot giao dịch.
Hiện tại, WinRate đang ở mức 0.0% trong quá trình Test. Hãy đóng vai một chuyên gia nghiêm khắc và phân tích mã nguồn/cấu hình để tìm ra lỗ hổng, đề xuất phương án và đặt 1 câu hỏi phản biện sắc bén."""
    send_prompt_to_gemini(prompt)
