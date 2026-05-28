import sys
import json
sys.path.append('.')
from flow_manager import FlowManager

# Initialize FlowManager
fm = FlowManager()

# Let's find customer with phone "+919881012766"
matches = fm.find_customer_by_phone("+919881012766")
customer_id = matches[0]["id"] if matches else "12"
print(f"Customer found: {customer_id}")

call_sid = "DEBUG_PD_CALL_123"

# Step 1: Initialize voice call (language = hi-IN)
print("\n--- TURN 0: GREETING ---")
response_twiml = fm.handle_voice(
    customer_id=customer_id,
    call_sid=call_sid,
    flow_type="pd_pickup_coordination",
    language="hi-IN",
    from_number="+919881012766"
)
print("TwiML output:")
print(response_twiml)

# Get session state
session = fm.session_manager.get_session(call_sid)
print(f"Session after greeting: {json.dumps(session, indent=2)}")

# Step 2: User responds "haa"
print("\n--- TURN 1: USER SAYS 'haa' ---")
response_twiml2 = fm.handle_process(
    customer_id=customer_id,
    step="pd_pickup_consent",
    speech_result="haa",
    call_sid=call_sid,
    flow_type="pd_pickup_coordination"
)
print("TwiML output:")
print(response_twiml2)

# Get session state
session = fm.session_manager.get_session(call_sid)
print(f"Session after 'haa': {json.dumps(session, indent=2)}")

# Step 3: User responds with raw slot sentence
print("\n--- TURN 2: USER SAYS 'send him tomorrow at 10am' ---")
response_twiml3 = fm.handle_process(
    customer_id=customer_id,
    step="pd_pickup_slot",
    speech_result="send him tomorrow at 10am",
    call_sid=call_sid,
    flow_type="pd_pickup_coordination"
)
print("TwiML output:")
print(response_twiml3)

# Get session state
session = fm.session_manager.get_session(call_sid)
print(f"Session after slot selection: {json.dumps(session, indent=2)}")
