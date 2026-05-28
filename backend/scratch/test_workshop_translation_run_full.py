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
            "name": "Manish Pandey",
            "car_model": "Hyundai Venue",
            "phone": "+919881012770"
        }

fm = FlowManager()
fm.session_manager = MockSessionManager()
fm.db = MockDatabaseManager()

customer_id = "18"
call_sid = "TEST_CALL_123"

session = {
    "step": "pd_workshop_estimate",
    "flow_type": "pd_workshop_update",
    "customer_id": customer_id,
    "params": {
        "language": "hi-IN",
        "phone": "+919881012770"
    }
}

test_inputs = [
    "हाँ अब कर सकते हैं",
    "haa aab service shuru kar sakte hai",
    "aap shuru kar sakte hai",
    "itni cost kisliye",
    "mai advisor se baat karna chahungi",
    "मैं एडवाइजर से बात करना चाहूंगी"
]

print("--- Testing full handle_process with simulated Hindi inputs ---")
for user_in in test_inputs:
    session["step"] = "pd_workshop_estimate"
    fm.session_manager.save_session(call_sid, session)
    
    twiml_str = fm.handle_process(customer_id, "pd_workshop_estimate", user_in, call_sid, flow_type="pd_workshop_update")
    
    # Parse TwiML XML
    root = ET.fromstring(twiml_str)
    ai_says = [say.text for say in root.findall('.//{*}Say') if say.text]
    ai_text = "\n".join(ai_says)
    
    gather = root.find('.//{*}Gather')
    action = gather.get('action') if gather is not None else "None (Hangup/Transfer)"
    
    print(f"\nInput: '{user_in}'")
    print(f"  AI response: '{ai_text}'")
    print(f"  Next Action URL: '{action}'")
