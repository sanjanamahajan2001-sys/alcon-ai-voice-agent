import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_flow(template_id, phone, steps, expected_vars):
    print(f"\n🚀 Testing Flow: {template_id}...")
    
    # 1. Create a draft from the template
    try:
        draft_resp = requests.post(f"{BASE_URL}/flows/from-template/{template_id}").json()
        flow_id = draft_resp['flow_id']
        print(f"✨ Draft created: {flow_id}")
    except Exception as e:
        print(f"❌ Failed to create draft: {e}")
        return False

    # 2. Start session
    session = requests.post(f"{BASE_URL}/sessions/start/{flow_id}?from_phone={phone}").json()
    if 'session_id' not in session:
        print(f"❌ Failed to start session: {session}")
        return False
        
    session_id = session['session_id']
    
    # Process greeting
    for r in session.get('responses', []):
        if "Spoke:" in r:
            print(f"🤖 AI: {r.replace('Spoke: ', '')}")

    # 3. Conversation
    for msg, label in steps:
        print(f"👤 USER ({label}): {msg}")
        resp = requests.post(f"{BASE_URL}/sessions/{session_id}/message", json={"text": msg}).json()
        for r in resp.get('responses', []):
            if "Spoke:" in r:
                print(f"🤖 AI: {r.replace('Spoke: ', '')}")

    # 4. Verification
    print("📊 Verifying Captured Data...")
    final_session = requests.get(f"{BASE_URL}/sessions/{session_id}").json()
    variables = final_session.get('variables', {})
    
    success = True
    for var, expected in expected_vars.items():
        actual = variables.get(var)
        if str(actual) == str(expected):
            print(f"  ✅ {var}: {actual} (Match)")
        else:
            print(f"  ❌ {var}: Expected {expected}, got {actual}")
            success = False
    return success

def run_tests():
    phone = "+919881012767" # Sanjana (ID 1)
    
    # 1. Pickup Flow Test
    pickup_steps = [
        ("yes speaking", "Identity check"),
        ("tomorrow morning", "Slot capture")
    ]
    pickup_expected = {
        "id": "1",
        "name": "Sanjana",
        "confirmed_date": "Tuesday, May 12 at 10:00 AM" # tomorrow morning from May 11
    }

    
    # 2. Workshop Update Test
    workshop_steps = [
        ("yes speaking", "Identity check"),
        ("no additional concerns", "Concerns ack"),
        ("why is it expensive?", "Price objection"),
        ("yes proceed", "Proceed confirmation")
    ]
    workshop_expected = {
        "estimated_cost": "₹4,500",
        "reported_concerns": "Brake squealing and minor AC cooling issue"
    }

    # 3. Ready / Delivery Test
    ready_steps = [
        ("yes speaking", "Identity check"),
        ("please drop it back to my home", "Delivery choice")
    ]
    ready_expected = {
        "service_summary": "Front brake pads replaced, AC gas topped up, and general service completed."
    }

    results = []
    results.append(test_flow("pd_pickup_coordination", phone, pickup_steps, pickup_expected))
    results.append(test_flow("pd_workshop_update", phone, workshop_steps, workshop_expected))
    results.append(test_flow("pd_ready_delivery", phone, ready_steps, ready_expected))

    print("\n" + "="*30)
    if all(results):
        print("✨ ALL P&D FLOW TESTS PASSED!")
    else:
        print("🛑 SOME P&D FLOW TESTS FAILED!")
    print("="*30)

if __name__ == "__main__":
    run_tests()
