import requests
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8000"

def run_simulation():
    call_sid = "SIM_TEST_RECEPTION_123"
    from_phone = "+919881012767"
    
    print("--- Step 1: Call Init ---")
    res = requests.post(f"{BASE_URL}/voice?flow_type=reception", data={
        "CallSid": call_sid,
        "From": from_phone,
        "Direction": "inbound"
    })
    print("Status:", res.status_code)
    print("Response:", res.text)
    
    # Follow redirect if present
    root = ET.fromstring(res.text)
    redirect = root.find('.//{*}Redirect')
    if redirect is not None:
        redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
        print("Redirecting to:", redirect_url)
        res = requests.post(redirect_url, data={
            "CallSid": call_sid,
            "From": from_phone,
            "Direction": "inbound"
        })
        print("Redirected Response:", res.text)
        root = ET.fromstring(res.text)
    
    # Extract action URL from gather
    gather = root.find('.//{*}Gather')
    action_url = BASE_URL + gather.get('action')
    print("Gather Action:", action_url)
    
    print("\n--- Step 2: Press 2 (Hindi) ---")
    res = requests.post(action_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "Digits": "2"
    })
    print("Status:", res.status_code)
    print("Response:", res.text)
    
    # Follow redirect
    redirect = ET.fromstring(res.text).find('.//{*}Redirect')
    redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
    print("Redirect to:", redirect_url)
    
    print("\n--- Step 3: Fetch Redirected Voice Node (Greeting in Hindi) ---")
    res = requests.post(redirect_url, data={
        "CallSid": call_sid,
        "From": from_phone
    })
    print("Status:", res.status_code)
    print("Response:", res.text)
    
    # Next process step
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    action_url = BASE_URL + gather.get('action')
    print("Gather Action:", action_url)
    
    print("\n--- Step 4: Say 'mujhe nayi gaadi ke baare mein jaana hai' ---")
    res = requests.post(action_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "SpeechResult": "mujhe nayi gaadi ke baare mein jaana hai"
    })
    print("Status:", res.status_code)
    print("Response:", res.text)
    
    # Next process step
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    action_url = BASE_URL + gather.get('action')
    print("Gather Action:", action_url)
    
    print("\n--- Step 5: Say 'creta dekh raha tha' ---")
    res = requests.post(action_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "SpeechResult": "creta dekh raha tha"
    })
    print("Status:", res.status_code)
    print("Response:", res.text)
    
    # Next process step
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    if gather is not None:
        action_url = BASE_URL + gather.get('action')
        print("Gather Action:", action_url)
        
        print("\n--- Step 6: Say 'mujhe venue ki bhi jaankari chahiye' ---")
        res = requests.post(action_url, data={
            "CallSid": call_sid,
            "From": from_phone,
            "SpeechResult": "mujhe venue ki bhi jaankari chahiye"
        })
        print("Status:", res.status_code)
        print("Response:", res.text)

if __name__ == "__main__":
    run_simulation()
