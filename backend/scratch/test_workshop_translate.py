import sys
sys.path.append('.')
from flows.translation_utils import TranslationAdapter

print("Translation of 'four thousand five hundred rupees':", TranslationAdapter.translate_to_hindi("four thousand five hundred rupees"))
print("Translation of 'by evening':", TranslationAdapter.translate_to_hindi("by evening"))
