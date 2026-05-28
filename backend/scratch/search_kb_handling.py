import os

def main():
    path = "poc/backend/orchestration_bridge.py"
    if os.path.exists(path):
        print(f"=== {path} ===")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "IntentEngine" in line or "intent_engine" in line or "KnowledgeBase" in line or "kb_handler" in line:
                print(f"Line {i+1}: {line.strip()}")
                for j in range(max(0, i-2), min(len(lines), i+8)):
                    print(f"  {j+1}: {lines[j]}")
                print("-" * 35)

if __name__ == "__main__":
    main()
