import requests

# Use your local URL or Ngrok URL
URL = "http://localhost:8000/voice"

def test_inbound(phone_number, description):
    print(f"\n--- Testing Inbound: {description} ({phone_number}) ---")
    payload = {
        "CallSid": f"TEST_CALL_{phone_number[-4:]}",
        "From": phone_number 
    }
    response = requests.post(URL, data=payload)
    print(f"Status Code: {response.status_code}")
    print("Response TwiML:")
    print(response.text)

if __name__ == "__main__":
    # Test 1: Known Customer (Sanjana)
    test_inbound("+919881012767", "Known Customer")
    
    # Test 2: Unknown Caller
    test_inbound("+910000000000", "Unknown Caller")
