import requests
import uuid
import time

# Configuration
BASE_URL = "http://localhost:8000"

def get_session_id():
    return f"web-test-{uuid.uuid4().hex[:6]}"

def chat(session_id, message, scenario_name=""):
    if scenario_name:
        print(f"\n--- SCENARIO: {scenario_name} ---")
    print(f"[YOU]: {message}")
    payload = {"session_id": session_id, "message": message}
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"[AI]: {data['text']}")
            print(f"DEBUG: Next Step: {data.get('next_step')} | UI State: {data.get('ui_state')}")
            return data
        else:
            print(f"ERROR: {response.status_code}")
            return None
    except Exception as e:
        print(f"FAILED TO CONNECT: {e}")
        return None

def test_gibberish_and_fallback():
    sid = get_session_id()
    chat(sid, "Hello", "Gibberish & Fallback")
    chat(sid, "I want to book a service")
    chat(sid, "my car number is xyzabc123") # Should be rejected by new regex (all letters/digits mix but no pattern)
    chat(sid, "asdkjhadskjh") # Pure gibberish
    chat(sid, "still random text") # 3rd fail -> Transfer

def test_spam_control():
    sid = get_session_id()
    chat(sid, "Book service", "Spam Control")
    chat(sid, "Repeat this")
    chat(sid, "Repeat this")
    chat(sid, "Repeat this") # 3rd identical -> Transfer

def test_global_exit():
    sid = get_session_id()
    chat(sid, "Hello", "Global Exit")
    chat(sid, "I want to buy a new car")
    chat(sid, "Actually, nevermind") # Exit intent
    chat(sid, "Are you there?") # Should be back at start or end state

def test_intent_switching():
    sid = get_session_id()
    chat(sid, "I want to book a service", "Intent Switching")
    chat(sid, "Wait, what's the price of the Creta?") # Switch to sales
    chat(sid, "And the Venue?") # Stay in sales
    chat(sid, "Okay, back to service") # Switch back to service

def test_typo_tolerance():
    sid = get_session_id()
    chat(sid, "Hello", "Typo Tolerance")
    chat(sid, "tell me about the venuw") # Typo in Venue
    chat(sid, "how much for creeta") # Typo in Creta

def test_single_field_entry():
    sid = get_session_id()
    chat(sid, "Book a service", "Single Field Entry")
    chat(sid, "mh15ab1234") # Should be accepted and ask for phone
    chat(sid, "9881012767") # Should then authenticate
    
def test_stress_scenarios():
    sid = get_session_id()
    print("\n--- SCENARIO: Stress Test (Sales Loop & State Leak) ---")
    chat(sid, "Book a service")
    chat(sid, "mh15ab1234") # Enter reg no
    chat(sid, "actually track my service") # Switch flow
    # Should NOT say "Got it MH15AB1234" because params should be cleared
    chat(sid, "9881012767") 
    
    chat(sid, "tell me about creeta") # Typo Creta
    chat(sid, "hello") # 1st spam
    chat(sid, "hello") # 2nd spam
    chat(sid, "hello") # 3rd spam -> Transfer

if __name__ == "__main__":
    print("Starting Strong Scenario Testing...")
    test_gibberish_and_fallback()
    test_spam_control()
    test_global_exit()
    test_intent_switching()
    test_typo_tolerance()
    test_single_field_entry()
    test_stress_scenarios()
