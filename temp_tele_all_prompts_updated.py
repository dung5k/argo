# -*- coding: utf-8 -*-
import subprocess

msg = """✅ [CẬP NHẬT CHIẾN THUẬT TOÀN HỆ THỐNG] Sếp Lê, đã vá xong MẪU BÁO CÁO cho tất cả 4 phiên V6!

🔧 Danh sách file đã cập nhật:
1. ✅ `.agent/periodic_prompt_ltc_asian_v6_local.md` — (Phiên Châu Á, dùng nhãn HolyGrail)
2. ✅ `.agent/periodic_prompt_ltc_london_v6_local.md` — (Phiên London, đã cập nhật trước đó)
3. ✅ `.agent/periodic_prompt_ltc_ny_v6_local.md` — (Phiên New York)
4. ✅ `.agent/periodic_prompt_ltc_weekend_v6_local.md` — (Phiên Cuối Tuần)

📋 Mỗi phiên đều được thêm cùng cấu trúc bảng tổng kết 6 vòng gần nhất:
| Seed | Score | WR@0.80 | WR@0.94 |

Riêng phiên Á dùng WR@0.86 (ngưỡng min_prob_thresh hiện tại) thay vì 0.94.

Từ chu kỳ tiếp theo, toàn bộ 4 phiên sẽ báo cáo nhất quán theo cùng một format chuẩn! 🎯"""

subprocess.run(["python", ".agent/send_to_tele.py", msg, "--channel", "1816854047", "--done"], check=True)
