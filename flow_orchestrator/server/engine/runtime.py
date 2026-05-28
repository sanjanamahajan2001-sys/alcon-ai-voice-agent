from typing import Dict, Any, List, Optional
from engine.registry import NodeRegistry

class FlowRuntime:
    def __init__(self, registry: NodeRegistry):
        self.registry = registry

    async def execute_step(self, flow: Dict[str, Any], session: Dict[str, Any], user_input: Optional[str] = None):
        current_node_id = session.get("current_node_id")
        nodes = {n["id"]: n for n in flow.get("nodes", [])}
        edges = flow.get("edges", [])

        current_node = nodes.get(current_node_id)
        if not current_node:
            return {"error": "Current node not found in flow definition"}

        executor = self.registry.get_executor(current_node["type"])
        if not executor:
            execution_result = {"status": "SUCCESS", "logs": f"Executed generic node {current_node['type']}"}
        else:
            execution_result = await executor.execute(current_node["data"], session)

        # Console logging for user observability
        print(f"  [EXECUTE] Node: {current_node_id} ({current_node['type']})")
        print(f"  [RESULT] Status: {execution_result.get('status')}")
        if "logs" in execution_result:
            print(f"  [LOGS] {execution_result['logs']}")
        if "outcome" in execution_result:
            print(f"  [BRANCH] Path: {execution_result['outcome']}")

        # Update session audit logs
        session["audit_logs"].append({
            "node": current_node_id,
            "status": execution_result.get("status"),
            "logs": execution_result.get("logs")
        })

        # Determine next node
        next_node_id = self._get_next_node(current_node_id, edges, execution_result)
        if next_node_id:
            session["current_node_id"] = next_node_id
            return {
                "execution_result": execution_result,
                "node_id": current_node_id,
                "next_node_id": next_node_id,
                "status": "CONTINUE"
            }
        else:
            return {
                "execution_result": execution_result,
                "node_id": current_node_id,
                "status": "END"
            }

    async def simulate(self, flow: Dict[str, Any], initial_context: Optional[Dict[str, Any]] = None):
        print("\n" + "="*50)
        print(f"🚀 STARTING FLOW SIMULATION: {flow.get('flow_id')}")
        print("="*50)
        
        # Find start node
        start_node = next((n for n in flow["nodes"] if n["type"] == "startNode"), None)
        if not start_node:
            print("❌ ERROR: No start node found")
            return {"error": "No start node found"}

        session = {
            "session_id": "sim_123",
            "current_node_id": start_node["id"],
            "variables": initial_context or {},
            "audit_logs": []
        }

        execution_steps = []
        limit = 20 # Prevent infinite loops
        count = 0

        while count < limit:
            step_result = await self.execute_step(flow, session)
            if "error" in step_result:
                print(f"❌ Execution Error: {step_result['error']}")
                break

            # Update our session state
            current_node_id = session.get("current_node_id")
            variables = session.get("variables", {})
            
            execution_steps.append({
                "node_id": step_result["node_id"],
                "status": step_result["execution_result"].get("status"),
                "logs": step_result["execution_result"].get("logs")
            })
            
            # If we just spoke a message, stop and wait for user reply
            if step_result["status"] == "END" or "Spoke:" in step_result["execution_result"].get("logs", ""):
                break

            count += 1

        print("="*50)
        print(f"🏁 SIMULATION COMPLETE in {count+1} steps")
        print(f"📦 FINAL CONTEXT: {session['variables']}")
        print("="*50 + "\n")
        return {
            "execution_steps": execution_steps,
            "context": session["variables"]
        }

    def _get_next_node(self, current_node_id: str, edges: List[Dict[str, Any]], result: Dict[str, Any]) -> Optional[str]:
        # Branching logic for Condition nodes
        outcome = result.get("outcome") # "true" or "false"
        
        print(f"  [DEBUG] Finding next node for '{current_node_id}' with outcome '{outcome}'")
        
        # 1. Primary Branching (Explicit sourceHandle match)
        for edge in edges:
            if edge["source"] == current_node_id:
                if outcome:
                    # Match exact handle
                    if edge.get("sourceHandle") == outcome:
                        print(f"  [DEBUG] Matched edge {edge.get('id')} -> {edge['target']} (Handle: {outcome})")
                        return edge["target"]
                    # Fallback for true/false: if no handle is defined on the edge, treat as default path
                    if outcome in ["true", "false"] and edge.get("sourceHandle") is None:
                        print(f"  [DEBUG] Matched unlabeled edge -> {edge['target']} (Outcome: {outcome})")
                        return edge["target"]
                else:

                    # Default: first outgoing edge for non-condition nodes
                    print(f"  [DEBUG] No outcome, following default edge -> {edge['target']}")
                    return edge["target"]

        
        # --- FALLBACK LOGIC ---
        # If we have an outcome (like 'busy', 'wrong_number', 'transfer') but no specific edge is connected, 
        # fallback to the 'false' branch or the first available edge to prevent stuck flows.
        if outcome and outcome not in ["true", "false"]:
            # 1. Look for 'false' branch
            for edge in edges:
                if edge["source"] == current_node_id and edge.get("sourceHandle") == "false":
                    print(f"  [ENGINE_FALLBACK] No '{outcome}' edge found, following 'false' path")
                    return edge["target"]
            # 2. Look for any branch
            for edge in edges:
                if edge["source"] == current_node_id:
                    print(f"  [ENGINE_FALLBACK] No '{outcome}' or 'false' edge found, following first available path")
                    return edge["target"]
                    
        return None


