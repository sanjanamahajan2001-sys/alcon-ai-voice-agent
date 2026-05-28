import os

filepath = "/home/sanjana/Alcon/poc/backend/flows/translation_utils.py"

try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()
        # Find where def translate_to_english is defined
        for idx, line in enumerate(lines):
            if "def translate_to_english" in line:
                start = idx
                end = idx + 100
                print(f"Viewing lines {start+1}-{end+1} of translation_utils.py:")
                for l_idx in range(start, min(len(lines), end)):
                    print(f"  {l_idx+1}: {lines[l_idx]}")
                break
except Exception as e:
    print(f"Error: {e}")
