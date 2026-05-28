import requests
import xml.etree.ElementTree as ET
import urllib.parse
import sys

# Configuration
BASE_URL = "http://localhost:8000"
START_URL = f"{BASE_URL}/voice"

def simulate_call(from_phone="+919881012767", flow_type="reception"):
    print(f"\n--- Starting Call Simulation (From: {from_phone}, Flow: {flow_type}) ---")
    
    current_url = START_URL
    payload = {
        "CallSid": "SIM_CALL_12345",
        "From": from_phone,
        "Direction": "inbound"
    }
    
    # Optional flow_type for entry point
    if flow_type:
        current_url += f"?flow_type={flow_type}"

    while True:
        try:
            response = requests.post(current_url, data=payload)
            if response.status_code != 200:
                print(f"Error: Server returned {response.status_code}")
                break
            
            twiml = response.text
            root = ET.fromstring(twiml)
            
            # 1. Process <Say> tags (recursively)
            for say in root.findall('.//{*}Say'):
                if say.text:
                    print(f"\n[AI]: {say.text}")
            
            # 2. Check for <Hangup> (recursively)
            if root.find('.//{*}Hangup') is not None:
                print("\n--- Call Ended (Hangup) ---")
                break
                
            # 3. Check for <Dial> (recursively)
            dial = root.find('.//{*}Dial')
            if dial is not None:
                print(f"\n--- Call Transferred to: {dial.text} ---")
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
    print("Alcon Voice Agent Simulation Tool")
    print("1. Inbound Reception (Known Customer)")
    print("2. Inbound Reception (Unknown Caller)")
    print("3. Outbound Pre-Sales")
    print("4. Outbound 15-Day Post-Service Feedback (Template-Driven)")
    print("5. Outbound Service Booking (Template-Driven)")
    print("6. Outbound 3rd-Day Post-Service Feedback (Template-Driven)")
    print("7. Outbound Pick & Drop Coordination (Template-Driven)")
    print("8. Outbound Workshop Update (Template-Driven)")
    print("9. Outbound Ready for Delivery (Template-Driven)")
    
    choice = input("Select test case (1-9): ")
    
    if choice == "1":
        simulate_call(from_phone="+919881012767", flow_type="reception")
    elif choice == "2":
        simulate_call(from_phone="+910000000000", flow_type="reception")
    elif choice == "3":
        simulate_call(from_phone="+919881012767", flow_type="pre_sales")
    elif choice == "4":
        simulate_call(from_phone="+919881012767", flow_type="feedback_15day_v2")
    elif choice == "5":
        simulate_call(from_phone="+919881012767", flow_type="booking")
    elif choice == "6":
        simulate_call(from_phone="+919881012767", flow_type="feedback_3rd_day")
    elif choice == "7":
        simulate_call(from_phone="+919881012766", flow_type="pd_pickup_coordination")
    elif choice == "8":
        simulate_call(from_phone="+919881012770", flow_type="pd_workshop_update")
    elif choice == "9":
        simulate_call(from_phone="+919881012774", flow_type="pd_ready")
    else:
        print("Invalid choice.")
