import os

filename = "flow_manager.py"
search_phrase = "handle_consent"

with open(filename, "r", encoding="utf-8") as f:
    content = f.read()

lines = content.split("\n")
for idx, line in enumerate(lines):
    if search_phrase in line:
        print(f"Line {idx+1}: {line}")
