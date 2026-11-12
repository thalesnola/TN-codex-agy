import json
import sys
import time
import subprocess
from pathlib import Path

if "models" in sys.argv:
    print("gemini-4-argon-high\tArgon High\ngemini-4-argon-medium\tArgon Medium\ngemini-3.8-flash-high\tFlash")
    raise SystemExit()
prompt = sys.argv[sys.argv.index("-p")+1]
if "GRANDCHILD" in prompt:
    subprocess.Popen([sys.executable,"-c","import time;from pathlib import Path;time.sleep(2);Path('grandchild-marker.txt').write_text('alive')"])
if "SLEEP" in prompt:
    time.sleep(30)
if "EMPTY" in prompt:
    print(json.dumps({"response":""}))
elif "MALFORMED" in prompt:
    print('{"response":')
else:
    if "EDIT" in prompt:
        Path("new file.txt").write_text("changed\n", encoding="utf-8")
    if "OUTSIDE" in prompt:
        Path("outside.txt").write_text("wrong\n", encoding="utf-8")
    print("notice: fake AGY")
    print(json.dumps({"conversation_id":"fake", "response":"Verified fake result", "usage":{"input_tokens":4,"output_tokens":3}}))
