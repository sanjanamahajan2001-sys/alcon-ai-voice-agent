import os
import glob

workspace = "/home/sanjana/Alcon/poc/backend"

print("Searching for 'customers.json' in backend files (Unix paths)...")
for filepath in glob.glob(os.path.join(workspace, "**", "*.py"), recursive=True):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            if "customers.json" in content:
                print(f"Found in: {filepath}")
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if "customers.json" in line:
                        start = max(0, idx - 2)
                        end = min(len(lines), idx + 3)
                        print(f"  Lines {start+1}-{end}:")
                        for l_idx in range(start, end):
                            print(f"    {l_idx+1}: {lines[l_idx]}")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
