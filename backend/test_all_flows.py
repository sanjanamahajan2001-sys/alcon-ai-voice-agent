import requests
import xml.etree.ElementTree as ET
import urllib.parse
import json
import time
import sys

import os
BASE_URL = "http://localhost:8000"
base_dir = os.path.dirname(os.path.abspath(__file__))
CUSTOMERS_JSON_PATH = os.path.join(base_dir, "data", "customers.json")

def reset_customer_db():
    """Resets key customer states in customers.json to make them eligible for testing."""
    print("🔄 Resetting database state in customers.json...")
    try:
        with open(CUSTOMERS_JSON_PATH, "r") as f:
            customers = json.load(f)
            
        for c in customers:
            c_id = str(c["id"])
            if c_id == "1": # Sanjana (Hindi Service Booking)
                c["last_service_date"] = "2025-11-15"
                c["service_due_date"] = "2026-05-15"
                c["service_status"] = "idle"
                c["notes"] = ""
            elif c_id == "2": # Anika (English Service Booking)
                c["last_service_date"] = "2025-05-10"
                c["service_due_date"] = "2026-05-22"
                c["service_status"] = "idle"
                c["notes"] = ""
            elif c_id == "10": # Aarav Mehta (English Pre-Sales Inbound)
                c["campaign_status"] = "synced"
            elif c_id == "11": # Diya Sharma (Hindi Pre-Sales Inbound)
                c["campaign_status"] = "synced"
            elif c_id == "14": # Rohan Deshmukh (English Pre-Sales Upgrade)
                c["service_status"] = "idle"
            elif c_id == "15": # Pooja Patil (Hindi Pre-Sales Upgrade)
                c["service_status"] = "idle"
            elif c_id == "16": # Dev Joshi (English Receptionist)
                c["last_service_date"] = "2025-11-15"
                c["service_status"] = "idle"
            elif c_id == "17": # Sanya Malhotra (Hindi Receptionist)
                c["service_status"] = "idle"
            elif c_id == "18": # Manish Pandey (English Feedback)
                c["service_status"] = "in-progress"
                c["workshop_update_eligible"] = True
                c["workshop_stage"] = "Washing & Cleaning"
            elif c_id == "19": # Kiran Shah (Hindi Feedback)
                c["service_status"] = "in-progress"
                c["workshop_update_eligible"] = True
                c["workshop_stage"] = "Part Allocation"
                
        with open(CUSTOMERS_JSON_PATH, "w") as f:
            json.dump(customers, f, indent=4)
        print("✅ Database reset completed successfully.\n")
    except Exception as e:
        print(f"❌ Failed to reset database: {e}\n")

