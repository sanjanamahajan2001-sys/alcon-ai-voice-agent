import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flow_manager import FlowManager
from telephony_logger import TelephonyLogger

fm = FlowManager()
logger = TelephonyLogger()

call_sid = "test_call_123"

# Simulate the first turn
print("--- TURN 1 ---")
twiml1 = fm.handle_voice("1", call_sid, "insurance_start", logger=logger, language="hi-IN")
print(f"AI: {twiml1}")

# Simulate the second turn with "आप मुझे डिटेल्स बता सकती है पहले?"
print("\n--- TURN 2 ---")
twiml2 = fm.handle_process("1", "insurance_consent", "आप मुझे डिटेल्स बता सकती है पहले?", call_sid, "insurance_start", logger=logger)
print(f"AI: {twiml2}")
