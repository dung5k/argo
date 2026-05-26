import os
import json
import time
import cv2
import numpy as np
import mss
import pyautogui
import threading

pyautogui.FAILSAFE = False

class AutoClicker(threading.Thread):
    def __init__(self, config_path, templates_dir):
        super().__init__()
        self.config_path = config_path
        self.templates_dir = templates_dir
        self.daemon = True # Allows program to exit even if this thread is running
        self.templates = []
        self._last_template_load = 0

    def _load_templates(self):
        # Reload templates every 10 seconds to detect new files
        current_time = time.time()
        if current_time - self._last_template_load < 10:
            return
            
        self._last_template_load = current_time
        self.templates = []

        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)
            return

        for filename in os.listdir(self.templates_dir):
            if filename.lower().endswith(".png"):
                filepath = os.path.join(self.templates_dir, filename)
                template = cv2.imread(filepath, cv2.IMREAD_COLOR)
                if template is not None:
                    self.templates.append({
                        "name": filename,
                        "image": template
                    })
        if self.templates:
            print(f"[AutoClicker] Loaded {len(self.templates)} templates.")

    def run(self):
        print("[AutoClicker] Background thread started.")
        with mss.mss() as sct:
            while True:
                try:
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        full_config = json.load(f)
                        config = full_config.get("auto_clicker", {})
                except Exception as e:
                    print(f"[AutoClicker] Error reading config: {e}")
                    time.sleep(2)
                    continue
                
                if not config.get("enabled", True):
                    time.sleep(config.get("scan_interval", 1.0))
                    continue

                self._load_templates()

                if not self.templates:
                    time.sleep(config.get("scan_interval", 1.0))
                    continue

                region = config.get("region", {"top": 0, "left": 0, "width": 1920, "height": 1080})
                threshold = config.get("confidence_threshold", 0.85)
                
                try:
                    # Capture screen
                    screenshot = sct.grab(region)
                    # Convert to numpy array for cv2
                    img_np = np.array(screenshot)
                    # Convert from BGRA to BGR
                    img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

                    clicked = False
                    for tmpl in self.templates:
                        template_img = tmpl["image"]
                        h, w = template_img.shape[:2]
                        
                        # Match template
                        result = cv2.matchTemplate(img_bgr, template_img, cv2.TM_CCOEFF_NORMED)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

                        if max_val >= threshold:
                            print(f"[AutoClicker] Found '{tmpl['name']}' (confidence {max_val:.2f} >= {threshold})!")
                            
                            # Calculate absolute screen coordinates (center of the matched region)
                            click_x = region["left"] + max_loc[0] + w // 2
                            click_y = region["top"] + max_loc[1] + h // 2
                            
                            print(f"[AutoClicker] -> Clicking at ({click_x}, {click_y})")
                            pyautogui.click(x=click_x, y=click_y)
                            clicked = True
                            break # Only click one thing per scan
                    
                    if clicked:
                        time.sleep(config.get("cooldown_after_click", 2.0))
                    else:
                        time.sleep(config.get("scan_interval", 0.5))

                except Exception as e:
                    print(f"[AutoClicker] Error during scan: {e}")
                    time.sleep(2)

if __name__ == '__main__':
    # For independent testing
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    tmpl_dir = os.path.join(os.path.dirname(__file__), "templates")
    clicker = AutoClicker(config_file, tmpl_dir)
    clicker.start()
    while True:
        time.sleep(1)
