import sys
sys.path.append('.')
from slot_manager import SlotParser

test_cases = [
    "send him tomorrow at 10am",
    "10am",
    "10:00",
    "10:30 PM",
    "at 2",
    "around 4:15 pm",
    "tomorrow morning at 9"
]

for tc in test_cases:
    print(f"Input: '{tc}' -> parsed: '{SlotParser.parse_specific_time(tc)}'")
