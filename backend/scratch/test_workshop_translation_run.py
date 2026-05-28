import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flows.translation_utils import TranslationAdapter

test_phrases = [
    "हाँ अब कर सकते हैं",
    "यह आप ड्रॉप कर दीजिए प्लीज!",
    "thoda kam karo na premium",
    "zero dep kya hota hai",
    "nayi gaadi leni hai",
    "mujhe suv segment mein gaadi dekhni hai"
]

for phrase in test_phrases:
    result = TranslationAdapter.translate_to_english(phrase)
    print(f"Input: '{phrase}' -> Translated: '{result}'")
