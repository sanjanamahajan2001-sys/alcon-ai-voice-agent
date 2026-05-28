import json

with open("data/telephony_history.json", "r") as f:
    history = json.load(f)

# The history dictionary key-values
recent_sid = None
recent_data = None
for sid, data in list(history.items())[-5:]:
    print("SID:", sid)
    print("KEYS:", data.keys())
    print("TRANSCRIPT:")
    for t in data.get("transcript", []):
        print(f"  {t['speaker']}: {t['text']}")
