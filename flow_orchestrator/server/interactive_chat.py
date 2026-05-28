import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def interactive_chat():
    print("\n" + "="*50)
    print("💬 ALCON ORCHESTRATOR - LIVE CHAT SIMULATOR")
    print("="*50)

    # 1. Select Flow
    print("\nSelect Flow to Simulate:")
    templates = requests.get(f"{BASE_URL}/templates").json()
    drafts_list = requests.get(f"{BASE_URL}/flows").json()
    
    # Merge for selection
    available_flows = []
    for d in drafts_list:
        available_flows.append({"id": d['flow_id'], "name": f"[DRAFT] {d['name']} ({d['flow_id']})"})
    for t in templates:
        available_flows.append({"id": t['id'], "name": f"[TEMPLATE] {t['name']} ({t['id']})"})
        
    for i, f in enumerate(available_flows):
        print(f"[{i+1}] {f['name']}")
    
    flow_choice = input(f"\nSelect flow (1-{len(available_flows)}, default 1): ") or "1"
    selected_flow = available_flows[int(flow_choice)-1]
    flow_id = selected_flow['id']

    if "[TEMPLATE]" in selected_flow['name']:
        print(f"📄 Creating session draft from {flow_id}...")
        draft_resp = requests.post(f"{BASE_URL}/flows/from-template/{flow_id}").json()
        flow_id = draft_resp['flow_id']

    # 2. Select Customer (Dynamic fetch from backend data)
    print("\nSelect Customer to simulate Outbound Call:")
    try:
        # Resolve path relative to this script
        import os
        base_path = os.path.dirname(os.path.abspath(__file__))
        customers_path = os.path.join(base_path, "..", "..", "backend", "data", "customers.json")
        with open(customers_path, 'r') as f:
            all_customers = json.load(f)
            # Pick first few for simulation list
            customers = [{"name": c['name'], "phone": c['phone']} for c in all_customers[:7]]
    except Exception as e:
        print(f"⚠️ Could not load dynamic customers, using defaults. Error: {e}")
        customers = [
            {"name": "Sanjana", "phone": "+919881012767"},
            {"name": "Kavita", "phone": "+919881012768"},
            {"name": "Unknown Caller", "phone": "+910000000000"}
        ]
    for i, c in enumerate(customers):
        print(f"[{i+1}] {c['name']} ({c['phone']})")
    
    c_choice = input("\nSelect customer (default 1): ") or "1"
    selected_customer = customers[int(c_choice)-1]
    from_phone = selected_customer['phone']

    print(f"\n🚀 Starting session for {flow_id} to {selected_customer['name']}...")
    try:
        # Pass the 'from' phone number to initialize context
        session = requests.post(f"{BASE_URL}/sessions/start/{flow_id}?from_phone={from_phone}").json()
        session_id = session['session_id']
    except Exception as e:
        print(f"❌ Failed to start session: {e}")
        return

    # 3. Chat Loop
    first_turn = True
    while True:
        # Print AI responses FIRST
        for resp in session.get('responses', []):
            if "Spoke:" in resp:
                # Clean up the message for the UI
                clean_msg = resp.replace('Spoke: ', '').split('[SYSTEM]')[0].strip()
                print(f"\n🤖 AI: {clean_msg}")
            
            if "[SYSTEM]" in resp or "TRANSFER" in resp:
                sys_msg = resp[resp.find('[SYSTEM]'):] if '[SYSTEM]' in resp else resp
                print(f"\n📞 {sys_msg}")

        
        if session.get('status') == "COMPLETED":
            print("\n🏁 Conversation Ended.")
            break

        # Get User Input
        user_input = input("\n👤 YOU: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            break

        # Send to Orchestrator
        session = requests.post(
            f"{BASE_URL}/sessions/{session_id}/message",
            json={"text": user_input}
        ).json()

if __name__ == "__main__":
    interactive_chat()
