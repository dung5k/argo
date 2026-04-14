import codecs

target_file = 'src/training_v2/train_v2.py'
with codecs.open(target_file, 'r', 'utf-8') as f:
    content = f.read()

import_str = 'from src.training_v2.evaluator_v2 import EVEvaluator, EpochEvalResult\nfrom src.training_v2.eval_plotter import plot_and_notify_chart'
content = content.replace('from src.training_v2.evaluator_v2 import EVEvaluator, EpochEvalResult', import_str)

old_logic = "                if improved:\n                    phx.notify_improved()"
new_logic = """                if improved:
                    try:
                        main_cfg = improved[0]
                        plot_and_notify_chart(result, s_name, main_cfg, total_epoch, run_dir)
                    except Exception as e:
                        print(f"[PLOT ERROR] {e}")
                    phx.notify_improved()"""

content = content.replace(old_logic, new_logic)

with codecs.open(target_file, 'w', 'utf-8') as f:
    f.write(content)
print("Updated train_v2.py!")
