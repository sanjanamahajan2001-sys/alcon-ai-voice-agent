import json
with open("data/customers.json") as f:
    customers = json.load(f)
for c in customers:
    if str(c["id"]) == "10":
        print(json.dumps(c, indent=2))
