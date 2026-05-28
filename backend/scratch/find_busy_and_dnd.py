import os
import glob

workspace = "/home/sanjana/Alcon/poc/backend"

print("Searching for prompts in codebase...")
keywords = ["not call you again", "दोबारा कॉल न करने", "help you with pricing", "convenient"]

for filepath in glob.glob(os.path.join(workspace, "**", "*.*"), recursive=True):
    # skip venv
    if "venv" in filepath:
        continue
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for kw in keywords:
                if kw in content:
                    print(f"Found '{kw}' in: {filepath}")
                    lines = content.splitlines()
                    for idx, line in enumerate(lines):
                        if kw in line:
                            start = max(0, idx - 2)
                            end = min(len(lines), idx + 3)
                            print(f"  Lines {start+1}-{end}:")
                            for l_idx in range(start, end):
                                print(f"    {l_idx+1}: {lines[l_idx]}")
    except Exception as e:
        pass
