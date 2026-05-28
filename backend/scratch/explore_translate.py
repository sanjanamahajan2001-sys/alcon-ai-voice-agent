import os

utils_path = "flows/translation_utils.py"
if not os.path.exists(utils_path):
    utils_path = "/home/sanjana/Alcon/poc/backend/flows/translation_utils.py"

with open(utils_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def translate_to_english" in line:
        print(f"Found at line {idx+1}:")
        start = max(0, idx - 5)
        end = min(len(lines), idx + 80)
        for i in range(start, end):
            print(f"{i+1}: {lines[i]}", end="")
        break
