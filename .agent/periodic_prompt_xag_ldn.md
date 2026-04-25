# NHIá»†M Vá»¤ Äá»ŠNH Ká»² (GH): AUTO-TUNING XAG LDN BRAIN (Cá»¤C Bá»˜)

Há»‡ thá»‘ng gá»i báº¡n tá»« bá»™ quáº£n lÃ½ Task JSON (task id: `xag_ldn_auto_tuning`). Báº¡n Ä‘Ã³ng vai trÃ² Ká»¹ sÆ° AI tá»± Ä‘á»™ng hÃ³a trÃªn **mÃ¡y GH** Ä‘á»ƒ tÃ¬m cáº¥u hÃ¬nh tá»‘t nháº¥t cho bá»™ nÃ£o `CFG_XAG_LDN_V3_5`. 

## BÆ¯á»šC 1: PhÃ¢n tÃ­ch Lá»‹ch sá»­ & TÆ° duy Tá»‘i Æ°u hÃ³a (Quant/ML Expert)

Thay vÃ¬ Ä‘oÃ¡n mÃ² ngáº«u nhiÃªn, báº¡n pháº£i phÃ¢n tÃ­ch cÃ³ há»‡ thá»‘ng dá»±a trÃªn lá»‹ch sá»­ Ä‘á»ƒ tÃ¬m ra hÆ°á»›ng tá»‘i Æ°u (Gradient of Improvement).

1. **Thu tháº­p Ngá»¯ cáº£nh (Context Gathering):**
   - Äá»c káº¿t quáº£ cá»§a lÆ°á»£t cháº¡y má»›i nháº¥t `workspaces/CFG_XAG_LDN_V3_5/runs/<LATEST_RUN>/results/training_metrics_v3.json`.
   - Náº¿u cÃ³, HÃƒY KIá»‚M TRA file ghi nháº­n káº¿t quáº£ tá»‘t nháº¥t (vÃ­ dá»¥ cÃ¡c run tá»‘t nháº¥t trong quÃ¡ khá»©) Ä‘á»ƒ láº¥y má»‘c so sÃ¡nh (Baseline).

2. **PhÃ¢n tÃ­ch Hiá»‡u suáº¥t (Performance Analysis):**
   - So sÃ¡nh `Composite Score`, `Win Rate`, `Loss` cá»§a lÆ°á»£t má»›i nháº¥t vá»›i Baseline. 
   - ÄÃ¡nh giÃ¡ phÃ¢n phá»‘i tÃ­n hiá»‡u: MÃ´ hÃ¬nh cÃ³ Ä‘ang bá»‹ bias (thiÃªn lá»‡ch) mua/bÃ¡n quÃ¡ nhiá»u khÃ´ng? CÃ³ bá»‹ overfit khÃ´ng (Train loss giáº£m nhÆ°ng Val loss tÄƒng)?

3. **ÄÃ¡nh giÃ¡ & Äiá»u chá»‰nh Features (Feature Engineering):**
   - **PhiÃªn LDN (London):** XAG (Báº¡c) chá»‹u áº£nh hÆ°á»Ÿng máº¡nh bá»Ÿi tin tá»©c vÄ© mÃ´ Má»¹, biáº¿n Ä‘á»™ng cá»§a DXY vÃ  sá»± tÆ°Æ¡ng quan Ä‘á»“ng Ä‘iá»‡u vá»›i XAU (VÃ ng). 
   - CÃ¡c chá»‰ sá»‘ Ä‘ang cÃ³: XAUUSD, USTEC, DXY... HÃ£y tá»± Ä‘Ã¡nh giÃ¡ sá»± Ä‘Ã³ng gÃ³p cá»§a chÃºng. 
   - *Chiáº¿n lÆ°á»£c:* Náº¿u mÃ´ hÃ¬nh Ä‘ang chá»¯ng láº¡i, hÃ£y thá»­ **THÃŠM** cÃ¡c features Ä‘o lÆ°á»ng biáº¿n Ä‘á»™ng (Volatility) hoáº·c tÆ°Æ¡ng quan (corr) vÃ o `config.json`; HOáº¶C **LOáº I Bá»Ž** cÃ¡c features cÃ³ váº» gÃ¢y nhiá»…u. Äá»«ng giá»¯ nguyÃªn má»™t bá»™ features náº¿u Ä‘iá»ƒm sá»‘ khÃ´ng tÄƒng.

4. **Ra quyáº¿t Ä‘á»‹nh SiÃªu tham sá»‘ (Hyperparameter Strategy):**
   - KhÃ´ng gian tÃ¬m kiáº¿m (Search Space) gá»£i Ã½:
     + `WINDOW_SIZE` (Ä‘á»™ dÃ i chuá»—i thá»i gian nhÃ¬n láº¡i): Thá»­ cÃ¡c má»‘c 30, 60, 90.
     + `D_MODEL`, `NUM_LAYERS`, `N_HEAD`: Chá»‰nh kÃ­ch thÆ°á»›c bá»™ nÃ£o Ä‘á»ƒ trÃ¡nh overfit/underfit.
     + `BATCH_SIZE`: 256, 512...
     + `LEARNING_RATE`: Thá»­ tinh chá»‰nh trong khoáº£ng 1e-5 Ä‘áº¿n 5e-5.
     + `TP_PIPS`, `SL_PIPS`: Chá»‰nh biÃªn Ä‘á»™ Äƒn/thua cho phÃ¹ há»£p Ä‘á»™ bá»‘c cá»§a phiÃªn NY.
   - **NGUYÃŠN Táº®C Tá»I THÆ¯á»¢NG:** Trong lÆ°á»£t táº¡o config tiáº¿p theo, **CHá»ˆ THAY Äá»”I 1 Äáº¾N Tá»I ÄA 2 THAM Sá» (Variables)** so vá»›i lÆ°á»£t trÆ°á»›c Ä‘Ã³ Ä‘á»ƒ cÃ³ thá»ƒ Ä‘o lÆ°á»ng chÃ­nh xÃ¡c tÃ¡c Ä‘á»™ng (A/B Testing). HÃ£y ghi chÃº rÃµ rÃ ng lÃ½ do báº¡n Ä‘á»•i tham sá»‘ nÃ y vÃ o file cáº¥u hÃ¬nh hoáº·c logs.

