import sys
sys.path.append('..')
sys.path.append('.')
from flows.translation_utils import TranslationAdapter

inputs = [
    "आप आगे बढ़ सकती है?",
    "आप आगे बढ़ सकती है",
    "aap aage badh sakti hai",
    "आप पॉलिसी रिन्यू कर सकती है",
    "आप मैनेजर से बात करवाइए",
    "आप मैनेजर से बात करवाईये"
]

for inp in inputs:
    res = TranslationAdapter.translate_to_english(inp)
    print(f"Input: '{inp}' -> English: '{res}'")
