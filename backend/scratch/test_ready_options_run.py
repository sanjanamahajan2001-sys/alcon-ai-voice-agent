import sys
import os
import xml.etree.ElementTree as ET

# Set up paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flow_manager import FlowManager, SessionManager
from database import DatabaseManager

class MockSessionManager(SessionManager):
    def __init__(self):
        super().__init__()
        self.sessions = {}

class MockDatabaseManager(DatabaseManager):
    def __init__(self):
        pass
    def update_call_status(self, call_sid, status):
        pass
    def log_call_history(self, *args, **kwargs):
        pass
    def get_customer(self, customer_id):
        return {
            "id": customer_id,
            "name": "Rohan Deshmukh",
            "car_model": "Hyundai Creta",
            "phone": "+919881012767"
        }

fm = FlowManager()
fm.session_manager = MockSessionManager()
fm.db = MockDatabaseManager()

customer_id = "14" # Rohan Deshmukh
call_sid = "TEST_CALL_PANDD"

session = {
    "step": "pd_ready_options",
    "flow_type": "pd_ready",
    "customer_id": customer_id,
    "params": {
        "language": "hi-IN",
        "phone": "+919881012767"
    }
}

test_inputs = [
    "यह आप ड्रॉप कर दीजिए प्लीज!",
    "yeh aap drop kar dijiye please",
    "mai khud aaunga",
    "मैं खुद आऊंगा"
]

print("--- Testing full handle_process with simulated P&D Hindi inputs ---")
for user_in in test_inputs:
    session["step"] = "pd_ready_options"
    fm.session_manager.save_session(call_sid, session)
    
    twiml_str = fm.handle_process(customer_id, "pd_ready_options", user_in, call_sid, flow_type="pd_ready")
    
    # Parse TwiML XML
    root = ET.fromstring(twiml_str)
    ai_says = [say.text for say in root.findall('.//{*}Say') if say.text]
    ai_text = "\n".join(ai_says)
    
    print(f"\nInput: '{user_in}'")
    print(f"  AI response: '{ai_text}'")
