import sys
import os
import asyncio

# Adjust path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orchestration_bridge import OrchestrationBridge
from database import DatabaseManager

db = DatabaseManager()
bridge = OrchestrationBridge(db)

call_sid = "DEBUG_VOICE_CALL_123"
user_input = "can you reduce the premium"
template_name = "insurance_v2_template"

context = {
    "current_node_id": "query_handler_1",
    "variables": {
        "id": "10",
        "name": "Aarav Mehta",
        "salutation": "Sir",
        "gender": "male",
        "car_model": "Hyundai Venue",
        "car": "Hyundai Venue",
        "insurance_provider": "HDFC Ergo",
        "insurance_expiry_date": "2026-06-15",
        "flow_type": "insurance_start",
        "stage": 1,
        "comparison_offered": False
    },
    "history": [
        {"role": "ai", "text": "Hello Aarav Sir, I am Supriya from Alcon... Your insurance is due..."}
    ]
}

res = asyncio.run(bridge.process_turn(call_sid, user_input, template_name, context))
print("Final Text Response:", repr(res["text"]))
print("Next Node ID:", repr(res["current_node_id"]))
