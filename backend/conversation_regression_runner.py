import sys
import os
import asyncio
import json
import time
from typing import List, Dict, Any

# Add current working directory to path
sys.path.append(os.getcwd())

from flow_manager import FlowManager
from database import DatabaseManager

class RegressionRunner:
    def __init__(self):
        self.db = DatabaseManager()
        self.scenarios = []

    def load_scenarios(self, file_path: str):
        with open(file_path, "r") as f:
            self.scenarios = json.load(f)

    async def run_scenario(self, scenario: Dict[str, Any]):
        name = scenario["name"]
        inputs = scenario["inputs"]
        expected = scenario["expected"]
        call_sid = f"reg_test_{int(time.time())}_{name[:10].replace(' ', '_')}"
        
        print(f"\n[SCENARIO] {name}")
        print("-" * 50)
        
        # Enable Template for this run
        os.environ["USE_PRE_SALES_TEMPLATE"] = "true"
        fm = FlowManager()
        
        # Init Session
        customer_id = scenario.get("customer_id", "1")
        session = {
            "call_sid": call_sid,
            "customer_id": customer_id,
            "flow_type": "pre_sales",
            "step": "start",
            "current_node_id": "start",
            "params": scenario.get("initial_params", {
                "name": "Test User",
                "car_model": "Hyundai Creta",
                "campaign_type": "upgrade",
                "car": "Hyundai Creta",
                "salutation": "Sir"
            }),
            "history": [],
            "last_updated": time.time()
        }
        # 1. Initialize Call (Get Greeting)
        print(f"  AI Greeting...")
        fm.handle_voice(customer_id, call_sid, flow_type="pre_sales")
        session = fm.session_manager.get_session(call_sid)

        # 2. Process User Inputs
        for i, inp in enumerate(inputs):
            print(f"  Turn {i+1}: User -> {inp}")
            fm.handle_process(customer_id, session["step"], inp, call_sid, flow_type="pre_sales")
            session = fm.session_manager.get_session(call_sid)

        # Assertions
        state = self.db.get_lead_state(call_sid)
        audit = self.get_audit_trail(call_sid)
        
        results = self.validate(state, audit, expected)
        
        if results["passed"]:
            print(f"✅ PASSED: {name}")
        else:
            print(f"❌ FAILED: {name}")
            for err in results["errors"]:
                print(f"   - {err}")
        
        return results

    def get_audit_trail(self, call_sid: str) -> List[Dict[str, Any]]:
        # Query PG for audit trail
        query = "SELECT * FROM orchestration_audit WHERE call_sid = %s ORDER BY timestamp ASC"
        return self.db.execute_query(query, (call_sid,), fetch=True)

    def validate(self, state: Dict[str, Any], audit: List[Dict[str, Any]], expected: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        
        # 1. State Assertions
        if expected.get("disposition") and state.get("disposition") != expected["disposition"]:
            errors.append(f"Disposition Mismatch: Expected {expected['disposition']}, Got {state.get('disposition')}")
        
        if expected.get("escalation") and state.get("escalation_status") != expected["escalation"]:
            errors.append(f"Escalation Mismatch: Expected {expected['escalation']}, Got {state.get('escalation_status')}")

        if expected.get("min_audit_rows") and len(audit) < expected["min_audit_rows"]:
            errors.append(f"Audit Incomplete: Expected at least {expected['min_audit_rows']} rows, Got {len(audit)}")

        return {"passed": len(errors) == 0, "errors": errors}

    async def run_parity(self, scenario: Dict[str, Any]):
        print(f"\n[PARITY CHECK] {scenario['name']}")
        
        # 1. Run Legacy
        legacy_res = await self.run_simulation("legacy", scenario)
        
        # 2. Run Template
        template_res = await self.run_simulation("template", scenario)
        
        # Compare
        l_disp = legacy_res.get("disposition")
        t_disp = template_res.get("disposition")
        
        if l_disp == t_disp:
            print(f"✅ PARITY MATCH: {t_disp}")
        elif l_disp is None and t_disp is not None:
            print(f"✨ TEMPLATE ENHANCEMENT: Legacy (None) -> Template ({t_disp})")
        else:
            print(f"⚠️ PARITY MISMATCH!")
            print(f"   Legacy:   {l_disp}")
            print(f"   Template: {t_disp}")

    async def run_simulation(self, mode: str, scenario: Dict[str, Any]):
        call_sid = f"reg_{mode}_{int(time.time())}_{scenario['name'][:10].replace(' ', '_')}"
        os.environ["USE_PRE_SALES_TEMPLATE"] = "true" if mode == "template" else "false"
        fm = FlowManager()
        
        customer_id = "1"
        session = {
            "call_sid": call_sid, "customer_id": customer_id, "flow_type": "pre_sales",
            "step": "start", "current_node_id": "start",
            "params": scenario.get("initial_params", {
                "name": "Test User",
                "car_model": "Hyundai Creta",
                "car": "Hyundai Creta",
                "salutation": "Sir",
                "campaign_type": "upgrade"
            }),
            "history": [], "last_updated": time.time()
        }
        # Initialize Call
        fm.handle_voice(customer_id, call_sid, flow_type="pre_sales")
        session = fm.session_manager.get_session(call_sid)
        
        for inp in scenario["inputs"]:
            fm.handle_process(customer_id, session["step"], inp, call_sid, flow_type="pre_sales")
            session = fm.session_manager.get_session(call_sid)
            
        state = self.db.get_lead_state(call_sid)
        return state

    async def run_all(self):
        print("="*60)
        print("ALCON BEHAVIORAL REGRESSION SUITE")
        print("="*60)
        
        summary = {"total": 0, "passed": 0, "failed": 0}
        for scenario in self.scenarios:
            res = await self.run_scenario(scenario)
            summary["total"] += 1
            if res["passed"]: summary["passed"] += 1
            else: summary["failed"] += 1
            
            # Also run parity for this scenario
            await self.run_parity(scenario)
            
        print("\n" + "="*60)
        print(f"REGRESSION SUMMARY: {summary['passed']}/{summary['total']} PASSED")
        print("="*60)

    def validate_audit_integrity(self, audit: List[Any], expected_intents: List[str]):
        # Validate turn-by-turn intent classification
        for i, row in enumerate(audit):
            if i < len(expected_intents):
                actual = row["resolved_intent"]
                if actual != expected_intents[i]:
                    return False, f"Turn {i+1} Intent Mismatch: {actual} vs {expected_intents[i]}"
        return True, ""

if __name__ == "__main__":
    # Define test scenarios inline
    test_scenarios = [
        {
            "name": "Hot Lead Direct Transfer",
            "inputs": [
                "I want to buy the car this week.",
                "Yes connect me to manager."
            ],
            "expected": {
                "disposition": "TRANSFER_REQUESTED",
                "escalation": "IN_PROGRESS",
                "min_audit_rows": 2
            }
        },
        {
            "name": "Wrong Vehicle Exit",
            "inputs": [
                "I sold that car already."
            ],
            "expected": {
                "disposition": "WRONG_NUMBER",
                "min_audit_rows": 1
            }
        },
        {
            "name": "Query Skip Intro",
            "inputs": [
                "What is the EMI?"
            ],
            "expected": {
                "min_audit_rows": 1
            }
        }
    ]
    
    runner = RegressionRunner()
    runner.scenarios = test_scenarios
    asyncio.run(runner.run_all())
