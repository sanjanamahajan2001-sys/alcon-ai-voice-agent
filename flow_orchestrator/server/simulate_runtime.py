import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def test_runtime():
    print("\n" + "="*50)
    print("🚀 ALCON ORCHESTRATOR - RUNTIME TESTER")
    print("="*50)

    # 1. List Templates
    try:
        templates = requests.get(f"{BASE_URL}/templates").json()
    except:
        print("❌ Error: Backend not running at localhost:8000")
        return

    print("\nAvailable Templates:")
    for i, t in enumerate(templates):
        print(f"[{i+1}] {t['name']} ({t['id']})")
    
    choice = input("\nSelect template to clone & test (default 1): ") or "1"
    template_id = templates[int(choice)-1]['id']

    # 2. Clone to Draft
    print(f"\n⚡ Cloning '{template_id}' to editable operational draft...")
    draft = requests.post(f"{BASE_URL}/flows/from-template/{template_id}").json()
    draft_id = draft['flow_id']
    print(f"✅ Created Draft: {draft_id}")

    # 3. Run Simulation
    print(f"\n🎬 Starting Real-time Playback Simulation for {draft_id}...")
    print("-" * 50)
    
    response = requests.post(f"{BASE_URL}/flows/{draft_id}/simulate")
    if response.status_code != 200:
        print(f"❌ Simulation failed: {response.text}")
        return

    steps = response.json().get("execution_steps", [])
    
    for i, step in enumerate(steps):
        status_icon = "✅" if step['status'] == "SUCCESS" else "❌"
        print(f"[{i+1}] {status_icon} Node: {step['node_id']}")
        print(f"    Logs: {step['logs']}")
        time.sleep(0.8) # Simulate real-time delay

    print("-" * 50)
    print("🏁 Simulation Complete!")
    print("="*50 + "\n")

if __name__ == "__main__":
    test_runtime()
