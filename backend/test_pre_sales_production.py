import os
import json
import time
import requests
import sqlite3
from simulate_v2 import simulate_call
from datetime import datetime

BASE_URL = "http://localhost:8000"
DB_PATH = "data/alcon.db"

def run_interactive_pre_sales_suite():
    print("\n" + "="*70)
    print("ALCON PRE-SALES: PRODUCTION READINESS TEST SUITE")
    print("="*70)
    
    # --- STEP 1: SCANNING ---
    print("\n[STEP 1] SCANNING & CATEGORIZATION")
    print("-" * 70)
    
    with open("data/customers.json", "r") as f:
        customers = json.load(f)
    
    today = datetime.now()
    targets = []
    
    print(f"{'NAME':<12} | {'CAR':<15} | {'AGE':<4} | {'CAMPAIGN':<15} | {'STATUS'}")
    print("-" * 70)
    
    for c in customers:
        if "Hyundai" not in c.get("car_model", ""): continue
        
        reg_date_str = c.get("registration_date")
        if not reg_date_str: continue
        
        reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
        age = (today.year - reg_date.year) - ((today.month, today.day) < (reg_date.month, reg_date.day))
        
        if age >= 5: campaign = "exchange"
        elif age >= 3: campaign = "upgrade"
        else: campaign = "emi_benefit"
        
        targets.append({"id": c['id'], "name": c['name'], "phone": c['phone'], "age": age, "campaign": campaign, "car": c['car_model']})
        print(f"{c['name']:<12} | {c['car_model']:<15} | {age:<4} | {campaign:<15} | TARGETED")

    print("-" * 70)
    print(f"Total Targets Identified: {len(targets)}")
    
    # --- STEP 2: INTERACTIVE CALLS ---
    print("\n[STEP 2] LIVE INTERACTIVE OUTBOUND QUEUE")
    print("Starting automated outbound queue. You will now talk to the AI for each lead.")
    
    for t in targets:
        print(f"\n>>> NEXT IN QUEUE: {t['name']} ({t['phone']})")
        print(f">>> CONTEXT: {t['age']}y {t['car']} - Campaign: {t['campaign'].upper()}")
        
        choice = input(f"Start live interactive call with {t['name']}? (y/skip/quit): ").lower()
        if choice == 'q' or choice == 'quit':
            break
        if choice == 's' or choice == 'skip':
            continue
            
        # Trigger full interactive simulation from simulate_v2
        simulate_call(
            from_phone=t['phone'],
            customer_id=t['id'],
            flow_type="pre_sales",
            campaign_type=t['campaign'],
            vehicle_age=t['age']
        )
        
        print(f"\n[POST-CALL] Call with {t['name']} completed.")
        
        # Verify Follow-up if any
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT scheduled_time FROM scheduled_followups WHERE customer_id = ? ORDER BY id DESC LIMIT 1", (t['id'],))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            print(f"[SYSTEM] Detected a scheduled follow-up for this customer at: {row[0]}")

    print("\n" + "="*70)
    print("PRODUCTION TEST SUITE FINISHED")
    print("="*70)

if __name__ == "__main__":
    run_interactive_pre_sales_suite()
