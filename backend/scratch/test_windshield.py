import sys
sys.path.append('.')
from flows.translation_utils import TranslationAdapter

user_input = "haan please aap windshield bhi check kijiyega usme bhi issue hai"
english_translated = TranslationAdapter.translate_to_english(user_input)
print("1. translate_to_english result:")
print(english_translated)

ai_response_english = f"I've noted down: {english_translated}."
hindi_translated = TranslationAdapter.translate_to_hindi(ai_response_english)
print("\n2. translate_to_hindi result:")
print(hindi_translated)
