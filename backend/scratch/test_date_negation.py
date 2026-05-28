import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from slot_manager import SlotManager

manager = SlotManager()
base_date = datetime(2026, 5, 28).date() # Thursday
current_period = "morning"

# Test date negation: "actually not on thursday"
print("\n=== TEST DATE NEGATION ===")
user_input = "actually not on thursday"
target_date, target_period, specific_time, range_override, negated_times = manager.parse_counter_proposal(user_input, base_date, current_period)
print(f"Input: '{user_input}'")
print(f"Target Date: {target_date} (Should be Friday, May 29)")
print(f"Target Period: {target_period}")
print(f"Specific Time: {specific_time}")
print(f"Negated Times: {negated_times}")
