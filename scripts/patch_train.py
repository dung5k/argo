import sys
import os

with open('src/training_v6/train_v6.py', 'r', encoding='utf-8') as f:
    content = f.read()

head_idx = content.find('# [PHA?C D? 3] Early Stopping')
if head_idx == -1:
    head_idx = content.find('# [PHÁC ĐỒ 3] Early Stopping')

tail_idx = content.find('# [TẠM DISABLE] Báo cáo Telegram định kỳ')

if head_idx != -1 and tail_idx != -1:
    print('Found block boundaries')
    
    new_block = '''            # [PHÁC ĐỒ 3] Early Stopping & Model Checkpointing
            improved = val_ce_loss < _es_best_ce_val
            
            if improved:
                _es_best_ce_val = val_ce_loss
                _es_streak      = 0
                
                best_score      = comp_score
                best_win_rate   = max([float(m.win_rate) for m in eval_res.threshold_metrics]) if eval_res.threshold_metrics else 0.0
                
                print(f"  [ARGO2] MO HINH HOI TU TOT NHAT! Val CE Loss = {_es_best_ce_val:.4f} (WR: {best_win_rate*100:.1f}%). Luu model...", flush=True)
                if 'tbot' in locals() and 'chat_id' in locals():
                    try:
                        tbot.send_message(chat_id, f"[ARGO2] TOI UU LOSS THANH CONG!\\nCau hinh: {cfg_id}\\nEpoch: {epoch} | Val CE Loss: {_es_best_ce_val:.4f} | WinRate: {best_win_rate*100:.1f}%")
                    except: pass
                
                # Save local
                model_export_path = os.path.join(model_dir, f"aamt_v3_{cfg_id}_final.pth")
                torch.save(model.state_dict(), model_export_path)
                
                # Ghi json metrics
                try:
                    session_name = config.get("SESSION", "ny").lower()
                    target_sym = config.get("TARGET_SYMBOL", "xauusd").lower().replace('m', '')
                    nfe = config.get("MODEL_DIMENSIONS", {}).get("num_features", 38)
                    t_metrics = []
                    for m in eval_res.threshold_metrics:
                        t_metrics.append({
                            "threshold": float(m.threshold),
                            "total_signals": int(m.total_signals),
                            "win_rate": float(m.win_rate),
                            "avg_win_return": 0.001,
                            "avg_loss_return": 0.001,
                            "ev_score": float(m.balanced_score),
                            "sharpe_score": 0.0,
                            "tus_score": float(m.tus_score),
                            "total_buy": int(m.n_buy),
                            "total_sell": int(m.n_sell)
                        })
                        
                    metrics_data = {
                        "target": target_sym,
                        "version": "Transformer_V3",
                        "dimensions": {
                            "num_features_target": 0,
                            "num_features_macro": nfe
                        },
                        "sessions": {
                            session_name: {
                                "BEST_VLOSS": {
                                    "epoch": int(epoch),
                                    "max_threshold": float(max([m.threshold for m in eval_res.threshold_metrics])) if eval_res.threshold_metrics else 0.5,
                                    "composite_score": float(eval_res.composite_score()),
                                    "val_loss": float(eval_res.val_loss),
                                    "threshold_metrics": t_metrics,
                                    "win_rates": [float(m.win_rate) for m in eval_res.threshold_metrics],
                                    "thresholds": [float(m.threshold) for m in eval_res.threshold_metrics],
                                    "totals": [int(m.total_signals) for m in eval_res.threshold_metrics]
                                }
                            }
                        }
                    }
                    with open(os.path.join(results_dir, "training_metrics_v3.json"), "w", encoding="utf-8") as fm:
                        json.dump(metrics_data, fm, indent=4)
                except Exception as e:
                    print(f"  Loi ghi json metrics: {e}", flush=True)
                
                try:
                    sync_chunks = config.get("HF_CLOUD", {}).get("SYNC_CHUNKS", True)
                    if sync_chunks:
                        from scripts.sync_workspaces import push_run
                        import threading
                        threading.Thread(target=push_run, args=(cfg_id, run_id), daemon=True).start()
                except Exception as e:
                    print(f"  Loi kich hoat Push: {e}", flush=True)
            else:
                _es_streak += 1
                if comp_score > best_score:
                    best_score = comp_score
                    print(f"  Luu y: Score/WR tang (Score: {comp_score:.4f}) nhung Loss khong giam ({val_ce_loss:.4f}). Bo qua viec save model.", flush=True)

                if _es_streak >= _ES_PATIENCE:
                    es_msg = f"\\nEARLY STOPPING kich hoat tai Epoch {epoch}!\\n"
                    es_msg += f"   CE Loss val khong cai thien lien tiep {_es_streak} epoch (Tot nhat: {_es_best_ce_val:.4f})\\n"
                    print(es_msg, flush=True)
                    if 'tbot' in locals() and 'chat_id' in locals():
                        try:
                            tbot.send_message(chat_id, f"[ARGO2] HE THONG DUNG DAO TAO\\n" + es_msg)
                        except Exception:
                            pass
                    break
    
'''
    new_content = content[:head_idx] + new_block + content[tail_idx:]
    with open('src/training_v6/train_v6.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print('Successfully patched train_v6.py')
else:
    print('Could not find block boundaries')
