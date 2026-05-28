import requests
import xml.etree.ElementTree as ET
import sys
import urllib.parse

BASE_URL = "http://localhost:8000"

INSURANCE_FAQ_TEST_CASES = [
    {
        "id": 1,
        "category": "Identity / Trust",
        "hinglish": "aapko mera number kaha se mila",
        "english": "How did you get my number?",
        "expected_hindi": ["अल्कॉन हुंडई", "डीलरशिप रिकॉर्ड"],
        "expected_english": ["Alcon Hyundai", "dealership records"]
    },
    {
        "id": 2,
        "category": "Identity / Trust",
        "hinglish": "ye genuine call hai kya",
        "english": "Are you calling from Hyundai directly?",
        "expected_hindi": ["अल्कॉन हुंडई", "डीलरशिप रिकॉर्ड"],
        "expected_english": ["Alcon Hyundai", "dealership records"]
    },
    {
        "id": 3,
        "category": "Identity / Trust",
        "hinglish": "whatsapp pe details bhejo pehle",
        "english": "Can you send details on WhatsApp first?",
        "expected_hindi": ["व्हाट्सएप नंबर पर", "डीलरशिप"],
        "expected_english": ["WhatsApp number", "dealership contact"]
    },
    {
        "id": 4,
        "category": "Policy Understanding",
        "hinglish": "zero dep kya hota hai",
        "english": "What is zero depreciation?",
        "expected_hindi": ["जीरो डेप्रिसिएशन", "100% कवरेज"],
        "expected_english": ["Zero Depreciation", "100% coverage"]
    },
    {
        "id": 5,
        "category": "Policy Understanding",
        "hinglish": "bumper to bumper matlab",
        "english": "What is bumper to bumper insurance?",
        "expected_hindi": ["जीरो डेप्रिसिएशन", "100% कवरेज"],
        "expected_english": ["Zero Depreciation", "100% coverage"]
    },
    {
        "id": 6,
        "category": "Policy Understanding",
        "hinglish": "engine protection included hai kya",
        "english": "Does this include engine protection?",
        "expected_hindi": ["इंजन प्रोटेक्शन", "हाइड्रोस्टेटिक लॉक"],
        "expected_english": ["Engine Protection", "hydrostatic lock"]
    },
    {
        "id": 7,
        "category": "Policy Understanding",
        "hinglish": "ncb kya hota hai",
        "english": "What is NCB?",
        "expected_hindi": ["नो क्लेम बोनस", "50%"],
        "expected_english": ["No Claim Bonus", "50%"]
    },
    {
        "id": 8,
        "category": "Claim & Accident",
        "hinglish": "last year claim liya tha premium badega kya",
        "english": "Will my previous claim affect premium?",
        "expected_hindi": ["नो क्लेम बोनस", "NCB"],
        "expected_english": ["No Claim Bonus", "NCB"]
    },
    {
        "id": 9,
        "category": "Claim & Accident",
        "hinglish": "cashless claim available hai kya",
        "english": "Will cashless claims be available?",
        "expected_hindi": ["कैशलेस क्लेम", "अधिकृत"],
        "expected_english": ["cashless claim", "authorized"]
    },
    {
        "id": 10,
        "category": "Claim & Accident",
        "hinglish": "ncb milega kya abhi bhi",
        "english": "Can I still get NCB?",
        "expected_hindi": ["नो क्लेम बोनस", "NCB"],
        "expected_english": ["No Claim Bonus", "NCB"]
    },
    {
        "id": 11,
        "category": "Competitor Comparison",
        "hinglish": "policybazaar cheaper de raha hai",
        "english": "PolicyBazaar is giving cheaper",
        "expected_hindi": ["पॉलिसीबाज़ार", "कैशलेस क्लेम"],
        "expected_english": ["PolicyBazaar", "cashless claims"]
    },
    {
        "id": 12,
        "category": "Competitor Comparison",
        "hinglish": "acko ka quote kam hai",
        "english": "Acko is cheaper than this",
        "expected_hindi": ["पॉलिसीबाज़ार", "कैशलेस क्लेम"],
        "expected_english": ["PolicyBazaar", "cashless claims"]
    },
    {
        "id": 13,
        "category": "Competitor Comparison",
        "hinglish": "online sasta mil raha hai",
        "english": "Online is cheaper",
        "expected_hindi": ["पॉलिसीबाज़ार", "कैशलेस क्लेम"],
        "expected_english": ["PolicyBazaar", "cashless claims"]
    },
    {
        "id": 14,
        "category": "Competitor Comparison",
        "hinglish": "dealership se hi kyu renew karu",
        "english": "Why should I renew through dealership?",
        "expected_hindi": ["डीलरशिप", "कैशलेस क्लेम", "ओईएम पार्ट्स"],
        "expected_english": ["dealership", "cashless claims", "OEM parts"]
    },
    {
        "id": 15,
        "category": "Discount Negotiation",
        "hinglish": "thoda kam karo na premium",
        "english": "Can you reduce the premium?",
        "expected_hindi": ["लॉयल्टी डिस्काउंट", "15%", "इंश्योरेंस मैनेजर"],
        "expected_english": ["loyalty discount", "15%", "Insurance Manager"]
    },
    {
        "id": 16,
        "category": "Discount Negotiation",
        "hinglish": "best price batao",
        "english": "Give me your best price",
        "expected_hindi": ["लॉयल्टी डिस्काउंट", "15%", "इंश्योरेंस मैनेजर"],
        "expected_english": ["loyalty discount", "15%", "Insurance Manager"]
    },
    {
        "id": 17,
        "category": "Discount Negotiation",
        "hinglish": "online wala rate match karoge",
        "english": "Can you match online price?",
        "expected_hindi": ["लॉयल्टी डिस्काउंट", "15%", "इंश्योरेंस मैनेजर"],
        "expected_english": ["loyalty discount", "15%", "Insurance Manager"]
    },
    {
        "id": 18,
        "category": "Expiry & Risk",
        "hinglish": "expiry ke baad renew ho jayega kya",
        "english": "Can I renew after expiry?",
        "expected_hindi": ["अवैध", "निरीक्षण"],
        "expected_english": ["illegal", "inspection"]
    },
    {
        "id": 19,
        "category": "Expiry & Risk",
        "hinglish": "inspection lagega kya",
        "english": "Will inspection be required?",
        "expected_hindi": ["अवैध", "निरीक्षण"],
        "expected_english": ["illegal", "inspection"]
    },
    {
        "id": 20,
        "category": "Expiry & Risk",
        "hinglish": "ncb chala jayega kya",
        "english": "Will I lose NCB?",
        "expected_hindi": ["अवैध", "निरीक्षण"],
        "expected_english": ["illegal", "inspection"]
    },
    {
        "id": 21,
        "category": "Payment & Transaction",
        "hinglish": "payment link bhej do",
        "english": "Can you send payment link?",
        "expected_hindi": ["डिजिटल भुगतान", "भुगतान लिंक"],
        "expected_english": ["secure digital payment", "payment link"]
    },
    {
        "id": 22,
        "category": "Payment & Transaction",
        "hinglish": "upi chalega kya",
        "english": "Is UPI accepted?",
        "expected_hindi": ["डिजिटल भुगतान", "भुगतान लिंक"],
        "expected_english": ["secure digital payment", "payment link"]
    },
    {
        "id": 23,
        "category": "Payment & Transaction",
        "hinglish": "emi pe payment ho jayega",
        "english": "Can I pay in EMI?",
        "expected_hindi": ["डिजिटल भुगतान", "भुगतान लिंक"],
        "expected_english": ["secure digital payment", "payment link"]
    },
    {
        "id": 24,
        "category": "Human Transfer / Escalation",
        "hinglish": "human se baat karni hai",
        "english": "I want to speak with a human",
        "expected_hindi": ["इंश्योरेंस डेस्क", "जोड़"],
        "expected_english": ["connect you to our insurance desk"]
    },
    {
        "id": 25,
        "category": "Human Transfer / Escalation",
        "hinglish": "manager se connect karo",
        "english": "Connect me to manager",
        "expected_hindi": ["इंश्योरेंस डेस्क", "जोड़"],
        "expected_english": ["connect you to our insurance desk"]
    },
    {
        "id": 26,
        "category": "Frustrated / Angry Customer",
        "hinglish": "baar baar call mat karo",
        "english": "You people keep calling me",
        "expected_hindi": ["असुविधा के लिए", "डू नॉट डिस्टर्ब"],
        "expected_english": ["apologize", "Do Not Disturb"]
    },
    {
        "id": 27,
        "category": "Frustrated / Angry Customer",
        "hinglish": "premium itna expensive kyu hai",
        "english": "Why are premiums increasing every year?",
        "expected_hindi": ["असुविधा के लिए", "डू नॉट डिस्टर्ब"],
        "expected_english": ["apologize", "Do Not Disturb"]
    }
]

