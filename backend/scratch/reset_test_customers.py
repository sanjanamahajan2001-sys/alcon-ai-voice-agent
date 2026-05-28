import json
import os

CUSTOMERS_JSON_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/customers.json"))

print(f"🔄 Resetting test customers in: {CUSTOMERS_JSON_PATH}")

try:
    with open(CUSTOMERS_JSON_PATH, "r") as f:
        customers = json.load(f)
        
    reset_count = 0
    for c in customers:
        c_id = str(c["id"])
        
        # Reset Sanjana (ID 1)
        if c_id == "1":
            c["last_service_date"] = "2025-11-15"
            c["service_due_date"] = "2026-05-15"
            c["service_status"] = "idle"
            c["notes"] = ""
            reset_count += 1
            print("👉 Reset Sanjana (ID 1) to eligible state")
            
        # Reset Aarav Mehta (ID 10)
        elif c_id == "10":
            c["last_service_date"] = "2025-11-15"
            c["service_due_date"] = "2025-09-20"
            c["service_status"] = "idle"
            c["notes"] = "general checkup"
            c["campaign_status"] = "synced"
            reset_count += 1
            print("👉 Reset Aarav Mehta (ID 10) to eligible state")
            
        # Reset Rohan Deshmukh (ID 14)
        elif c_id == "14":
            c["last_service_date"] = "2025-11-15"
            c["service_status"] = "idle"
            c["notes"] = ""
            c["campaign_status"] = "synced"
            reset_count += 1
            print("👉 Reset Rohan Deshmukh (ID 14) to eligible state")
            
        # Reset Sanya Malhotra (ID 17)
        elif c_id == "17":
            c["last_service_date"] = "2025-11-15"
            c["service_status"] = "idle"
            c["notes"] = ""
            c["campaign_status"] = "synced"
            reset_count += 1
            print("👉 Reset Sanya Malhotra (ID 17) to eligible state")
            
    with open(CUSTOMERS_JSON_PATH, "w") as f:
        json.dump(customers, f, indent=4)
        
    print(f"✅ Successfully reset {reset_count} test customers in customers.json.\n")
except Exception as e:
    print(f"❌ Failed to reset database: {e}\n")
