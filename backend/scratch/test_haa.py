import sys
import os

# Add parent path so we can import translation_utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../flows")))

from flows.translation_utils import TranslationAdapter

test_cases = [
    # Positive / Consent
    ("हाँ", "yes"),
    ("हाँ बोलिए", "yes"),
    ("हाँ बोलिये", "yes"),
    ("हाँ जी बोलिए", "yes"),
    ("बोलिए!", "yes"),
    ("हाँ!", "yes"),
    ("हाँ बोल रही हूँ", "yes"),
    ("बोल रही हूँ", "yes"),
    ("बोल रही हु", "yes"),
    ("हाँ बोल रहा हूँ", "yes"),
    ("हाँ बोल रही हु", "yes"),
    ("ठीक है", "yes"),
    ("हाँजी बोलिए", "yes"),
    ("हां", "yes"),
    ("हां संजना बोल रही हो", "yes"),
    ("हां बोल रही हो", "yes"),
    ("बोल रही हो", "yes"),
    ("हांजी बोलिए", "yes"),
    
    # Negative
    ("नहीं", "no"),
    ("नही जी", "no"),
    ("मत करो", "no"),
    ("नहीं करना", "no"),
    
    # Handover
    ("बात कराइए", "connect me"),
    ("बात करवाओ", "connect me"),
    ("कनेक्ट कर दो", "connect me"),
    
    # Intents
    ("नयी गाड़ी खरीदनी है", "i want to buy a new car"),
    ("सर्विस बुक करनी है", "i want to book a service"),
    
    # Unchanged
    ("कल सुबह 10 baje", "tomorrow morning 10:00"),
    
    # ASR errors and slot negotiation/negation
    ("9:00 a.m. तो बहुत जल्दी हो जाएगा। आप 10:00 आम का स्लॉट बुक कीजिए।", "9:00 am तो too early हो जाएगा। आप 10:00 am का स्लॉट बुक कीजिए।"),
]

print("🔍 RUNNING DEVANAGARI TRANSLATION TESTS...")
passed = 0
failed = 0

for val, expected in test_cases:
    res = TranslationAdapter.translate_to_english(val)
    if res == expected:
        print(f"✅ PASS: '{val}' -> '{res}'")
        passed += 1
    else:
        print(f"❌ FAIL: '{val}' -> expected '{expected}', got '{res}'")
        failed += 1

print(f"\n📊 RESULTS: {passed} passed, {failed} failed.")
if failed > 0:
    sys.exit(1)
else:
    sys.exit(0)
