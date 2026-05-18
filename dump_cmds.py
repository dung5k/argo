import urllib.request
import json
import os

try:
    with open(r'd:\DungLA\client1\.agent\.bridge_port', 'r') as f:
        port = int(f.read().strip())
    req = urllib.request.urlopen(f"http://127.0.0.1:{port}/dump-commands")
    print(req.read().decode('utf-8'))
except Exception as e:
    print(e)
