import sys
import os
import json
import asyncio

sys.path.append('..')
sys.path.append('.')

# Set env variable to use template
os.environ["USE_INSURANCE_TEMPLATE"] = "True"

from flow_manager import FlowManager
from database import DatabaseManager
from orchestration_bridge import ConditionNodeExecutor

async def test_scenarios():
    db = DatabaseManager()
    fm = FlowManager(db)
    executor = ConditionNodeExecutor(db)
    
    # We want to see how these user inputs behave:
    test_inputs = [
        "app aage bad sakti hai",
        "app aage badh sakti hai",
        "aap policy renew kar sakti hai",
        "आप पॉलिसी रिन्यू कर सकती है",
        "aap manager se baat karvaiye",
        "aap manager se baat karwaye",
        "आप मैनेजर से बात करवाइए"
    ]
    
    for inp in test_inputs:
        print(f"\n=====================================")
        print(f"RAW USER INPUT: '{inp}'")
        
        # 1. Translation
        from flows.translation_utils import TranslationAdapter
        translated = TranslationAdapter.translate_to_english(inp)
        print(f"TRANSLATED INPUT: '{translated}'")
        
        # 2. Check if yes/no/rejection/dnd match on raw and translated input
        def check_word(word_list, text):
            import re
            for word in word_list:
                if any(ord(c) > 127 for c in word):
                    pattern = rf'(?<![a-zA-Z0-9\u0900-\u097F]){re.escape(word)}(?![a-zA-Z0-9\u0900-\u097F])'
                else:
                    pattern = rf'\b{re.escape(word)}\b'
                if re.search(pattern, text, re.I):
                    return True
            return False
            
        for text_type, text_to_check in [("RAW", inp), ("TRANSLATED", translated)]:
            last_msg = text_to_check.lower().strip()
            is_busy = check_word(['busy', 'meeting', 'later', 'call back', 'not now', 'driving'], last_msg)
            is_rejection = check_word(["no thanks", "dont need", "no interest", "not interested", "dont want", "not looking"], last_msg)
            is_wrong = check_word(["wrong number", "not me", "incorrect", "wrong person", "sold", "no longer have", "don't have that car"], last_msg)
            is_dnd = check_word(['stop', 'don\'t call', 'do not call', 'remove', 'dnd', 'annoying', 'not interested'], last_msg)
            is_yes = check_word(["yes", "yeah", "correct", "yep", "speaking", "sure", "ok", "okay", "good", "satisfied", "proceed", "hello", "hi", "send", "share", "whatsapp", "bilkul", "हाँ", "हां", "हाँजी", "हांजी", "ठीक", "बोल रही हूँ", "बोल रही हो", "बोल रहा हूँ", "बोल रहा हो", "बोल रही हु", "बोल रहा हु", "आगे बढ़", "आगे बढ़", "aage badh", "aage badho", "aage badhiye"], last_msg)
            is_no = check_word(["no", "nope", "dont", "don't", "not now", "stop", "not interested"], last_msg)
            is_transfer = check_word(['advisor', 'manager', 'person', 'human', 'specialist', 'connect', 'transfer', 'speak to someone', 'sales', 'representative', 'executive'], last_msg)
            
            print(f"  [{text_type}] is_yes: {is_yes}, is_no: {is_no}, is_dnd: {is_dnd}, is_rejection: {is_rejection}, is_busy: {is_busy}, is_transfer: {is_transfer}")
            
        # 3. Direct handle_consent check
        from flows.insurance_flow import InsuranceFlow
        intent = InsuranceFlow.handle_consent(translated.lower())
        print(f"  handle_consent on translated: '{intent}'")

if __name__ == "__main__":
    asyncio.run(test_scenarios())
