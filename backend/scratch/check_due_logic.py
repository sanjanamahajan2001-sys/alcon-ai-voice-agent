import json
from datetime import datetime, date

with open("data/customers.json", "r") as f:
    customers = json.load(f)

today = date.today()
print(f"Current Date: {today}")
print(f"{'ID':<3} | {'Name':<12} | {'Last Service':<12} | {'Due Months':<10} | {'Calculated Delta':<16} | {'Is Due (Calc)':<13} | {'Service Status':<15} | {'DND':<5}")
print("-" * 100)

for c in customers:
    last_svc_str = c.get("last_service_date")
    due_months = int(c.get("service_due_months", 6))
    
    if last_svc_str and last_svc_str != "recent date":
        last_svc = datetime.strptime(last_svc_str, "%Y-%m-%d").date()
        delta = (today.year - last_svc.year) * 12 + (today.month - last_svc.month)
        is_due_calc = delta >= due_months
    else:
        delta = "N/A"
        is_due_calc = True
        
    print(f"{c['id']:<3} | {c['name']:<12} | {str(last_svc_str):<12} | {due_months:<10} | {str(delta):<16} | {str(is_due_calc):<13} | {c.get('service_status'):<15} | {str(c.get('dnd_status')):<5}")
