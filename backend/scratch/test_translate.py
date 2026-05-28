import sys
import os

# Adjust path to import flows
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flows.translation_utils import TranslationAdapter

TranslationAdapter.load_locales()

test_cases = [
    "The Creta is available in both Petrol and Diesel with advanced Automatic and Manual options.",
    "The Hyundai creta is available in both Petrol and Diesel with advanced Automatic (IVT/DCT) and Manual options. Would you like to know the price for the Automatic variant?. The Hyundai creta comes in multiple engine options including the Turbo Petrol and Diesel. For a detailed variant comparison, I can connect you with our product specialist.",
    "Certainly! Regarding the Verna, The Verna comes packed with features like Horizon LED Lamps, Heated Seats, 10.25-inch Screen, 6 Airbags standard. Would you like to know more about EMI?. That's a valid point. The Verna comes packed with features like Horizon LED Lamps, Heated Seats, 10.25-inch Screen, 6 Airbags standard.",
]

for idx, tc in enumerate(test_cases, 1):
    print(f"Test Case #{idx}:")
    print(f"  Input:  {tc}")
    print(f"  Output: {TranslationAdapter.translate_to_hindi(tc)}")
    print("-" * 50)
