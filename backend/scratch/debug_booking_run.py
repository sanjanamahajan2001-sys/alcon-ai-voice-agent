import sys
import os
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flow_manager import FlowManager
from orchestration_bridge import OrchestrationBridge

flow_manager = FlowManager()
call_sid = "DEBUG_TEST_CALL_12345"

# Let's mock a customer call flow
customer_id = "10"  # Aarav Mehta
flow_type = "booking"

# Turn 1: Start/Greeting and first input
print("--- TURN 1 ---")
# When call is first received, flow_manager.handle_voice is called
# Let's inspect handles
twiml1 = flow_manager.handle_voice(customer_id, call_sid, flow_type, None)
print("TwiML 1:\n", twiml1)

# Press 1 for English
print("\n--- TURN 2 (Select English) ---")
# Gather language redirect or next step
twiml2 = flow_manager.handle_process(customer_id, "language-callback", "1", call_sid, flow_type, None, language="en-IN")
print("TwiML 2:\n", twiml2)

# AI says: Am I speaking with Aarav Mehta Sir?
# User says "yes"
print("\n--- TURN 3 (Speak 'yes') ---")
twiml3 = flow_manager.handle_process(customer_id, "process", "yes", call_sid, flow_type, None, language="en-IN")
print("TwiML 3:\n", twiml3)

# AI says: Would you like to book it today?
# User says "yes"
print("\n--- TURN 4 (Speak 'yes' for booking) ---")
twiml4 = flow_manager.handle_process(customer_id, "process", "yes", call_sid, flow_type, None, language="en-IN")
print("TwiML 4:\n", twiml4)

# AI says: Great. What date would you prefer for the service?.
# User says "28th may"
print("\n--- TURN 5 (Speak '28th may') ---")
s_before = flow_manager.session_manager.get_session(call_sid)
print("Session params before Turn 5:", s_before.get("params", {}) if s_before else "None")
twiml5 = flow_manager.handle_process(customer_id, "process", "28th may", call_sid, flow_type, None, language="en-IN")
print("TwiML 5:\n", twiml5)
s_after = flow_manager.session_manager.get_session(call_sid)
print("Session params after Turn 5:", s_after.get("params", {}) if s_after else "None")

# AI says: Sure. On Thursday, May 28 we have slots at 09:00 AM and 11:00 AM. Which one works better for you?.
# User says "No, I’ll be busy in the morning."
print("\n--- TURN 6 (Speak 'No, I’ll be busy in the morning.') ---")
twiml6 = flow_manager.handle_process(customer_id, "process", "No, I’ll be busy in the morning.", call_sid, flow_type, None, language="en-IN")
print("TwiML 6:\n", twiml6)

# Print variables and current state from session
session = flow_manager.session_manager.get_session(call_sid)
print("\nFINAL SESSION STATE:")
if session:
    print("current_node_id:", session.get("current_node_id"))
    print("variables:")
    for k, v in sorted(session.get("params", {}).items()):
        print(f"  {k}: {v}")
else:
    print("Session not found")
