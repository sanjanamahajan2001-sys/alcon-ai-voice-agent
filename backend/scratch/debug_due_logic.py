import json
from datetime import datetime, timedelta

def debug_check():
    # Load Sanjana's details from customers.json
    with open("data/customers.json", "r") as f:
        customers = json.load(f)
    
    sanjana = customers[0]
    print("Sanjana raw data:", sanjana)
    
    last_date_str = sanjana.get("last_service_date")
    print("last_date_str:", last_date_str)
    
    interval_months = int(sanjana.get("service_due_months", 6))
    print("interval_months:", interval_months)
    
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
    due_date = last_date + timedelta(days=interval_months * 30)
    service_due_date = due_date.strftime("%d %B %Y")
    print("Calculated service_due_date:", service_due_date)
    
    # We simulate current time as 2026-05-26 (from ADDITIONAL_METADATA)
    simulated_now = datetime(2026, 5, 26).date()
    is_due = simulated_now > due_date.date()
    print("simulated_now:", simulated_now)
    print("due_date.date():", due_date.date())
    print("Is Due (simulated):", is_due)
    
    # Real now
    real_now = datetime.now().date()
    is_due_real = real_now > due_date.date()
    print("real_now:", real_now)
    print("Is Due (real):", is_due_real)

if __name__ == "__main__":
    debug_check()