class FlowTester:
    def __init__(self, name, customer_id, flow_type, language, phone, turns):
        self.name = name
        self.customer_id = customer_id
        self.flow_type = flow_type
        self.language = language # "1" for English, "2" for Hindi
        self.phone = phone
        self.turns = turns
        self.logs = []
        self.passed = True
        self.error_message = ""

    def run(self):
        print("=" * 70)
        print(f"RUNNING TEST: {self.name}")
        print(f"Flow: {self.flow_type} | Language: {'Hindi' if self.language == '2' else 'English'} | Customer ID: {self.customer_id}")
        print("=" * 70)

        call_sid = f"TEST_CALL_{self.flow_type}_{self.customer_id}_{int(time.time())}"
        
        # 1. Start Turn: hit /voice
        current_url = f"{BASE_URL}/voice?flow_type={self.flow_type}&customer_id={self.customer_id}"
        payload = {
            "CallSid": call_sid,
            "From": self.phone,
            "Direction": "inbound"
        }
        
        # Turn counter
        turn_idx = 0
        
        try:
            # First response must be language redirect
            res = requests.post(current_url, data=payload)
            if res.status_code != 200:
                self.passed = False
                self.error_message = f"Failed to connect to /voice, status: {res.status_code}"
                return False
                
            root = ET.fromstring(res.text)
            
            # Verify it redirects or prompts for language
            redirect = root.find('.//{*}Redirect')
            gather = root.find('.//{*}Gather')
            
            if redirect is not None and "language" in redirect.text:
                current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
                res = requests.post(current_url, data=payload)
                root = ET.fromstring(res.text)
                gather = root.find('.//{*}Gather')

            # Select language
            if gather is not None and "language" in gather.get('action', ''):
                action = gather.get('action')
                lang_url = BASE_URL + action if action.startswith('/') else action
                # Send language selection digit
                payload["Digits"] = self.language
                res = requests.post(lang_url, data=payload)
                root = ET.fromstring(res.text)
                
                # Check for redirection to /voice with language param
                redirect = root.find('.//{*}Redirect')
                if redirect is not None:
                    current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
                    # Clear digits
                    payload.pop("Digits", None)
                    res = requests.post(current_url, data=payload)
                    root = ET.fromstring(res.text)

            # Now we are in the actual conversation loop!
            while True:
                # 1. Read AI responses
                ai_says = []
                for say in root.findall('.//{*}Say'):
                    if say.text:
                        ai_says.append(say.text)
                
                ai_text = "\n".join(ai_says)
                self.logs.append(f"AI: {ai_text}")
                print(f"\033[94m[AI]:\033[0m {ai_text}")
                
                # Check if call is hung up
                if root.find('.//{*}Hangup') is not None:
                    self.logs.append("Call Ended (Hangup)")
                    print("\033[90m--- Call Ended (Hangup) ---\033[0m")
                    break
                    
                dial = root.find('.//{*}Dial')
                if dial is not None:
                    self.logs.append(f"Call Transferred: {dial.text}")
                    print(f"\033[92m--- Call Transferred to {dial.text} ---\033[0m")
                    break
                    
                gather = root.find('.//{*}Gather')
                redirect = root.find('.//{*}Redirect')
                
                # If there are no more turns in our test case, but AI is expecting input
                if turn_idx >= len(self.turns):
                    if gather is not None or redirect is not None:
                        self.passed = False
                        self.error_message = "Conversation expected more turns, but script ran out of test inputs."
                        print(f"\033[91m❌ [FAIL] Missing input at Turn {turn_idx}\033[0m")
                        break
                    else:
                        break
                        
                # 2. Provide User Input
                user_msg = self.turns[turn_idx]
                turn_idx += 1
                self.logs.append(f"YOU: {user_msg}")
                print(f"\033[92m[YOU]:\033[0m {user_msg}")
                
                # Update payload
                payload["SpeechResult"] = user_msg
                payload["Digits"] = user_msg
                
                if gather is not None:
                    action = gather.get('action')
                    current_url = BASE_URL + action if action.startswith('/') else action
                elif redirect is not None:
                    current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
                else:
                    # No gather or redirect, but we have inputs left
                    self.passed = False
                    self.error_message = f"TwiML did not provide Gather or Redirect, cannot send input: '{user_msg}'"
                    print(f"\033[91m❌ [FAIL] No input action available for: {user_msg}\033[0m")
                    break
                    
                # Post next turn
                res = requests.post(current_url, data=payload)
                if res.status_code != 200:
                    self.passed = False
                    self.error_message = f"Server returned status {res.status_code} at turn {turn_idx}"
                    print(f"\033[91m❌ [FAIL] HTTP {res.status_code}\033[0m")
                    break
                root = ET.fromstring(res.text)

            # Extra assertion on output
            self.post_run_verifications()
            
        except Exception as e:
            self.passed = False
            self.error_message = f"Exception: {str(e)}"
            print(f"\033[91m❌ [EXCEPTION] {str(e)}\033[0m")
            
        print("\n")
        return self.passed

    def post_run_verifications(self):
        """Perform custom assertions on conversation history/outcome depending on flow."""
        ai_responses = [log[4:] for log in self.logs if log.startswith("AI: ")]
        
        # Check translation bug: if Hindi flow, final confirmation shouldn't contain English phrases
        if self.language == "2": # Hindi
            for response in ai_responses:
                # "Your service is confirmed" or "50-point safety check" shouldn't be in English
                if "Your service is confirmed" in response or "peak performance" in response:
                    self.passed = False
                    self.error_message = "Hindi translation fallback bug detected! Final booking confirmation printed in English."
                    print("\033[91m❌ [FAIL] English confirmation sentence leak in Hindi flow!\033[0m")
                    return
        
        # Booking checks
        if self.flow_type == "booking":
            last_resp = ai_responses[-1] if ai_responses else ""
            if self.language == "2":
                if "पुष्टि" not in last_resp and "अद्भुत" not in last_resp:
                    self.passed = False
                    self.error_message = "Service Booking confirmation node not reached or translated."
                    print("\033[91m❌ [FAIL] Service booking confirmation node not reached in Hindi.\033[0m")
            else:
                if "confirmed" not in last_resp.lower():
                    self.passed = False
                    self.error_message = "Service Booking confirmation node not reached."
                    print("\033[91m❌ [FAIL] Service booking confirmation node not reached in English.\033[0m")


