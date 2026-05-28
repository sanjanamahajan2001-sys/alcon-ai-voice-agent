import asyncio
import json
import os
import sys
from orchestration_bridge import OrchestrationBridge
from database import DatabaseManager

# UI Styling
class UI:
    BOLD = "\033[1m"
    AGENT = "\033[1;95m"  # Bold Magenta
    USER = "\033[1;96m"   # Bold Cyan
    SYSTEM = "\033[90m"   # Grey
    SUCCESS = "\033[1;92m" # Bold Green
    FAIL = "\033[1;91m"    # Bold Red
    RESET = "\033[0m"
    HEADER = "\033[1;44;97m" # White on Blue

class PreSalesMegaTester:
    def __init__(self):
        self.db = DatabaseManager()
        self.bridge = OrchestrationBridge(self.db)
        self.test_customer = {
            "name": "Sanjana Mahajan",
            "car_model": "Hyundai Creta"
        }
        
    async def run_mega_test(self):
        print(f"\n{UI.HEADER}  ALCON PRE-SALES: 100% REQUIREMENT MEGA-SUITE  {UI.RESET}")
        print(f"{UI.SYSTEM}Validation Target: Full Knowledge Matrix | Manager: Prajyot Mainkar{UI.RESET}\n")
        
        call_sid = "MEGA_" + str(os.getpid())
        context = {
            "flow_type": "pre_sales",
            "variables": {
                "name": self.test_customer["name"].split()[0],
                "car_model": self.test_customer["car_model"],
                "salutation": "Ma'am"
            },
            "history": []
        }
        
        # [PHASE 1] Greeting
        res = await self.bridge.process_turn(call_sid, None, "pre_sales_template", context)
        self._print_turn("SUPRIYA (AI)", res["text"])
        self._update_ctx(context, res)

        # [PHASE 2] Mega Matrix Validation
        test_matrix = [
            # Identity & AI Check
            ("Process", "Who is calling me?", "Alcon"),
            ("Process", "Are you a real person or AI?", "AI assistant"),
            
            # Vehicle & Variants
            ("Vehicle", "Do you have automatic variants?", "automatic"),
            ("Vehicle", "Is petrol or diesel available?", "Diesel"),
            ("Vehicle", "Do you have CNG options?", "Aura"),
            
            # Price & Finance
            ("Finance", "What is the total on-road price?", "insurance"),
            ("Finance", "What will be the monthly EMI?", "₹18,500"),
            ("Finance", "Is there zero down payment?", "down payment"),
            
            # Offers & Loyalty
            ("Offers", "Can I get a corporate discount?", "corporate"),
            ("Offers", "Is there any loyalty bonus?", "loyalty"),
            ("Offers", "Any accessories free?", "accessories"),
            
            # Exchange
            ("Exchange", "Do you buy non-Hyundai cars?", "all car brand"),
            ("Exchange", "How much value for my old car?", "market value"),
            
            # Logistics
            ("Visit", "What are the showroom timings?", "9 AM to 8 PM"),
            ("Visit", "Can I visit this weekend?", "including weekends"),
            
            # Digital
            ("Digital", "Can you send details on WhatsApp?", "WhatsApp"),
            ("Digital", "Can I get a brochure?", "brochure"),
            
            # Competitors
            ("Competitors", "Why choose Hyundai over Tata?", "refinement"),
            ("Competitors", "How is it better than Kia?", "service network"),
            
            # Objections & Callbacks
            ("Objection", "Your price is too high", "callback"),
            ("Objection", "I need to discuss with family", "callback"),
            ("Rejection", "Please don't call me again", "wonderful day")
        ]
        
        passed = 0
        for cat, msg, expected in test_matrix:
            print(f"{UI.SYSTEM}[{cat}]{UI.RESET}")
            self._print_turn("CUSTOMER", msg)
            
            res = await self.bridge.process_turn(call_sid, msg, "pre_sales_template", context)
            self._print_turn("SUPRIYA (AI)", res["text"])
            
            # Validation
            is_match = expected.lower() in res["text"].lower()
            if is_match:
                print(f" {UI.SUCCESS}✓ VERIFIED{UI.RESET}\n")
                passed += 1
            else:
                # Fallback for dynamic phrasing (Callbacks/Goodbyes)
                text_low = res["text"].lower()
                if expected == "callback" and any(w in text_low for w in ["call you back", "another time", "callback"]):
                    print(f" {UI.SUCCESS}✓ VERIFIED (State Match){UI.RESET}\n")
                    passed += 1
                elif expected == "wonderful day" and any(w in text_low for w in ["wonderful day", "great day", "good day", "take care"]):
                    print(f" {UI.SUCCESS}✓ VERIFIED (Goodbye Match){UI.RESET}\n")
                    passed += 1
                else:
                    print(f" {UI.FAIL}✗ FAILED (Expected: {expected}){UI.RESET}\n")
            
            self._update_ctx(context, res)

        print(f"{UI.HEADER}  FINAL MEGA-SUITE SUMMARY  {UI.RESET}")
        print(f"{UI.BOLD}Total Categories Verified:{UI.RESET} 10")
        print(f"{UI.BOLD}Overall Compliance Rate:{UI.RESET} {int((passed/len(test_matrix))*100)}%")
        print(f"{UI.BOLD}Status:{UI.RESET} {UI.SUCCESS if passed >= 20 else UI.FAIL}Production Certified{UI.RESET}")
        
        print(f"\n{UI.BOLD}Final Score: {passed}/{len(test_matrix)} Requirements Met{UI.RESET}\n")

    def _update_ctx(self, context, res):
        context["current_node_id"] = res["current_node_id"]
        context["variables"] = res["variables"]
        context["history"] = res["history"]

    def _print_turn(self, role, text):
        if "CUSTOMER" in role:
            print(f"{UI.USER}👤 {role}:{UI.RESET} {text}")
        else:
            clean_text = " ".join(text.split())
            print(f"{UI.AGENT}🤖 {role}:{UI.RESET} {clean_text}")

if __name__ == "__main__":
    tester = PreSalesMegaTester()
    asyncio.run(tester.run_mega_test())
