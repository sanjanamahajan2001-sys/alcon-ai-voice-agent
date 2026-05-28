with open("/home/sanjana/Alcon/poc/backend/flow_manager.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "translate_to_hindi" in line or "translate_to_english" in line:
        print(f"Line {idx + 1}: {line.strip()}")
