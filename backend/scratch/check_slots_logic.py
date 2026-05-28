import json

with open("data/customers.json", "r") as f:
    customers = json.load(f)

for idx, c in enumerate(customers):
    if idx < 10:
        print(f"Index {idx}: ID={c['id']}, Name={c['name']}, Phone={c['phone']}, Car={c['car_model']}")
