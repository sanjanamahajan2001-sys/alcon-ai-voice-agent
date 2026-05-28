with open("flows/translation_utils.py", "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for idx, line in enumerate(lines):
    if "is the variant available" in line:
        print(f"Line {idx+1}: {line}")
