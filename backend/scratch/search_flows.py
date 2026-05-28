import os

backend_dir = "/home/sanjana/Alcon/poc/backend"
for root, dirs, files in os.walk(backend_dir):
    if "venv" in root or "__pycache__" in root or ".git" in root or "scratch" in root:
        continue
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if "translate_to_hindi" in content or "translate_to_english" in content:
                        print(f"Found in {path}")
            except Exception as e:
                pass
