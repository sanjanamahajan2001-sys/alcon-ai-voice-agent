with open("/home/sanjana/Alcon/poc/backend/flow_manager.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_line = 2770
end_line = 2970
for idx in range(start_line - 1, min(end_line, len(lines))):
    print(f"{idx + 1}: {lines[idx].rstrip()}")
