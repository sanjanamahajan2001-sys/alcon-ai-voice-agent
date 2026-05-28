import requests
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8000"
START_URL = f"{BASE_URL}/voice?flow_type=pd_workshop_update"

payload = {
    "CallSid": "SIM_CALL_123456",
    "From": "+919881012770",
    "Direction": "inbound"
}

# 1. Start Call
print("--> Posting to /voice with From=+919881012770 and flow_type=pd_workshop_update")
res = requests.post(START_URL, data=payload)
print(f"Status: {res.status_code}")
root = ET.fromstring(res.text)

# Find redirect/say
for say in root.findall('.//{*}Say'):
    print(f"AI say: {say.text}")

redirect = root.find('.//{*}Redirect')
if redirect is not None:
    current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
    print(f"Redirecting to: {current_url}")
    
    # 2. Select Language 2 (Hindi)
    payload["Digits"] = "2"
    res = requests.post(current_url, data=payload)
    print(f"Status: {res.status_code}")
    root = ET.fromstring(res.text)
    
    # Find redirect again
    redirect = root.find('.//{*}Redirect')
    if redirect is not None:
        current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
        print(f"Redirecting to: {current_url}")
        payload.pop("Digits", None)
        
        # 3. Follow redirect to /voice with language param
        res = requests.post(current_url, data=payload)
        print(f"Status: {res.status_code}")
        root = ET.fromstring(res.text)
        
        for say in root.findall('.//{*}Say'):
            print(f"AI say: {say.text}")
            
        redirect = root.find('.//{*}Redirect')
        if redirect is not None:
            current_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
            print(f"Redirecting to: {current_url}")
            res = requests.post(current_url, data=payload)
            print(f"Status: {res.status_code}")
            root = ET.fromstring(res.text)
            for say in root.findall('.//{*}Say'):
                print(f"AI say: {say.text}")
            gather = root.find('.//{*}Gather')
            if gather is not None:
                print(f"Gather Action: {gather.get('action')}")
