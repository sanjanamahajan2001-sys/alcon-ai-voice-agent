import os

def search_files(directory):
    for root, dirs, files in os.walk(directory):
        if "venv" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    for i, line in enumerate(lines):
                        if "[0]" in line:
                            print(f"{file}:{i+1}: {line.strip()}")
                except Exception:
                    pass

if __name__ == "__main__":
    search_files(".")
