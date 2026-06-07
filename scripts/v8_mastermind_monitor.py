# -*- coding: utf-8 -*-
"""
V8 Mastermind Monitor - Hội Đồng Phân Tích Đa-Agent
=====================================================
Mỗi chu kỳ báo cáo, Mastermind triệu tập "Hội đồng phân tích" gồm nhiều agent:
  1. [COLLECTOR]    - Thu thập log từ Argo1 & Argo2
  2. [QUANT]        - Phân tích Expectancy, Edge, WinRate
  3. [ML]           - Phân tích Loss convergence, Overfitting, Look-ahead bias
  4. [SIGNAL]       - Phân tích tần suất tín hiệu và chất lượng lọc nhiễu
  5. [SYNTHESIZER]  - Tổng hợp kết luận và đề xuất hành động
  6. [ACTION]       - Thực thi hành động tự động (restart, alert, adjust)
"""

import os
import sys
import re
import subprocess
import paramiko
import time

TELEGRAM_BOT = ".agent/send_to_tele.py"
CHANNEL_ID = "1816854047"
ARGO2_IP = "192.168.1.18"
ARGO2_USER = "dungla"
ARGO3_IP = "192.168.1.16"
ARGO3_USER = "dungla"
REPORT_INTERVAL = 300  # 5 phút
BE_WR = 51.5  # Mức hòa vốn WR cho M15 1:1 RR + Spread

# ==================== TIỆN ÍCH ====================

def send_tele(msg):
    subprocess.run([sys.executable, TELEGRAM_BOT, msg, "--channel", CHANNEL_ID])

def parse_log_lines(raw_text):
    """Parse log lines thành structured dicts. Trả về list of metric dicts."""
    results = []
    if not raw_text:
        return results
    for line in raw_text.strip().split('\n'):
        line = line.strip()
        m = re.search(
            r'Split\s+(\d+)\s*\|\s*Ep\s+(\d+)\s*\|'
            r'\s*Loss\(T/V\):\s*([\d.]+)/([\d.]+)\s*\|'
            r'\s*WR:\s*([\d.]+)%.*?Edge:\s*([+\-]?[\d.]+)%\s*\|'
            r'\s*Signals:\s*(\d+)\s*\(([\d.]+)/day\)',
            line
        )
        if m:
            results.append({
                'split': int(m.group(1)),
                'epoch': int(m.group(2)),
                'train_loss': float(m.group(3)),
                'val_loss': float(m.group(4)),
                'wr': float(m.group(5)),
                'edge': float(m.group(6)),
                'signals': int(m.group(7)),
                'signals_per_day': float(m.group(8)),
            })
    return results

# ==================== AGENT: COLLECTOR ====================

def agent_collector():
    """Thu thập log từ cả 2 node. Trả về (argo1_raw, argo2_raw, argo1_parsed, argo2_parsed)."""
    argo1_raw = _read_local_log()
    argo2_raw = _read_remote_log()
    return argo1_raw, argo2_raw, parse_log_lines(argo1_raw), parse_log_lines(argo2_raw)

