# 📐 Yêu Cầu Kiến Trúc Thuật Toán V3.0
# Autoencoder-Augmented Multi-Task Transformer (AAMT)

**Phiên bản:** 3.0  
**Ngày khởi tạo:** 2026-04-17  
**Trạng thái:** 🚧 Thiết Kế

---

## 1. Tổng quan (Overview)

### Vấn đề cốt lõi cần giải quyết

Khi nhồi ma trận `[60 nến × 70 features]` vào Transformer thông thường, mạng sẽ cố gắng kết nối *mọi thứ* với nhãn Target. Do thị trường tài chính chứa đến **80% nhiễu ngẫu nhiên**, mạng rơi vào một trong hai trạng thái thất bại:

| Trạng thái thất bại | Biểu hiện |
|---|---|
| 🔴 Overfit vào nhiễu | Val Loss vọt, WR âm khi live |
| 🟡 Sụp đổ trạng thái | Luôn dự đoán ~0.5, từ chối ra quyết định |

### Giải pháp: Học Đa Nhiệm (Multi-task Learning)

Thay vì ép mạng chỉ học **"Dự đoán tương lai"**, V3.0 buộc mạng phải đồng thời học **"Hiểu hiện tại"** thông qua kiến trúc Autoencoder lai Classifier.

---

## 2. Kiến Trúc Mô Hình (Architecture)

```
Input: [Batch, 60 timesteps, N_features]
          │
          ▼
┌─────────────────────────┐
│   ENCODER (Transformer)  │   ← Module 1: Đọc & Nén
│   60 × N → Latent Vec   │
└───────────┬─────────────┘
            │ Latent Vector
     ┌──────┴──────┐
     ▼             ▼
┌─────────┐  ┌─────────────┐
│Reconstruct│  │Classify Head│   ← Module 2 & 3
│  Head   │  │  (3-Class)  │
│60×N out │  │ Buy/Sell/SW │
└─────────┘  └─────────────┘
     │             │
  MSE Loss    CrossEntropy
     └──────┬──────┘
            ▼
       Joint Loss
```

### Module 1: Lõi Encoder (Transformer)

- **Input:** Ma trận `[Batch, 60, N_features]`
- **Output:** **Latent Vector** – bản tóm tắt hình thái thị trường
- **Kiến trúc:** Transformer Encoder (Multi-Head Self-Attention + Feed-Forward)
- **Nhiệm vụ:** Nén toàn bộ ngữ cảnh 60 nến thành vector cốt lõi, lọc bỏ các chiều không quan trọng

### Module 2: Reconstruction Head (Bộ Giải Nén)

- **Input:** Latent Vector
- **Output:** Ma trận `[Batch, 60, N_features]` – bản phục dựng đầu vào
- **Logic hoạt động:**
  - Nếu đoạn nến có quy luật rõ ràng (Cờ đuôi nheo, Vai-Đầu-Vai, Breakout): Encoder nén dễ → MSE **thấp**
  - Nếu đoạn nến là rác ngẫu nhiên: Encoder không thể nén → MSE **cao**
- **Vai trò:** Bộ lọc nhiễu thụ động – phát hiện dữ liệu chất lượng thấp trước khi ra tín hiệu

### Module 3: Classification Head (Bộ Phân Loại)

- **Input:** Latent Vector
- **Output:** Softmax 3-class: `[P_Buy, P_Sell, P_Sideway]`
- **Nhãn:** Theo Triple-Barrier Labeling (xem mục 3A)

---

## 3. Chuẩn Bị Dữ Liệu (Data Preparation)

### A. Gắn Nhãn: Triple-Barrier Labeling

> ⚠️ **Bỏ hoàn toàn** phương pháp nhìn trước T+5 nến (Soft label của V2.x).

Gắn nhãn 3-class dựa trên mô phỏng TP/SL thực tế:

| Class | Điều kiện | Ý nghĩa |
|---|---|---|
| `0` (SELL) | Chạm StopLoss trước khi chạm TP | Giá đi ngược chiều |
| `1` (BUY) | Chạm TakeProfit trước khi chạm TP | Giá đi đúng chiều |
| `2` (SIDEWAY) | Hết thời gian nắm giữ, giá lình xình | Thị trường không có xu hướng |

