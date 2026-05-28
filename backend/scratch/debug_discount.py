import sys
import os
import json
import asyncio

sys.path.append('..')
sys.path.append('.')

from flows.translation_utils import TranslationAdapter
from flows.insurance_flow import InsuranceFlow

inputs = [
    "premium itna expensive kyun hai?",
    "expiry ke badd renew ho jayega kya?",
    "delarship se hi kyun renew karu",
    "app aage bad sakti hai",
    "aap policy renew kar sakti hai",
    "आप पॉलिसी रिन्यू कर सकती है"
]

for inp in inputs:
    inp_lower = inp.lower()
    translated = TranslationAdapter.translate_to_english(inp_lower)
    intent = InsuranceFlow.handle_consent(translated)
    query_res = InsuranceFlow.handle_query(translated, {"car_model": "i10", "car": "i10", "current_premium": "₹9,800", "loyalty_premium": "₹9,100"}, stage=3)
    
    print(f"\n=====================================")
    print(f"RAW INPUT: '{inp}'")
    print(f"TRANSLATED: '{translated}'")
    print(f"Consent Intent: '{intent}'")
    print(f"Query Result (English): '{query_res}'")
    if query_res:
        hindi_res = TranslationAdapter.translate_to_hindi(query_res)
        print(f"Query Result (Hindi): '{hindi_res}'")
