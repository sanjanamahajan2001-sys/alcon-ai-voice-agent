class FallbackHandler:
    @staticmethod
    def handle_fallback(fallback_count: int, department: str = "Service") -> str:
        """Requirement: Safe Fallbacks - 3rd strike rule."""
        if fallback_count >= 3:
            return f"I'm having trouble following. Let me connect you to our {department} team for better assistance. Please stay on the line."
        
        prompts = [
            "I'm sorry, I didn't quite catch that. Could you please repeat it?",
            "I'm having a little trouble understanding. Could you please say that again?",
            "Apologies, I missed that. One more time please?"
        ]
        return prompts[min(fallback_count - 1, len(prompts) - 1)]
