import os

def main():
    path = "poc/backend/orchestration_bridge.py"
    if os.path.exists(path):
        print(f"=== {path} ===")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines()
        for idx in range(1500, min(1570, len(lines))):
            print(f"{idx+1}: {lines[idx]}")
            
if __name__ == "__main__":
    main()
