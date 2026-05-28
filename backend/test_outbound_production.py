import requests
import json
import time
import sqlite3
from datetime import datetime

BASE_URL = "http://localhost:8000"
DB_PATH = "data/alcon.db"

def get_db_state():
    """Poll the SQLite database for the current state of all calls."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.call_sid, c.customer_id, c.status, c.retry_count, l.interest_level, l.reasoning_trace
            FROM calls c
            LEFT JOIN lead_states l ON c.call_sid = l.call_sid
            ORDER BY c.created_at DESC
        ''')
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return []

def run_production_demo():
    print("\n" + "="*60)
    print("ALCON PRODUCTION-GRADE OUTBOUND SIMULATOR")
    print("="*60)

    # 1. Trigger a Campaign
    print("\n[1] INITIATING UPGRADE CAMPAIGN...")
    campaign_data = {
        "campaign_id": f"DEMO_{int(time.time())}",
        "customer_ids": ["1", "2"] # Sanjana and Anika
    }
    
    try:
        response = requests.post(f"{BASE_URL}/dms/campaign/start", json=campaign_data)
        if response.status_code == 200:
            print(f"SUCCESS: Campaign {campaign_data['campaign_id']} queued.")
        else:
            print(f"ERROR: Failed to start campaign: {response.text}")
            return
    except Exception as e:
        print(f"CONNECTION ERROR: Is main.py running? ({str(e)})")
        return

    # 2. Monitor Lifecycle
    print("\n[2] MONITORING CALL LIFECYCLE & AI INTELLIGENCE...")
    print(f"{'CALL_SID':<15} | {'CUSTOMER':<10} | {'STATUS':<10} | {'INTEREST':<10}")
    print("-" * 60)

    # Simulate 15 seconds of monitoring
    for _ in range(15):
        states = get_db_state()
        for s in states:
            sid_short = s['call_sid'][:12] + ".."
            print(f"{sid_short:<15} | {s['customer_id']:<10} | {s['status']:<10} | {s['interest_level'] or 'None':<10}")
            
            # If we have a reasoning trace, show it once
            if s['reasoning_trace']:
                trace = json.loads(s['reasoning_trace'])
                print(f"   ↳ [AI REASONING]: Decision={trace['decision']}, Matches={trace['matched_hot']}")
        
        time.sleep(3)
        print("." * 60)

    # 3. Simulate a Webhook Callback (State Machine Test)
    print("\n[3] TESTING STATE MACHINE (SIMULATING ANSWERED CALL)...")
    if states:
        test_sid = states[0]['call_sid']
        webhook_data = {
            "CallSid": test_sid,
            "CallStatus": "answered",
            "CallDuration": "0"
        }
        requests.post(f"{BASE_URL}/status-callback", data=webhook_data)
        print(f"Callback sent for {test_sid}. Status should now be 'answered'.")
        
        # Check again
        time.sleep(1)
        updated = get_db_state()
        for u in updated:
            if u['call_sid'] == test_sid:
                print(f"VERIFIED: {test_sid} status is now {u['status']}")

    print("\n" + "="*60)
    print("DEMO COMPLETE: Check data/alcon.db for full audit trail.")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_production_demo()
