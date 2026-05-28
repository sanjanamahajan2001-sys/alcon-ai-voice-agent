import requests
import xml.etree.ElementTree as ET
import sys
import urllib.parse

BASE_URL = "http://localhost:8000"

FAQ_TEST_CASES = [
    {
        "id": 1,
        "hinglish": "mujhe suv segment mein gaadi dekhni hai",
        "english": "I am looking for a car in the SUV segment.",
        "expected_hindi": ["Creta", "Venue", "SUV"],
        "expected_english": ["Creta", "Venue", "SUV"]
    },
    {
        "id": 2,
        "hinglish": "diesel available hai kya",
        "english": "Is diesel available?",
        "expected_hindi": ["पेट्रोल", "डीजल"],
        "expected_english": ["Petrol", "Diesel"]
    },
    {
        "id": 3,
        "hinglish": "automatic variant ka price kya hai",
        "english": "What is the price of the automatic variant?",
        "expected_hindi": ["ऑटोमैटिक", "Creta", "Venue"],
        "expected_english": ["automatic", "Creta", "Venue"]
    },
    {
        "id": 4,
        "hinglish": "emi kitni padegi",
        "english": "How much will the EMI be?",
        "expected_hindi": ["ईएमआई", "शुरू"],
        "expected_english": ["EMI", "starting"]
    },
    {
        "id": 5,
        "hinglish": "down payment minimum kitna hoga",
        "english": "What will be the minimum down payment?",
        "expected_hindi": ["डाउनपेमेंट", "Creta", "Venue"],
        "expected_english": ["down payment", "Creta", "Venue"]
    },
    {
        "id": 6,
        "hinglish": "waiting period kitna hai",
        "english": "What is the waiting period?",
        "expected_hindi": ["वेटिंग", "सप्ताह"],
        "expected_english": ["waiting", "weeks"]
    },
    {
        "id": 7,
        "hinglish": "turbo variant available hai kya",
        "english": "Is the turbo variant available?",
        "expected_hindi": ["टर्बो", "वेरिएंट"],
        "expected_english": ["turbo", "variant"]
    },
    {
        "id": 8,
        "hinglish": "exchange mein kitna value milega",
        "english": "How much value will I get in exchange?",
        "expected_hindi": ["एक्सचेंज बोनस", "पुरानी कार"],
        "expected_english": ["exchange bonus", "old car"]
    },
    {
        "id": 9,
        "hinglish": "cng model available hai kya",
        "english": "Is the CNG model available?",
        "expected_hindi": ["सीएनजी", "Grand i10"],
        "expected_english": ["CNG", "i10"]
    },
    {
        "id": 10,
        "hinglish": "service package kya milta hai",
        "english": "What service package is available?",
        "expected_hindi": ["वारंटी", "सर्विस पैकेज"],
        "expected_english": ["warranty", "service package"]
    },
    {
        "id": 11,
        "hinglish": "insurance included hai kya",
        "english": "Is insurance included?",
        "expected_hindi": ["बीमा", "ऑन-रोड"],
        "expected_english": ["insurance", "on-road"]
    },
    {
        "id": 12,
        "hinglish": "accessories free milengi kya",
        "english": "Will free accessories be provided?",
        "expected_hindi": ["मुफ्त", "एक्सेसरीज"],
        "expected_english": ["free", "accessories"]
    },
    {
        "id": 13,
        "hinglish": "mujhe white colour chahiye",
        "english": "I want the white colour.",
        "expected_hindi": ["रंगों", "Creta"],
        "expected_english": ["colors", "Creta"]
    },
    {
        "id": 14,
        "hinglish": "ghar pe test drive possible hai kya",
        "english": "Is a home test drive possible?",
        "expected_hindi": ["घर पर", "टेस्ट ड्राइव"],
        "expected_english": ["doorstep", "test drive"]
    },
    {
        "id": 15,
        "hinglish": "loan approval kitne time mein hota hai",
        "english": "How much time does loan approval take?",
        "expected_hindi": ["लोन अप्रूवल", "घंटे"],
        "expected_english": ["loan approval", "hours"]
    },
    {
        "id": 16,
        "hinglish": "mujhe venue ka on road price chahiye",
        "english": "i want on road price of venue",
        "expected_hindi": ["on-road", "price", "Venue"],
        "expected_english": ["on-road", "price", "Venue"]
    },
    {
        "id": 17,
        "hinglish": "creta ka diesel automatic hai kya",
        "english": "is creta diesel automatic available",
        "expected_hindi": ["पेट्रोल", "डीजल", "ऑटोमैटिक", "मैनुअल"],
        "expected_english": ["Petrol", "Diesel", "Automatic", "Manual"]
    },
    {
        "id": 18,
        "hinglish": "i20 sports variant available hai kya",
        "english": "is i20 sports variant available",
        "expected_hindi": ["Sportz", "Asta", "variants"],
        "expected_english": ["Sportz", "Asta", "variants"]
    },
    {
        "id": 19,
        "hinglish": "turbo engine wala model batao",
        "english": "tell me turbo engine models",
        "expected_hindi": ["टर्बो", "Creta", "Venue"],
        "expected_english": ["turbo", "Creta", "Venue"]
    },
    {
        "id": 20,
        "hinglish": "sunroof wali gaadi chahiye",
        "english": "i want sunroof car",
        "expected_hindi": ["sunroof", "Creta", "Venue"],
        "expected_english": ["sunroof", "Creta", "Venue"]
    },
    {
        "id": 21,
        "hinglish": "7 se 10 lakh ke andar kya options hain",
        "english": "what are the options between 7 to 10 lakhs",
        "expected_hindi": ["₹7.94", "Venue", "Lakh"],
        "expected_english": ["₹7.94", "Venue", "Lakh"]
    },
    {
        "id": 22,
        "hinglish": "manual nahi automatic chahiye",
        "english": "i want automatic not manual",
        "expected_hindi": ["ऑटोमैटिक", "मैनुअल"],
        "expected_english": ["automatic", "Automatic", "Manual"]
    },
    {
        "id": 23,
        "hinglish": "rukho pehle emi batao",
        "english": "wait tell me emi first",
        "expected_hindi": ["EMI", "Creta", "शुरू"],
        "expected_english": ["EMI", "Creta", "starts"]
    },
    {
        "id": 24,
        "hinglish": "acha exchange ka process batao",
        "english": "okay tell me exchange process",
        "expected_hindi": ["एक्सचेंज बोनस", "पुरानी कार"],
        "expected_english": ["exchange bonus", "old car", "market value"]
    },
    {
        "id": 25,
        "hinglish": "sabse zyada bikne wali gaadi kaunsi hai",
        "english": "which is the best selling car",
        "expected_hindi": ["Creta", "सबसे", "अधिक"],
        "expected_english": ["Creta", "highest-selling"]
    },
    {
        "id": 26,
        "hinglish": "family ke liye best model kaunsa hai",
        "english": "which is the best model for a family",
        "expected_hindi": ["Creta", "family", "पारिवारिक"],
        "expected_english": ["Creta", "family", "spacious"]
    },
    {
        "id": 27,
        "hinglish": "maintenance kam kiski hai",
        "english": "which has lowest maintenance",
        "expected_hindi": ["Venue", "maintenance", "कम", "लागत"],
        "expected_english": ["Venue", "maintenance", "paise"]
    },
    {
        "id": 28,
        "hinglish": "mileage accha kiska hai",
        "english": "which has best mileage",
        "expected_hindi": ["Venue", "Grand i10", "माइलेज"],
        "expected_english": ["Venue", "fuel efficiency", "Grand i10", "mileage"]
    },
    {
        "id": 29,
        "hinglish": "why should i choose hyundai",
        "english": "Why should I buy Hyundai?",
        "expected_hindi": ["रिफाइनमेंट", "सुरक्षा", "सर्विस", "रीसेल"],
        "expected_english": ["refinement", "safety", "service", "resale"]
    },
    {
        "id": 30,
        "hinglish": "main kia bhi dekh raha hoon",
        "english": "How is Hyundai better than Kia?",
        "expected_hindi": ["किया", "हुंडई", "रिफाइंड", "सर्विस"],
        "expected_english": ["Kia", "Hyundai", "refined", "service"]
    },
    {
        "id": 31,
        "hinglish": "hyundai better hai ya tata",
        "english": "I am also considering Tata",
        "expected_hindi": ["टाटा", "असाधारण", "रिफाइनमेंट", "ट्रांसमिशन"],
        "expected_english": ["Tata", "exceptional", "refinement", "transmission"]
    },
    {
        "id": 32,
        "hinglish": "seltos aur creta mein kya difference hai",
        "english": "Is Creta better than Seltos?",
        "expected_hindi": ["क्रेटा", "सेल्टोस", "रिफाइंड", "सर्विस"],
        "expected_english": ["Creta", "Seltos", "refined", "service"]
    },
    {
        "id": 33,
        "hinglish": "venue ya nexon better rahegi",
        "english": "Which is better, Venue or Nexon?",
        "expected_hindi": ["वेन्यू", "नेक्सॉन", "रखरखाव", "विश्वसनीयता"],
        "expected_english": ["Venue", "Nexon", "maintenance", "reliability"]
    },
    {
        "id": 34,
        "hinglish": "mahindra ka bhi option dekh raha hoon",
        "english": "Why Hyundai over Mahindra?",
        "expected_hindi": ["महिंद्रा", "शहरी", "गतिशीलता", "आराम"],
        "expected_english": ["Mahindra", "maneuverability", "comfort", "refinement"]
    },
    {
        "id": 35,
        "hinglish": "verna aur city compare karo",
        "english": "compare verna and honda city",
        "expected_hindi": ["वरना", "सिटी", "शक्तिशाली", "सुरक्षा"],
        "expected_english": ["Verna", "City", "powerful", "safety"]
    },
    {
        "id": 36,
        "hinglish": "punch aur exter mein compare karo",
        "english": "compare exter and tata punch",
        "expected_hindi": ["एक्स्टर", "पंच", "एयरबैग", "डैशकैम"],
        "expected_english": ["Exter", "Punch", "airbags", "dashcam"]
    },
    {
        "id": 37,
        "hinglish": "baleno ya i20 better rahegi",
        "english": "is i20 better than baleno",
        "expected_hindi": ["i20", "बलेनो", "स्पोर्टी", "केबिन"],
        "expected_english": ["i20", "Baleno", "sporty", "cabin"]
    },
    {
        "id": 38,
        "hinglish": "compass se better hai kya tucson",
        "english": "is tucson better than jeep compass",
        "expected_hindi": ["टक्सन", "कम्पस", "लक्जरी", "इंजन"],
        "expected_english": ["Tucson", "Compass", "luxury", "engine"]
    },
    {
        "id": 39,
        "hinglish": "hyundai maintenance costly hai kya",
        "english": "is hyundai maintenance costly",
        "expected_hindi": ["Venue", "रखरखाव", "लागत", "35 पैसे"],
        "expected_english": ["Venue", "lowest", "maintenance", "35 paise"]
    },
    {
        "id": 40,
        "hinglish": "kia ka interior better lagta hai",
        "english": "kia has better interior than hyundai",
        "expected_hindi": ["केबिन", "प्रीमियम", "टिकाऊपन", "एर्गोनॉमिक्स"],
        "expected_english": ["cabins", "premium", "durability", "ergonomics"]
    },
    {
        "id": 41,
        "hinglish": "tata safer hai na?",
        "english": "tata is safer right?",
        "expected_hindi": ["सुरक्षा", "एयरबैग", "स्टील", "एडीएएस"],
        "expected_english": ["safety", "airbags", "steel", "ADAS"]
    },
    {
        "id": 42,
        "hinglish": "mileage kam hai",
        "english": "mileage is low",
        "expected_hindi": ["Venue", "Grand i10", "शानदार", "माइलेज"],
        "expected_english": ["Venue", "Grand i10", "excellent", "mileage"]
    },
    {
        "id": 43,
        "hinglish": "resale value kaisi hai",
        "english": "how is the resale value",
        "expected_hindi": ["उत्कृष्ट", "रीसेल", "मजबूत", "मांग"],
        "expected_english": ["excellent", "resale", "durable", "demand"]
    },
    {
        "id": 44,
        "hinglish": "mahindra zyada powerful lagti hai",
        "english": "mahindra feels more powerful",
        "expected_hindi": ["क्रेटा", "पेट्रोल", "डीजल", "टर्बो"],
        "expected_english": ["Creta", "petrol", "diesel", "turbo"]
    },
    {
        "id": 45,
        "hinglish": "family ke liye best suv kaunsi hai",
        "english": "Which SUV is best for family?",
        "expected_hindi": ["पारिवारिक", "विशाल", "बूट स्पेस", "एयरबैग"],
        "expected_english": ["perfect", "family", "spacious", "boot space"]
    },
    {
        "id": 46,
        "hinglish": "city driving ke liye best car",
        "english": "which car is best for city driving",
        "expected_hindi": ["माइलेज", "वेन्यू", "i10", "परफेक्ट"],
        "expected_english": ["mileage", "efficiency", "commutes", "perfect"]
    },
    {
        "id": 47,
        "hinglish": "best automatic car under 15 lakh",
        "english": "Best automatic under 15 lakhs?",
        "expected_hindi": ["15 लाख", "वेन्यू", "शुरू", "ऑटोमैटिक"],
        "expected_english": ["15 Lakhs", "Venue", "starts", "automatic"]
    },
    {
        "id": 48,
        "hinglish": "service achi hai kya",
        "english": "is after sales service good",
        "expected_hindi": ["वर्कशॉप", "विशाल", "ग्राहक", "संतुष्टि"],
        "expected_english": ["workshops", "expert", "customer", "satisfaction"]
    },
    {
        "id": 49,
        "hinglish": "parts easily mil jaate hain?",
        "english": "are parts easily available",
        "expected_hindi": ["असली", "स्पेयर", "पार्ट्स", "उचित"],
        "expected_english": ["genuine", "spare", "parts", "reasonable"]
    },
    {
        "id": 50,
        "hinglish": "long drive ke liye achi rahegi?",
        "english": "is it good for long drive",
        "expected_hindi": ["आरामदायक", "सीटें", "शांत", "सस्पेंशन"],
        "expected_english": ["comfortable", "seats", "silent", "suspension"]
    },
    {
        "id": 51,
        "hinglish": "adas feature hai?",
        "english": "does it have ADAS feature",
        "expected_hindi": ["उन्नत", "स्तर 2", "एडीएएस", "सुरक्षा"],
        "expected_english": ["advanced", "Level 2", "ADAS", "safety"]
    },
    {
        "id": 52,
        "hinglish": "ventilated seats chahiye",
        "english": "does it have ventilated seats",
        "expected_hindi": ["वेंटिलेटेड", "सीटें", "क्रेटा", "वरना"],
        "expected_english": ["ventilated", "seats", "Creta", "Verna"]
    },
    {
        "id": 53,
        "hinglish": "6 airbags wali car",
        "english": "which cars have 6 airbags",
        "expected_hindi": ["गर्व", "सभी", "मानक", "6 एयरबैग"],
        "expected_english": ["proud", "all", "standard", "6 airbags"]
    }
]

