import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime
from slot_manager import SlotManager

manager = SlotManager()
base_date = datetime.strptime("2026-05-28", "%Y-%m-%d").date()
current_period = "morning"
last_msg = "No, I’ll be busy in the morning."

target_date, target_period, specific_time, range_override = manager.parse_counter_proposal(last_msg, base_date, current_period)
print("parse_counter_proposal:")
print("  target_date:", target_date)
print("  target_period:", target_period)
print("  specific_time:", specific_time)
print("  range_override:", range_override)
