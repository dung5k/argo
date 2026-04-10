import requests
import os
import json
import re

def call_llm_meta_optimizer(history_buffer, current_epoch, base_dir=None):
    api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyBuJP93STno4RBbF-wQACneWKQ6kF22-3o")
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
    
    sys_prompt = """Bạn là AI Supervisor (Meta-Optimizer) giám sát quá trình training của Trading Bot Forex (Unified V2).
Nhiệm vụ: Phân tích history_buffer và trả về 1 JSON strict theo đúng format dưới đây.

Danh sách tham số bạn được phép điều chỉnh (tất cả đều optional):
- `new_lr`           : float, 1e-6..1e-2.  Learning Rate hiện tại của optimizer.
- `base_lr`          : float, 1e-5..1e-3.  Base LR dùng khi Phoenix khởi động lại (chiến lược A/B). Chỉnh khi thấy spike quá mạnh hoặc yếu.
- `weight_decay`     : float, 0..0.1.      Weight decay của AdamW. Tăng nếu overfit.
- `active_window_size`: int, 10..60.       Số nến cuối Model được "mở mắt" (Curriculum Masking). Tăng dần khi WR cải thiện.
- `masked_features`  : list[str] hoặc [].  Danh sách tên features bị mask hoàn toàn (zero-out). Dùng khi phát hiện feature gây nhiễu. Để [] để bỏ mask.
- `label_smoothing`  : float, 0.0..0.3.   Giảm xuống 0.05 nếu model thiếu tự tin. Tăng lên 0.2 nếu overconfident.
- `patience`         : int, 3..30.        LR Scheduler patience. Giảm nếu loss đóng băng quá lâu.
- `min_signals`      : int, 10..100.      Ngưỡng tín hiệu tối thiểu để ghi nhận đỉnh WR. Giảm nếu model quá thận trọng.
- `batch_size`       : int, 128/256/512/1024. Thay đổi batch size.
- `grad_clip`        : float, 0.5..5.0.   Max-norm gradient clipping. Giảm nếu gradients nổ.
- `action_type`      : "continue" | "stop" | "force_phoenix".  force_phoenix = kích hoạt tái sinh ngay lập tức.

Format JSON trả về (STRICT - không markdown, không comment):
{
  "global_reasoning": [
    "Bước 1: ...",
    "Bước 2: ..."
  ],
  "analysis_report": "Tóm tắt 1-2 câu về tình trạng tổng thể.",
  "telegram_message": "Tin nhắn Telegram ngắn gọn cho operator.",
  "actions": {
    "2": {
       "session_evaluation": "Mô tả tình trạng session.",
       "action_type": "continue",
       "new_lr": 0.0002,
       "base_lr": 0.0003,
       "weight_decay": 0.001,
       "active_window_size": 40,
       "masked_features": [],
       "label_smoothing": 0.15,
       "patience": 10,
       "min_signals": 30,
       "batch_size": 512,
       "grad_clip": 1.0
    }
  },
  "global_action": "continue"
}

Quy tắc:
- Chỉ cần trả field bạn muốn thay đổi, không cần trả tất cả.
- Key session duy nhất là "2" (Unified model, không chia phiên).
- action_type: "continue", "stop", hoặc "force_phoenix".
- TUYỆT ĐỐI không markdown, không code block, chỉ JSON thuần.
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
