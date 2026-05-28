import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flows.translation_utils import TranslationAdapter

print("Starting Hindi translation test...")
english_response = "Certainly! Regarding the Venue, The Venue comes packed with features like Electric Sunroof, Air Purifier, Wireless Charger, 8-inch Touchscreen. Would you like to know more about the features?"
translated = TranslationAdapter.translate_to_hindi(english_response)
print(f"English: {english_response}")
print(f"Hindi: {translated}")
print("Hindi translation finished successfully!")
