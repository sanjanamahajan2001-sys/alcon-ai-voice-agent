from flow_manager import FlowManager

def test_expert():
    fm = FlowManager()
    session_id = "expert_tester"
    
    # High-difficulty scenarios
    queries = [
        "does the creta have a sunroof?",       # Specific feature check
        "do you sell toyota cars?",             # Out of scope (Competitor)
        "I want a Verna but first book my Creta service", # Multi-intent Switch
        "1234",                                 # Registration for booking
        "Creta",                                # Disambiguation
        "Actually I meant the Venue price",     # Correction / Context change
        "compare it with Verna",                # Comparison from new context
        "track my service 1234",                # Direct Tracking jump
        "talk to person"                        # Transfer during tracking
    ]

    print("\n" + "="*50)
    print("🏆 ALCON AI: EXPERT SCENARIO TEST")
    print("="*50 + "\n")

    for q in queries:
        print(f"👤 USER: {q}")
        action = fm.get_next_action(session_id, q, channel="web")
        print(f"🤖 SUPRIYA: {action['text']}")
        print("-" * 50)

if __name__ == "__main__":
    test_expert()
