import json

with open("/home/sanjana/Alcon/poc/flow_orchestrator/server/templates/insurance_v2_template.json", "r") as f:
    data = json.load(f)

print(json.dumps(data.get("edges", [])[:5], indent=2))
