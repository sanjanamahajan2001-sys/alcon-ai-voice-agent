import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flows.translation_utils import TranslationAdapter
from flows.insurance_flow import InsuranceFlow

# Initialize locales if needed
TranslationAdapter.load_locales()

test_phrases = [
    "आप मुझे डिटेल्स बता सकती है पहले?",
    "आप मुझे बता सकती है प्रीमियम कितना है?",
    "आप बता सकती है कि जीरो डिप्रेशिएशन क्या होता है?",
    "बंपर तू बंपर का मतलब क्या?",
    "एमसी क्या होता है?",
    "क्या पॉलिसी में इंजन प्रोटेक्शन इंक्लूड है?",
    "कैशलैस क्लेम अवेलेबल है क्या?",
    "पॉलिसी बाजार पेपर दे रहा है।",
    "मैं डीलरशिप से ही क्यों? रिन्यू करूं?",
    "इंफेक्शन एक्सपायरी के बाद व्हेन यू हो जाएगा क्या?"
]

print("=== TRANSLATION & CONSENT TEST RUN ===")
for p in test_phrases:
    eng = TranslationAdapter.translate_to_english(p)
    consent = InsuranceFlow.handle_consent(eng.lower())
    query_ans = InsuranceFlow.handle_query(eng.lower(), {
        "car_model": "Creta",
        "insurance_provider": "HDFC Ergo",
        "current_premium": "₹12,500",
        "loyalty_premium": "₹11,800"
    })
    print(f"Input: '{p}'")
    print(f"  Translated: '{eng}'")
    print(f"  Consent: '{consent}'")
    print(f"  Query Ans: '{query_ans[:60] if query_ans else 'None'}'")
    print("-" * 50)
