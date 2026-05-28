import sys
sys.path.append('.')
from intent_engine import IntentEngine
from flows.translation_utils import TranslationAdapter

# Mock KB data
kb_data = {
    "models": {
        "creta": {
            "name": "Creta",
            "price": "₹11 Lakhs",
            "emi_starts": "₹18,500"
        }
    }
}

engine = IntentEngine(kb_data)

queries = [
    "aapko mera number kaha se mila?",
    "yeh genuine call hai kya?"
]

for q in queries:
    print(f"Query: {q}")
    res = engine.handle_query(q, info=kb_data["models"]["creta"], variables={"car_model": "creta"})
    if res:
        english_text = res["text"]
        print(f"  English: {english_text}")
        hindi_text = TranslationAdapter.translate_to_hindi(english_text)
        print(f"  Hindi: {hindi_text}")
    else:
        print("  No response from intent engine!")
