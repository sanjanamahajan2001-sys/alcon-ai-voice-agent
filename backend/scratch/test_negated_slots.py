import sys
import os
from datetime import datetime

# Add parent path so we can import translation_utils and slot_manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../flows")))

from flows.translation_utils import TranslationAdapter
from slot_manager import SlotManager

# Initialize SlotManager
sm = SlotManager()

# Reference date: Thursday, May 28, 2026
base_date = datetime(2026, 5, 28).date()

# Test Case 1: Specific slots and ASR error
input_text1 = "9:00 a.m. तो बहुत जल्दी हो जाएगा। आप 10:00 आम का स्लॉट बुक कीजिए।"
print(f"Original text 1: {input_text1}")
translated1 = TranslationAdapter.translate_to_english(input_text1)
print(f"Translated text 1: {translated1}")
res1 = sm.parse_counter_proposal(translated1, base_date, "morning")
target_date1, target_period1, specific_time1, range_override1, negated_times1 = res1

print("\n--- Parsing Results 1 ---")
print(f"Target Date: {target_date1}")
print(f"Target Period: {target_period1}")
print(f"Specific Time: {specific_time1}")
print(f"Range Override: {range_override1}")
print(f"Negated Times: {negated_times1}")

assert specific_time1 == "10:00 AM", f"Expected '10:00 AM', got '{specific_time1}'"
assert "09:00 AM" in negated_times1, f"Expected '09:00 AM' in negated_times, got {negated_times1}"

# Test Case 2: Period negation and Devanagari English inquiry
input_text2 = "नहीं, मुझे सुबह तो पॉसिबल नहीं है। आफ्टरनून नहीं है क्या?"
print(f"\nOriginal text 2: {input_text2}")
translated2 = TranslationAdapter.translate_to_english(input_text2)
print(f"Translated text 2: {translated2}")
res2 = sm.parse_counter_proposal(translated2, base_date, "morning")
target_date2, target_period2, specific_time2, range_override2, negated_times2 = res2

print("\n--- Parsing Results 2 ---")
print(f"Target Date: {target_date2}")
print(f"Target Period: {target_period2}")
print(f"Specific Time: {specific_time2}")
print(f"Range Override: {range_override2}")

assert target_period2 == "afternoon", f"Expected 'afternoon' period, got '{target_period2}'"

print("\n✅ All slot negation and period translation integration tests PASSED successfully!")
