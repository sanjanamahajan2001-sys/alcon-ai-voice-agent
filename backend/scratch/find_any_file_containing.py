import os
import glob

workspace = "/home/sanjana/Alcon/poc"

print("Searching for DND prompts in all files...")
keywords = ["not call you again", "दोबारा कॉल न करने", "record"]

for root, dirs, files in os.walk(workspace):
    if "venv" in root or ".git" in root or "__pycache__" in root:
        continue
    for file in files:
        filepath = os.path.join(root, file)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for kw in keywords:
                    if kw in content:
                        print(f"Found '{kw}' in file: {filepath}")
                        lines = content.splitlines()
                        for idx, line in enumerate(lines):
                            if kw in line:
                                print(f"  Line {idx+1}: {line.strip()[:150]}")
        except Exception:
            pass
