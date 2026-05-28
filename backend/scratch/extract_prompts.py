import os
import json

script_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(script_dir, "..", "..", "flow_orchestrator", "server", "templates")
output_path = os.path.join(script_dir, "extracted_prompts.txt")

with open(output_path, "w", encoding="utf-8") as out:
    for filename in os.listdir(templates_dir):
        if filename.endswith(".json"):
            path = os.path.join(templates_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                out.write(f"\n==================== {filename} ====================\n")
                # Find all nodes and their labels/prompts
                for node in data.get("nodes", []):
                    node_type = node.get("type")
                    node_data = node.get("data", {})
                    label = node_data.get("label")
                    if label:
                        out.write(f"[{node_type}] {label}\n")
            except Exception as e:
                out.write(f"Error reading {filename}: {e}\n")
print(f"Extracted to {output_path}")
