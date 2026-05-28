import os

filepath = "/home/sanjana/Alcon/poc/backend/flow_manager.py"

try:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        start = 1050
        end = 1110
        print(f"Viewing lines {start}-{end} of flow_manager.py:")
        for idx in range(start - 1, min(len(lines), end)):
            print(f"  {idx+1}: {lines[idx]}")
except Exception as e:
    print(f"Error: {e}")
