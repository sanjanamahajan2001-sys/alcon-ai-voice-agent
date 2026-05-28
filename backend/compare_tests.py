import sys
import json
import requests
import xml.etree.ElementTree as ET
import urllib.parse
from test_all_flows import FlowTester, reset_customer_db

reset_customer_db()

# Run Test 3 (Aarav) and Test 4 (Diya)
for t in [
    FlowTester(
        name="3. Pre-Sales Enquiry Inbound - English (Aarav)",
        customer_id="10",
        flow_type="pre_sales",
        language="1",
        phone="+919881012761",
        turns=[
            "yes this is Aarav",
            "i am looking to buy a new SUV like Venue",
            "what EMI options do you have?",
            "what are the safety features?",
            "call me back tomorrow at 5pm"
        ]
    ),
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
    )
]:
    print(f"\n--- RUNNING {t.name} ---")
    t.run()
