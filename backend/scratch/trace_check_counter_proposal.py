import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
from slot_manager import SlotManager

manager = SlotManager()
variables = {
    'target_date_raw': '2026-05-28', 
    'target_period': None,
    'slot_negotiation_depth': 1
}
last_msg = "no, i’ll be busy in the morning."

base_date_str = variables.get("target_date_raw", datetime.now().date().strftime("%Y-%m-%d"))
base_date = datetime.strptime(base_date_str, "%Y-%m-%d").date()
current_period = variables.get("target_period")

target_date, target_period, specific_time, range_override = manager.parse_counter_proposal(last_msg, base_date, current_period)
print("parse_counter_proposal:")
print("  target_date:", target_date)
print("  target_period:", target_period)
print("  specific_time:", specific_time)
print("  range_override:", range_override)

available_slots = manager.find_slots_for_date_and_period(target_date, target_period, range_override)
print("available_slots:", available_slots)

if len(available_slots) > 1:
    variables["matching_period_slots_text"] = " and ".join(available_slots[:2])
    variables["target_date_raw"] = target_date.strftime("%Y-%m-%d")
    variables["target_period"] = target_period
    
    # Determine relative day phrase
    from date_utils import format_date_full
    today = datetime.now().date()
    if target_date == today:
        day_rel = "today"
    elif target_date == today + timedelta(days=1):
        day_rel = "tomorrow"
    else:
        day_rel = format_date_full(target_date)
    
    if target_period:
        variables["requested_day_rel"] = f"{day_rel} {target_period}"
    else:
        variables["requested_day_rel"] = day_rel

print("\nAFTER EXECUTION:")
for k, v in variables.items():
    print(f"  {k}: {v}")
