import os
import json
from dotenv import load_dotenv
import psycopg2

# Paths
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
customers_json_path = os.path.join(base_dir, "data", "customers.json")
dotenv_path = os.path.join(base_dir, ".env")

load_dotenv(dotenv_path)

print("--- STEP 1: Updating customers.json ---")
try:
    with open(customers_json_path, "r", encoding="utf-8") as f:
        customers = json.load(f)
        
    updated_count = 0
    for c in customers:
        c_id = str(c["id"])
        
        # 1. Sanjana (ID 1)
        if c_id == "1":
            c["dnd_status"] = False
            # Re-assert correct insurance fields
            c["insurance_expiry_date"] = "2026-06-03"
            c["insurance_provider"] = "HDFC Ergo"
            c["policy_number"] = "POL-123456"
            c["current_premium"] = "₹12,500"
            c["loyalty_premium"] = "₹11,800"
            c["policy_status"] = "PENDING"
            updated_count += 1
            print("👉 Updated Sanjana (ID 1): set DND to false, verified insurance fields.")
            
        # 2. Rohan Deshmukh (ID 14)
        elif c_id == "14":
            c["dnd_status"] = False
            c["insurance_expiry_date"] = "2026-06-03"
            c["insurance_provider"] = "Tata AIG"
            c["policy_number"] = "POL-ROHAN14"
            c["current_premium"] = "₹15,400"
            c["loyalty_premium"] = "₹14,200"
            c["policy_status"] = "PENDING"
            # Clear old service redirect/outcome if needed
            c["campaign_last_outcome"] = None
            c["notes"] = ""
            updated_count += 1
            print("👉 Updated Rohan Deshmukh (ID 14): set DND to false, added Tata AIG insurance fields.")
            
        # 3. Sanya Malhotra (ID 17)
        elif c_id == "17":
            c["dnd_status"] = False
            c["insurance_expiry_date"] = "2026-06-03"
            c["insurance_provider"] = "ICICI Lombard"
            c["policy_number"] = "POL-SANYA17"
            c["current_premium"] = "₹9,800"
            c["loyalty_premium"] = "₹9,100"
            c["policy_status"] = "PENDING"
            # Clear old outcome
            c["campaign_last_outcome"] = None
            c["notes"] = ""
            updated_count += 1
            print("👉 Updated Sanya Malhotra (ID 17): set DND to false, added ICICI Lombard insurance fields.")

    with open(customers_json_path, "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=4)
        
    print(f"✅ Successfully updated {updated_count} customer records in customers.json.\n")
except Exception as e:
    print(f"❌ Error updating customers.json: {e}\n")


print("--- STEP 2: Updating PostgreSQL Database ---")
try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT")
    )
    cursor = conn.cursor()
    
    # Let's check for any DND status in calls or lead_states for these customers
    # ID list: 1, 14, 17
    # Reset lead_states for these customers' call_sids
    cursor.execute("""
        SELECT ls.call_sid FROM lead_states ls
        JOIN calls c ON ls.call_sid = c.call_sid
        WHERE c.customer_id IN ('1', '14', '17');
    """)
    rows = cursor.fetchall()
    call_sids = [row[0] for row in rows]
    
    if call_sids:
        print(f"Found active lead states in DB for call SIDs: {call_sids}")
        # Update lead statuses to make them fresh or set them to a non-DND state
        # We can set disposition to NULL and lead_status to NULL or COLD/WARM
        placeholders = ', '.join(['%s'] * len(call_sids))
        cursor.execute(f"""
            UPDATE lead_states 
            SET lead_status = NULL, disposition = NULL, policy_status = 'PENDING'
            WHERE call_sid IN ({placeholders});
        """, call_sids)
        print(f"Reset {cursor.rowcount} lead states in DB.")
        
        # Also let's update status in calls table
        cursor.execute(f"""
            UPDATE calls 
            SET status = 'initiated', retry_count = 0
            WHERE call_sid IN ({placeholders});
        """, call_sids)
        print(f"Reset {cursor.rowcount} calls in DB.")
    else:
        print("No active call/lead state records in DB to reset.")

    # Let's delete any campaign queue records for these customers to let them re-trigger cleanly
    cursor.execute("DELETE FROM campaign_queue WHERE customer_id IN ('1', '14', '17');")
    print(f"Removed {cursor.rowcount} campaign queue records for target customers.")

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Successfully updated PostgreSQL database records.\n")
except Exception as e:
    print(f"❌ Error updating PostgreSQL database: {e}\n")
