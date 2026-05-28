import json

with open("/home/sanjana/Alcon/poc/flow_orchestrator/server/templates/insurance_v2_template.json", "r") as f:
    data = json.load(f)

print("NODES:")
for node in data.get("nodes", []):
    print(f"Node ID: {node['id']} | Type: {node['type']} | Label: {node.get('data', {}).get('label', '')}")

print("\nEDGES:")
for edge in data.get("edges", []):
    print(f"Edge: {edge['source']} -> {edge['target']} | Condition/Outcome: {edge.get('data', {}).get('outcome', edge.get('label', ''))}")
