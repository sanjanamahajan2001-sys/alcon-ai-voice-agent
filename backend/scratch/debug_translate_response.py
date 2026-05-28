import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flows.translation_utils import TranslationAdapter

english_response = "Since you are a valued Alcon Hyundai customer, I have already applied our maximum 15% dealership loyalty discount and waived all physical vehicle inspection charges. To see if we can match a competitor's price or secure a special manager discount, I can connect you to our Insurance Manager right now. Would you like to connect?"

print("Translating:")
print(repr(english_response))
print("\nResult:")
translated = TranslationAdapter.translate_to_hindi(english_response)
print(repr(translated))
