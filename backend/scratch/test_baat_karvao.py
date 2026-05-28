import sys
import os
import json
import asyncio

sys.path.append('..')
sys.path.append('.')

os.environ["USE_INSURANCE_TEMPLATE"] = "True"

from flow_manager import FlowManager
from database import DatabaseManager

async def test_baat_karvao():
    db = DatabaseManager()
    fm = FlowManager(db)
    fm.use_insurance_template = True
    session_id = "test_baat_karvao_session"
    fm.session_manager.clear_session(session_id)
    
    # Sanya Malhotra
    customer_id = 9
    
    session = {
        "step": "start",
        "flow_type": "insurance_start",
        "customer_id": customer_id,
        "params": {
            "stage": 3,
            "language": "hi-IN"
        },
        "chat_history": []
    }
    fm.session_manager.save_session(session_id, session)
    
    # 1. Start greeting
    fm.get_next_action(session_id, None)
    # 2. Correct person
    fm.get_next_action(session_id, "हां जी!")
    # 3. Premium question
    fm.get_next_action(session_id, "आप मुझे एक बार फिर प्रीमियम के बारे में बताएंगे?")
    # 4. Zero dep question
    fm.get_next_action(session_id, "जीरो डिप्रेशिएशन क्या?")
    
    # Now we are at check_consent node (offer_details is shown)
    # Let's say "आप मैनेजर से बात करवाइए"
    print("\n--- Customer says: 'आप मैनेजर से बात करवाइए' ---")
    response = fm.get_next_action(session_id, "आप मैनेजर से बात करवाइए")
    print(f"Agent response: '{response.get('text')}'")
    print(f"Next Node / Step: '{response.get('next_step')}'")
    
    current_session = fm.session_manager.get_session(session_id)
    print(f"Session Step: '{current_session.get('step')}'")
    print(f"Session Node: '{current_session.get('current_node_id')}'")

if __name__ == "__main__":
    asyncio.run(test_baat_karvao())
