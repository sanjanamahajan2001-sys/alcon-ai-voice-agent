import sys
import os

# Add the current directory to path so we can import FlowManager
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flow_manager import FlowManager

def test_kb():
    fm = FlowManager()
    
    test_queries = [
        "What is the price of Creta?",
        "What features does the Verna have?",
        "How much mileage does the Venue give?",
        "Give me a comparison between Venue and Creta",
        "Which one is best if my budget is low?",
        "Tell me about EMI options",
        "Can I get a test drive?",
        "Where is your dealership located?",
        "Which cars do you have?"
    ]
    
    print("--- Alcon KB Lookup Test ---")
    for query in test_queries:
        print(f"\nUser: {query}")
        answer = fm.handle_query(query)
        print(f"AI: {answer if answer else 'No answer found'}")

if __name__ == "__main__":
    test_kb()
