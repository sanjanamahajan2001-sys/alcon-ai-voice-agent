import json
from datetime import datetime
from flow_manager import FlowManager
from simulate_v2 import simulate_call

def run_dms_scan():
    fm = FlowManager()
    
    print("\n" + "="*50)
    print("ALCON DMS SERVICE SCANNER - MORNING REPORT")
    print("="*50)
    print(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    print("-"*50)
    
    with open("data/customers.json", "r") as f:
        customers = json.load(f)
        
    due_customers = []
    
    print(f"{'NAME':<15} | {'CAR':<15} | {'LAST SERVICE':<15} | {'STATUS'}")
    print("-"*50)
    
    for c in customers:
        is_due, delta = fm.get_service_status(c)
        is_dnd = c.get("dnd_status", False)
        
        status = "DUE" if is_due else "OK"
        if delta > 9: status = "OVERDUE"
        if is_dnd: status = "DND (SKIP)"
        
        print(f"{c['name']:<15} | {c['car_model']:<15} | {c['last_service_date']:<15} | {status}")
        
        if is_due and not is_dnd:
            due_customers.append(c)
            
    print("-"*50)
    print(f"Total Customers Scanned: {len(customers)}")
    print(f"Service Due Targets Identified: {len(due_customers)}")
    print("="*50 + "\n")
    
    if not due_customers:
        print("No service campaigns needed today.")
        return

    choice = input("Initiate automated outbound campaign for these targets? (y/n): ")
    if choice.lower() == 'y':
        print("\n" + "-"*50)
        print("INITIATING CAMPAIGN...")
        print("-"*50)
        
        for c in due_customers:
            print(f"\n[QUEUE] Next Target: {c['name']} ({c['phone']})")
            start_choice = input(f"Start live call with {c['name']}? (y/s to skip): ")
            
            if start_choice.lower() == 'y':
                simulate_call(from_phone=c['phone'], customer_id=c['id'], flow_type="booking")
            else:
                print(f"Skipping {c['name']}...")
                
        print("\nCampaign session complete.")

if __name__ == "__main__":
    run_dms_scan()