**Tham số cần cấu hình:**
```python
TP_PIPS = 15        # Ngưỡng Chốt lời (pips)
SL_PIPS = 15        # Ngưỡng Cắt lỗ (pips)
MAX_HOLD_BARS = 20  # Số nến tối đa nắm giữ trước khi gán Sideway
```

### B. Lựa Chọn Features: 4 Nhóm Trực Giao (Orthogonal Feature Groups)

> ⚠️ **Không** nhồi toàn bộ 70 features của V2.x – nhiều features chồng chéo sẽ phá vỡ khả năng tái cấu trúc của Autoencoder.

#### Nhóm 1: Price Action (Hình Thái Giá)
```
- log_return_open   = log(Open[t] / Close[t-1])
- log_return_high   = log(High[t] / Close[t-1])
- log_return_low    = log(Low[t] / Close[t-1])
- log_return_close  = log(Close[t] / Close[t-1])   ← Log Return, KHÔNG dùng giá tuyệt đối
- upper_wick_pct    = (High - max(Open,Close)) / abs(Close-Open)   ← Bóng nến trên
- lower_wick_pct    = (min(Open,Close) - Low) / abs(Close-Open)    ← Bóng nến dưới
```
> 🚫 **Cấm tuyệt đối** dùng giá tuyệt đối (ví dụ: `Close = 2350.50`). Phải dùng Log Returns.

#### Nhóm 2: Volatility (Biến Động - RẤT QUAN TRỌNG)
```
- atr_normalized    = ATR(14) / Close[t]          ← ATR chuẩn hóa theo giá
- bb_width          = (BB_Upper - BB_Lower) / BB_Mid   ← Bollinger Band Width
```
> 💡 `bb_width` là **tính năng sinh tử**: AI phân biệt thị trường đang *nén tích lũy* (width hẹp) hay *bùng phát* (width rộng).

#### Nhóm 3: Momentum (Động Lượng)
```
- rsi_14            = RSI(14) / 100               ← Chuẩn hóa về [0, 1]
- macd_hist         = MACD_Histogram chuẩn hóa    ← Đại diện đà tăng/giảm
```
> ⚠️ Chỉ dùng **1-2 chỉ báo đại diện**. Tránh dùng RSI ở 10 chu kỳ khác nhau → gây nhiễu đa cộng tuyến.

#### Nhóm 4: Time Context (Ngữ Cảnh Thời Gian)
```
- hour_sin          = sin(2π × hour / 24)
- hour_cos          = cos(2π × hour / 24)         ← Mã hóa vòng tròn, tránh bước nhảy 23→0
- is_asian          = 1 nếu trong giờ Á (00:00-07:00 UTC)
- is_london         = 1 nếu trong giờ Âu (07:00-12:30 UTC)
- is_ny             = 1 nếu trong giờ Mỹ (13:00-22:00 UTC)
```

**Tổng số features dự kiến: ~15 features** (giảm từ 70 → tập trung, sắc bén hơn)

### C. Chuẩn Hóa Dữ Liệu (Scaling)

| Phương pháp | Đánh giá |
|---|---|
| ❌ `QuantileTransformer` (V2.x) | Bóp phẳng biên độ nến, mất cấu trúc Volatility |
| ✅ **`RobustScaler`** (V3.0) | Loại outlier bằng IQR, **giữ nguyên biên độ tương đối** |

```python
from sklearn.preprocessing import RobustScaler
scaler = RobustScaler()  # Median + IQR – bền với cây nến dài bất thường
```

### D. Tạo Tensor (Sliding Window)

```python
# Output shape: [Batch_Size, 60, N_features]
WINDOW_SIZE = 60
STEP_SIZE   = 1        # Bước trượt 1 nến (có thể tăng để giảm tương quan serial)
```

---

## 4. Đào Tạo Mô Hình (Training Strategy)

### Hàm Mất Mát Tổng Hợp (Joint Loss)

$$\text{Total\_Loss} = (\lambda_1 \times \text{Classification\_Loss}) + (\lambda_2 \times \text{Reconstruction\_Loss})$$

| Thành phần | Phương pháp | Mặc định |
|---|---|---|
| `Classification_Loss` | Cross-Entropy (3-Class) | `λ₁ = 1.0` |
| `Reconstruction_Loss` | MSE (đầu vào vs. phục dựng) | `λ₂ = 1.0` |

### Giai Đoạn 1: Warm-up Autoencoder

> 🎯 *Mục đích: Dạy AI đọc bản đồ thị trường – hiểu hình thái trước khi ra quyết định*

