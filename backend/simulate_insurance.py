import requests
import json
import time
import re
import xml.etree.ElementTree as ET
import urllib.parse
import sys

# Configuration
BASE_URL = "http://localhost:8000"
START_URL = f"{BASE_URL}/voice"

def simulate_insurance_call(customer_id, phone, stage=1):
    print(f"\n--- Starting Insurance Simulation (Stage: {stage}) ---")
    
    current_url = f"{START_URL}?flow_type=insurance_start&customer_id={customer_id}&stage={stage}"
    payload = {
        "CallSid": f"SIM_INS_{stage}_" + str(hash(customer_id))[-6:],
        "From": phone,
        "Direction": "inbound"
    }
    
    while True:
        try:
            response = requests.post(current_url, data=payload)
            if response.status_code != 200:
                print(f"Error: Server returned {response.status_code}")
                print(response.text)
                break
            
            twiml = response.text
            root = ET.fromstring(twiml)
            
            # 1. Process <Say> tags (recursively)
            spoke = False
            for say in root.findall('.//{*}Say'):
                if say.text:
                    print(f"\n[AI]: {say.text}")
                    spoke = True
            
            if not spoke and root.find('.//{*}Hangup') is None and root.find('.//{*}Dial') is None:
                 # If AI didn't say anything and didn't hang up/dial, something is wrong
                 print("\n[AI]: (No response/Empty text)")
            
            # 2. Check for <Hangup> (recursively)
            if root.find('.//{*}Hangup') is not None:
                print("\n--- Call Ended (Hangup) ---")
                break
                
            # 3. Check for <Dial> (recursively)
            dial = root.find('.//{*}Dial')
            if dial is not None:
                print(f"\n\033[93m--- Call Transferred to Expert: {dial.text} ---\033[0m")
                print("\n\033[1m[LIVE HUMAN SESSION START]\033[0m")
                print("You are now simulating BOTH sides of the human-user conversation.")
                print("Type 'resume' at any time to hand the call back to the AI.")
                
                import sys, select

                def get_input_with_polling(prompt, call_sid):
                    print(prompt, end="", flush=True)
                    while True:
                        try:
                            # Poll database for status change
                            try:
                                leads_res = requests.get(f"{BASE_URL}/telephony/dashboard/leads")
                                my_lead = next((l for l in leads_res.json() if l['call_sid'] == call_sid), None)
                                if my_lead and my_lead.get('escalation_status') == 'NONE':
                                    return "DASHBOARD_RESUME"
                            except:
                                pass
                            
                            # Check for keyboard input (non-blocking)
                            if select.select([sys.stdin], [], [], 1.0)[0]:
                                return sys.stdin.readline().strip()
                        except KeyboardInterrupt:
                            print("\n\n[SYSTEM] Simulation Terminated by User.")
                            sys.exit(0)

                human_transcript = []
                while True:
                    m_msg = get_input_with_polling("\n[MANAGER]: ", payload['CallSid'])
                    if m_msg == "DASHBOARD_RESUME":
                        print("\n\033[92m[RESUMED] Dashboard 'Resume AI' button was clicked!\033[0m")
                        break
                    if m_msg.lower() == 'resume': 
                        requests.post(f"{BASE_URL}/telephony/resume-ai/{payload['CallSid']}", json={})
                        break
                    requests.post(f"{BASE_URL}/telephony/log-human/{payload['CallSid']}", json={"speaker": "Human", "text": m_msg})
                    human_transcript.append(f"Manager: {m_msg}")
                    
                    u_msg = get_input_with_polling("[USER]: ", payload['CallSid'])
                    if u_msg == "DASHBOARD_RESUME":
                        print("\n\033[92m[RESUMED] Dashboard 'Resume AI' button was clicked!\033[0m")
                        import time
                        time.sleep(0.5) # Wait for DB consistency
                        break
                    if u_msg.lower() == 'resume': 
                        requests.post(f"{BASE_URL}/telephony/resume-ai/{payload['CallSid']}", json={})
                        break
                    requests.post(f"{BASE_URL}/telephony/log-human/{payload['CallSid']}", json={"speaker": "Customer", "text": u_msg})
                    human_transcript.append(f"User: {u_msg}")

                # [NEW] Check if dashboard already provided updates
                lead_data = requests.get(f"{BASE_URL}/telephony/leads/{payload['CallSid']}").json()
                dashboard_data = lead_data.get("pending_updates")
                
                if dashboard_data and dashboard_data != "null" and dashboard_data != "None":
                    print(f"\n\033[92m[DASHBOARD DETECTED] Using staged updates: {dashboard_data}\033[0m")
                else:
                    print("\n\033[1m[MANAGER DASHBOARD SIMULATION]\033[0m")
                    summary_input = input("Enter final summary for AI (or press Enter for auto-summary): ")
                    print("Update Data (Press Enter to skip or type JSON e.g. {'premium': 10620, 'nominee': 'Priya'})")
                    data_input = input("Data Update: ")
                    
                    # Manually trigger the Resume AI endpoint with the summary and data updates
                    print(f"\n[SYSTEM] Triggering AI Resumption...")
                    resume_payload = {"summary": summary_input}
                    if data_input:
                        import ast
                        try:
                            # Safely evaluate string to dict
                            updates = ast.literal_eval(data_input)
                            resume_payload["data_updates"] = updates
                        except:
                            print("\033[91mInvalid JSON/Dict format. Skipping updates.\033[0m")
                    
                    requests.post(f"{BASE_URL}/telephony/resume-ai/{payload['CallSid']}", json=resume_payload)
                
                lead_state = requests.get(f"{BASE_URL}/telephony/leads/{payload['CallSid']}").json()
                disposition = lead_state.get('disposition') or ""
                
                if "REVIEW_REQUIRED" in disposition and "STATUS:SYNCED" not in disposition:
                    print(f"\n[PRODUCTION SIMULATION] Supervisor Sync Required! Please click 'Approve & Sync' on the Dashboard UI.")
                    
                    # Wait for Dashboard Sync
                    import time
                    while True:
                        time.sleep(2)
                        res = requests.get(f"{BASE_URL}/telephony/leads/{payload['CallSid']}")
                        updated_state = res.json()
                        if "STATUS:SYNCED" in updated_state.get('disposition', ''):
                            print(f"[SYNC] Dashboard Approval Detected! Proceeding...")
                            break
                
                # Move simulation to the resume TwiML
                current_url = f"{BASE_URL}/telephony/resume-twiml?call_sid={payload['CallSid']}"
                continue
                
            # 4. Check for <Gather> (recursively)
            gather = root.find('.//{*}Gather')
            if gather is not None:
                action = gather.get('action')
                user_input = input("\n[YOU]: ")
                
                # [NEW] Special handling for testing No Response (Silence)
                if user_input.lower() == "silence":
                    user_input = "" # Empty speech
                
                # Update payload for next step
                payload["SpeechResult"] = user_input
                payload["Digits"] = user_input
                
                # Resolve relative action URL
                if action.startswith('/'):
                    current_url = BASE_URL + action
                else:
                    current_url = action
                continue
            
            # 5. Check for <Redirect> (recursively)
            redirect = root.find('.//{*}Redirect')
            if redirect is not None:
                current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
                continue
            
            break

        except Exception as e:
            print(f"Error during simulation: {str(e)}")
            break
            
    # [NEW] Trigger finalization via status callback AFTER the loop ends
    try:
        requests.post(f"{BASE_URL}/status-callback", data={
            "CallSid": payload["CallSid"],
            "CallStatus": "completed",
            "From": phone
        })
    except:
        pass
            
        # [NEW] Poll backend logs for reasoning trace / interest level
        try:
            log_res = requests.get(f"{BASE_URL}/telephony/logs/{payload['CallSid']}")
            if log_res.status_code == 200:
                log_data = log_res.json()
                if log_data.get("interest_level"):
                    print(f"\033[94m[BACKEND] Interest Level: {log_data['interest_level']}\033[0m")
                if log_data.get("reasoning_trace"):
                    print(f"\033[90m[TRACE] {log_data['reasoning_trace']}\033[0m")
                # Check for outbound hook logs in reasoning trace if we added them there
                # (Alternatively, we can just look for specific outcomes)
                if "interested" in str(log_data.get("reasoning_trace", "")):
                     print(f"\033[92m[OUTBOUND HOOK] Payment link sent via WhatsApp/SMS\033[0m")
        except:
            pass

