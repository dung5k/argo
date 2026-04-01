import os
import json
import torch
import numpy as np
import pandas as pd
from flask import Flask, request, Response

try:
    from train_final import CNN_LSTM_Model
except ImportError:
    try:
        from src.train_final import CNN_LSTM_Model
    except ImportError:
        pass # Handle in execution

app = Flask(__name__)

# Toàn cục lưu trữ Model để khỏi load lại mỗi Tick
models = {}
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
num_features = 112

def load_models_once():
    """Tải 3 Phiên Não Bộ lên RAM để bắn API tức thời"""
    global models, num_features
    genes_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\best_genes.json"
    
    window_size, cnn_filters, lstm_units, lstm_layers, dropout_rate = 60, 16, 128, 2, 0.2
    if os.path.exists(genes_path):
        with open(genes_path, "r", encoding='utf-8') as f:
            genes = json.load(f)
            window_size = genes.get("window_size", 60)
            cnn_filters = genes.get("cnn_filters", 16)
            lstm_units = genes.get("lstm_units", 128)
            lstm_layers = genes.get("lstm_layers", 2)
            dropout_rate = genes.get("dropout_rate", 0.2)
            
    base_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\models"
    for session in ["asian", "european", "us"]:
        model = CNN_LSTM_Model(num_features, cnn_filters, lstm_units, lstm_layers, dropout_rate).to(device)
        weights_path = os.path.join(base_path, f"xauusd_{session}_weights.pth")
        if os.path.exists(weights_path):
            model.load_state_dict(torch.load(weights_path, map_location=device, weights_only=True))
        model.eval()
        models[session] = model
        
    return window_size

WINDOW_SIZE = load_models_once()

def get_session(hour):
    if 8 <= hour < 13: return "european"
    elif 13 <= hour < 22: return "us"
    else: return "asian"

@app.route('/api/history', methods=['GET'])
def get_history():
    """
    MT5 Gọi Lệnh này lúc Vừa Gắn Indicator.
    Trả về Lực Bò (0-1) của 1000 nến cuối cùng.
    Format: Timestamp,Score\nTimestamp,Score
    """
    limit = int(request.args.get('limit', 1000))
    parquet_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\final_features_2d.parquet"
    
    if not os.path.exists(parquet_path):
        return "Error: No Features Data", 400
        
    # Đọc Parquet siêu nhanh
    df = pd.read_parquet(parquet_path)
    
    # Chỉ lấy phần đuôi cần thiết + Lượng nến chừa hao (Window Size)
    if len(df) > limit + WINDOW_SIZE:
        df = df.iloc[-(limit + WINDOW_SIZE):]
        
    if len(df) <= WINDOW_SIZE:
        return "Error: Not enough data", 400
        
    values = df.values
    times = df.index
    
    X_batch = []
    t_batch = []
    sess_batch = []
    
    # Cắt Sliding Window (Hàng loạt)
    for i in range(len(df) - WINDOW_SIZE):
        window = values[i : i + WINDOW_SIZE]
        X_batch.append(window)
        # Nến mục tiêu là nến cuối cùng của Window
        t = times[i + WINDOW_SIZE - 1] 
        t_batch.append(int(t.timestamp()))
        sess_batch.append(get_session(t.hour))
        
    X_tensor = torch.tensor(np.array(X_batch), dtype=torch.float32).to(device)
    
    # Chia mẻ inference theo từng Session Model
    scores = np.zeros(len(X_batch))
    
    with torch.no_grad():
        for i in range(len(X_batch)):
            sess = sess_batch[i]
            model = models[sess]
            # Inference từng nến (có thể tối ưu thành batch, nhưng 1000 nến C++ MQL gọi 1 lần lúc bật máy thì O(N) vẫn mất < 0.2s)
            xx = X_tensor[i:i+1] 
            out = model(xx)
            probs = torch.softmax(out, dim=1).squeeze()
            prob_up = probs[1].item() if probs.dim() > 0 else 0.5
            scores[i] = prob_up
            
    # Tạo CSV Thô cho MT5 Parse dễ dàng
    csv_lines = [f"{t_batch[i]},{scores[i]:.4f}" for i in range(len(t_batch))]
    response_text = "\n".join(csv_lines)
    
    return Response(response_text, mimetype='text/plain')

@app.route('/api/live', methods=['GET'])
def get_live():
    """
    MT5 gọi lệnh này Cực Nhanh mỗi Tích Tắc.
    Chỉ tốn 10 mili-giây.
    """
    # Mở đuôi Parquet (đã được trade_mt5.py nhồi vào RAM/Disk mỗi phút)
    parquet_path = r"C:\Users\Le Anh Dung\OneDrive\Apps\ck\forex_predictor\data\final_features_2d.parquet"
    if not os.path.exists(parquet_path):
        return "0,0.5" # Timestamp 0, Tỉ lệ 50/50 
        
    # Chỉ load vài dòng cuối cùng từ Disk (Siêu nhẹ)
    import pyarrow.parquet as pq
    table = pq.read_table(parquet_path)
    df = table.to_pandas().tail(WINDOW_SIZE)
    
    if len(df) < WINDOW_SIZE:
        return "0,0.5"
        
    X_tensor = torch.tensor(df.values, dtype=torch.float32).unsqueeze(0).to(device)
    
    current_time = df.index[-1]
    sess = get_session(current_time.hour)
    model = models[sess]
    
    with torch.no_grad():
        out = model(X_tensor)
        probs = torch.softmax(out, dim=1).squeeze()
        prob_up = probs[1].item()
        
    response_text = f"{int(current_time.timestamp())},{prob_up:.4f}"
    return Response(response_text, mimetype='text/plain')

if __name__ == '__main__':
    print("🔥 HỆ THỐNG MẮT THẦN API ĐÃ KHỞI CHẠY TẠI CỔNG 5050 🔥")
    print("   Lắng nghe tín hiệu TensorPyTorch từ MT5 C++...")
    app.run(host='127.0.0.1', port=5050, debug=False)
