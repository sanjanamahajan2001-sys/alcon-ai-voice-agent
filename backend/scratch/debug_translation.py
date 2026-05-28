import sys
import os

# Insert backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flows.translation_utils import TranslationAdapter

test_text_1 = "The Hyundai creta is available in stunning colors like Abyss Black, Atlas White, Titan Grey, Ranger Khaki. I'll keep the Hyundai creta details ready for you. Would you like to know more about its latest features?"
test_text_2 = "Hyundai cars offer extremely comfortable seats, silent cabin, and smooth suspension, making them absolute joy for long highway drives. I'll share the latest Hyundai creta details with you. Would you like to know more about EMI or offers?. Absolutely Ma'am."

print("--- Test 1 (Colors) ---")
res1 = TranslationAdapter.translate_to_hindi(test_text_1)
print(f"Input: {test_text_1}")
print(f"Output: {res1}")

print("\n--- Test 2 (Comfort) ---")
res2 = TranslationAdapter.translate_to_hindi(test_text_2)
print(f"Input: {test_text_2}")
print(f"Output: {res2}")
