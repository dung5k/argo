import os
import sys

def list_runs():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    runs_dir = os.path.join(base_dir, "runs")
    
    if not os.path.exists(runs_dir):
        print("Trống (Thư mục runs không tồn tại)")
        return
        
    print("="*50)
    print("CÂY THƯ MỤC 'runs' TRÊN CLIENT (Bỏ qua runs/old)")
    print("="*50)
    
    empty = True
    for root, dirs, files in os.walk(runs_dir):
        # Bỏ qua thư mục old
        if "old" in root.split(os.sep):
            continue
            
        rel_path = os.path.relpath(root, runs_dir)
        if rel_path == ".":
            rel_path = ""
        else:
            empty = False
            print(f"\n📂 {rel_path}/")
            
        for f in files:
            empty = False
            size = os.path.getsize(os.path.join(root, f)) / (1024*1024)
            print(f"   📄 {f} ({size:.2f} MB)")
            
    if empty:
        print("Thu mục rỗng.")
    print("="*50)

if __name__ == "__main__":
    list_runs()
