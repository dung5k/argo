# -*- coding: utf-8 -*-
"""
scripts/run_v7_batch_training.py - Script tự động đào tạo tuần tự các phiên (Asian, London, NY)
và lặp lại liên tục để tối ưu tìm kiếm nhiều bộ não V7 khác nhau.
"""
import os
import sys
import time
import argparse
import traceback

# Add project root to path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Add huyen_thoai to path for dependency VTM
_HT = os.path.join(_ROOT, "huyen_thoai")
if _HT not in sys.path:
    sys.path.insert(0, _HT)

from src.training_v7.v7_ai_init import run_ai_initialization
from src.training_v7.v7_walk_forward import run_walk_forward_learning

def run_batch_training(loop_count=1):
    configs = [
        "v7_configs/v7_master_config_asian.json",
        "v7_configs/v7_master_config_london.json",
        "v7_configs/v7_master_config_ny.json"
    ]
    
    print(f"[START] [QTS-V7 Batch Training] Bat dau huan luyen tuan tu voi {loop_count} vong lap...")
    
    for loop_idx in range(1, loop_count + 1):
        print(f"\n[LOOP] ==================== VONG LAP HUAN LUYEN #{loop_idx} ====================")
        
        for cfg_path in configs:
            session_name = cfg_path.split("_")[-1].replace(".json", "").upper()
            print(f"\n[RUN] [SESSION {session_name}] Dang khoi dong dao tao phien {session_name}...")
            
            try:
                # 1. Khởi tạo cấu hình bot từ master config của phiên tương ứng
                print(f"   • Dang chay AI-Initialization voi {cfg_path}...")
                run_ai_initialization(master_config_path=cfg_path)
                
                # Cooldown ngắn tránh xung đột api
                time.sleep(2)
                
                # 2. Huấn luyện phiên tương ứng
                print(f"   • Dang khoi dong Walk-Forward Learning Loop...")
                workspace_dir = run_walk_forward_learning(bot_config_path="bot_config_v7.json")
                
                print(f"[OK] [SUCCESS] Hoan tat dao tao phien {session_name}! Brains & Results saved at:\n   {workspace_dir}")
                
            except Exception as e:
                print(f"[FAIL] [ERROR] Loi xay ra trong qua trinh huan luyen phien {session_name}: {e}")
                traceback.print_exc()
                if "AI_FEEDBACK_REQUIRED" in str(e):
                    print("[FATAL] Thoat khoi Batch Training de Antigravity AI phan tich!")
                    sys.exit(1)
                
            # Nghỉ ngắn giữa các phiên để hạ nhiệt hệ thống
            time.sleep(5)
            
    print("\n[SUCCESS] [BATCH DONE] Hoan thanh toan bo tien trinh huan luyen batch V7!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QTS-V7 Batch Training Runner")
    parser.add_argument("--loops", type=int, default=1, help="So lan lap lai chu ky dao tao ca 3 phien")
    args = parser.parse_args()
    
    run_batch_training(loop_count=args.loops)
