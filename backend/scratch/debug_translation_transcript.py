import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flows.translation_utils import TranslationAdapter

queries = [
    "आपको मेरा नंबर कहां से मिला?",
    "क्या ऑफर है?",
    "एमी कितनी पड़ेगी?",
    "एमी कितनी पढ़ेंगे?",
    "डीजल अवेलेबल है क्या?",
    "सीएनजी मॉडल अवेलेबल है क्या?",
    "मुझे व्हाइट कलर चाहिए था।",
    "आप मुझे बता सकती है की वैल्यू की प्राइस क्या है?",
    "मुझे बीनू की ऑन रोड प्राइस बताइए।"
]

for q in queries:
    print(f"\nQuery: {q}")
    translated_eng = TranslationAdapter.translate_to_english(q)
    print(f"  Translated English: {translated_eng}")
    translated_hi = TranslationAdapter.translate_to_hindi(translated_eng)
    print(f"  Translated Hindi: {translated_hi}")

print("\n--- Test Paragraph Splicing Fix ---")
para = "The Hyundai Creta starts at ₹11 Lakhs with EMI options starting from ₹18,500 per month. I'll share the latest Hyundai creta details with you. Would you like to know more about EMI or offers?"
print("Original English:")
print(para)
print("Translated Hindi:")
print(TranslationAdapter.translate_to_hindi(para))

print("\n--- Test Downpayment Translation Fix ---")
down = "The minimum down payment for the Hyundai creta starts at approximately ₹1.5 Lakhs. Would you like to know more about the features?"
print("Original English:")
print(down)
print("Translated Hindi:")
print(TranslationAdapter.translate_to_hindi(down))


