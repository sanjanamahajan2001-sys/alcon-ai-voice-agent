import json
import os

def main():
    path = "poc/flow_orchestrator/server/templates/inbound_receptionist.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        edges = data.get("edges", [])
        search_nodes = ["sales_query_loop", "service_query_loop", "kb_handler_sales", "kb_handler_service"]
        print("--- Edges connected to Query / KB nodes ---")
        for e in edges:
            if e.get("source") in search_nodes or e.get("target") in search_nodes:
                print(e)
                
if __name__ == "__main__":
    main()
