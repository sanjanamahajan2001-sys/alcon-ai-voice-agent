class ServiceBridgeFlow:
    @staticmethod
    def get_bridge_prompt(salutation: str, car_model: str) -> str:
        """Requirement 3F: Pivot to service if sales interest is low."""
        return (f"I understand {salutation}. By the way, I noticed your {car_model} is due for its periodic service. "
                "Since we are already speaking, would you like me to book a maintenance appointment for you instead?")

    @staticmethod
    def handle_bridge_response(user_input_lower: str) -> bool:
        return any(word in user_input_lower for word in ['yes', 'yeah', 'sure', 'ok', 'book', 'service'])
