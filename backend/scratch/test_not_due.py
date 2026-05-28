import requests
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8000"

def run_test():
    # Vikash's phone number: +919881012774
    payload = {
        "CallSid": "TEST_NOT_DUE_123",
        "From": "+919881012774",
        "Direction": "inbound"
    }
    
    url = f"{BASE_URL}/voice?flow_type=booking"
    
    # 1. Start Call
    res = requests.post(url, data=payload)
    print("Greeting:")
    print(res.text)
    
    # Follow redirect to language selection
    root = ET.fromstring(res.text)
    redirect = root.find('.//{*}Redirect')
    if redirect is not None:
        url = BASE_URL + redirect.text
        res = requests.post(url, data=payload)
        print("Language Selection Greeting:")
        print(res.text)
        
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    action = gather.get('action')
    url = BASE_URL + action
    
    # Select Hindi (2)
    payload["Digits"] = "2"
    res = requests.post(url, data=payload)
    print("Language Callback Redirect:")
    print(res.text)
    
    # Follow redirect
    redirect = ET.fromstring(res.text).find('.//{*}Redirect')
    url = BASE_URL + redirect.text
    res = requests.post(url, data=payload)
    print("Main Greeting after language selection:")
    print(res.text)
    
    # Reply "haan" (yes, I am Vikash)
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    action = gather.get('action')
    url = BASE_URL + action
    payload["SpeechResult"] = "haan"
    
    res = requests.post(url, data=payload)
    print("Response after confirming identity:")
    print(res.text)

if __name__ == "__main__":
    run_test()
