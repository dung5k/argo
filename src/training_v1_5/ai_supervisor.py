import requests
import os
import json
import re

def call_llm_meta_optimizer(history_buffer, current_epoch, base_dir=None):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model_name = os.environ.get("LLM_MODEL", "gemini-3-flash-preview")
    
    if base_dir:
        import pathlib
        cfg_path = pathlib.Path(base_dir) / "tg_config.json"
        if cfg_path.exists():
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    c = json.load(f)
                    api_key = c.get("gemini_api_key", api_key)
                    model_name = c.get("llm_model", model_name)
            except: pass
            
    if not api_key:
        print("[AI SUPERVISOR] ⚠️ Không có GEMINI_API_KEY (hoặc gemini_api_key) trong môi trường hoặc tg_config.json. Bỏ qua.")
        return None

    # Google Gemini REST API endpoint    
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        
    prompt = {
        "current_epoch": current_epoch,
        "sessions_status": history_buffer
    }
    
    sys_prompt = """Bạn là AI Supervisor (Meta-Optimizer) giám sát quá trình training của Trading Bot đa phiên.
Nhiệm vụ: Phân tích history_buffer và trả về 1 JSON hợp lệ theo format STRICT. 
Ngoài Soft configs cũ (LR, WD), bạn được cấp thêm quyền thay đổi:
- `active_window_size`: Từ 30 đến 60. Thay đổi ACTIVE_WINDOW_SIZE của Curriculum Masking (tăng khó/giảm mờ).
- `label_smoothing`: Từ 0.05 đến 0.2. Làm mượt loss chống Model bị Overconfidence nổ to.
- `patience`: Khởi tạo 10. Giảm xuống nếu đồ thị loss đóng băng ngang quá lâu mà ko rớt LR.

{
  "global_reasoning": [
    "Bước 1: So sánh cục diện các phiên...",
    "Bước 2: Phát hiện bất thường cục bộ..."
  ],
  "analysis_report": "Tóm tắt ngắn (1-2 câu).",
  "telegram_message": "Nội dung ngắn gọn để gửi Tele.",
  "actions": {
    "0": {
       "session_evaluation": "Val loss tăng, đe doạ overfitting, tăng label_smoothing.",
       "action_type": "continue", 
       "new_lr": ...., 
       "weight_decay": ...., 
       "min_signals": 30,
       "active_window_size": 60,
       "label_smoothing": 0.15,
       "patience": 10
    },
    "1": {
       "session_evaluation": "Đi ngang quá lâu, bế tắc hoàn toàn, ép tái sinh.",
       "action_type": "force_phoenix"
    },
    "2": {
       "session_evaluation": "Hội tụ tốt, tăng window size để nới curriculum.",
       "action_type": "continue", "active_window_size": 45
    }
  },
  "global_action": "continue"
}

Luật:
- Mã phiên: 0 (Asia), 1 (London), 2 (NY). Trả đúng key 0,1,2 dạng chuỗi.
- action_type: "continue", "stop", hoặc "force_phoenix".
- Hàm chỉ chấp nhận strict JSON string, tuyệt đối KHÔNG markdown.
"""
    try:
        resp = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {
                    "parts": [{"text": sys_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": json.dumps(prompt)}]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            },
            timeout=40
        )
        if resp.status_code == 200:
            data = resp.json()
            try:
                content = data["candidates"][0]["content"]["parts"][0]["text"]
            except KeyError:
                print(f"[AI SUPERVISOR] ⚠️ JSON parse error từ Google: {data}")
                return None
                
            content = re.sub(r"```json\s*", "", content).replace("```", "").strip()
            return json.loads(content)
        else:
            print(f"[AI SUPERVISOR] ⚠️ Lỗi API Gemini: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"[AI SUPERVISOR] ⚠️ Lỗi Exception: {e}")
    return None

def ask_ai_for_phoenix_strategy(s_name: str, history_buffer: dict, base_dir: str):
    """
    Hỏi AI chọn 1 trong 4 chiến lược đột biến (A, B, C, D) cho mạng bị chết lâm sàng.
    Trả về Dict: {"strategy": "A", "reason": "...", "action_log": "..."}
    """
    cfg_path = os.path.join(base_dir, "data", "bot_config_xau.json")
    if not os.path.exists(cfg_path):
        cfg_path = os.path.join(base_dir, "data", "bot_config.json")
        
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
            
    api_key = cfg.get("gemini_api_key", "").strip()
    if not api_key:
        api_key = "AIzaSyBuJP93STno4RBbF-wQACneWKQ6kF22-3o"
        
    if not api_key or not api_key.startswith("AIza"):
        print("[PHOENIX AI] Không tìm thấy API Key hợp lệ, tự động Fallback về Random!")
        return None
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    session_data = history_buffer.get(s_name, {}) if isinstance(s_name, str) else history_buffer
    
    prompt = {
        "event": "PHOENIX_RESTART_TRIGGER",
        "target_session": s_name,
        "stagnation_duration_epochs": 10,
        "current_state": session_data
    }
    
    sys_prompt = """ĐÂY LÀ KHẨN CẤP. Mạng Nơ-ron của phiên giao dịch này đã đóng băng xuyên suốt 10 Epoch không có đột biến (Validation Loss nằm ngang hoặc đi lùi). 
Theo quy trình PHOENIX RESTART, hệ thống đã Reset lại trọng số về đỉnh cũ tốt nhất. 
Nhiệm vụ của bạn: Dựa vào tình trạng Loss và LR gần nhất, chỉ định 1 trong 4 mũi vắc-xin Tái Sinh (A, B, C, D) phù hợp nhất.
- Chọn A (Spike LR mạnh): Nếu Learning Rate (LR) gần đây quá bé (<5e-5).
- Chọn B (Noise Injection): Nếu loss chạy thành một đường thẳng tắp kẹt cứng bất kể LR.
- Chọn C (Fine-tune giỏ giọt): Nếu VLoss nhảy múa dữ dội, cần ép đi nhẹ.
- Chọn D (Data Shuffle thuần): Nếu muốn xào bài làm lại từ đầu.

Chú ý: Trả về CHUẨN JSON chứa 3 field:
{
  "strategy": "A", (Chỉ đúng chữ cái A, B, C hoặc D)
  "reason": "Lý do ngắn 1 câu",
  "telegram_message": "Nội dung báo cáo lên phòng điều hành về chiến dịch tái sinh này"
}
"""
    try:
        resp = requests.post(
            api_url,
            json={
                "system_instruction": {
                    "parts": [{"text": sys_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": json.dumps(prompt)}]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            },
            timeout=20
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            content = re.sub(r"```json\s*", "", content).replace("```", "").strip()
            return json.loads(content)
        else:
            print(f"[PHOENIX AI] ⚠️ API HTTP Code {resp.status_code}")
    except Exception as e:
        print(f"[PHOENIX AI] ⚠️ Network Error: {e}")
    return None
