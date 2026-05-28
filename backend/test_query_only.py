from flow_manager import FlowManager

def test_queries():
    fm = FlowManager()
    session_id = "query_tester"
    
    # Sequence of queries to test context and category coverage
    queries = [
        "Tell me about the Venue",
        "What is its mileage?",
        "how many colors can I choose from?",
        "and what is the lowest price for it?",
        "is there any EMI option available?",
        "Actually, what about the Verna?",
        "show me its features",
        "is it budget friendly?",
        "compare it with the Creta",
        "where is your showroom?",
        "can I get a test drive for the Creta?"
    ]

    print("\n" + "="*50)
    print("🔍 ALCON AI: FOCUSED QUERY HANDLING TEST")
    print("="*50 + "\n")

    for q in queries:
        print(f"👤 USER: {q}")
        action = fm.get_next_action(session_id, q, channel="web")
        print(f"🤖 SUPRIYA: {action['text']}")
        print("-" * 50)

if __name__ == "__main__":
    test_queries()
