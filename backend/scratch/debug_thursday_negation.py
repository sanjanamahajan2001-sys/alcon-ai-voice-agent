import sys
import os
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from test_all_flows import FlowTester, reset_customer_db

def run_scenario(name, turns, language="1"):
    # Reset standard DB
    reset_customer_db()
    
    # Reset customer 12 (Kabir Kapoor)
    CUSTOMERS_JSON_PATH = "data/customers.json"
    with open(CUSTOMERS_JSON_PATH, "r") as f:
        customers = json.load(f)
    for c in customers:
        if str(c["id"]) == "12":
            c["last_service_date"] = "2025-11-21"
            c["service_due_date"] = "2026-05-23"
            c["service_status"] = "idle"
            break
    with open(CUSTOMERS_JSON_PATH, "w") as f:
        json.dump(customers, f, indent=4)
        
    test = FlowTester(
        name=name,
        customer_id="12",
        flow_type="booking",
        language=language,
        phone="+919881012763",
        turns=turns
    )
    return test.run()

print("🚀 RUNNING COMPREHENSIVE DATE NEGATION TEST SUITE...\n")

# Scenario 1: Correct spelling "actually not on thursday"
s1_passed = run_scenario(
    name="Scenario 1: Weekday Negation (Thursday)",
    turns=["speaking", "yes", "28th may", "actually not on thursday", "2 PM", "45000", "general checkup", "no"],
    language="1"
)

# Scenario 2: Misspelling "actually not on thrusday"
s2_passed = run_scenario(
    name="Scenario 2: Weekday Negation Misspelled (Thrusday)",
    turns=["speaking", "yes", "28th may", "actually not on thrusday", "2 PM", "45000", "general checkup", "no"],
    language="1"
)

# Scenario 3: Date number negation "not on 28th"
s3_passed = run_scenario(
    name="Scenario 3: Date Number Negation (28th)",
    turns=["speaking", "yes", "28th may", "not on 28th", "2 PM", "45000", "general checkup", "no"],
    language="1"
)

# Scenario 4: Hindi/Hinglish flow from User Report
s4_passed = run_scenario(
    name="Scenario 4: Hindi Weekday Negation (Kabir Kapoor)",
    turns=["haan", "theeke book kijiye", "28th may ke liye book kijiye", "actually not on thursday", "2 PM", "45000", "general checkup", "no"],
    language="2" # Hindi
)

print("=" * 70)
print("                    FINAL REPORT")
print("=" * 70)
print(f"Scenario 1 (Thursday): {'PASS' if s1_passed else 'FAIL'}")
print(f"Scenario 2 (Thrusday): {'PASS' if s2_passed else 'FAIL'}")
print(f"Scenario 3 (28th):     {'PASS' if s3_passed else 'FAIL'}")
print(f"Scenario 4 (Hindi):    {'PASS' if s4_passed else 'FAIL'}")
print("=" * 70)
