import io

with io.open('src/training_v2/train_v2.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''    train_loader  = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader    = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)'''

replacement = '''    # === [GPU AUTO-TUNE BATCH SIZE] ===
    print(f"\\n[GPU AUTO-TUNE] Bắt đầu dò chuẩn Batch Size tối đa cho VRAM (Mặc định: {BATCH_SIZE})...")
    _test_batch = BATCH_SIZE
    try:
        num_target_features = num_features # approximate for dummy
        dummy_model = TransformerModel(
            num_features, d_model=D_MODEL, nhead=NHEAD,
            num_layers=NUM_ATTN_LAYERS, dropout_rate=DROPOUT_RATE,
            num_xau_features=38, # DUMMY
        ).to(device)
        dummy_optimizer = torch.optim.Adam(dummy_model.parameters(), lr=1e-4)
        while _test_batch >= 128:
            try:
                torch.cuda.empty_cache()
                dummy_loader = DataLoader(train_dataset, batch_size=_test_batch, shuffle=True)
                x, y, r, s = next(iter(dummy_loader))
                dummy_model.train()
                dummy_optimizer.zero_grad()
                out = dummy_model(x)
                loss = F.mse_loss(out.squeeze(), y)
                loss.backward()
                dummy_optimizer.step()
                
                # Thành công:
                del x, y, r, s, out, loss, dummy_loader
                print(f"  -> ✅ Chốt mức Batch Size Tối đa an toàn: {_test_batch}")
                BATCH_SIZE = _test_batch
                break
            except Exception as e:
                err_str = str(e).lower()
                if "out of memory" in err_str or "oom" in err_str or "cuda error" in err_str:
                    torch.cuda.empty_cache()
                    print(f"  -> ⚠️ Batch {_test_batch} quá lớn gây Tràn bộ nhớ (OOM). Đang giảm xuống kích cỡ an toàn...")
                    _test_batch = int(_test_batch * 0.75) if _test_batch >= 2048 else _test_batch // 2
                    _test_batch = (_test_batch // 64) * 64 # align 64
                else:
                    raise e
        del dummy_model, dummy_optimizer
        torch.cuda.empty_cache()
    except Exception as e:
        print(f"[GPU AUTO-TUNE] Bỏ qua auto-tune do lỗi khởi tạo định lượng: {e}")
    # ==================================
    
    train_loader  = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
    val_loader    = DataLoader(val_dataset,   batch_size=BATCH_SIZE, shuffle=False)'''

if target in text:
    with io.open('src/training_v2/train_v2.py', 'w', encoding='utf-8') as f:
        f.write(text.replace(target, replacement))
    print('REPLACED')
else:
    print('TARGET NOT FOUND')
