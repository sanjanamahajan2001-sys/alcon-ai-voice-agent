import sys
import json
from test_all_flows import FlowTester, reset_customer_db

reset_customer_db()

test_cases = [
    # Test 4
    FlowTester(
        name="4. Pre-Sales Enquiry Inbound - Hindi (Diya)",
        customer_id="11",
        flow_type="pre_sales",
        language="2",
        phone="+919881012762",
        turns=[
            "haan main diya bol rahi hoon",
            "haan gaadi purchase karni hai creta ka benefits batao",
            "EMI options aur price kitna hai?",
            "safe hai kya airbags hai?",
            "driving kar raha hoon baad me call karo"
        ]
    ),
    # Test 8
    FlowTester(
        name="8. Receptionist Inbound to Sales Path - Hindi (Sanya Malhotra)",
        customer_id="17",
        flow_type="reception",
        language="2",
        phone="+919881012769",
        turns=[
            "namaste",
            "mujhe nayi gaadi kharidni hai",
            "haan main sanya hoon",
            "i10 car buy karni hai details batao",
            "sure call me back tomorrow"
        ]
    ),
    # Test 10
    FlowTester(
        name="10. Post-Service Feedback - Hindi (Kiran Shah) [Escalation Trigger Path]",
        customer_id="19",
        flow_type="feedback_initial",
        language="2",
        phone="+919881012771",
        turns=[
            "haan main kiran bol raha hoon",
            "nahi main satisfied nahi hoon service se",
            "haan bilkul call kijiye team se",
            "panch",
            "braking was still not proper",
            "six",
            "valet was late",
            "seven",
            "water marks on windshield",
            "five",
            "highly disappointed please improve"
        ]
    )
]

for t in test_cases:
    t.run()
