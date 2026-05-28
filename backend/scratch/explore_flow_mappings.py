import json

with open("/home/sanjana/Alcon/poc/flow_orchestrator/server/templates/insurance_v2_template.json", "r") as f:
    data = json.load(f)

for edge in data.get("edges", []):
    print(f"Edge: {edge['source']} -> {edge['target']} | sourceHandle: {edge.get('sourceHandle')}")
