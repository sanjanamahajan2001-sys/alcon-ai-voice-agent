import json
import os

def main():
    path = "poc/flow_orchestrator/server/templates/inbound_receptionist.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("--- Inbound Receptionist Flow Structure ---")
        print("Flow Name:", data.get("name"))
        print("Start Node:", data.get("start_node_id"))
        
        nodes = data.get("nodes", [])
        print(f"Total nodes: {len(nodes)}")
        for idx, node in enumerate(nodes):
            print(f"\nNode #{idx+1} ID: {node.get('id')}")
            print(f"  Type: {node.get('type')}")
            print(f"  Text: {node.get('text')}")
            print(f"  Edges: {node.get('edges')}")
            
if __name__ == "__main__":
    main()
