import sys
import os
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flows.translation_utils import TranslationAdapter
from flows.insurance_flow import InsuranceFlow

# Let's inspect rejection phrases matching
rejection_phrases = [
    r'\bnot interested\b', r'\bstop calling\b', r'\bdont call\b', r'\bdon\'t call\b', 
    r'\bno thanks\b', r'\bwrong number\b', r'\bno\b', r'\bnope\b', r'\bnot want\b', 
    r'\bwhy are you calling\b', r'\bagain and again\b', r'\bdon\'t want\b', r'\bremove me\b'
]

inputs = [
    "aap mujhe details bata sakti hai pehle",
    "आप मुझे डिटेल्स बता सकती है पहले",
    "आप बता सकती है कि जीरो डिप्रेशिएशन क्या होता है",
    "एमसी क्या होता है",
    "कैशलैस क्लेम अवेलेबल है क्या",
    "मैं डीलरशिप से ही क्यों रिन्यू करूं"
]

print("=== REJECTION PHRASE MATCHING TEST ===")
for inp in inputs:
    matched = []
    for phrase in rejection_phrases:
        if re.search(phrase, inp.lower()):
            matched.append(phrase)
    print(f"Input: '{inp}' -> Matches: {matched}")
