import requests
import json
import time

BASE_URL = "http://localhost:8000"

def run_test():
    print("🚀 Starting Feedback Flow Integration Test...")
    
    # 1. Create a draft from the template first (Plug & Play requirement)
    template_id = "post_service_feedback"
    print(f"📄 Creating draft from template: {template_id}")
    
    try:
        draft_resp = requests.post(f"{BASE_URL}/flows/from-template/{template_id}").json()
        flow_id = draft_resp['flow_id']
        print(f"✨ Draft created: {flow_id}")
    except Exception as e:
        print(f"❌ Failed to create draft: {e}")
        return

    # 2. Start session with the new draft
    customer_phone = "+919881012767" # Sanjana
    session = requests.post(f"{BASE_URL}/sessions/start/{flow_id}?from_phone={customer_phone}").json()
    
    if 'session_id' not in session:
        print(f"❌ Failed to start session: {session}")
        return
        
    session_id = session['session_id']
    print(f"✅ Session started: {session_id}")
    
    # Print first AI response (Greeting)
    for r in session.get('responses', []):
        if "Spoke:" in r:
            print(f"🤖 AI: {r.replace('Spoke: ', '')}")

    # 3. Simulate conversation steps (Numeric Threshold Test)
    steps = [
        ("yes speaking", "Identity check"),
        ("yes it was good", "Satisfaction check"),
        ("i give it an 8", "Advisor rating (threshold check)"),
        ("advisor was a bit too fast", "Reason for low advisor rating"),
        ("10", "Pickup rating (above threshold)"),
        ("i would say 7", "Cleanliness rating (threshold check)"),
        ("car was still dusty inside", "Reason for low cleanliness rating"),
        ("overall i give 9", "Overall rating (above threshold)"),
        ("yes i want pick and drop", "Pick & Drop Service Offer"),
        ("no final suggestions", "Suggestions"),
    ]

    for msg, label in steps:
        print(f"\n👤 USER ({label}): {msg}")
        resp = requests.post(f"{BASE_URL}/sessions/{session_id}/message", json={"text": msg}).json()
        for r in resp.get('responses', []):
            if "Spoke:" in r:
                print(f"🤖 AI: {r.replace('Spoke: ', '')}")
        
    # 4. Verify final data in session record
    print("\n📊 Verifying Captured Data...")
    final_session = requests.get(f"{BASE_URL}/sessions/{session_id}").json()
    variables = final_session.get('variables', {})
    
    expected_vars = {
        "advisor_rating": 8,
        "pickup_rating": 10,
        "cleanliness_rating": 7,
        "overall_rating": 9,
        "satisfaction_check": True
    }

    success = True
    for var, expected in expected_vars.items():
        actual = variables.get(var)
        if actual == expected:
            print(f"✅ {var}: {actual} (Match)")
        else:
            print(f"❌ {var}: Expected {expected}, got {actual}")
            success = False
            
    if success:
        print("\n✨ FEEDBACK FLOW TEST PASSED!")
    else:
        print("\n🛑 FEEDBACK FLOW TEST FAILED!")

if __name__ == "__main__":
    run_test()
