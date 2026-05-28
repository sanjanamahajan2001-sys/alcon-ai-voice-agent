import httpx
import sys
import json

def trigger_demo_call(customer_id, phone_number):
    url = f"http://localhost:8000/make-call/{customer_id}"
    payload = {"to_number": phone_number}
    
    print(f"--- Alcon Hyundai AI Demo ---")
    print(f"Triggering call for Customer ID: {customer_id}")
    print(f"To Number: {phone_number}")
    print(f"Connecting to backend: {url}")
    
    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=10.0)
            
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Call SID: {result.get('call_sid')}")
            print(f"Watch your phone! Supriya will call you shortly.")
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error connecting to backend: {str(e)}")
        print(f"Make sure your FastAPI server is running on port 8000.")

if __name__ == "__main__":
    # Default values
    cust_id = "1"
    phone = "+919881012767"
    
    if len(sys.argv) > 1:
        cust_id = sys.argv[1]
    if len(sys.argv) > 2:
        phone = sys.argv[2]
        if not phone.startswith('+'):
            phone = '+91' + phone
            
    trigger_demo_call(cust_id, phone)
