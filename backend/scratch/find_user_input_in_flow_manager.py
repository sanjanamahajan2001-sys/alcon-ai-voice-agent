import os

filepath = "/home/sanjana/Alcon/poc/backend/flow_manager.py"

print("Searching for user_input in flow_manager.py...")
keywords = ["user_input", "user_input_lower", "translate_to_english"]

try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()
        for kw in keywords:
            print(f"\n--- Matches for '{kw}' ---")
            found = 0
            for idx, line in enumerate(lines):
                if kw in line:
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 3)
                    print(f"  Line {idx+1}: {line.strip()}")
                    found += 1
                    if found >= 15:
                        print("  ... and more matches")
                        break
except Exception as e:
    print(f"Error: {e}")
