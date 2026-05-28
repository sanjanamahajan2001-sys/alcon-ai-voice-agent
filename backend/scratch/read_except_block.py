import os

filepath = "/home/sanjana/Alcon/poc/backend/orchestration_bridge.py"

try:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        start = 1125
        end = 1195
        print(f"Viewing lines {start}-{end} of orchestration_bridge.py:")
        for idx in range(start - 1, min(len(lines), end)):
            print(f"  {idx+1}: {lines[idx]}")
except Exception as e:
    print(f"Error: {e}")
