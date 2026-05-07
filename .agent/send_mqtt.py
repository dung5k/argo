import sys
import json
import urllib.request
import urllib.error
import os

def get_bridge_port():
    port_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bridge_port")
    try:
        if os.path.exists(port_file):
            with open(port_file, "r") as f:
                return int(f.read().strip())
    except:
        pass
    return None

def send_mqtt_via_bridge(target_agent, command_text):
    port = get_bridge_port()
    if port is None:
        print("Không tìm thấy Bridge Port. Extension chưa chạy?", file=sys.stderr)
        return False
        
    url = f'http://127.0.0.1:{port}/send-mqtt'
    data = json.dumps({
        'target': target_agent,
        'command': command_text
    }).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return True
    except Exception as e:
        print(f"Lỗi gửi MQTT qua Bridge: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python send_mqtt.py \"Nội dung lệnh\" --target <TargetAgent>")
        sys.exit(1)
        
    target_agent = None
    if '--target' in sys.argv:
        idx = sys.argv.index('--target')
        if idx + 1 < len(sys.argv):
            target_agent = sys.argv[idx + 1]
            sys.argv.pop(idx + 1)
        sys.argv.pop(idx)
        
    if not target_agent:
        print("Thiếu --target <TargetAgent>", file=sys.stderr)
        sys.exit(1)
        
    command_text = sys.argv[1]
    
    # 1. Gửi lệnh ngầm qua MQTT
    success = send_mqtt_via_bridge(target_agent, command_text)
    
    # 2. Tự động tường thuật hành động lên Telegram Group ARGO1-ARGO2 (-5144257068)
    if success:
        try:
            # Lấy tên mình từ network_config
            agent_dir = os.path.dirname(os.path.abspath(__file__))
            net_cfg = os.path.join(agent_dir, "network_config.json")
            my_identity = "Antigravity"
            if os.path.exists(net_cfg):
                with open(net_cfg, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    my_identity = data.get("agent_identity", "Antigravity")
            
            narration = f"Đã gửi yêu cầu MQTT ngầm tới **{target_agent}**: '{command_text}'"
            
            import subprocess
            send_tele_py = os.path.join(agent_dir, "send_to_tele.py")
            if os.path.exists(send_tele_py):
                # Hardcode channel group ARGO1-ARGO2 (-5144257068) for narration
                subprocess.Popen([sys.executable, send_tele_py, narration, "--channel", "-5144257068"])
        except Exception as e:
            pass
            
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
