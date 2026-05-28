import sys
import os

# Set up paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flows.translation_utils import TranslationAdapter

phrases = [
    "theeke baat karaviye",
    "manager se baat karavaiye",
    "baat karavaiye",
    "baat karvaiye",
    "baat karwayiye",
    "baat karvayiye"
]

print("Testing manager transfer translations:")
for phrase in phrases:
    translated = TranslationAdapter.translate_to_english(phrase)
    print(f"Original: '{phrase}' -> Translated: '{translated}'")
