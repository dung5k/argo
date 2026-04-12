import os
import sys

def probe():
    print(f"OS Name: {os.name}")
    print(f"ARGO_DATA_DIR: {os.environ.get('ARGO_DATA_DIR')}")
    try:
        import client_tg_agent
        print(f"Agent __file__: {client_tg_agent.__file__}")
    except Exception as e:
        print(e)
    # Check what the actual source code is
    try:
        agent_path = os.path.abspath("src/orchestration/client_tg_agent.py")
        with open(agent_path, "r", encoding="utf-8") as f:
            content = f.read()
            if "C:\\\\argo\\\\data" in content:
                print("✅ Found C:\\argo\\data in client_tg_agent.py")
            elif "C:\\argo\\data" in content:
                print("✅ Found C:\\argo\\data in client_tg_agent.py (single slash)")
            else:
                print("❌ NOT FOUND: C:\\argo\\data in client_tg_agent.py!")
    except Exception as e:
        print(f"Read error: {e}")

if __name__ == "__main__":
    probe()
