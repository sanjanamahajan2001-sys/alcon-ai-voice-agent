from typing import Dict, Any

class IntroFlow:
    @staticmethod
    def get_greeting(salutation: str, name: str, car: str, campaign_type: str, vehicle_age: Any = None, location: str = None, current_emi: str = None) -> str:
        """Requirement 3A: Establish context + permission with relevant hooks."""
        try:
            if vehicle_age is not None:
                vehicle_age = int(vehicle_age)
        except (ValueError, TypeError):
            vehicle_age = None
            
        age_suffix = "s" if vehicle_age and vehicle_age > 1 else ""
        age_str = f" {vehicle_age}-year-old" if vehicle_age else ""
        age_duration = f" {vehicle_age} year{age_suffix}" if vehicle_age else " some time"
        
        # Personalized fragments
        loc_fragment = f" for the {location} region" if location else ""
        emi_fragment = f" You're currently paying {current_emi} EMI, and with our latest options, we could potentially lower that or upgrade you for the same amount." if current_emi else ""

        if campaign_type == "upgrade":
            return f"Hello {salutation}, I'm Supriya from Alcon. I see you've been enjoying your {car} for{age_duration} now, and I'm calling because it's currently eligible for an exclusive upgrade to the 2024 model with the same EMI. Is this something you'd like to explore?"
        elif campaign_type == "exchange":
            return f"Hello {salutation}, I'm Supriya from Alcon. I'm calling regarding your {car}{loc_fragment}. We are running a special exchange festival this week, and I noticed your vehicle qualifies for a premium exchange bonus of up to 50,000 rupees. Would you like to know more?"
        elif campaign_type == "emi_benefit":
            return f"Hello {salutation}, I'm Supriya from Alcon. I'm calling to share some exciting new EMI schemes that could significantly reduce your monthly payments on a new Hyundai. Since you've had your {car} for{age_duration} now, I thought you might be interested in these benefits. Is this a good time to talk?"
        else:
            return f"Hello {salutation}, I'm Supriya from Alcon. I'm calling regarding your {car}. I have some exciting updates to share with you. Is this a good time to talk?"

    @staticmethod
    def handle_identity_intent(user_input_lower: str) -> str:
        """Categorize identity verification intent into YES, BUSY, WRONG_NUMBER, or UNKNOWN."""
        import re
        
        # 1. Busy / Call Later
        if any(word in user_input_lower for word in ['busy', 'meeting', 'later', 'call back', 'driving', 'not now']):
            return "BUSY"
            
        # 2. Wrong Number / Not Me
        wrong_phrases = ['wrong number', 'rong number', 'wrong person', 'rong person', 'not me', 'not speaking', 'incorrect number', 'not him', 'not her', 'galat number', 'wrong no', 'rong no']
        if any(phrase in user_input_lower for phrase in wrong_phrases):
            return "WRONG_NUMBER"
            
        # 3. Positive / Speaking
        positive = ['yes', 'yeah', 'sure', 'yep', 'speaking', 'correct', 'it is me', 'this is']
        if any(re.search(rf'\b{word}\b', user_input_lower) for word in positive):
            return "YES"
            
        # 4. Explicit No (without 'later' or 'wrong')
        if re.search(r'\bno\b|\bnope\b', user_input_lower):
            return "NO"
            
        return "UNKNOWN"

    @staticmethod
    def handle_consent(user_input_lower: str) -> bool:
        """Requirement 3A: Detect permission to proceed with the sales pitch."""
        import re
        
        # 1. Leverage identity intent for baseline YES
        intent = IntroFlow.handle_identity_intent(user_input_lower)
        if intent == "YES":
            return True
            
        # 2. Explicit Positive/Consent variations
        positive_extras = ['ok', 'okay', 'fine', 'proceed', 'go ahead', 'talk', 'sharing', 'share']
        if any(re.search(rf'\b{word}\b', user_input_lower) for word in positive_extras):
            return True
            
        # 3. Implicit interest signals (Queries that imply consent to talk)
        interest_keywords = ['tell me', 'know more', 'what is it', 'which scheme', 'benefit', 'price', 'offer', 'scheme', 'details']
        if any(word in user_input_lower for word in interest_keywords):
            return True
            
        return False
