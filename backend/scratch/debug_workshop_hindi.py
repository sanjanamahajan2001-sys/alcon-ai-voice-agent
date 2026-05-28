import sys
import json
sys.path.append('.')
from flow_manager import FlowManager

fm = FlowManager()
customer_id = "18" # Manish Pandey
call_sid = "TEST_WORKSHOP_HINDI_CALL"

def run_scenario(name, turns):
    print(f"\n==============================================")
    print(f" SCENARIO: {name}")
    print(f"==============================================")
    
    # Reset call
    fm.session_manager.clear_session(call_sid)
    
    # Greeting
    greeting = fm.handle_voice(
        customer_id=customer_id,
        call_sid=call_sid,
        flow_type="pd_workshop_update",
        language="hi-IN",
        from_number="+919881012770"
    )
    
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
        
        # Get next step from session
        session = fm.session_manager.get_session(call_sid)
        if session:
            step = session.get("step")
            if step == "end":
                print("--- CALL ENDED ---")
                break

# Scenario 1: Confirm issues, no additional concerns, proceed
run_scenario("Scenario 1: Confirm issues -> No additional concerns -> Proceed", [
    "haan",
    "nahi bas utna hi",
    "theek hai proceed karo"
])

# Scenario 2: Confirm issues, add windshield concern, proceed
run_scenario("Scenario 2: Confirm issues -> Add windshield -> Proceed", [
    "haan",
    "windshield bhi check kar lena",
    "theek hai"
])

# Scenario 3: Confirm issues, no concerns, cost objection explanation, proceed
run_scenario("Scenario 3: Confirm issues -> No concerns -> Cost objection -> Explanation -> Proceed", [
    "haan",
    "nahi bas utna hi",
    "itna mehenga kyu hai?",
    "chalo theek hai proceed karo"
])

# Scenario 4: Confirm issues, no concerns, cost objection explanation, connect to advisor
run_scenario("Scenario 4: Confirm issues -> No concerns -> Cost objection -> Request Advisor Callback", [
    "haan",
    "nahi bas utna hi",
    "bahut zyada price hai kyu?",
    "nahi proceed mat karo, advisor se connect karvao"
])
