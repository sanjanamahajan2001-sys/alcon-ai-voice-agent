import os

# We will search for the Hindi string "record update" or similar in translation_utils.py
# and see what English string it maps to.
hindi_string = "रिकॉर्ड अपडेट कर दूँगी"
english_equivalent = "DND"

with open("flows/translation_utils.py", "r", encoding="utf-8") as f:
    content = f.read()

print("Searching for DND-related translation rules...")
matches = []
for line in content.split("\n"):
    if "Do Not Disturb" in line or "records" in line or "records" in line or "DND" in line:
        matches.append(line)

print(f"Found {len(matches)} matches. Printing first 20:")
for m in matches[:20]:
    print(m)
