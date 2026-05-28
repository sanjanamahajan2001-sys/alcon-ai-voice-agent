import json
import os

def main():
    path = "poc/flow_orchestrator/server/templates/inbound_receptionist.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        nodes = data.get("nodes", [])
        for node in nodes:
            if "transfer" in node.get("id", "").lower() or "action" in node.get("type", "").lower():
                print(f"Node ID: {node.get('id')}")
                print(f"  Type: {node.get('type')}")
                print(f"  Data: {node.get('data')}")
                print(f"  Edges: {node.get('edges')}")
                print("-" * 40)
                
if __name__ == "__main__":
    main()
