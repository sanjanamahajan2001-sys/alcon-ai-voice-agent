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

async def run_simulation():
    db = DatabaseManager()
    fm = FlowManager(db)
    
    # Enable insurance template in flow manager
    fm.use_insurance_template = True
    
    # We use a unique session ID
    session_id = "test_proceed_simulation_1"
    
    # Reset/clear previous session from DB or memory if any
    fm.session_manager.clear_session(session_id)
    
    # Insert a dummy customer into DB
    # Hyundai i10, Sanya Malhotra
    customer_id = 9  # Sanya Malhotra in database is usually 9 or we can check or create one
    # Let's find customer 9 in database or customers.json
    customers_path = "data/customers.json"
    customer = None
    if os.path.exists(customers_path):
        with open(customers_path, "r") as f:
            customers = json.load(f)
            for c in customers:
                if "Sanya" in c.get("name", ""):
                    customer = c
                    customer_id = c.get("id")
                    break
    
    if not customer:
        customer_id = 9
    
    # Start session
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
    
    # Simulating the turn-by-turn conversation
    turns = [
        (None, "Start/Greeting"),
        ("हां जी!", "हां जी!"),
        ("आप मुझे एक बार फिर प्रीमियम के बारे में बताएंगे?", "प्रीमियम?"),
        ("जीरो डिप्रेशिएशन क्या?", "जीरो डिप्रेशिएशन?"),
        ("मुझे पॉलिसी बाजार चिपर दे रहा है।", "पॉलिसी बाजार चिपर"),
        ("आप आगे बढ़ सकती है?", "आगे बढ़ सकती है?")
    ]
    
    for user_input, label in turns:
        print(f"\n--- Customer says: '{user_input}' ({label}) ---")
        response = fm.get_next_action(session_id, user_input)
        print(f"Agent response: '{response.get('text')}'")
        print(f"Next Node / Step: '{response.get('next_step')}'")
        
        # Print session variables and state
        current_session = fm.session_manager.get_session(session_id)
        print(f"Session Step: '{current_session.get('step')}'")
        print(f"Session Node: '{current_session.get('current_node_id')}'")
        print(f"Lead status: '{current_session.get('params', {}).get('lead_status')}'")
        print(f"Disposition: '{current_session.get('params', {}).get('disposition')}'")

if __name__ == "__main__":
    asyncio.run(run_simulation())
