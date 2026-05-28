import sys
sys.path.append('.')
from database import DatabaseManager
from flow_manager import FlowManager

db = DatabaseManager()
fm = FlowManager(db)

call_sid = "DEBUG_CALL_12345"
# Setup the session state exactly as it would be before turn 5
# Before turn 5, the session has:
# step: "continue" (from _start_gather)
# current_node_id: "check_consent"
# language: hi-IN
session = {
    "step": "continue",
    "flow_type": "pre_sales_upgrade",
    "customer_id": "12",
    "params": {
        "phone": "+919881012763",
        "language": "hi-IN",
        "car_model": "i20",
        "car": "I20",
        "salutation": "Sir"
    },
    "history": [
        {"role": "ai", "text": "नमस्ते सर। मैं अल्कॉन से सुप्रिया हूँ।..."}
    ],
    "current_node_id": "check_consent"
}
fm.session_manager.save_session(call_sid, session)

# Now execute handle_process
twiml = fm.handle_process(
    customer_id="12",
    step="continue",
    speech_result="aapko mera number kaha se mila?",
    call_sid=call_sid,
    flow_type="pre_sales_upgrade"
)
print("Returned TwiML:")
print(twiml)

# Let's inspect the saved session step and current node ID after execution
updated_session = fm.session_manager.get_session(call_sid)
print("Updated Session:", updated_session)
