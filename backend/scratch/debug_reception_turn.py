import sys
import os

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flow_manager import FlowManager
from telephony_logger import TelephonyLogger

class MockBackgroundTasks:
    def add_task(self, func, *args, **kwargs):
        pass

def main():
    os.chdir("/home/sanjana/Alcon/poc/backend")
    flow_manager = FlowManager()
    telephony_logger = TelephonyLogger()
    
    customer_id = "1"
    step = "continue"
    speech_result = "I am looking for a car in the SUV segment."
    call_sid = "DEBUG_RECEPTION_1"
    flow_type = "reception"
    background_tasks = MockBackgroundTasks()
    
    # We also need params like language
    params = {"language": "en-IN"}
    
    print("1. Call Init (handle_voice)...")
    twiml1 = flow_manager.handle_voice(
        customer_id=customer_id,
        call_sid=call_sid,
        flow_type=flow_type,
        logger=telephony_logger,
        from_number="+919881012767",
        background_tasks=background_tasks,
        **params
    )
    print("twiml1 Say:", [say.text for say in from_xml(twiml1)])
    
    print("2. Call process turn (handle_process)...")
    twiml2 = flow_manager.handle_process(
        customer_id=customer_id,
        step=step,
        speech_result=speech_result,
        call_sid=call_sid,
        flow_type=flow_type,
        logger=telephony_logger,
        background_tasks=background_tasks,
        **params
    )
    print("twiml2 Say:", [say.text for say in from_xml(twiml2)])

def from_xml(xml_str):
    import xml.etree.ElementTree as ET
    try:
        return ET.fromstring(xml_str).findall('.//{*}Say')
    except Exception as e:
        print("XML parse error:", e)
        return []

if __name__ == "__main__":
    main()
