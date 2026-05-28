import requests
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8000"

def debug_flow():
    call_sid = "DEBUG_CALL_12345"
    from_phone = "+919881012767" # Customer 12's phone
    
    # 1. Start Call
    res = requests.post(f"{BASE_URL}/voice?flow_type=pre_sales_upgrade&customer_id=12", data={
        "CallSid": call_sid,
        "From": from_phone,
        "Direction": "inbound"
    })
    print("--- 1. Voice Response ---")
    print(res.text)
    
    root = ET.fromstring(res.text)
    redirect = root.find('.//{*}Redirect')
    if redirect is not None:
        redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
        res = requests.post(redirect_url, data={
            "CallSid": call_sid,
            "From": from_phone
        })
        print("--- 2. Redirected Voice Response ---")
        print(res.text)
        root = ET.fromstring(res.text)
        
    gather = root.find('.//{*}Gather')
    if gather is not None:
        action_url = BASE_URL + gather.get('action')
        # Select language (Hindi - 2)
        res = requests.post(action_url, data={
            "CallSid": call_sid,
            "From": from_phone,
            "Digits": "2"
        })
        print("--- 3. Language Callback Response ---")
        print(res.text)
        
        redirect = ET.fromstring(res.text).find('.//{*}Redirect')
        if redirect is not None:
            redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
            res = requests.post(redirect_url, data={
                "CallSid": call_sid,
                "From": from_phone
            })
            print("--- 4. Main Greeting Response ---")
            print(res.text)
            
            # Post the FAQ query
            gather = ET.fromstring(res.text).find('.//{*}Gather')
            if gather is not None:
                action_url = BASE_URL + gather.get('action')
                res = requests.post(action_url, data={
                    "CallSid": call_sid,
                    "From": from_phone,
                    "SpeechResult": "aapko mera number kaha se mila?"
                })
                print("--- 5. Process Response for FAQ ---")
                print(res.text)
            else:
                print("Main greeting gather not found!")
        else:
            print("Language redirect not found!")
    else:
        print("Language gather not found!")

if __name__ == "__main__":
    debug_flow()
