import json
import os

customers_path = "/home/sanjana/Alcon/poc/backend/data/customers.json"

try:
    with open(customers_path, "r", encoding="utf-8") as f:
        customers = json.load(f)

    updated = 0
    for c in customers:
        c_id = str(c["id"])
        
        # 1. Manish Pandey (ID 18) -> +919881012770
        if c_id == "18" and c["phone"] != "+919881012770":
            c["phone"] = "+919881012770"
            updated += 1
            print("Updated Manish Pandey (ID 18) phone to +919881012770")
            
        # 2. Kiran Shah (ID 19) -> +919881012771
        elif c_id == "19" and c["phone"] != "+919881012771":
            c["phone"] = "+919881012771"
            updated += 1
            print("Updated Kiran Shah (ID 19) phone to +919881012771")
            
        # 3. Aarav Mehta (ID 10) -> +919881012761
        elif c_id == "10" and c["phone"] != "+919881012761":
            c["phone"] = "+919881012761"
            updated += 1
            print("Updated Aarav Mehta (ID 10) phone to +919881012761")

    if updated > 0:
        with open(customers_path, "w", encoding="utf-8") as f:
            json.dump(customers, f, indent=4)
        print(f"Successfully updated {updated} customer phone numbers in customers.json")
    else:
        print("No updates needed, numbers are already aligned!")
        
except Exception as e:
    print(f"Error updating phone numbers: {e}")
