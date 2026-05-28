import sys
import json
sys.path.append('.')
from flow_manager import FlowManager

fm = FlowManager()
customer_id = "15" # Pooja Patil
call_sid = "TEST_DRIVER_SAFETY_CALL"

print("\n=== STEP 1: GREETING ===")
greeting = fm.handle_voice(
    customer_id=customer_id,
    call_sid=call_sid,
    flow_type="pd_pickup_coordination",
    language="hi-IN",
    from_number="+919881012766"
)

# User asks "क्या राजेश सेफ ड्राइवर है?" at consent step
print("\n=== STEP 2: USER ASKS 'क्या राजेश सेफ ड्राइवर है?' AT CONSENT ===")
response_consent_query = fm.handle_process(
    customer_id=customer_id,
    step="pd_pickup_consent",
    speech_result="क्या राजेश सेफ ड्राइवर है?",
    call_sid=call_sid,
    flow_type="pd_pickup_coordination"
)
print("TwiML Response:")
print(response_consent_query)

# User answers "haa" to proceed
print("\n=== STEP 3: USER SAYS 'haa' TO PROCEED ===")
response_proceed = fm.handle_process(
    customer_id=customer_id,
    step="pd_pickup_consent",
    speech_result="haa",
    call_sid=call_sid,
    flow_type="pd_pickup_coordination"
)
print("TwiML Response:")
print(response_proceed)

# User asks "क्या राजेश लाइसेंस ड्राइवर है?" at slot selection step
print("\n=== STEP 4: USER ASKS 'क्या राजेश लाइसेंस ड्राइवर है?' AT SLOT SELECTION ===")
response_slot_query = fm.handle_process(
    customer_id=customer_id,
    step="pd_pickup_slot",
    speech_result="क्या राजेश लाइसेंस ड्राइवर है?",
    call_sid=call_sid,
    flow_type="pd_pickup_coordination"
)
print("TwiML Response:")
print(response_slot_query)

# User finally gives slot "send him tomorrow at 10am"
print("\n=== STEP 5: USER GIVES SLOT 'send him tomorrow at 10am' ===")
response_slot_selection = fm.handle_process(
    customer_id=customer_id,
    step="pd_pickup_slot",
    speech_result="send him tomorrow at 10am",
    call_sid=call_sid,
    flow_type="pd_pickup_coordination"
)
print("TwiML Response:")
print(response_slot_selection)
