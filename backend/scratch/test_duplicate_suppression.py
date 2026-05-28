import re

def clean_text(t):
    return re.sub(r'[^\w\s]', '', t).lower().strip()

text = "Sure. On Thursday, May 28 afternoon we have slots at 01:30 PM and 04:00 PM. Which one works better for you?"
last_ai_text = "Sure. On Thursday, May 28 we have slots at 09:00 AM and 11:00 AM. Which one works better for you?."

print("clean_text(text):", clean_text(text))
print("clean_text(last_ai_text):", clean_text(last_ai_text))
print("clean_text(text) in clean_text(last_ai_text):", clean_text(text) in clean_text(last_ai_text))
print("clean_text(last_ai_text) in clean_text(text):", clean_text(last_ai_text) in clean_text(text))
