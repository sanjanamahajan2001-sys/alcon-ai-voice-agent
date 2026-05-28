import requests
import xml.etree.ElementTree as ET

BASE_URL = "http://localhost:8000"
call_sid = "VERBOSE_TEST_CALL_7"
from_phone = "+919881012767"

print("Step 1: Init call")
res = requests.post(f"{BASE_URL}/voice?flow_type=insurance_start", data={
    "CallSid": call_sid,
    "From": from_phone,
    "Direction": "inbound"
})
print("Init Response XML:")
print(res.text)

root = ET.fromstring(res.text)
redirect = root.find('.//{*}Redirect')
if redirect is not None:
    redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
    print("\nFollowing Redirect to Language Selection:")
    res = requests.post(redirect_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "Direction": "inbound"
    })
    print(res.text)
    root = ET.fromstring(res.text)

gather = root.find('.//{*}Gather')
action_url = BASE_URL + gather.get('action')

print("\nStep 2: Select Hindi Language (Digits=2)")
res = requests.post(action_url, data={
    "CallSid": call_sid,
    "From": from_phone,
    "Digits": "2"
})
print(res.text)

redirect = ET.fromstring(res.text).find('.//{*}Redirect')
redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text

print("\nFollowing Redirect to Main Greeting:")
res = requests.post(redirect_url, data={
    "CallSid": call_sid,
    "From": from_phone
})
print(res.text)

gather = ET.fromstring(res.text).find('.//{*}Gather')
action_url = BASE_URL + gather.get('action')

print("\nStep 3: Post the query 'थोड़ा कम करो ना प्रीमियम।' to action URL:", action_url)
res = requests.post(action_url, data={
    "CallSid": call_sid,
    "From": from_phone,
    "SpeechResult": "थोड़ा कम करो ना प्रीमियम।"
})
print("Final Response XML:")
print(res.text)
