import asyncio
import json
import os
import sys
from orchestration_bridge import OrchestrationBridge
from database import DatabaseManager

class PreSalesAutomationTester:
    def __init__(self):
        self.db = DatabaseManager()
        self.bridge = OrchestrationBridge(self.db)
        self.test_customer = {
            "id": "1",
            "name": "Sanjana",
            "phone": "+919881012767",
            "car_model": "Hyundai Creta",
            "campaign_type": "emi_benefit",
            "vehicle_age": 2
        }
        
    async def run_comprehensive_test(self):
        print("\n" + "="*60)
        print("ALCON PRE-SALES AUTOMATION TEST SUITE")
        print("="*60)
        
        call_sid = "AUTO_TEST_" + str(os.getpid())
        context = {
            "flow_type": "pre_sales",
            "variables": {
                "id": self.test_customer["id"],
                "name": self.test_customer["name"],
                "car_model": self.test_customer["car_model"],
                "campaign_type": self.test_customer["campaign_type"],
                "vehicle_age": self.test_customer["vehicle_age"],
                "is_due": False
            },
            "history": []
        }
        
        # 1. Start Turn (Greeting)
        print(f"\n[STEP 1] Initializing Call for {self.test_customer['name']}...")
        res = await self.bridge.process_turn(call_sid, None, "pre_sales_template", context)
        self._print_turn("AI", res["text"])
        
        # Verify Salutation
        if "Ma'am" in res["text"]:
            print("✅ Salutation Check: Correct (Ma'am detected for Sanjana)")
        else:
            print("❌ Salutation Check: Failed (Expected Ma'am)")

        # Update context for next turns
        context["current_node_id"] = res["current_node_id"]
        context["variables"] = res["variables"]
        context["history"] = res["history"]

        # 2. Test Suite: Iterating through Requirement Queries
        queries = [
            ("What are the benefits?", "offers", "₹50,000"),
            ("What are the EMI options?", "price", "EMI from ₹18,500"),
            ("What colors do you have?", "colors", "Abyss Black"),
            ("What features are included?", "features", "Panoramic Sunroof"),
            ("What is the mileage?", "mileage", "18 kmpl"),
            ("Is it safe?", "safety", "6 Airbags"),
            ("What is the waiting period?", "availability", "3-week")
        ]
        
        for user_msg, intent, expected_keyword in queries:
            print(f"\n[QUERY TEST] User: \"{user_msg}\"")
            res = await self.bridge.process_turn(call_sid, user_msg, "pre_sales_template", context)
            
            # Update local context
            context["current_node_id"] = res["current_node_id"]
            context["variables"] = res["variables"]
            context["history"] = res["history"]
            
            # Validation
            self._print_turn("AI", res["text"])
            if expected_keyword.lower() in res["text"].lower():
                print(f"✅ Intent [{intent}]: Passed (Matched: {expected_keyword})")
            else:
                print(f"❌ Intent [{intent}]: Failed (Keyword '{expected_keyword}' not found in AI response)")

            # Check Readiness Score increment
            score = context["variables"].get("readiness_score", 0)
            print(f"📈 Current Readiness Score: {score}")

        # 3. Final Step: Request Callback
        print(f"\n[STEP 3] Testing Callback Scheduling...")
        res = await self.bridge.process_turn(call_sid, "call me back tomorrow at 5pm", "pre_sales_template", context)
        self._print_turn("AI", res["text"])
        
        if "callback" in res["text"].lower() or "scheduled" in res["text"].lower():
            print("✅ Callback logic: Passed")
        else:
            print("❌ Callback logic: Failed")

        # 4. Persistence Check
        print(f"\n[STEP 4] Verifying Database Persistence...")
        lead_state = self.db.get_lead_state(call_sid)
        if lead_state and lead_state.get("lead_status") == "FOLLOW_UP":
            print("✅ DB Persistence: Passed (Status is FOLLOW_UP)")
        else:
            print(f"❌ DB Persistence: Failed (Actual status: {lead_state.get('lead_status') if lead_state else 'None'})")

        print("\n" + "="*60)
        print("TEST SUITE COMPLETED")
        print("="*60 + "\n")

    def _print_turn(self, role, text):
        color = "\033[94m" if role == "AI" else "\033[92m"
        print(f"{color}[{role}]: {text}\033[0m")

if __name__ == "__main__":
    tester = PreSalesAutomationTester()
    asyncio.run(tester.run_comprehensive_test())
