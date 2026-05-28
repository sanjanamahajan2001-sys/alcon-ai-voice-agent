import os

filepath = "/home/sanjana/Alcon/poc/backend/flows/insurance_flow.py"

print("Searching in insurance_flow.py...")
keywords = ["not call you again", "busy", "dnd", "convenient", "rejection", "callback"]

try:
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        for kw in keywords:
            count = content.lower().count(kw.lower())
            print(f"Keyword '{kw}': {count} occurrences")
            if count > 0:
                lines = content.splitlines()
                print(f"--- Matches for '{kw}' ---")
                found = 0
                for idx, line in enumerate(lines):
                    if kw.lower() in line.lower():
                        start = max(0, idx - 3)
                        end = min(len(lines), idx + 4)
                        print(f"  Lines {start+1}-{end}:")
                        for l_idx in range(start, end):
                            print(f"    {l_idx+1}: {lines[l_idx]}")
                        found += 1
                        if found >= 10:  # limit output
                            print("  ... and more matches")
                            break
except Exception as e:
    print(f"Error: {e}")
