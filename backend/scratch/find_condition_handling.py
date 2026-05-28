import os

filepath = "/home/sanjana/Alcon/poc/backend/orchestration_bridge.py"

print("Searching in orchestration_bridge.py...")
keywords = ["User Intent", "Consent Check"]

try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()
        for kw in keywords:
            print(f"\n--- Matches for '{kw}' ---")
            for idx, line in enumerate(lines):
                if kw in line:
                    start = max(0, idx - 4)
                    end = min(len(lines), idx + 35)  # show plenty of lines to see logic
                    print(f"  Lines {start+1}-{end}:")
                    for l_idx in range(start, end):
                        print(f"    {l_idx+1}: {lines[l_idx]}")
except Exception as e:
    print(f"Error: {e}")
