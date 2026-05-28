import os

log_path = r"C:\Users\acer\.gemini\antigravity\brain\f807b0ee-51f5-4b03-9e44-76581081f661\.system_generated\tasks\task-654.log"

if not os.path.exists(log_path):
    log_path = "/mnt/c/Users/acer/.gemini/antigravity/brain/f807b0ee-51f5-4b03-9e44-76581081f661/.system_generated/tasks/task-654.log"

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i in range(1475, min(1526, len(lines))):
    print(f"{i+1}: {lines[i]}", end="")
