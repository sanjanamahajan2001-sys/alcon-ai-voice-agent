import requests
import xml.etree.ElementTree as ET
import urllib.parse
import sys
import time

# Configuration
BASE_URL = "http://localhost:8000"
START_URL = f"{BASE_URL}/voice"

def simulate_call(from_phone="+919881012767", flow_type="booking", customer_id="1", **kwargs):
    print(f"\n--- Starting Call Simulation (Customer ID: {customer_id}, Flow: {flow_type}) ---")
    
    # Construct extra params string
    extra_params = ""
    for k, v in kwargs.items():
        extra_params += f"&{k}={urllib.parse.quote(str(v))}"

    current_url = f"{START_URL}?flow_type={flow_type}&customer_id={customer_id}{extra_params}"
    payload = {
        "CallSid": "SIM_V2_CALL_" + str(hash(customer_id))[-6:],
        "From": from_phone,
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
            
            # 1. Process <Say> tags (recursively find all, including nested inside <Gather>)
            for say in root.findall('.//{*}Say'):
                if say.text:
                    print("\n[AI is thinking...]")
                    time.sleep(1.2) # Realistic processing delay
                    print(f"[AI]: {say.text}")
            
            # 2. Check for <Hangup> (recursively)
            if root.find('.//{*}Hangup') is not None:
                print("\n--- Call Ended (Hangup) ---")
                break
                
            # 3. Check for <Dial> (recursively)
            dial = root.find('.//{*}Dial')
            if dial is not None:
                print(f"\n--- Call Transferred: {dial.text} ---")
                break
                
            # 4. Check for <Gather> (recursively)
            gather = root.find('.//{*}Gather')
            if gather is not None:
                action = gather.get('action')
                user_input = input("\n[YOU]: ")
                
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
                
            # If nothing else, stop
            print("\n--- Call Ended (No further instructions) ---")
            break

        except Exception as e:
            print(f"Error during simulation: {str(e)}")
            break

if __name__ == "__main__":
    print("Alcon Multi-Flow Simulation Tool")
    print("--------------------------------")
    
    try:
        customers = requests.get(f"{BASE_URL}/customers").json()
        
        print("\nAvailable Flows:")
        flows = [
            ("booking", "Service Booking (Inbound)"),
            ("pre_sales", "Pre-Sales Enquiry (Inbound)"),
            ("pre_sales_upgrade", "Pre-Sales Upgrade Campaign (Outbound)"),
            ("reception", "Receptionist (Inbound)"),
            ("feedback_initial", "Post-Service Feedback")
        ]
        for idx, (f_id, f_name) in enumerate(flows):
            print(f"{idx+1}. {f_name}")
            
        flow_choice = input(f"\nSelect flow (1-{len(flows)}): ")
        if not flow_choice: flow_choice = "1"
        flow_type = flows[int(flow_choice)-1][0]

        print("\nAvailable Customers:")
        for idx, c in enumerate(customers):
            print(f"{idx+1}. {c['name']} ({c['phone']}) - {c['car_model']}")
            
        choice = input(f"\nSelect customer (1-{len(customers)} or Enter for 1): ")
        if not choice:
            customer_id = customers[0]['id']
            phone = customers[0]['phone']
        else:
            customer_id = customers[int(choice)-1]['id']
            phone = customers[int(choice)-1]['phone']
            
        simulate_call(from_phone=phone, customer_id=customer_id, flow_type=flow_type)
        
    except Exception as e:
        print(f"Error connecting to backend: {str(e)}")
