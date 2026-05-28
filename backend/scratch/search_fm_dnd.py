import os

files = ["flow_manager.py", "flows/insurance_flow.py", "orchestration_bridge.py"]
search_phrase = "helpful today"

for filename in files:
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        if search_phrase in content:
            print(f"Found in {filename}!")
            lines = content.split("\n")
            for idx, line in enumerate(lines):
                if search_phrase in line:
                    print(f"Line {idx+1}: {line}")
