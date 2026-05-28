import json
from flow_manager import FlowManager

def run_stress_test():
    fm = FlowManager()
    session_id = "test_user_123"
    
    # Define a sequence of realistic, random, and complex user queries
    test_scenarios = [
        ("I want to buy a new car", "Greeting/Intro"),
        ("What models are available right now?", "General Model List"),
        ("Tell me more about the Creta", "Specific Model Summary"),
        ("What features does it have?", "Pronoun + Features"),
        ("How much do I have to shell out for it?", "Fuzzy Price Query"),
        ("Is the Venue cheaper than this?", "Comparison + Budget"),
        ("What emi options available for the Venue?", "Specific EMI"),
        ("and how many colors can I choose from?", "Pronoun + Category"),
        ("can you tell me where you are located?", "General FAQ (Location)"),
        ("I also need to book a service for my other car", "Intent Switch (Booking)"),
        ("1234", "Registration Lookup"),
        ("Creta", "Disambiguation"),
        ("Wait, actually tell me about Verna's mileage first", "Sudden Context Switch"),
        ("Okay, what is its price?", "Pronoun + Price"),
        ("Can I get a test drive for that?", "Lead Intent")
    ]

    print("\n" + "="*50)
    print("🚀 ALCON AI AGENT: REAL-WORLD STRESS TEST")
    print("="*50 + "\n")

    current_model = None

    for user_input, label in test_scenarios:
        print(f"👤 USER ({label}): {user_input}")
        
        # Simulate the FlowManager processing (Web channel logic)
        action = fm.get_next_action(session_id, user_input, channel="web")
        
        # Extract model context for internal tracking if available
        if "model" in action:
            current_model = action["model"]

        print(f"🤖 SUPRIYA: {action['text']}")
        print(f"📍 STATE: {action['ui_state']} | NEXT: {action['next_step']}")
        print("-" * 50)

if __name__ == "__main__":
    run_stress_test()
