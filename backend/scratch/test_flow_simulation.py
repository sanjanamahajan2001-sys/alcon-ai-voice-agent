import sys
import os
import asyncio

# Set up paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database import DatabaseManager
from orchestration_bridge import ConditionNodeExecutor

async def run_simulation():
    # Mock DB
    db = DatabaseManager()
    executor = ConditionNodeExecutor(db)
    
    # Context setup
    node_data = {
        "id": "check_intent",
        "type": "conditionNode",
        "label": "User Intent"
    }
    
    # 1. Hindi busy input
    context_hindi = {
        "user_input": "मैं अभी बिजी हूं। आप बाद में कॉल कीजिए।",
        "variables": {
            "flow_type": "insurance_start",
            "stage": 3,
            "salutation": "Ma'am"
        },
        "session_id": "test_session_123",
        "current_node_id": "check_intent"
    }
    
    print("\n--- Simulating untranslated/direct Hindi input ---")
    res_hindi = await executor.execute(node_data, context_hindi)
    print(f"Condition executor outcome: {res_hindi}")
    
    # 2. Translated busy input (what actually happens in get_next_action after TranslationAdapter runs)
    context_translated = {
        "user_input": "busy",
        "variables": {
            "flow_type": "insurance_start",
            "stage": 3,
            "salutation": "Ma'am"
        },
        "session_id": "test_session_123",
        "current_node_id": "check_intent"
    }
    
    print("\n--- Simulating translated input ('busy') ---")
    res_trans = await executor.execute(node_data, context_translated)
    print(f"Condition executor outcome: {res_trans}")
    
    print("\n✅ Verification complete.")

if __name__ == "__main__":
    asyncio.run(run_simulation())
