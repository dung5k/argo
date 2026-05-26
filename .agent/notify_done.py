import sys
import json
import urllib.request
import urllib.error
import os

def get_bridge_port():
    port_file = os.path.join(".agent", ".bridge_port")
    try:
        if os.path.exists(port_file):
            with open(port_file, "r") as f:
                return int(f.read().strip())
    except:
        pass
    return 38124

BRIDGE_PORT = get_bridge_port()
BRIDGE_URL = f"http://127.0.0.1:{BRIDGE_PORT}/trigger-task"

def notify_done(trigger_id: str):
    payload = json.dumps({"triggerId": trigger_id}).encode("utf-8")
    req = urllib.request.Request(
        BRIDGE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
            result = json.loads(body)
            status = result.get("status", "unknown")
            print(f"[notify_done] trigger_id={trigger_id} -> status={status}")
            return status == "triggered"
    except urllib.error.URLError as e:
        print(f"[notify_done] Lỗi kết nối extension ở port {BRIDGE_PORT}: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[notify_done] Lỗi: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python .agent/notify_done.py <triggerId>", file=sys.stderr)
        sys.exit(1)
    trigger_id = sys.argv[1]
    success = notify_done(trigger_id)
    sys.exit(0 if success else 1)
