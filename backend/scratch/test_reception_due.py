import json
from flow_manager import FlowManager

class MockLogger:
    def start_call(self, *args, **kwargs): pass
    def update_step(self, *args, **kwargs): pass
    def log_event(self, *args, **kwargs): pass

def test_due_check():
    fm = FlowManager()
    call_sid = "TEST_RECEPTION_1"
    
    print("\n--- TURN 0: INITIAL GREETING ---")
    twiml0 = fm.handle_voice(
        customer_id="1",
        call_sid=call_sid,
        flow_type="reception",
        logger=MockLogger(),
        from_number="+919881012767",
        language="hi-IN"
    )
    print("TwiML 0 Response:")
    print(twiml0)
    
    session = fm.session_manager.get_session(call_sid)
    print("Session step after turn 0:", session.get("step"))
    print("Session current_node_id after turn 0:", session.get("current_node_id"))
    print("Session params 'is_due' after turn 0:", session.get("params", {}).get("is_due"))
    
    print("\n--- TURN 1: USER REQUESTS SERVICE ---")
    # User says "mujhe service appointment book karni thi"
    twiml1 = fm.handle_process(
        customer_id="1",
        step="continue",
        speech_result="mujhe service appointment book karni thi",
        call_sid=call_sid,
        flow_type="reception",
        logger=MockLogger()
    )
    print("TwiML 1 Response:")
    print(twiml1)
    
    session = fm.session_manager.get_session(call_sid)
    print("Session step after turn 1:", session.get("step"))
    print("Session current_node_id after turn 1:", session.get("current_node_id"))
    
    print("\n--- TURN 2: USER PROVIDES REG NUMBER ---")
    # User says "mh15ab1234"
    twiml2 = fm.handle_process(
        customer_id="1",
        step="continue",
        speech_result="mh15ab1234",
        call_sid=call_sid,
        flow_type="reception",
        logger=MockLogger()
    )
    print("TwiML 2 Response:")
    print(twiml2)
    
    session = fm.session_manager.get_session(call_sid)
    print("Session step after turn 2:", session.get("step"))
    print("Session current_node_id after turn 2:", session.get("current_node_id"))
    print("Session params 'is_due' after turn 2:", session.get("params", {}).get("is_due"))
    print("Session params 'service_due_date' after turn 2:", session.get("params", {}).get("service_due_date"))

if __name__ == "__main__":
    test_due_check()