def test_query(language_choice, query_text, expected_keywords):
    call_sid = f"INS_FAQ_TEST_{language_choice}_{hash(query_text)}"
    from_phone = "+919881012767"
    
    # 1. Call Init (flow_type = insurance_start)
    res = requests.post(f"{BASE_URL}/voice?flow_type=insurance_start", data={
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
    
    # 2. Select Language (1 = English, 2 = Hindi)
    res = requests.post(action_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "Digits": str(language_choice)
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
    
    # 3. Post the FAQ Query
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

def run_realistic_mixed_flow_test():
    print("\n" + "=" * 80)
    print("                REALISTIC MIXED INSURANCE FLOW TEST")
    print("=" * 80)
    
    call_sid = "INS_STRESS_TEST_MIXED_FLOW_TURN"
    from_phone = "+919881012767"
    
    # 1. Start Call
    res = requests.post(f"{BASE_URL}/voice?flow_type=insurance_start", data={
        "CallSid": call_sid,
        "From": from_phone,
        "Direction": "inbound"
    })
    
    root = ET.fromstring(res.text)
    redirect = root.find('.//{*}Redirect')
    if redirect is not None:
        redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
        res = requests.post(redirect_url, data={
            "CallSid": call_sid,
            "From": from_phone
        })
        root = ET.fromstring(res.text)
        
    gather = root.find('.//{*}Gather')
    if gather is None:
        print("Error: Language IVR Gather not found")
        return False
        
    action_url = BASE_URL + gather.get('action')
    
    # 2. Select Language (Hindi - 2)
    res = requests.post(action_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "Digits": "2"
    })
    
    redirect = ET.fromstring(res.text).find('.//{*}Redirect')
    if redirect is None:
        print("Error: Language callback redirect not found")
        return False
    redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
    
    res = requests.post(redirect_url, data={
        "CallSid": call_sid,
        "From": from_phone
    })
    
    # Main greeting gather action
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    if gather is None:
        print("Error: Main greeting gather not found")
        return False
    action_url = BASE_URL + gather.get('action')
    
    # Category 10: Mixed turns
    # We will simulate: 
    # Turn 1: haan bataiye -> Greeting response
    # Turn 2: premium kitna hai -> loyalty premium details
    # Turn 3: itna zyada kyu hai policybazaar sasta de raha hai -> competitor comparison & transfer question
    # Turn 4: zero dep included hai kya -> Zero Dep explanation & transfer question (since comparison offered)
    # Turn 5: acha whatsapp pe bhejo -> interested consent transition
    # Turn 6: main abhi busy hoon kal call karna -> callback callback scheduling
    
    turns = [
        {"input": "haan bataiye", "expected": ["क्या आप इसे आज ही बुक", "रिन्यू", "रिन्यूअल"]},
        {"input": "premium kitna hai", "expected": ["प्रीमियम", "लॉयल्टी कोट"]},
        {"input": "itna zyada kyu hai policybazaar sasta de raha hai", "expected": ["पॉलिसीबाज़ार", "कैशलेस क्लेम"]},
        {"input": "zero dep included hai kya", "expected": ["जीरो डेप्रिसिएशन"]},
        {"input": "acha whatsapp pe bhejo", "expected": ["लिंक"]},
        {"input": "main abhi busy hoon kal call karna", "expected": ["कॉल बैक"]}
    ]
    
    for idx, turn in enumerate(turns, 1):
        print(f"Turn #{idx} | Input: '{turn['input']}' -> ", end="")
        sys.stdout.flush()
        
        res = requests.post(action_url, data={
            "CallSid": call_sid,
            "From": from_phone,
            "SpeechResult": turn["input"]
        })
        
        root = ET.fromstring(res.text)
        ai_says = [say.text for say in root.findall('.//{*}Say') if say.text]
        ai_response = " ".join(ai_says)
        
        # Verify expected keywords
        missing = []
        if idx == 1:
            stage1_kw = ["रिन्यू", "रिन्यूअल"]
            stage3_kw = ["नो क्लेम", "बोनस", "सुरक्षित"]
            has_stage1 = all(kw in ai_response for kw in stage1_kw)
            has_stage3 = all(kw in ai_response for kw in stage3_kw)
            if not (has_stage1 or has_stage3):
                missing = ["रिन्यू/रिन्यूअल (Stage 1) OR नो क्लेम/बोनस/सुरक्षित (Stage 3)"]
        else:
            missing = [kw for kw in turn["expected"] if kw.lower() not in ai_response.lower()]
            
        if missing:
            print("\033[91m[FAIL]\033[0m")
            print(f"  Reason: Missing expected keywords {missing}")
            print(f"  AI Response: \033[96m\033[1m{ai_response}\033[0m")
            return False
            
        print("\033[92m[PASS]\033[0m")
        print(f"  AI Response: \033[96m\033[1m{ai_response}\033[0m")
        
        # Get next action url
        gather = root.find('.//{*}Gather')
        if gather is not None:
            action_url = BASE_URL + gather.get('action')
            
    print("\n\033[92mREALISTIC MIXED INSURANCE FLOW TEST PASSED PERFECTLY!\033[0m")
    return True

def main():
    print("=" * 80)
    print("                MULTILINGUAL INSURANCE FAQ AUTOMATION VERIFICATION SCRIPT")
    print("=" * 80)
    
    total_tests = 0
    passed_tests = 0
    failures = []
    
    languages = [
        {"choice": 1, "name": "English", "field": "english", "keywords": "expected_english"},
        {"choice": 2, "name": "Hindi", "field": "hinglish", "keywords": "expected_hindi"}
    ]
    
    for lang in languages:
        print(f"\nRunning FAQ validation for Insurance Flow | Language: {lang['name']}")
        print("-" * 80)
        for tc in INSURANCE_FAQ_TEST_CASES:
            query_text = tc[lang["field"]]
            expected_kw = tc[lang["keywords"]]
            total_tests += 1
            
            print(f"Test #{tc['id']} | [{tc['category']}] | Query: '{query_text}' -> ", end="")
            sys.stdout.flush()
            
            success, reason, response = test_query(lang["choice"], query_text, expected_kw)
            if success:
                print("\033[92m[PASS]\033[0m")
                print(f"  AI Response: \033[96m\033[1m{response}\033[0m")
                passed_tests += 1
            else:
                print("\033[91m[FAIL]\033[0m")
                print(f"  Reason: {reason}")
                print(f"  AI Response was: \033[96m\033[1m{response}\033[0m")
                failures.append({
                    "id": tc["id"],
                    "category": tc["category"],
                    "lang": lang["name"],
                    "query": query_text,
                    "reason": reason,
                    "response": response
                })
                
    print("\n" + "=" * 80)
    print("                     INSURANCE FAQ VERIFICATION REPORT")
    print("=" * 80)
    print(f"Total Tests Run: {total_tests}")
    print(f"Passed: \033[92m{passed_tests}\033[0m")
    print(f"Failed: \033[91m{len(failures)}\033[0m")
    print(f"Success Rate: {passed_tests / total_tests * 100:.1f}%")
    print("=" * 80)
    
    if failures:
        print("\nDetail of Failures:")
        for idx, f in enumerate(failures, 1):
            print(f"{idx}. Test #{f['id']} | Category: {f['category']} | Lang: {f['lang']} | Query: '{f['query']}'")
            print(f"   Reason: {f['reason']}")
            print(f"   Response: \033[96m\033[1m{f['response']}\033[0m")
            print("-" * 50)
        sys.exit(1)
    else:
        print("\n\033[92mALL MULTILINGUAL INSURANCE FAQ VERIFICATIONS PASSED PERFECTLY!\033[0m")
        stress_passed = run_realistic_mixed_flow_test()
        if not stress_passed:
            print("\n\033[91mREALISTIC MIXED INSURANCE FLOW TEST FAILED!\033[0m")
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    main()