```
Thiết lập:
  λ₁ = 0.0   ← Tắt nhánh Classification hoàn toàn
  λ₂ = 1.0   ← Chỉ tối ưu Reconstruction

Số epochs: 20–30
Kỳ vọng:
  - Encoder học cách tập trung vào cấu trúc quan trọng
  - Reconstruction Loss giảm dần và ổn định
  - Trọng số mạng chứa "hiểu biết hình thái thị trường"
```

### Giai Đoạn 2: Fine-tuning (Full Training)

> 🎯 *Mục đích: Từ nền tảng "đã hiểu hình thái", học thêm cách ra quyết định*

```
Thiết lập:
  λ₁ = 1.0   ← Bật nhánh Classification
  λ₂ = 1.0   ← Giữ nguyên Reconstruction

Số epochs: 50–100
Kỳ vọng:
  - Classification Loss giảm dần
  - Reconstruction Loss KHÔNG tăng quá nhiều (encoder không quên hình thái)
  - Validator WR > 55%
```

---

## 5. Logic Ra Quyết Định Live (Inference Logic)

### Bộ Lọc Nhiễu 2 Tầng

```python
def predict(model, candles_60, mse_threshold, prob_threshold=0.7):
    """
    Args:
        candles_60     : Tensor [1, 60, N_features] – 60 nến gần nhất
        mse_threshold  : Điểm phân vị thứ 70 của MSE trên tập Validation
        prob_threshold : Ngưỡng xác suất tối thiểu để ra lệnh (mặc định 0.7)
    """
    latent, reconstructed, class_probs = model(candles_60)
    
    # ── Tầng 1: Lọc nhiễu qua Reconstruction MSE ──────────────────────────
    current_mse = MSE(candles_60, reconstructed)
    
    if current_mse > mse_threshold:
        return "TÍN HIỆU RÁC - ĐỨNG NGOÀI"   # AI không nhận ra mẫu hình này
    
    # ── Tầng 2: Phân loại từ Classification Head ──────────────────────────
    prob_buy, prob_sell, prob_sideway = class_probs
    
    if prob_buy > prob_threshold:
        return "BUY"
    elif prob_sell > prob_threshold:
        return "SELL"
    else:
        return "SIDEWAY - ĐỨNG NGOÀI"
```

### Hiệu Chỉnh MSE Threshold

```python
# Tính trên tập Validation sau Giai đoạn 1:
mse_scores = [compute_mse(model, sample) for sample in val_dataset]
MSE_THRESHOLD = np.percentile(mse_scores, 70)
# → ~30% dữ liệu "khó" sẽ bị lọc, chỉ trade trên 70% dữ liệu "rõ ràng"
```

---

## 6. Kế Hoạch Triển Khai (Roadmap)

| Giai đoạn | Hạng mục | Trạng thái |
|---|---|---|
| 📁 **Cấu trúc** | Tạo thư mục `src/training_v3/` | ✅ Hoàn thành |
| 📄 **Yêu cầu** | Tài liệu này | ✅ Hoàn thành |
| 🔧 **Data Pipeline** | Triple-Barrier Labeling + Feature Engineering | ⏳ Chờ |
| 🏗️ **Model** | Transformer Encoder + 2 Heads | ⏳ Chờ |
| 🎓 **Training** | 2-Phase Training Loop | ⏳ Chờ |
| 📊 **Evaluation** | MSE Distribution + WR Backtest | ⏳ Chờ |
| 🚀 **Deployment** | Tích hợp vào Bot V2 (A/B Test) | ⏳ Chờ |

---

## 7. So Sánh V2.x vs V3.0

| Tiêu chí | V2.x (Hiện tại) | V3.0 (Mục tiêu) |
|---|---|---|
| **Kiến trúc** | Transformer thuần | Transformer + Autoencoder |
| **Số features** | ~70 (chồng chéo) | ~15 (trực giao, sắc bén) |
| **Gắn nhãn** | Soft label T+5 | Triple-Barrier 3-Class |
| **Scaling** | QuantileTransformer | RobustScaler |
| **Lọc nhiễu** | Chỉ dựa vào ngưỡng xác suất | MSE Filter + Xác suất |
| **Training** | 1 giai đoạn | 2 giai đoạn (Warm-up + Fine-tune) |
| **Phát hiện rác** | ❌ Không | ✅ Tự động qua Reconstruction MSE |
