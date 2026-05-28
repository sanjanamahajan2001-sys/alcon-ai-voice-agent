with open("/home/sanjana/Alcon/poc/backend/intent_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

if "grand i10" in content:
    print("Found 'grand i10' in intent_engine.py")
else:
    print("NOT found 'grand i10' in intent_engine.py")