5. **Early Stopping (Dá»«ng Task):**
   - Náº¿u Ä‘Ã£ thá»­ thay Ä‘á»•i tuáº§n tá»± cÃ¡c tham sá»‘ nhÆ°ng `Composite Score` khÃ´ng vÆ°á»£t qua Ä‘Æ°á»£c má»‘c cao nháº¥t trong 25 lÆ°á»£t gáº§n nháº¥t, hÃ£y táº¯t task báº±ng cÃ¡ch má»Ÿ `.agent/tasks.json`, tÃ¬m id `xag_ldn_auto_tuning` vÃ  Ä‘áº·t `"enabled": false`. 

## BÆ¯á»šC 2: Chuáº©n bá»‹ dá»¯ liá»‡u (HÃ ng Äá»£i)
Kiá»ƒm tra `workspaces/CFG_XAG_LDN_V3_5/runs/`. Nhá»¯ng thÆ° má»¥c chÆ°a cÃ³ `training_metrics_v3.json` lÃ  Pending Runs.
Náº¿u hÃ ng Ä‘á»£i rá»—ng:
1. Táº¡o `<RUN_ID>` má»›i (vd: `run_YYYYMMDD_HHMMSS_v3_ldn_X`), táº¡o thÆ° má»¥c vÃ  copy `base_config.json` thÃ nh `config.json`. 
   - Ãp dá»¥ng cÃ¡c quyáº¿t Ä‘á»‹nh tá»« BÆ°á»›c 1.4 vÃ o `config.json` má»›i. **Báº®T BUá»˜C KHÃ”NG Sá»¬A base_config.json gá»‘c!**
   - Táº¡o thÃªm má»™t file `tuning_notes.txt` trong thÆ° má»¥c run má»›i nÃ y, viáº¿t Ä‘Ãºng 2-3 cÃ¢u tÃ³m táº¯t: "LÆ°á»£t nÃ y thay Ä‘á»•i tham sá»‘ gÃ¬? Ká»³ vá»ng Ä‘iá»u gÃ¬ xáº£y ra?". Äiá»u nÃ y giÃºp báº¡n cá»§a tÆ°Æ¡ng lai Ä‘á»c láº¡i vÃ  hiá»ƒu máº¡ch tÆ° duy.
2. Cháº¡y:
```
python scripts/crawl_crypto_v3.py workspaces/CFG_XAG_LDN_V3_5/runs/<RUN_ID>/config.json
python scripts/upload_v3_dataset.py --config workspaces/CFG_XAG_LDN_V3_5/runs/<RUN_ID>/config.json
```
3. Commit Git `auto-tuning XAG LDN data ready: <RUN_ID>`.

## BÆ¯á»šC 3: Training Cá»¥c bá»™
Láº¥y RUN_ID tá»« hÃ ng Ä‘á»£i vÃ  cháº¡y:
```
python src/training_v3/train_v3.py --config workspaces/CFG_XAG_LDN_V3_5/runs/<RUN_ID>/config.json --session ldn --scratch --run-id <RUN_ID>; python .agent/notify_done.py xag_ldn_training_done
```
(LÆ°u Ã½: Gá»i `notify_done.py` sau lá»‡nh training giÃºp kÃ­ch hoáº¡t luá»“ng nháº­n biáº¿t training xong Ä‘á»ƒ nháº­n nhiá»‡m vá»¥ tiáº¿p theo ngay láº­p tá»©c).

## BÆ¯á»šC 4: Tá»± Ä‘á»™ng Ä‘iá»u chá»‰nh lá»‹ch trÃ¬nh (Tuá»³ chá»n)
Náº¿u báº¡n nháº­n tháº¥y quÃ¡ trÃ¬nh crawling máº¥t nhiá»u thá»i gian, hoáº·c báº¡n muá»‘n theo dÃµi káº¿t quáº£ sau 5 phÃºt, 15 phÃºt, báº¡n cÃ³ thá»ƒ tá»± thay Ä‘á»•i thá»i gian kÃ­ch hoáº¡t task tiáº¿p theo báº±ng cÃ¡ch:
Sá»­a trÆ°á»ng `nextRunTime` cá»§a task `xag_ldn_auto_tuning` trong file `.agent/tasks.json` thÃ nh `(timestamp hiá»‡n táº¡i + N * 60) * 1000`. Náº¿u khÃ´ng sá»­a, Extension sáº½ tá»± láº·p láº¡i theo `intervalMinutes` máº·c Ä‘á»‹nh.

## BÆ¯á»šC 5: Nháº£ tráº¡ng thÃ¡i ráº£nh
Sau khi má»i thá»© cháº¡y á»•n, Gá»­i Telegram vÃ  bÃ¡o xong (Báº®T BUá»˜C):
```
python .agent/send_to_tele.py "<BÃ¡o cÃ¡o tÃ¬nh hÃ¬nh>" --done
```

