import requests
url = "http://localhost:8000/voice?flow_type=reception"
payload = {
    "CallSid": "SIM_CALL_TEST_1",
    "From": "+910000000000",
    "Direction": "inbound"
}
try:
    response = requests.post(url, data=payload)
    print("Status:", response.status_code)
    print("Text:", response.text)
except Exception as e:
    print("Error:", e)
