import os

workspace = "/home/sanjana/Alcon/poc"

print("Searching for DND prompts in all json files...")
keywords = ["not call you again", "दोबारा कॉल न करने", "convenient"]

for root, dirs, files in os.walk(workspace):
    if "venv" in root or ".git" in root or "node_modules" in root:
        continue
    for file in files:
        if not file.endswith(".json"):
            continue
        filepath = os.path.join(root, file)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                for kw in keywords:
                    if kw in content:
                        print(f"Found '{kw}' in json file: {filepath}")
        except Exception as e:
            pass
