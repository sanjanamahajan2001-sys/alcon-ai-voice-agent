import os

filepath = "/home/sanjana/Alcon/poc/backend/flows/translation_utils.py"

try:
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        start = 1639
        end = 1700
        print(f"Viewing lines {start}-{end} of translation_utils.py:")
        for idx in range(start - 1, min(len(lines), end)):
            print(f"  {idx+1}: {lines[idx]}")
except Exception as e:
    print(f"Error: {e}")
