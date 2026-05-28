import re
from typing import Dict, Any

class DataCollectionFlow:
    @staticmethod
    def get_missing_field_prompt(customer: Dict[str, Any], session_params: Dict[str, Any]) -> str:
        """Requirement 3B & 3D: Proactively ask for missing fields (Location, EMI Interest)."""
        # 1. Check Location
        if not customer.get("location") and not session_params.get("location"):
            return "By the way, to give you the most accurate on-road price, could you let me know which city you are calling from? This helps me check the latest regional offers at your nearest showroom."
        
        # 2. Check EMI Interest
        if not customer.get("emi_preference") and not session_params.get("emi_preference"):
            return "Are you planning to go for a finance scheme or an EMI option for your next car? We have some very competitive low-interest plans running right now that I can share with you."
            
        # 3. Check Exchange Interest (New)
        if not session_params.get("exchange_interest") and "exchange" not in session_params.get("campaign_type", ""):
            return "Also, would you be interested in exchanging your current vehicle? We offer a free doorstep evaluation and the best market price."

        return None

    @staticmethod
    def extract_data(user_input: str, field_type: str) -> str:
        """Extract specific data from user input."""
        if field_type == "location":
            # Simple extraction for demo purposes
            # In production, this would use a city list or NLP
            words = user_input.split()
            if words: return words[-1].title() 
        return None
