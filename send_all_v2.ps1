python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\evaluator_v2.py" --dest "src\training_v2\evaluator_v2.py" ; Start-Sleep -s 5
python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\feature_pipeline_v2.py" --dest "src\training_v2\feature_pipeline_v2.py" ; Start-Sleep -s 5
python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\focal_loss.py" --dest "src\training_v2\focal_loss.py" ; Start-Sleep -s 5
python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\label_generator.py" --dest "src\training_v2\label_generator.py" ; Start-Sleep -s 5
python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\phoenix_v2.py" --dest "src\training_v2\phoenix_v2.py" ; Start-Sleep -s 5
python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\train_v2.py" --dest "src\training_v2\train_v2.py" ; Start-Sleep -s 5
python src\orchestration\host_controller.py send_file -c clientEW --file "src\training_v2\__init__.py" --dest "src\training_v2\__init__.py" ; Start-Sleep -s 5
