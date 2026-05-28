import sys
sys.path.append('.')
from flow_manager import FlowManager

fm = FlowManager()
customer_id = "18" # Manish Pandey
call_sid = "TEST_WORKSHOP_HINDI_SCENARIO_2"

# Reset session
fm.session_manager.clear_session(call_sid)

# Greeting
greeting = fm.handle_voice(
    customer_id=customer_id,
    call_sid=call_sid,
    flow_type="pd_workshop_update",
    language="hi-IN",
    from_number="+919881012770"
)

turns = [
    "haan",
    "windshield bhi check kar lena",
    "theek hai"
]

step = "pd_workshop_consent"
for speech_input in turns:
    print(f"\n[YOU]: {speech_input}")
    response = fm.handle_process(
        customer_id=customer_id,
        step=step,
        speech_result=speech_input,
        call_sid=call_sid,
        flow_type="pd_workshop_update"
    )
    print("TwiML Response:")
    print(response)
    
    session = fm.session_manager.get_session(call_sid)
    if session:
        step = session.get("step")
        if step == "end":
            print("--- CALL ENDED ---")
            break