if __name__ == "__main__":
    print("Alcon Insurance Flow Simulation Tool")
    print("------------------------------------")
    
    try:
        customers = requests.get(f"{BASE_URL}/customers").json()
        
        # Filter for customers with insurance data
        insurance_customers = [c for c in customers if c.get('insurance_expiry_date')]
        
        if not insurance_customers:
            print("No customers found with insurance data in customers.json")
            sys.exit(0)

        print("\nInsurance Testing Stages:")
        stages = [
            ("1", "T-30: Initial Intent Check"),
            ("2", "T-15: Follow-up Reminder"),
            ("3", "T-7: Final Reminder"),
            ("4", "T-1: Urgent Call"),
            ("5", "T+1: Post-Expiry Recovery")
        ]
        for id, name in stages:
            print(f"{id}. {name}")
            
        stage_choice = input("\nSelect Stage (1-5): ")
        if not stage_choice: stage_choice = "1"

        # --- Explain History Simulation ---
        history_map = {
            "1": "Initial Call: No previous interaction.",
            "2": "Follow-up: Customer was 'Interested but Busy' in Call 1.",
            "3": "Final Reminder: Customer has been notified twice; urgency high.",
            "4": "Urgent: Customer has not committed yet; insurance expires tomorrow.",
            "5": "Recovery: Insurance has expired; focus on legal/fine risks."
        }
        print(f"\n[INFO] {history_map.get(stage_choice, '')}")

        print("\nAvailable Customers:")
        for idx, c in enumerate(insurance_customers):
            print(f"{idx+1}. {c['name']} ({c['insurance_provider']}) - Expiry: {c['insurance_expiry_date']}")
            
        choice = input(f"\nSelect customer (1-{len(insurance_customers)}): ")
        if not choice:
            customer = insurance_customers[0]
        else:
            customer = insurance_customers[int(choice)-1]
            
        simulate_insurance_call(customer['id'], customer['phone'], stage=stage_choice)
        
    except Exception as e:
        print(f"Error connecting to backend: {str(e)}")