def test_query(flow_type, language_choice, query_text, expected_keywords):
    call_sid = f"FAQ_TEST_{flow_type}_{language_choice}_{hash(query_text)}"
    from_phone = "+919881012767"
    
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
    
    # 2. Select Language
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

def run_memory_stress_test():
    print("\n" + "=" * 80)
    print("                CONVERSATIONAL MEMORY CORRUPTION STRESS TEST")
    print("=" * 80)
    
    call_sid = "STRESS_TEST_CONVERSATIONAL_MEMORY"
    from_phone = "+919881012767"
    
    # 1. Start Call
    res = requests.post(f"{BASE_URL}/voice?flow_type=pre_sales", data={
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
    
    # 2. Select Language (English - 1)
    res = requests.post(action_url, data={
        "CallSid": call_sid,
        "From": from_phone,
        "Digits": "1"
    })
    
    # Follow redirect to main voice greeting
    redirect = ET.fromstring(res.text).find('.//{*}Redirect')
    if redirect is None:
        print("Error: Language callback redirect not found")
        return False
    redirect_url = BASE_URL + redirect.text if redirect.text.startswith('/') else redirect.text
    
    res = requests.post(redirect_url, data={
        "CallSid": call_sid,
        "From": from_phone
    })
    
    # Get the gather action for the next process turn
    gather = ET.fromstring(res.text).find('.//{*}Gather')
    if gather is None:
        print("Error: Main greeting gather not found")
        return False
    action_url = BASE_URL + gather.get('action')
    
    # Sequential stress turns (creta -> venue -> nahi i20 -> acha verna ka price -> diesel hai?)
    turns = [
        {"input": "creeta", "expected": ["Creta", "starts"]},
        {"input": "vnue", "expected": ["Venue", "starts"]},
        {"input": "nahi i20", "expected": ["i20", "starts"]},
        {"input": "acha verna ka price", "expected": ["Verna", "₹11 Lakhs"]},
        {"input": "diesel hai?", "expected": ["Verna", "Petrol", "Diesel"]}
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
            
    print("\n\033[92mCONVERSATIONAL MEMORY STRESS TEST PASSED PERFECTLY!\033[0m")
    return True
 
def main():
    print("=" * 80)
    print("                MULTILINGUAL FAQ AUTOMATION VERIFICATION SCRIPT")
    print("=" * 80)
    
    total_tests = 0
    passed_tests = 0
    failures = []
    
    flows = ["reception", "pre_sales"]
    languages = [
        {"choice": 1, "name": "English", "field": "english", "keywords": "expected_english"},
        {"choice": 2, "name": "Hindi", "field": "hinglish", "keywords": "expected_hindi"}
    ]
    
    for flow in flows:
        for lang in languages:
            print(f"\nRunning FAQ validation for Flow: {flow.upper()} | Language: {lang['name']}")
            print("-" * 80)
            for tc in FAQ_TEST_CASES:
                query_text = tc[lang["field"]]
                expected_kw = tc[lang["keywords"]]
                total_tests += 1
                
                print(f"Test #{tc['id']} | Query: '{query_text}' -> ", end="")
                sys.stdout.flush()
                
                success, reason, response = test_query(flow, lang["choice"], query_text, expected_kw)
                if success:
                    print("\033[92m[PASS]\033[0m")
                    print(f"  AI Response: \033[96m\033[1m{response}\033[0m")
                    passed_tests += 1
                else:
                    print("\033[91m[FAIL]\033[0m")
                    print(f"  Reason: {reason}")
                    print(f"  AI Response was: \033[96m\033[1m{response}\033[0m")
                    failures.append({
                        "flow": flow,
                        "lang": lang["name"],
                        "query": query_text,
                        "reason": reason,
                        "response": response
                    })
                    
    print("\n" + "=" * 80)
    print("                         FAQ VERIFICATION REPORT")
    print("=" * 80)
    print(f"Total Tests Run: {total_tests}")
    print(f"Passed: \033[92m{passed_tests}\033[0m")
    print(f"Failed: \033[91m{len(failures)}\033[0m")
    print(f"Success Rate: {passed_tests / total_tests * 100:.1f}%")
    print("=" * 80)
    
    if failures:
        print("\nDetail of Failures:")
        for idx, f in enumerate(failures, 1):
            print(f"{idx}. Flow: {f['flow']} | Lang: {f['lang']} | Query: '{f['query']}'")
            print(f"   Reason: {f['reason']}")
            print(f"   Response: \033[96m\033[1m{f['response']}\033[0m")
            print("-" * 50)
        sys.exit(1)
    else:
        print("\n\033[92mALL MULTILINGUAL FAQ VERIFICATIONS PASSED PERFECTLY!\033[0m")
        stress_passed = run_memory_stress_test()
        if not stress_passed:
            print("\n\033[91mCONVERSATIONAL MEMORY STRESS TEST FAILED!\033[0m")
            sys.exit(1)
        sys.exit(0)
 
if __name__ == "__main__":
    main()
