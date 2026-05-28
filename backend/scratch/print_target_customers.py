import json
import os

customers_path = os.path.join(os.path.dirname(__file__), "../data/customers.json")

with open(customers_path, "r", encoding="utf-8") as f:
    customers = json.load(f)

print("Checking updated profiles in customers.json:")
for c in customers:
    if str(c["id"]) in ("1", "14", "17"):
        print(f"\n--- Customer {c.get('name')} (ID: {c.get('id')}) ---")
        print(json.dumps(c, indent=2))
