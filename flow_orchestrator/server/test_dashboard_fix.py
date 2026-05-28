import requests
import json

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("🔍 Testing Dashboard Endpoints...")
    
    endpoints = [
        "/telephony/dashboard/kpis",
        "/telephony/dashboard/leads",
        "/telephony/history"
    ]
    
    for ep in endpoints:
        print(f"\n📡 GET {ep}")
        try:
            resp = requests.get(f"{BASE_URL}{ep}")
            if resp.status_code == 200:
                print(f"✅ Success! (200 OK)")
                data = resp.json()
                if isinstance(data, list):
                    print(f"   Count: {len(data)}")
                else:
                    print(f"   Keys: {list(data.keys())}")
            else:
                print(f"❌ Failed! Status: {resp.status_code}")
                print(f"   Error: {resp.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_endpoints()
