import sys
import os

# Set up paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flows.translation_utils import TranslationAdapter

phrase = "मैं अभी बिजी हूं। आप बाद में कॉल कीजिए।"
print(f"Original phrase: '{phrase}'")

translated = TranslationAdapter.translate_to_english(phrase)
print(f"Translated to English: '{translated}'")
