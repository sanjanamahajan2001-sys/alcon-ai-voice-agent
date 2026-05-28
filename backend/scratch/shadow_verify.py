import sys
import os
import asyncio
import json
import time

# Add current working directory to path
sys.path.append(os.getcwd())

from flow_manager import FlowManager
from database import DatabaseManager

async def run_sim(call_sid, inputs, use_template):
    # Set ENV before instantiation
    os.environ["USE_PRE_SALES_TEMPLATE"] = "true" if use_template else "false"
    fm = FlowManager()
    db = DatabaseManager()
    
    # Pre-Sales Leads setup
    customer_id = "1" # Sanjana
    flow_type = "pre_sales"
    
    results = []
    
    # Initialize Session
    session = {
        "call_sid": call_sid,
        "customer_id": customer_id,
        "flow_type": flow_type,
        "step": "start",
        "current_node_id": "start",
        "params": {
            "name": "Sanjana",
            "salutation": "Ma'am",
            "car_model": "Hyundai Creta",
            "car": "Hyundai Creta",
            "campaign_type": "upgrade",
            "vehicle_age": 2,
            "flow_type": "pre_sales",
            "query_count": 0
        },
        "history": [],
        "last_updated": time.time()
    }
    fm.session_manager.save_session(call_sid, session)
    db.update_lead_state(call_sid, lead_status="INITIATED", interest_level="COLD")
    
    for i, inp in enumerate(inputs):
        # handle_process(self, customer_id, step, speech_result, call_sid, flow_type="booking", ...)
        fm.handle_process(customer_id, session["step"], inp, call_sid, flow_type=flow_type)
        
        # Get updated state
        updated_session = fm.session_manager.get_session(call_sid)
        state = db.get_lead_state(call_sid)
        
        results.append({
            "turn": i+1,
            "status": state.get("lead_status"),
            "disposition": state.get("disposition"),
            "escalation": state.get("escalation_status"),
            "interest": state.get("interest_level")
        })
        
        # Update local session for next turn
        session = updated_session
        
    return results

async def test_parity():
    test_inputs = [
        "Yes speaking. Tell me more about the exchange offer.",
        "What is the EMI for the top model?",
        "How does it compare to the Kia Seltos? I want to talk to a manager."
    ]
    
    print("="*60)
    print("ALCON SHADOW VALIDATION: LEGACY VS TEMPLATE")
    print("="*60)
    
    print("\nRunning Legacy Simulation...")
    legacy_results = await run_sim("shadow_legacy_v6", test_inputs, False)
    
    print("\nRunning Template Simulation...")
    template_results = await run_sim("shadow_template_v6", test_inputs, True)
    
    print("\n" + "="*60)
    print("PARITY REPORT")
    print("="*60)
    print(f"{'Turn':<5} | {'Legacy Status':<15} | {'Template Status':<15} | {'Match'}")
    print("-" * 60)
    
    for i in range(len(test_inputs)):
        l = legacy_results[i]
        t = template_results[i]
        match = "✅" if l["status"] == t["status"] else "❌"
        print(f"{i+1:<5} | {l['status']:<15} | {t['status']:<15} | {match}")
        
    print("\n" + "="*60)
    print("ESCALATION PARITY")
    print("-" * 60)
    l_esc = legacy_results[-1]["escalation"]
    t_esc = template_results[-1]["escalation"]
    match_esc = "✅" if l_esc == t_esc else "❌"
    print(f"Legacy: {l_esc} | Template: {t_esc} | Match: {match_esc}")

if __name__ == "__main__":
    asyncio.run(test_parity())