def run_all_tests():
    print("=" * 80)
    print("               ALCON VOICE ENGINE AUTOMATED TEST SUITE")
    print("=" * 80)
    
    # 1. Database Reset
    reset_customer_db()
    
    # 2. Defining test cases
    test_cases = [
        # --- FLOW 1: Service Booking Inbound ---
        FlowTester(
            name="1. Service Booking Inbound - English (Anika)",
            customer_id="2",
            flow_type="booking",
            language="1", # English
            phone="+919834681919",
            turns=[
                "yes this is Anika",
                "sure please book it",
                "28th May at 10 AM",
                "45000 kilometers",
                "ac is not cooling properly",
                "yes please send pick up"
            ]
        ),
        FlowTester(
            name="2. Service Booking Inbound - Hindi (Sanjana) [Translation Bug Verification]",
            customer_id="1",
            flow_type="booking",
            language="2", # Hindi
            phone="+919881012767",
            turns=[
                "haan main sanjana bol rahi hoon",
                "ji please book kar dijiye",
                "25th May ko booking kar do",
                "pachas hazaar", # Testing Hinglish verbal number parsing
                "brake pads se aawaz aa rahi hai", # Concern
                "nahi drop kar dungi khud" # Self drop
            ]
        ),
        
        # --- FLOW 2: Pre-Sales Enquiry Inbound ---
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
                "call me back tomorrow at 5pm" # schedules callback
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
                "driving kar raha hoon baad me call karo" # Schedules callback via Hinglish busy logic!
            ]
        ),
        
        # --- FLOW 3: Pre-Sales Upgrade Outbound ---
        FlowTester(
            name="5. Pre-Sales Upgrade Campaign - English (Rohan)",
            customer_id="14",
            flow_type="pre_sales_upgrade",
            language="1",
            phone="+919881012765",
            turns=[
                "yes Rohan speaking",
                "yes i am interested in exchange offer",
                "what colors are available?",
                "what is the waiting period?",
                "call me back next Monday morning"
            ]
        ),
        FlowTester(
            name="6. Pre-Sales Upgrade Campaign - Hindi (Pooja)",
            customer_id="15",
            flow_type="pre_sales_upgrade",
            language="2",
            phone="+919881012766",
            turns=[
                "haan pooja bol rahi hoon",
                "haan exchange scheme ke bare me bataiye",
                "creta me kaunse colors aate hai?",
                "mileage kitna deti hai?",
                "kal dopahar 2 baje baat karte hai" # Callback scheduled
            ]
        ),
        
        # --- FLOW 4: Receptionist Inbound ---
        FlowTester(
            name="7. Receptionist Inbound to Booking Path - English (Dev Joshi)",
            customer_id="16",
            flow_type="reception",
            language="1",
            phone="+919881012768",
            turns=[
                "hello",
                "i need to book a service for my car", # receptionist redirects to booking
                "yes please", # confirm name Dev Joshi
                "29th may please",
                "35000",
                "oil leakage issue",
                "no thanks"
            ]
        ),
        FlowTester(
            name="8. Receptionist Inbound to Sales Path - Hindi (Sanya Malhotra)",
            customer_id="17",
            flow_type="reception",
            language="2",
            phone="+919881012769",
            turns=[
                "namaste",
                "mujhe nayi gaadi kharidni hai", # receptionist redirects to sales
                "haan main sanya hoon",
                "i10 car buy karni hai details batao",
                "sure call me back tomorrow"
            ]
        ),
        
        # --- FLOW 5: Post-Service Feedback ---
        FlowTester(
            name="9. Post-Service Feedback - English (Manish Pandey) [Happy Path]",
            customer_id="18",
            flow_type="feedback_initial",
            language="1",
            phone="+919881012770",
            turns=[
                "yes this is Manish",
                "yes all jobs were done perfectly", # satisfaction_check = true
                "nine", # rate advisor
                "ten", # rate pickup
                "nine", # rate cleanliness
                "ten", # rate overall
                "everything was awesome thanks"
            ]
        ),
        FlowTester(
            name="10. Post-Service Feedback - Hindi (Kiran Shah) [Escalation Trigger Path]",
            customer_id="19",
            flow_type="feedback_initial",
            language="2",
            phone="+919881012771",
            turns=[
                "haan main kiran bol raha hoon",
                "nahi main satisfied nahi hoon service se", # triggers escalation flow!
                "haan bilkul call kijiye team se", # confirms escalation transfer/follow up
                "panch", # rate advisor (triggers reason ask)
                "braking was still not proper", # advisor reason
                "six", # rate pickup
                "valet was late", # pickup reason
                "seven", # rate cleanliness
                "water marks on windshield", # cleanliness reason
                "five", # overall rating
                "highly disappointed please improve" # overall reason
            ]
        )
    ]
    
    # 3. Execution and reporting
    passed_count = 0
    total_count = len(test_cases)
    results = []
    
    for test in test_cases:
        success = test.run()
        if success:
            passed_count += 1
        results.append((test.name, success, test.error_message))
        
    print("=" * 80)
    print("                      AUTOMATED TESTING REPORT DASHBOARD")
    print("=" * 80)
    for name, success, err in results:
        status = "\033[92m[PASS]\033[0m" if success else "\033[91m[FAIL]\033[0m"
        err_str = f" - Error: {err}" if not success else ""
        print(f"{status} {name}{err_str}")
        
    print("=" * 80)
    rate = (passed_count / total_count) * 100
    print(f"Summary: {passed_count}/{total_count} Passed ({rate:.1f}%)")
    print("=" * 80 + "\n")
    
    # Return code for pipeline integration
    if passed_count == total_count:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_all_tests()
