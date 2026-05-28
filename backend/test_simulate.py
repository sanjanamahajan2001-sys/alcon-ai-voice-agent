import sys
sys.path.append(".")
import asyncio
from fastapi import BackgroundTasks
from orchestration_bridge import OrchestrationBridge
from flow_manager import FlowManager

class MockLogger:
    def start_call(self, *args, **kwargs): pass
    def update_step(self, *args, **kwargs): pass
    def log_event(self, *args, **kwargs): pass

class MockBackgroundTasks(BackgroundTasks):
    def add_task(self, func, *args, **kwargs):
        pass

async def test_reception():
    flow_manager = FlowManager()
    
    # Simulate POST /voice logic Turn 0
    customer_id = "Unknown"
    call_sid = "SIM_CALL_TEST_999"
    flow_type = "reception"
    from_number = "+910000000000"
    
    bg_tasks = MockBackgroundTasks()
    
    print("TURN 0")
    try:
        twiml = flow_manager.handle_voice(
            customer_id=customer_id,
            call_sid=call_sid,
            flow_type=flow_type,
            logger=MockLogger(),
            from_number=from_number,
            background_tasks=bg_tasks
        )
        print("TWIML Turn 0:\n", twiml)
    except Exception as e:
        import traceback
        traceback.print_exc()

    print("\nTURN 1")
    try:
        twiml = flow_manager.handle_voice(
            customer_id=customer_id,
            call_sid=call_sid,
            flow_type=flow_type,
            logger=MockLogger(),
            from_number=from_number,
            background_tasks=bg_tasks,
            SpeechResult="new car"
        )
        print("TWIML Turn 1:\n", twiml)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reception())
