import os

filepath = "/home/sanjana/Alcon/poc/backend/flow_manager.py"

print("Searching in flow_manager.py...")
keywords = ["TranslationAdapter", "translate", "translation", "adapter", "dnd", "busy", "callback"]

try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()
        for kw in keywords:
            count = content.lower().count(kw.lower())
            print(f"Keyword '{kw}': {count} occurrences")
            if count > 0:
                print(f"--- Matches for '{kw}' ---")
                found = 0
                for idx, line in enumerate(lines):
                    if kw.lower() in line.lower():
                        start = max(0, idx - 2)
                        end = min(len(lines), idx + 3)
                        print(f"  Lines {start+1}-{end}:")
                        for l_idx in range(start, end):
                            print(f"    {l_idx+1}: {lines[l_idx]}")
                        found += 1
                        if found >= 5:
                            break
except Exception as e:
    print(f"Error: {e}")
