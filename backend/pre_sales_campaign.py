import json
import os
from datetime import datetime
from flow_manager import FlowManager
from simulate_v2 import simulate_call

def calculate_vehicle_age(reg_date_str):
    reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
    today = datetime.now()
    age = (today.year - reg_date.year) - ((today.month, today.day) < (reg_date.month, reg_date.day))
    return age

def run_pre_sales_scan():
    fm = FlowManager()
    
    print("\n" + "="*60)
    print("ALCON PRE-SALES LEAD SCANNER - OUTBOUND CAMPAIGN ENGINE")
    print("="*60)
    print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    print("-"*60)
    
    customers_file = "data/customers.json"
    if not os.path.exists(customers_file):
        print(f"Error: {customers_file} not found.")
        return

    with open(customers_file, "r") as f:
        customers = json.load(f)
        
    pre_sales_targets = []
    
    print(f"{'NAME':<12} | {'CAR':<15} | {'AGE':<4} | {'CAMPAIGN':<15} | {'STATUS'}")
    print("-"*60)
    
    for c in customers:
        car = c.get("car_model", "")
        reg_date = c.get("registration_date")
        
        # Requirement: Must be a Hyundai owner
        if "Hyundai" not in car:
            status = "SKIP (NOT HYUNDAI)"
            campaign = "N/A"
            age = "N/A"
        elif not reg_date:
            status = "SKIP (NO REG DATE)"
            campaign = "N/A"
            age = "N/A"
        else:
            age = calculate_vehicle_age(reg_date)
            
            # Categorization logic
            if age >= 5:
                campaign = "exchange"
            elif age >= 3:
                campaign = "upgrade"
            else:
                campaign = "emi_benefit"
                
            status = "TARGETED"
            if c.get("dnd_status", False):
                status = "DND (SKIP)"
            else:
                pre_sales_targets.append((c, campaign, age))
        
        age_str = str(age) if age != "N/A" else "N/A"
        print(f"{c['name']:<12} | {car:<15} | {age_str:<4} | {campaign:<15} | {status}")
            
    print("-"*60)
    print(f"Total Customers Scanned: {len(customers)}")
    print(f"Pre-Sales Targets Identified: {len(pre_sales_targets)}")
    print("="*60 + "\n")
    
    if not pre_sales_targets:
        print("No pre-sales campaigns needed today.")
        return

    choice = input("Initiate automated outbound pre-sales campaign for these targets? (y/n): ")
    if choice.lower() == 'y':
        print("\n" + "-"*60)
        print("INITIATING PRE-SALES CAMPAIGN...")
        print("-"*60)
        
        for c, campaign, age in pre_sales_targets:
            print(f"\n[QUEUE] Next Target: {c['name']} ({c['phone']})")
            print(f"[CONTEXT] {age} years old {c['car_model']} - Campaign: {campaign.upper()}")
            
            start_choice = input(f"Start live call with {c['name']}? (y/s to skip): ")
            
            if start_choice.lower() == 'y':
                # Trigger simulation with campaign context
                simulate_call(
                    from_phone=c['phone'], 
                    customer_id=c['id'], 
                    flow_type="pre_sales",
                    campaign_type=campaign,
                    vehicle_age=age
                )
            else:
                print(f"Skipping {c['name']}...")
                
        print("\nPre-sales campaign session complete.")

if __name__ == "__main__":
    run_pre_sales_scan()
