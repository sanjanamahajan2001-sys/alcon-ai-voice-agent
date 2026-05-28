import json
import os

def main():
    path = "poc/flow_orchestrator/server/templates/inbound_receptionist.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print("Root keys:", list(data.keys()))
        if "connections" in data:
            print("Connections length:", len(data["connections"]))
            print("First 5 connections:")
            for c in data["connections"][:5]:
                print(c)
        if "edges" in data:
            print("Edges length:", len(data["edges"]))
            print("First 5 edges:")
            for e in data["edges"][:5]:
                print(e)

if __name__ == "__main__":
    main()
