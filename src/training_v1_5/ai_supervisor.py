import requests
import os
import json
import re

def call_llm_meta_optimizer(history_buffer, current_epoch, base_dir=None):
    api_key = os.environ.get("LLM_API_KEY", "")
    model_name = os.environ.get("LLM_MODEL", "openai/gpt-4o-mini")
    api_base = os.environ.get("LLM_API_BASE", "https://openrouter.ai/api/v1/chat/completions")
    
    if base_dir:
        import pathlib
        cfg_path = pathlib.Path(base_dir) / "tg_config.json"
        if cfg_path.exists():
            try:
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    c = json.load(f)
                    api_key = c.get("llm_api_key", api_key)
                    model_name = c.get("llm_model", model_name)
                    api_base = c.get("llm_api_base", api_base)
            except: pass
            
    if not api_key:
        print("[AI SUPERVISOR] ⚠️ Không có LLM_API_KEY trong môi trường hoặc tg_config.json. Bỏ qua.")
        return None
        
    prompt = {
        "current_epoch": current_epoch,
        "sessions_status": history_buffer
    }
    
    sys_prompt = """Bạn là AI Supervisor (Meta-Optimizer) giám sát quá trình training của Trading Bot đa phiên.
Nhiệm vụ: Phân tích history_buffer và trả về 1 JSON hợp lệ theo format STRICT (không markdown lồng, chỉ JSON object):

{
  "analysis_report": "Tóm tắt ngắn (1-2 câu).",
  "telegram_message": "Nội dung ngắn gọn để gửi Tele.",
  "actions": {
    "0": {"action_type": "continue", "new_lr": ...., "weight_decay": ...., "min_signals": 30},
    "1": {"action_type": "force_phoenix", "new_lr": ...., "weight_decay": ...., "min_signals": 25},
    "2": {"action_type": "stop"}
  },
  "global_action": "continue"
}

Luật:
- Mã phiên: 0 (Asia), 1 (London), 2 (NY). Trả đúng key 0,1,2 dạng chuỗi nếu bạn hiểu.
- new_lr: float từ 1e-6 đến 1e-2. weight_decay: 0 đến 0.1. min_signals: nguyên 10..50.
- action_type: "continue", "stop", hoặc "force_phoenix".
- Bắt buộc trả về thuần JSON, không có ```json tag.
"""
    try:
        resp = requests.post(
            api_base,
            headers={
                "Authorization": f"Bearer {api_key}", 
                "Content-Type": "application/json"
            },
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": json.dumps(prompt)}
                ],
                "response_format": {"type": "json_object"}
            },
            timeout=40
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            content = re.sub(r"```json\s*", "", content).replace("```", "").strip()
            return json.loads(content)
        else:
            print(f"[AI SUPERVISOR] ⚠️ Lỗi API: {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"[AI SUPERVISOR] ⚠️ Lỗi Exception: {e}")
    return None