def _read_local_log():
    log_file = "logs/v8_train_ARGO1.log"
    if not os.path.exists(log_file):
        return ""
    try:
        result = subprocess.run(
            ["powershell", "-Command", f"Get-Content {log_file} -Tail 15"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except:
        return ""

def _read_remote_log():
    REMOTE_BASE = "D:/DungLA/Argo"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        key_path = os.path.expanduser("~/.ssh/id_rsa")
        client.connect(ip, username=user, key_filename=key_path, timeout=5)
        cmd = f'powershell -Command "if (Test-Path {REMOTE_BASE}/logs/v8_train_ARGO2.log) {{ Get-Content {REMOTE_BASE}/logs/v8_train_ARGO2.log -Tail 15 }} else {{ echo \'No log\' }}"'
        stdin, stdout, stderr = client.exec_command(cmd)
        out = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        return out
    except Exception as e:
        return f"Lỗi SSH: {e}"

# ==================== AGENT: QUANT ====================

def agent_quant(parsed_data, node_name):
    """Phân tích Expectancy, Edge, WinRate. Trả về verdict string."""
    if not parsed_data:
        return f"📊 [QUANT] {node_name}: Không có dữ liệu để phân tích."

    latest = parsed_data[-1]
    edges = [d['edge'] for d in parsed_data]
    wrs = [d['wr'] for d in parsed_data]
    avg_edge = sum(edges) / len(edges)
    avg_wr = sum(wrs) / len(wrs)

    verdict = []
    verdict.append(f"📊 [QUANT] {node_name} (Split {latest['split']}):")

    # 1. Đánh giá Edge
    if avg_edge > 1.0:
        verdict.append(f"  Edge TB: {avg_edge:+.1f}% → TÍCH CỰC. Mô hình đang học được tín hiệu có ý nghĩa.")
    elif avg_edge > -1.0:
        verdict.append(f"  Edge TB: {avg_edge:+.1f}% → TRUNG TÍNH. Mô hình đang ở mức hòa vốn, chưa có lợi thế rõ ràng.")
    else:
        verdict.append(f"  Edge TB: {avg_edge:+.1f}% → TIÊU CỰC. Expectancy ÂM. Nếu R:R = 1:1, trader sẽ THUA RÒNG.")

    # 2. Độ ổn định WinRate
    wr_spread = max(wrs) - min(wrs)
    if wr_spread > 8:
        verdict.append(f"  WR dao động mạnh: {min(wrs):.1f}% → {max(wrs):.1f}% (biên độ {wr_spread:.1f}%). Mô hình KHÔNG ỔN ĐỊNH.")
    else:
        verdict.append(f"  WR ổn định: {min(wrs):.1f}% → {max(wrs):.1f}% (biên độ {wr_spread:.1f}%).")

    # 3. Kiểm tra mức hòa vốn
    pct_above_be = sum(1 for e in edges if e > 0) / len(edges) * 100
    verdict.append(f"  {pct_above_be:.0f}% epoch có Edge > 0 (vượt mức hòa vốn {BE_WR}%).")

    return '\n'.join(verdict)

# ==================== AGENT: ML ====================

def agent_ml(parsed_data, node_name):
    """Phân tích Loss convergence, rủi ro Overfitting. Trả về verdict string."""
    if not parsed_data:
        return f"🤖 [ML] {node_name}: Không có dữ liệu để phân tích."

    latest = parsed_data[-1]
    train_losses = [d['train_loss'] for d in parsed_data]
    val_losses = [d['val_loss'] for d in parsed_data]

    verdict = []
    verdict.append(f"🤖 [ML] {node_name} (Split {latest['split']}):")

    # 1. Loss Gap (phát hiện Overfitting)
    gaps = [v - t for t, v in zip(train_losses, val_losses)]
    latest_gap = gaps[-1]

    if latest_gap > 0.02:
        verdict.append(f"  🔴 CẢNH BÁO OVERFIT: Val_Loss > Train_Loss = {latest_gap:.4f}. Mô hình đang học thuộc dữ liệu!")
    elif latest_gap < -0.005:
        verdict.append(f"  🟡 Underfitting: Train > Val = {abs(latest_gap):.4f}. Mô hình chưa học đủ - có thể tăng epochs.")
    else:
        verdict.append(f"  🟢 Khoảng cách Loss: {latest_gap:+.4f} → Hội tụ tốt, chưa có dấu hiệu overfit.")

    # 2. Xu hướng Loss (còn đang cải thiện?)
    if len(val_losses) >= 3:
        recent_trend = val_losses[-1] - val_losses[0]
        if recent_trend < -0.005:
            verdict.append(f"  Xu hướng: Val_Loss GIẢM {abs(recent_trend):.4f} → Mô hình VẪN ĐANG HỌC.")
        elif recent_trend > 0.005:
            verdict.append(f"  Xu hướng: Val_Loss TĂNG {recent_trend:.4f} → ĐANG XẤU ĐI. Cần xem xét Early Stopping.")
        else:
            verdict.append(f"  Xu hướng: Val_Loss ĐI NGANG ({recent_trend:+.4f}) → Plateau. Có thể cần điều chỉnh Learning Rate.")

    # 3. Mức Loss tuyệt đối
    if latest['val_loss'] < 0.690:
        verdict.append(f"  Val_Loss {latest['val_loss']:.3f} → RẤT TỐT. Mô hình đang hội tụ mạnh.")
    elif latest['val_loss'] < 0.700:
        verdict.append(f"  Val_Loss {latest['val_loss']:.3f} → KHÁ. Gần mức tốt, cần theo dõi thêm.")
    else:
        verdict.append(f"  Val_Loss {latest['val_loss']:.3f} → TRUNG BÌNH. Mô hình chưa tìm được pattern rõ ràng.")

    return '\n'.join(verdict)

# ==================== AGENT: SIGNAL ====================

def agent_signal(parsed_data, node_name):
    """Phân tích tần suất tín hiệu và chất lượng lọc nhiễu."""
    if not parsed_data:
        return f"📡 [SIGNAL] {node_name}: Không có dữ liệu."

    latest = parsed_data[-1]
    signals_per_day_list = [d['signals_per_day'] for d in parsed_data]
    avg_spd = sum(signals_per_day_list) / len(signals_per_day_list)

    verdict = []
    verdict.append(f"📡 [SIGNAL] {node_name} (Split {latest['split']}):")

    # Đánh giá tần suất
    if avg_spd > 80:
        verdict.append(f"  {avg_spd:.0f} lệnh/ngày → QUÁ NHIỀU. Mô hình đang bắt cả nhiễu lẫn tín hiệu. Cần lọc ADX/Volume mạnh hơn.")
    elif avg_spd > 40:
        verdict.append(f"  {avg_spd:.0f} lệnh/ngày → HỢP LÝ cho M15. Đủ tần suất để có ý nghĩa thống kê.")
    elif avg_spd > 10:
        verdict.append(f"  {avg_spd:.0f} lệnh/ngày → ÍT. Mô hình lọc rất chặt. WR cần > 55% để bù đắp.")
    else:
        verdict.append(f"  {avg_spd:.0f} lệnh/ngày → QUÁ ÍT. Không đủ mẫu để đánh giá. Cần nới lỏng bộ lọc.")

    # Độ ổn định số lượng signal
    signal_counts = [d['signals'] for d in parsed_data]
    if len(set(signal_counts)) == 1:
        verdict.append(f"  Số lượng signal ĐỒNG ĐỀU ({signal_counts[0]}) qua các epoch → Mô hình chưa học lọc, chỉ dựa trên threshold cố định.")
    else:
        verdict.append(f"  Signal thay đổi: {min(signal_counts)} → {max(signal_counts)} → Mô hình đang học phân biệt tín hiệu.")

    return '\n'.join(verdict)

# ==================== AGENT: CRITIC (PHẢN BIỆN THUẬT TOÁN) ====================

def agent_critic(parsed_a1, parsed_a2, parsed_a3):
    """Agent CRITIC: Đặt câu hỏi sắc bén về thuật toán dựa trên kết quả thực tế.
    Mục tiêu: Tìm ra nguyên nhân gốc rễ nếu mô hình không cải thiện."""
    all_data = (parsed_a1 or []) + (parsed_a2 or [])
    if not all_data:
        return "❓ [CRITIC] Chưa có dữ liệu để phản biện."

    questions = []
    questions.append("❓ [CRITIC - PHẢN BIỆN THUẬT TOÁN]:")

    edges = [d['edge'] for d in all_data]
    wrs = [d['wr'] for d in all_data]
    val_losses = [d['val_loss'] for d in all_data]
    signals_list = [d['signals'] for d in all_data]
    avg_edge = sum(edges) / len(edges)
    avg_wr = sum(wrs) / len(wrs)

    # === 1. WinRate không cải thiện? ===
    if avg_wr < BE_WR:
        questions.append(f"  1️⃣ WR trung bình = {avg_wr:.1f}% < Mức hòa vốn {BE_WR}%. TẠI SAO mô hình không thắng nổi đồng xu tung ngẫu nhiên?")
        # Phân tích nguyên nhân có thể
        if avg_wr > 48 and avg_wr < 52:
            questions.append(f"     → WR dao động quanh 50% = Mô hình CÓ THỂ đang đoán NGẪU NHIÊN. Feature đầu vào có thực sự mang thông tin dự đoán không?")
        if avg_wr < 46:
            questions.append(f"     → WR < 46% = Mô hình đang đoán NGƯỢC chiều thị trường. Kiểm tra: Nhãn BUY/SELL có bị ĐẢO NGƯỢC không?")
    elif avg_wr > 55:
        questions.append(f"  1️⃣ WR = {avg_wr:.1f}% > 55%. Quá cao cho Forex M15. NGHI VẤN: Có Look-ahead bias không? Kiểm tra lại pipeline gán nhãn!")
    else:
        questions.append(f"  1️⃣ WR = {avg_wr:.1f}% - Mức chấp nhận được. Tiếp tục theo dõi xu hướng.")

    # === 2. Loss không giảm? ===
    if len(val_losses) >= 5:
        first_half = val_losses[:len(val_losses)//2]
        second_half = val_losses[len(val_losses)//2:]
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        loss_improvement = avg_first - avg_second

        if abs(loss_improvement) < 0.002:
            questions.append(f"  2️⃣ Loss KHÔNG CẢI THIỆN giữa nửa đầu ({avg_first:.4f}) và nửa sau ({avg_second:.4f}). Mô hình có thể đã BÃO HÒA.")
            questions.append(f"     → Giả thuyết: (a) Learning Rate quá nhỏ? (b) Kiến trúc Transformer không đủ sâu? (c) Feature đầu vào thiếu thông tin dự đoán?")
        elif loss_improvement < 0:
            questions.append(f"  2️⃣ Loss ĐANG TĂNG: {avg_first:.4f} → {avg_second:.4f}. Mô hình ĐANG XẤU ĐI qua các split.")
            questions.append(f"     → Giả thuyết: (a) Data distribution thay đổi (regime shift)? (b) Overfitting tích lũy?")

    # === 3. Signal count cố định? ===
    unique_signals = len(set(signals_list))
    if unique_signals <= 2:
        questions.append(f"  3️⃣ Số lượng Signal gần như KHÔNG THAY ĐỔI ({signals_list[0]}). TẠI SAO?")
        questions.append(f"     → Mô hình đang output xác suất gần đều cho 3 class (HOLD/BUY/SELL). Lớp phân loại cuối cùng (softmax) có thể bị COLLAPSE.")
        questions.append(f"     → Kiểm tra: Class weights có cân bằng không? Tỷ lệ HOLD vs BUY/SELL trong training data là bao nhiêu?")

    # === 4. So sánh 3-Layer vs 5-Layer ===
    if parsed_a1 and parsed_a2:
        a1_edges = [d['edge'] for d in parsed_a1]
        a2_edges = [d['edge'] for d in parsed_a2]
        a1_avg = sum(a1_edges) / len(a1_edges)
        a2_avg = sum(a2_edges) / len(a2_edges)

        if abs(a1_avg - a2_avg) < 1.0:
            questions.append(f"  4️⃣ 3-Layer ({a1_avg:+.1f}%) và 5-Layer ({a2_avg:+.1f}%) cho kết quả GIỐNG NHAU. Tăng độ sâu mô hình KHÔNG giúp ích.")
            questions.append(f"     → Giả thuyết: Bottleneck không nằm ở kiến trúc mà ở CHẤT LƯỢNG DỮ LIỆU hoặc CÁCH GÁN NHÃN.")
            questions.append(f"     → Đề xuất: Thay vì tăng layers, hãy thử cải thiện Feature Engineering (thêm FVG, OB, Fractal CHOCH).")

    # === 5. Câu hỏi chiến lược gốc rễ (Dựa trên Market Hypothesis cốt lõi) ===
    if avg_edge < -1:
        questions.append(f"  5️⃣ CÂU HỎI KIM CHỈ NAM: Với Edge = {avg_edge:+.1f}%, mô hình có đang hiểu đúng QUY LUẬT THỊ TRƯỜNG?")
        questions.append(f"     → [SMC/Liquidity]: Mô hình có đang bị lừa bởi râu nến quét thanh khoản (Liquidity Sweep) không? Nó có phân biệt được đâu là lệnh quét Stop-loss của Mập, đâu là dòng tiền đẩy Trend?")
        questions.append(f"     → [Fractal Timeframe]: Mô hình có đang sử dụng H4 để xác định xu hướng lớn và M15 để tìm điểm vào chưa? Hay nó đang mù quáng giao dịch ngược sóng H4?")
        questions.append(f"     → [Nhiễu vs Tín hiệu]: Target horizon hiện tại có đủ dài để thoát khỏi vùng nhiễu (bid/ask bounce) chưa?")

    return '\n'.join(questions)

# ==================== AGENT: SYNTHESIZER ==

def agent_synthesizer(quant_a1, ml_a1, sig_a1, quant_a2, ml_a2, sig_a2, quant_a3, ml_a3, sig_a3, parsed_a1, parsed_a2, parsed_a3, actions_taken):
    """Tổng hợp tất cả agent và đưa ra kết luận."""
    verdict = []
    verdict.append("=" * 40)
    verdict.append("🧠 [TỔNG HỢP & ĐỀ XUẤT]:")

    # So sánh hai node
    if parsed_a1 and parsed_a2:
        a1_edge = sum(d['edge'] for d in parsed_a1) / len(parsed_a1)
        a2_edge = sum(d['edge'] for d in parsed_a2) / len(parsed_a2)
        a1_split = parsed_a1[-1]['split']
        a2_split = parsed_a2[-1]['split']

        if a1_edge > a2_edge + 1:
            verdict.append(f"  → ARGO1 (3-Layer) đang VƯỢT TRỘI ARGO2 (5-Layer) về Edge ({a1_edge:+.1f}% vs {a2_edge:+.1f}%). Mô hình nhỏ có thể tốt hơn cho dữ liệu này.")
        elif a2_edge > a1_edge + 1:
            verdict.append(f"  → ARGO2 (5-Layer) đang VƯỢT TRỘI ARGO1 (3-Layer) về Edge ({a2_edge:+.1f}% vs {a1_edge:+.1f}%). Độ sâu mô hình đang phát huy hiệu quả.")
        else:
            verdict.append(f"  → Hai node TƯƠNG ĐƯƠNG về Edge ({a1_edge:+.1f}% vs {a2_edge:+.1f}%). Chưa có sự khác biệt có ý nghĩa.")

        verdict.append(f"  → Tiến độ: ARGO1 Split {a1_split}/256, ARGO2 Split {a2_split}/256.")

    # Sức khỏe tổng thể
    all_parsed = (parsed_a1 or []) + (parsed_a2 or [])
    if all_parsed:
        all_edges = [d['edge'] for d in all_parsed]
        avg_all = sum(all_edges) / len(all_edges)
        if avg_all < -1:
            verdict.append(f"  ⚠️ CẢNH BÁO: Edge trung bình toàn hệ thống = {avg_all:+.1f}%. Mô hình đang THUA hoặc HÒA VỐN.")
            verdict.append("  💡 ĐỀ XUẤT CHIẾN LƯỢC HÀNH ĐỘNG (ACTION PLAN):")
            verdict.append("     1. [TARGET HORIZON] Dự đoán 30 phút (shift -2) vẫn quá nhiễu. Đề nghị nâng lên H1 hoặc H2 (shift -4 hoặc -8) để lọc bớt 'Market Noise'.")
            verdict.append("     2. [FEATURE ENGINEERING] Bổ sung tín hiệu Breakout (ví dụ phá vỡ đỉnh đáy phiên Á/Âu) hoặc Volatility (ATR) vào bộ Feature.")
            verdict.append("     3. [LOSS FUNCTION] Hiện tại CrossEntropyLoss phạt đều mọi lỗi sai. Đề nghị chuyển sang Profit-Weighted Loss: Phạt cực nặng nếu đoán ngược xu hướng bão (Trend).")
            verdict.append("     4. [LEARNING RATE] Cấu hình LR=1e-3 có thể hơi lớn cho Transformer. Đề nghị giảm LR xuống 1e-4 kết hợp AdamW Weight Decay.")
        elif avg_all < 0:
            verdict.append(f"  ⏳ THEO DÕI: Edge trung bình = {avg_all:+.1f}%. Chưa có lợi thế nhưng chưa báo động. Chờ thêm 20-30 splits.")
        else:
            verdict.append(f"  ✅ TÍCH CỰC: Edge trung bình = {avg_all:+.1f}%. Mô hình đang cho thấy dấu hiệu học được pattern thực.")

    # Hành động đã thực thi từ ACTION agent
    if actions_taken:
        verdict.append("\n🔧 [HÀNH ĐỘNG ĐÃ THỰC THI]:")
        for a in actions_taken:
            verdict.append(f"  {a}")

    return '\n'.join(verdict)

# ==================== AGENT: ACTION (THỰC THI) ====================

def agent_action(parsed_a1, parsed_a2, parsed_a3):
    """Agent ACTION: Kiểm tra sức khỏe tiến trình và TỰ ĐỘNG hành động.
    Trả về danh sách các hành động ĐÃ THỰC HIỆN (không chỉ gợi ý)."""
    actions_taken = []

    # === ARGO1: Kiểm tra tiến trình local ===
    argo1_alive = _check_local_process("v8_training_loop")
    if not argo1_alive:
        actions_taken.append("🔄 ARGO1: Tiến trình ĐÃ CHẾT. Đang tự động KHỞI ĐỘNG LẠI...")
        spawn_argo1()
        actions_taken.append("✅ ARGO1: Đã gửi lệnh khởi động lại thành công.")
    elif not parsed_a1:
        actions_taken.append("⏳ ARGO1: Tiến trình đang chạy nhưng chưa có log mới. Có thể đang khởi tạo dữ liệu.")
    else:
        latest = parsed_a1[-1]
        actions_taken.append(f"✅ ARGO1: Đang chạy bình thường tại Split {latest['split']}, Epoch {latest['epoch']}.")

    # === ARGO2: Kiểm tra tiến trình từ xa ===
    argo2_alive = _check_remote_process("v8_training_loop")
    if not argo2_alive:
        actions_taken.append("🔄 ARGO2: Tiến trình ĐÃ CHẾT. Đang tự động KHỞI ĐỘNG LẠI...")
        spawn_argo2()
        actions_taken.append("✅ ARGO2: Đã gửi lệnh khởi động lại thành công.")
    elif not parsed_a2:
        actions_taken.append("⏳ ARGO2: Tiến trình đang chạy nhưng chưa có log mới. Có thể đang khởi tạo dữ liệu.")
    else:
        latest = parsed_a2[-1]
        actions_taken.append(f"✅ ARGO2: Đang chạy bình thường tại Split {latest['split']}, Epoch {latest['epoch']}.")

    # === Cảnh báo Edge cực tệ & AUTO-ML EVOLUTION ===
    all_edges = []
    if parsed_a1: all_edges.extend([d['edge'] for d in parsed_a1])
    if parsed_a2: all_edges.extend([d['edge'] for d in parsed_a2])
    
    if all_edges:
        avg_all = sum(all_edges) / len(all_edges)
        if avg_all < -1.0:
            actions_taken.append(f"⚠️ CẢNH BÁO AUTO-EVOLVE: Edge trung bình hệ thống là {avg_all:+.1f}% (dưới -1.0%).")
            config_path = "v8_configs/strategy_config.json"
            if os.path.exists(config_path):
                import json
                with open(config_path, "r", encoding="utf-8-sig") as f:
                    cfg = json.load(f)
                
                # Nếu đã từng mutate ở epoch này thì bỏ qua (dựa trên thời gian chỉnh sửa config)
                import time
                last_mod = os.path.getmtime(config_path)
                if time.time() - last_mod > 600: # 10 phút cooldown
                    old_shift = cfg.get("target_shift", -2)
                    if old_shift == -2:
                        cfg["target_shift"] = -4
                        cfg["learning_rate_base"] = 5e-4
                        actions_taken.append("🤖 AUTO-ML EVOLUTION: Nâng Target lên H1 (shift -4), giảm LR xuống 5e-4. Tiến hành Reset Toàn Hệ Thống!")
                    elif old_shift == -4:
                        cfg["target_shift"] = -8
                        cfg["loss_function"] = "ProfitWeightedLoss"
                        actions_taken.append("🤖 AUTO-ML EVOLUTION: Nâng Target lên H2 (shift -8), kích hoạt ProfitWeightedLoss. Tiến hành Reset Toàn Hệ Thống!")
                    else:
                        cfg["target_shift"] = -2
                        cfg["loss_function"] = "CrossEntropyLoss"
                        actions_taken.append("🤖 AUTO-ML EVOLUTION: Xoay vòng về Target 30m mặc định. Tiến hành Reset Toàn Hệ Thống!")
                    
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(cfg, f, indent=4)
                    
                    # Force Reset Checkpoints
                    try:
                        if os.path.exists("v8_configs/checkpoint_ARGO1.pt"): os.remove("v8_configs/checkpoint_ARGO1.pt")
                        if os.path.exists("v8_configs/checkpoint_ARGO2.pt"): os.remove("v8_configs/checkpoint_ARGO2.pt")
                    except: pass
                    
                    # Kill local training
                    subprocess.run('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Where-Object {$_.CommandLine -match \'v8_training_loop\'} | Invoke-CimMethod -MethodName Terminate"', shell=True)
                    
                    # Kill remote training & delete remote checkpoint
                    try:
                        import paramiko
                        client = paramiko.SSHClient()
                        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        client.connect('192.168.1.18', username='dungla', password='Than1!chet', timeout=5)
                        client.exec_command('powershell -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Where-Object {$_.CommandLine -match \'v8_training_loop\'} | Invoke-CimMethod -MethodName Terminate"')
                        client.exec_command('powershell -Command "Remove-Item -Path D:\\DungLA\\Argo\\v8_configs\\checkpoint_ARGO2.pt -Force -ErrorAction SilentlyContinue"')
                        client.close()
                    except: pass

    return actions_taken

def _check_local_process(keyword):
    """Kiểm tra xem tiến trình Python có đang chạy trên máy local không."""
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"Get-WmiObject Win32_Process -Filter \"Name='python.exe'\" | Where-Object {{ $_.CommandLine -match '{keyword}' }} | Select-Object ProcessId"],
            capture_output=True, text=True, timeout=10
        )
        return keyword.lower() in result.stdout.lower() or "ProcessId" in result.stdout
    except:
        return False

def _check_remote_process(keyword, ip, user):
    """Kiểm tra xem tiến trình Python có đang chạy trên Argo2 không."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        key_path = os.path.expanduser("~/.ssh/id_rsa")
        client.connect(ip, username=user, key_filename=key_path, timeout=5)
        stdin, stdout, stderr = client.exec_command(
            f'powershell -Command "Get-WmiObject Win32_Process -Filter \\"Name=\'python.exe\'\\" | Where-Object {{ $_.CommandLine -match \'{keyword}\' }} | Select-Object ProcessId"'
        )
        out = stdout.read().decode('utf-8', errors='ignore').strip()
        client.close()
        return "ProcessId" in out
    except:
        return False

# ==================== KHỞI CHẠY NODE ====================

def spawn_argo1():
    print("[Mastermind] Khởi chạy Argo1 Training...")
    resume_flag = "--resume" if os.path.exists("temp/V8_RESUME_MODE") else ""
    bat_path = os.path.abspath("temp/train_argo1.bat")
    py_path = os.path.abspath("scripts/v8_training_loop.py")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(f'@echo off\nset PYTHONIOENCODING=utf-8\ncd /d "%~dp0\\.."\n"C:\\Users\\GiggaMan\\AppData\\Local\\Programs\\Python\\Python39\\python.exe" "{py_path}" --node_id ARGO1 --layers 3 --lr 1e-3 {resume_flag}\npause\n')
    user = "desktop-n67bhmu\\giggaman"
    cmd = f'schtasks /create /tn "V8_Argo1_Train" /tr "{bat_path}" /sc once /st 00:00 /ru "{user}" /it /f ; schtasks /run /tn "V8_Argo1_Train"'
    subprocess.run(["powershell", "-Command", cmd], shell=True)

def spawn_argo2():
    print("[Mastermind] Khởi chạy Argo2 Training...")
    REMOTE_BASE = "D:/DungLA/Argo"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        key_path = os.path.expanduser("~/.ssh/id_rsa")
        client.connect(ip, username=user, key_filename=key_path, timeout=10)
        resume_flag = "--resume" if os.path.exists("temp/V8_RESUME_MODE") else ""
        bat_content = f'@echo off\ncd /d "{REMOTE_BASE}"\n"D:\\argo\\venv\\Scripts\\python.exe" scripts/v8_training_loop.py --node_id ARGO2 --layers 5 --lr 5e-4 {resume_flag}\npause\n'
        sftp = client.open_sftp()
        with sftp.file(f'{REMOTE_BASE}/argo2_xag.bat', 'w') as f:
            f.write(bat_content)
        sftp.close()
        stdin, stdout, stderr = client.exec_command('schtasks /run /tn "AgentTrainingXAG"', timeout=5)
        out = stdout.read() # Read to avoid hanging
        client.close()
    except Exception as e:
        print(f"[Mastermind] Lỗi SSH: {e}")

# ==================== VÒNG LẶP CHÍNH ====================

def main():
    print("Mastermind V8 - Hội Đồng Phân Tích Đa-Agent đang khởi động...")

    os.makedirs("temp", exist_ok=True)
    mode_str = "TIẾP TỤC (RESUME)" if os.path.exists("temp/V8_RESUME_MODE") else "KHỞI TẠO MỚI (FRESH)"
    send_tele(f"[MASTERMIND V8] Hội Đồng Phân Tích khởi động!\n🚀 Chế độ: {mode_str}\n🏛️ Hội đồng: COLLECTOR | QUANT | ML | SIGNAL | SYNTHESIZER | ACTION\nĐang mở Console trên Argo1 & Argo2...")

    print("[Mastermind] Spawning Argo1...", flush=True)
    spawn_argo1()
    print("[Mastermind] Spawning Argo2...", flush=True)
    spawn_argo2()
    print("[Mastermind] Spawning Argo3...", flush=True)
    spawn_argo3()
    
    check_delay = 10
    print(f"[Mastermind] Đợi {check_delay}s để kiểm tra tiến trình...", flush=True)
    time.sleep(check_delay)
    
    argo1_alive = _check_local_process("v8_training_loop")
    argo2_alive = _check_remote_process("v8_training_loop", ARGO2_IP, ARGO2_USER)
    argo3_alive = _check_remote_process("v8_training_loop", ARGO3_IP, ARGO3_USER)
    
    if argo1_alive and argo2_alive and argo3_alive:
        send_tele(f"[MASTERMIND] Kiểm tra chéo: Cả 3 Node đã khởi chạy THÀNH CÔNG và đang hoạt động ổn định!")
    else:
        err_msg = "[MASTERMIND] ⚠️ CẢNH BÁO LỖI KHỞI ĐỘNG CỤM!\n"
        if not argo1_alive: err_msg += "- Ngoại tuyến: Argo1\n"
        if not argo2_alive: err_msg += "- Ngoại tuyến: Argo2\n"
        if not argo3_alive: err_msg += "- Ngoại tuyến: Argo3\n"
        send_tele(err_msg)

    while True:
        if os.path.exists("temp/stop_v8_mastermind"):
            send_tele("[MASTERMIND] Nhận lệnh DỪNG khẩn cấp. Ngắt kết nối!")
            os.remove("temp/stop_v8_mastermind")
            break

        time.sleep(REPORT_INTERVAL)

        # === GIAI ĐOẠN 1: THU THẬP ===
        argo1_raw, argo2_raw, parsed_a1, parsed_a2 = agent_collector()

        # === GIAI ĐOẠN 2: PHÂN TÍCH SONG SONG ===
        quant_a1 = agent_quant(parsed_a1, "ARGO1")
        quant_a2 = agent_quant(parsed_a2, "ARGO2")
        ml_a1 = agent_ml(parsed_a1, "ARGO1")
        ml_a2 = agent_ml(parsed_a2, "ARGO2")
        sig_a1 = agent_signal(parsed_a1, "ARGO1")
        sig_a2 = agent_signal(parsed_a2, "ARGO2")

        # === GIAI ĐOẠN 3: PHẢN BIỆN THUẬT TOÁN ===
        critic_verdict = agent_critic(parsed_a1, parsed_a2)

        # === GIAI ĐOẠN 4: HÀNH ĐỘNG (kiểm tra + tự khởi động lại nếu chết) ===
        actions_taken = agent_action(parsed_a1, parsed_a2)

        # === GIAI ĐOẠN 5: TỔNG HỢP ===
        synthesis = agent_synthesizer(quant_a1, ml_a1, sig_a1, quant_a2, ml_a2, sig_a2, parsed_a1, parsed_a2, actions_taken)

        # === BÁO CÁO CUỐI CÙNG ===
        report = f"""[BÁO CÁO V8 - HỘI ĐỒNG PHÂN TÍCH]

📋 DỮ LIỆU THÔ (3 dòng cuối):
🖥️ ARGO1: {argo1_raw[-300:] if argo1_raw else 'Không có log'}
💻 ARGO2: {argo2_raw[-300:] if argo2_raw else 'Không có log'}

--- PHÂN TÍCH CHI TIẾT ---
{quant_a1}

{ml_a1}

{sig_a1}

{quant_a2}

{ml_a2}

{sig_a2}

{critic_verdict}

{synthesis}"""

        send_tele(report)

if __name__ == "__main__":
    main()
