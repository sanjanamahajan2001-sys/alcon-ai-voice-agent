import requests
import xml.etree.ElementTree as ET
import sys

BASE_URL = "http://localhost:8000"

VOICE_TEST_CASES = [
    # --- Pre-Sales FAQ cases using pure Devanagari inputs (Telephony ASR simulated) ---
    {
        "id": 1,
        "flow_type": "pre_sales",
        "description": "SUV Segment query with Devanagari full stop (danda)",
        "query": "मुझे एसयूवी सेगमेंट में गाड़ी देखनी है।",
        "expected": ["Creta", "Venue", "SUV"]
    },
    {
        "id": 2,
        "flow_type": "pre_sales",
        "description": "Diesel availability query in Devanagari",
        "query": "डीजल उपलब्ध है क्या",
        "expected": ["पेट्रोल", "डीजल"]
    },
    {
        "id": 3,
        "flow_type": "pre_sales",
        "description": "Waiting period query with future tense 'होगा'",
        "query": "वेटिंग पीरियड कितना होगा?",
        "expected": ["वेटिंग", "सप्ताह"]
    },
    {
        "id": 4,
        "flow_type": "pre_sales",
        "description": "General availability query 'अवेलेबल है क्या'",
        "query": "अवेलेबल है क्या?",
        "expected": ["वेरिएंट", "उपलब्ध"]
    },
    {
        "id": 5,
        "flow_type": "pre_sales",
        "description": "ADAS safety feature query in Devanagari",
        "query": "एडीएएस फीचर है?",
        "expected": ["उन्नत", "एडीएएस"]
    },
    # --- Insurance cases using pure Devanagari inputs ---
    {
        "id": 6,
        "flow_type": "insurance_start",
        "description": "Identity query 'number kaha se mila' in Devanagari",
        "query": "आपको मेरा नंबर कहाँ से मिला?",
        "expected": ["अल्कॉन हुंडई", "डीलरशिप रिकॉर्ड"]
    },
    {
        "id": 7,
        "flow_type": "insurance_start",
        "description": "Discount query 'thoda kam karo premium' in Devanagari with danda",
        "query": "थोड़ा कम करो ना प्रीमियम।",
        "expected": ["लॉयल्टी डिस्काउंट", "15%"]
    }
]

def test_query(flow_type, query_text, expected_keywords):
    call_sid = f"VOICE_TEST_{flow_type}_{hash(query_text)}"
    from_phone = "+919881012767"
    
    try:
        # 1. Call Init
        res = requests.post(f"{BASE_URL}/voice?flow_type={flow_type}", data={
            "CallSid": call_sid,
            "From": from_phone,
            "Direction": "inbound"
        })
        
        # Follow redirect to language selection
        root = ET.fromstring(res.text)
        redirect = root.find('.//{*}Redirect')
        if redirect is not None:
            redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
            res = requests.post(redirect_url, data={
                "CallSid": call_sid,
                "From": from_phone,
                "Direction": "inbound"
            })
            root = ET.fromstring(res.text)
            
        # Extract action URL from gather
        gather = root.find('.//{*}Gather')
        if gather is None:
            return False, "Language IVR Gather not found", ""
            
        action_url = BASE_URL + gather.get('action')
        
        # 2. Select Hindi Language (2)
        res = requests.post(action_url, data={
            "CallSid": call_sid,
            "From": from_phone,
            "Digits": "2"
        })
        
        # Follow redirect to main voice greeting
        redirect = ET.fromstring(res.text).find('.//{*}Redirect')
        if redirect is None:
            return False, "Language callback redirect not found", ""
        redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
        
        res = requests.post(redirect_url, data={
            "CallSid": call_sid,
            "From": from_phone
        })
        
        # Get the gather action for the next process turn
        gather = ET.fromstring(res.text).find('.//{*}Gather')
        if gather is None:
            return False, "Main greeting gather not found", ""
        action_url = BASE_URL + gather.get('action')
        
        # 3. Post the Devanagari Voice Query
        res = requests.post(action_url, data={
            "CallSid": call_sid,
            "From": from_phone,
            "SpeechResult": query_text
        })
        
        # 4. Extract and Validate the Response
        try:
            root = ET.fromstring(res.text)
        except Exception as e:
            return False, f"XML Parse Error: {e} | Status: {res.status_code} | Body: {res.text[:150]}", ""
        
        ai_says = []
        for say in root.findall('.//{*}Say'):
            if say.text:
                ai_says.append(say.text)
                
        ai_response = " ".join(ai_says)
        
        # Check for expected keywords
        missing_keywords = []
        for kw in expected_keywords:
            if kw.lower() not in ai_response.lower():
                missing_keywords.append(kw)
                
        if missing_keywords:
            return False, f"Missing keywords: {missing_keywords}", ai_response
            
        return True, "PASSED", ai_response
        
    except Exception as ex:
        return False, f"Exception occurred: {str(ex)}", ""

def main():
    print("=" * 80)
    print("                MULTILINGUAL HINDI VOICE VERIFICATION SCRIPT")
    print("=" * 80)
    
    total_tests = len(VOICE_TEST_CASES)
    passed_tests = 0
    failures = []
    
    for tc in VOICE_TEST_CASES:
        print(f"Test #{tc['id']} | [{tc['flow_type'].upper()}] {tc['description']}")
        print(f"  Query: '{tc['query']}' -> ", end="")
        sys.stdout.flush()
        
        success, reason, response = test_query(tc["flow_type"], tc["query"], tc["expected"])
        if success:
            print("\033[92m[PASS]\033[0m")
            print(f"  AI Response: \033[96m\033[1m{response}\033[0m")
            passed_tests += 1
        else:
            print("\033[91m[FAIL]\033[0m")
            print(f"  Reason: {reason}")
            if response:
                print(f"  AI Response was: \033[96m\033[1m{response}\033[0m")
            failures.append({
                "id": tc["id"],
                "flow_type": tc["flow_type"],
                "query": tc["query"],
                "reason": reason,
                "response": response
            })
        print("-" * 80)
        
    print("\n" + "=" * 80)
    print("                    MULTILINGUAL HINDI VOICE REPORT")
    print("=" * 80)
    print(f"Total Tests Run: {total_tests}")
    print(f"Passed: \033[92m{passed_tests}\033[0m")
    print(f"Failed: \033[91m{len(failures)}\033[0m")
    print(f"Success Rate: {passed_tests / total_tests * 100:.1f}%")
    print("=" * 80)
    
    if failures:
        sys.exit(1)
    else:
        print("\n\033[92mALL DEVANAGARI HINDI VOICE VERIFICATIONS PASSED PERFECTLY!\033[0m")
        sys.exit(0)

if __name__ == "__main__":
    main()
