from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import time
import json
import os
import re
from datetime import datetime
import shutil
from data import MOCK_CRM
from engine.runtime import FlowRuntime
from engine.registry import NodeRegistry
from engine.schemas import NODE_SCHEMAS

app = FastAPI(title="Flow Orchestrator Runtime")

import sys
# Add backend to path for date_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
from date_utils import parse_date_phrase, format_date_full

# Initialize Engine
registry = NodeRegistry()
runtime = FlowRuntime(registry)

RECORDS_DIR = os.path.join(os.path.dirname(__file__), "data", "session_records")
os.makedirs(RECORDS_DIR, exist_ok=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/mock/crm/{phone}")
async def mock_crm_lookup(phone: str):
    return MOCK_CRM.get(phone, MOCK_CRM["default"])

# --- Models ---
class NodePosition(BaseModel):
    x: float
    y: float

class NodeDefinition(BaseModel):
    id: str
    type: str
    data: Dict[str, Any]
    position: Optional[NodePosition] = None

class EdgeDefinition(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None # Support branching
    data: Optional[Dict[str, Any]] = None

class FlowDefinition(BaseModel):
    flow_id: str
    version: int
    status: str
    nodes: List[NodeDefinition]
    edges: List[EdgeDefinition]
    description: Optional[str] = ""
    name: Optional[str] = ""

class SessionContext(BaseModel):
    session_id: str
    flow_id: str
    current_node_id: str
    variables: Dict[str, Any] = {}
    history: List[Dict[str, Any]] = []

def save_session_record(session_id: str, context: SessionContext):
    path = os.path.join(RECORDS_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(context.dict(), f, indent=2)

# --- Persistence Logic ---
DRAFTS_FILE = os.path.join(os.path.dirname(__file__), "flows_db.json")

def load_flows():
    if os.path.exists(DRAFTS_FILE):
        try:
            with open(DRAFTS_FILE, "r") as f:
                data = json.load(f)
                return {fid: FlowDefinition(**fval) for fid, fval in data.items()}
        except Exception as e:
            print(f"Error loading flows: {e}")
    return {}

def save_flows():
    try:
        with open(DRAFTS_FILE, "w") as f:
            json.dump({fid: fval.dict() for fid, fval in flows.items()}, f, indent=2)
    except Exception as e:
        print(f"Error saving flows: {e}")

# --- Mock Storage ---
flows = load_flows()
sessions: Dict[str, SessionContext] = {}

@app.get("/nodes/schemas")
async def get_node_schemas():
    return NODE_SCHEMAS

@app.get("/templates")
async def list_templates():
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    if not os.path.exists(templates_dir):
        return []
    
    template_files = [f for f in os.listdir(templates_dir) if f.endswith(".json")]
    result = []
    for f in template_files:
        path = os.path.join(templates_dir, f)
        with open(path, "r") as tf:
            data = json.load(tf)
            result.append({
                "id": f.replace(".json", ""),
                "name": data.get("name", f),
                "description": data.get("description", "")
            })
    return result

@app.post("/flows/from-template/{template_id}")
async def create_from_template(template_id: str):
    path = os.path.join(os.path.dirname(__file__), "templates", f"{template_id}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Template not found")
    
    with open(path, "r") as f:
        template_data = json.load(f)
        
    new_flow_id = f"{template_id}_draft_{uuid.uuid4().hex[:4]}"
    template_data["flow_id"] = new_flow_id
    template_data["status"] = "draft"
    template_data["version"] = 1
    
    flows[new_flow_id] = FlowDefinition(**template_data)
    save_flows()
    return flows[new_flow_id]

# --- Interactive Session Endpoints ---

@app.post("/sessions/start/{flow_id}")
async def start_interactive_session(flow_id: str, from_phone: Optional[str] = None):
    if flow_id not in flows:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    flow = flows[flow_id]
    start_node = next((n for n in flow.nodes if n.type == "startNode"), None)
    if not start_node:
        raise HTTPException(status_code=400, detail="Flow has no start node")

    session_id = f"chat_{uuid.uuid4().hex[:6]}"
    context = SessionContext(
        session_id=session_id,
        flow_id=flow_id,
        current_node_id=start_node.id,
        variables={"from": from_phone} if from_phone else {},
        history=[]
    )
    sessions[session_id] = context
    
    # Process until we need input (reaching first MessageNode)
    return await process_session_step(session_id)

@app.get("/sessions/{session_id}")
async def get_session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.post("/sessions/{session_id}/message")
async def send_session_message(session_id: str, message: Dict[str, str]):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    user_input = message.get("text", "").strip()
    context = sessions[session_id]
    context.history.append({"role": "user", "text": user_input})
    
    # --- UNIVERSAL DATA CAPTURE (Turn-by-Turn) ---
    # 1. Capture Date
    parsed_dt = parse_date_phrase(user_input)
    if parsed_dt:
        # 1. Check for specific times (e.g., 10 AM, 1:30 PM, 4pm)
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', user_input.lower())
        if time_match:
            hh = int(time_match.group(1))
            mm = time_match.group(2) or "00"
            period = time_match.group(3).upper()
            time_suffix = f"{hh:02d}:{mm} {period}"
        # 2. Check for "after X hours"
        elif re.search(r'(?:after|in)\s+(\d+)\s+(?:hour|hr)', user_input.lower()):
            hrs_match = re.search(r'(?:after|in)\s+(\d+)\s+(?:hour|hr)', user_input.lower())
            hrs = int(hrs_match.group(1))
            time_suffix = (datetime.now() + timedelta(hours=hrs)).strftime("%I:%M %p")
        # 3. Keyword slots
        elif "evening" in user_input.lower(): time_suffix = "06:00 PM"
        elif "afternoon" in user_input.lower(): time_suffix = "02:00 PM"
        elif "morning" in user_input.lower(): time_suffix = "10:00 AM"
        else: time_suffix = "09:00 AM"
        
        formatted = f"{format_date_full(parsed_dt)} at {time_suffix}"
        context.variables["confirmed_date"] = formatted
        context.variables["pickup_time"] = formatted
        print(f"[TURN_CAPTURE] Captured Date: {formatted}")



    # 2. Capture Mileage (Look for numbers > 100)
    mileage_match = re.search(r'(\d{3,6})', user_input)
    if mileage_match:
        context.variables["mileage"] = mileage_match.group(1)
        print(f"[TURN_CAPTURE] Captured Mileage: {context.variables['mileage']}")
    
    # 3. Capture Concerns (Simple keyword-based or just store if it looks like a description)
    if any(keyword in user_input.lower() for keyword in ["issue", "problem", "broken", "noise", "working", "check", "brakes"]):
        context.variables["concerns"] = user_input
        print(f"[TURN_CAPTURE] Captured Concerns: {user_input}")

    return await process_session_step(session_id)

async def process_session_step(session_id: str):
    context = sessions[session_id]
    flow = flows[context.flow_id]
    flow_dict = flow.dict()
    
    # Process steps one by one until we hit a Message node or end
    responses = []
    limit = 10
    count = 0
    
    while count < limit:
        # Create a session-like object for the engine
        runtime_session = {
            "current_node_id": context.current_node_id,
            "variables": context.variables,
            "history": context.history,
            "audit_logs": []
        }
        
        step_result = await runtime.execute_step(flow_dict, runtime_session)
        
        if "error" in step_result:
            print(f"❌ Execution Error: {step_result['error']}")
            break

        # Update our session state
        context.current_node_id = runtime_session.get("current_node_id")
        context.variables = runtime_session.get("variables", {})
        
        # PERSIST: Save state after each step for DMS readiness
        save_session_record(session_id, context)
        
        # Collect response
        exec_res = step_result.get("execution_result", {})
        if "logs" in exec_res:
            responses.append(exec_res["logs"])
        
        # If we just spoke a message, transferred, or hung up, stop and wait for user reply
        is_terminal = step_result["status"] == "END" or \
                      "Spoke:" in exec_res.get("logs", "") or \
                      exec_res.get("action") in ["transfer", "hangup"]
        
        if is_terminal:
            break


            
        count += 1
        
    return {
        "session_id": session_id,
        "responses": responses,
        "variables": context.variables,
        "status": "COMPLETED" if count >= limit or step_result["status"] == "END" else "AWAITING_INPUT"
    }

@app.get("/sessions/{session_id}")
async def get_session_state(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.post("/flows")
async def save_flow(flow: FlowDefinition):
    # If the flow exists, increment version
    if flow.flow_id in flows:
        flow.version = flows[flow.flow_id].version + 1
    else:
        flow.version = 1
    
    flow.name = flow.name or f"Flow {flow.flow_id}"
    flows[flow.flow_id] = flow
    save_flows()
    print(f"[VERSIONING] Saved {flow.flow_id} Version {flow.version}")
    return {"message": "Flow saved successfully", "flow_id": flow.flow_id, "version": flow.version}

@app.post("/flows/{flow_id}/publish")
async def publish_flow(flow_id: str):
    if flow_id not in flows:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    flow = flows[flow_id]
    template_name = flow_id.split("_draft_")[0]
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    history_dir = os.path.join(templates_dir, "history")
    
    if not os.path.exists(history_dir):
        os.makedirs(history_dir)
        
    path = os.path.join(templates_dir, f"{template_name}.json")
    
    # 1. Back up existing if it exists
    if os.path.exists(path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(history_dir, f"{template_name}_{timestamp}.json")
        import shutil
        shutil.copy2(path, backup_path)
        print(f"[BACKUP] Existing template moved to {backup_path}")
    
    # 2. Overwrite master template with a CLEAN version (no draft IDs)
    clean_flow = flow.dict()
    clean_flow["flow_id"] = template_name
    # Strip draft suffix from name if present
    if " (post_service_feedback_draft_" in clean_flow["name"]:
        clean_flow["name"] = clean_flow["name"].split(" (")[0]
    elif "_draft_" in clean_flow["name"]:
         clean_flow["name"] = clean_flow["name"].split("_draft_")[0]

    with open(path, "w") as f:
        json.dump(clean_flow, f, indent=2)
    
    print(f"[PUBLISH] Draft {flow_id} promoted to clean Template {template_name}")
    return {"message": "Flow published to template successfully", "template": template_name}

@app.get("/flows/{flow_id}/history")
async def get_flow_history(flow_id: str):
    template_name = flow_id.split("_draft_")[0]
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    history_dir = os.path.join(templates_dir, "history")
    
    if not os.path.exists(history_dir):
        return []
    
    backups = [f for f in os.listdir(history_dir) if f.startswith(f"{template_name}_") and f.endswith(".json")]
    backups.sort(reverse=True) # Latest first
    
    result = []
    for b in backups:
        # Extract timestamp from filename: template_name_YYYYMMDD_HHMMSS.json
        parts = b.replace(".json", "").split("_")
        timestamp_str = f"{parts[-2]}_{parts[-1]}"
        try:
            dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_time = timestamp_str
            
        result.append({
            "filename": b,
            "timestamp": formatted_time,
            "raw_timestamp": timestamp_str
        })
    return result

@app.post("/flows/{flow_id}/rollback")
async def rollback_flow(flow_id: str):
    if flow_id not in flows:
        # If it's not a draft ID, try to see if it's a template ID
        template_name = flow_id
    else:
        template_name = flow_id.split("_draft_")[0]
        
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    history_dir = os.path.join(templates_dir, "history")
    
    if not os.path.exists(history_dir):
        raise HTTPException(status_code=404, detail="No history found for this flow")
    
    backups = [f for f in os.listdir(history_dir) if f.startswith(f"{template_name}_") and f.endswith(".json")]
    if not backups:
        raise HTTPException(status_code=404, detail="No backup versions found")
        
    backups.sort(reverse=True) # Latest first
    latest_backup = backups[0]
    backup_path = os.path.join(history_dir, latest_backup)
    template_path = os.path.join(templates_dir, f"{template_name}.json")
    
    # 1. Restore the template file
    with open(backup_path, "r") as f:
        backup_data = json.load(f)
        
    with open(template_path, "w") as f:
        json.dump(backup_data, f, indent=2)
        
    # 2. Update the active draft if it exists, or create a new one from the rolled-back template
    if flow_id in flows:
        # Update existing draft
        rolled_back_flow = FlowDefinition(**backup_data)
        rolled_back_flow.flow_id = flow_id # Keep the draft ID
        rolled_back_flow.version = flows[flow_id].version + 1
        flows[flow_id] = rolled_back_flow
    else:
        # If we rolled back a master template directly, we might want to return it
        pass

    save_flows()
    print(f"[ROLLBACK] Reverted {template_name} to version {latest_backup}")
    
    # Return the data to the UI
    return {
        "message": "Rollback successful", 
        "version": latest_backup,
        "nodes": backup_data.get("nodes", []),
        "edges": backup_data.get("edges", [])
    }

@app.get("/flows")
async def list_active_flows():
    # Deduplicate: Only return the latest version for each unique flow name
    latest_drafts = {}
    for f in flows.values():
        # Group by the base name (e.g., service_booking_prod)
        base_name = f.flow_id.split("_draft_")[0]
        if base_name not in latest_drafts or f.version > latest_drafts[base_name].version:
            latest_drafts[base_name] = f
            
    return [f.dict() for f in latest_drafts.values()]

@app.get("/flows/latest")
async def get_latest_flow():
    if not flows:
        raise HTTPException(status_code=404, detail="No flows found")
    latest_id = list(flows.keys())[-1]
    return flows[latest_id]

@app.get("/flows/{flow_id}")
async def get_flow(flow_id: str):
    if flow_id not in flows:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flows[flow_id]

@app.post("/flows/{flow_id}/simulate")
async def simulate_flow(flow_id: str):
    if flow_id not in flows:
        raise HTTPException(status_code=404, detail="Flow not found")
    
    flow = flows[flow_id]
    flow_dict = flow.dict()
    result = await runtime.simulate(flow_dict)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
