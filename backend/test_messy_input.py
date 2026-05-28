from flow_manager import FlowManager

def test_messy_inputs():
    fm = FlowManager()
    session_id = "messy_tester"
    
    # Broken English, Typos, and Mixed Formats
    queries = [
        "creta price how much?",              # Broken English
        "venuu emi detail pls",               # Typo + Slang
        "any offer for varna?",               # Typo
        "want drive creeta tomorow",          # Broken English + Typo + Intent
        "showroom where?",                    # Keyword only
        "how much shell out for it?",         # Slang + Pronoun
        "mileage of it",                      # Short query
        "i want service my car 1234",         # Mixed Intent and Data
        "track my service 1234",              # Real-world status check
        "ok talk to person"                   # Transfer intent
    ]

    print("\n" + "="*50)
    print("🤪 ALCON AI: MESSY INPUT STRESS TEST")
    print("="*50 + "\n")

    for q in queries:
        print(f"👤 USER: {q}")
        action = fm.get_next_action(session_id, q, channel="web")
        print(f"🤖 SUPRIYA: {action['text']}")
        print("-" * 50)

if __name__ == "__main__":
    test_messy_inputs()
