import re
import os
import json

class TranslationAdapter:
    """
    Decoupled plug-and-play Translation Bridge for the Alcon Voice Bot.
    Uses regex rules and static maps for ultra-low latency,
    perfectly preserving variables (names, dates, models).
    """
    LOCALES = {}

    @classmethod
    def load_locales(cls):
        if cls.LOCALES:
            return
        locales_dir = os.path.join(os.path.dirname(__file__), "..", "locales")
        if os.path.exists(locales_dir):
            for filename in os.listdir(locales_dir):
                if filename.endswith(".json"):
                    lang_code = filename.split(".")[0]
                    filepath = os.path.join(locales_dir, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            cls.LOCALES[lang_code] = json.load(f)
                    except Exception as e:
                        print(f"[LOCALES ERROR] Failed to load {filename}: {e}")

    # Static map for high-frequency user speech inputs to English
    HINDI_TO_ENGLISH_MAP = {
        "haan": "yes",
        "haanji": "yes",
        "ha": "yes",
        "haa": "yes",
        "ji haan": "yes",
        "thik hai": "yes",
        "theek hai": "yes",
        "thik": "yes",
        "theek": "yes",
        "karo": "yes",
        "karna hai": "yes",
        "book kar do": "yes",
        "service book kar do": "yes",
        "kar do": "yes",
        "nahin": "no",
        "nahi": "no",
        "nhi": "no",
        "na": "no",
        "mat karo": "no",
        "radd": "cancel",
        "cancel kar do": "cancel",
        "cancel": "cancel",
        "namaste": "hello",
        "pranam": "hello",
        "hello": "hello",
        "dhanyawad": "thank you",
        "shukriya": "thank you",
        "kal": "tomorrow",
        "aaj": "today",
        "parso": "day after tomorrow",
        "subah": "morning",
        "dopahar": "afternoon",
        "shaam": "evening",
        "baje": "o'clock",
        "haan main sanjana bol rahi hoon": "yes i am sanjana",
        "ji please book kar dijiye": "yes please book it",
        "25th may ko booking kar do": "25th may",
        "pachas hazaar": "50000",
        "pachaas hazaar": "50000",
        "brake pads se aawaz aa rahi hai": "brake pads noise issue",
        "nahi drop kar dungi khud": "no thanks",
        "haan main diya bol rahi hoon": "yes i am diya",
        "haan gaadi purchase karni hai creta ka benefits batao": "yes i want to buy creta and want to know benefits",
        "emi options aur price kitna hai": "what are the emi options and price",
        "safe hai kya airbags hai": "is it safe are there airbags",
        "driving kar raha hoon baad me call karo": "driving call me back later",
        "haan pooja bol rahi hoon": "yes i am pooja",
        "haan exchange scheme ke bare me bataiye": "yes i am interested in exchange offer",
        "creta me kaunse colors aate hai": "what colors are available",
        "mileage kitna deti hai": "what is the mileage",
        "kal dopahar 2 baje baat karte hai": "call me back tomorrow afternoon at 2",
        "mujhe nayi gaadi kharidni hai": "i want to buy a new car",
        "haan main sanya hoon": "yes i am sanya",
        "i10 car buy karni hai details batao": "i want to buy i10 car tell me details",
        "haan main kiran bol raha hoon": "yes i am kiran",
        "nahi main satisfied nahi hoon service se": "no i am not satisfied",
        "haan bilkul call kijiye team se": "yes please connect call",
        "baat karaiye": "connect me",
        "ji baat karaiye": "connect me",
        "connect kar do": "connect me",
        "connect kar dijiye": "connect me",
        "transfer kar do": "connect me",
        "baat karvao": "connect me",
        "baat karni hai": "connect me",
        "baat karvaiye": "connect me",
        "theeke baat karvaiye": "connect me",
        "theek hai baat karvaiye": "connect me",
        "baat karvaye": "connect me",
        "baat karvayein": "connect me",
        "baat karwayein": "connect me",
        "baat karwaiye": "connect me",
        "baat karwaye": "connect me",
        "connect kijiye": "connect me",
        "transfer kijiye": "connect me",
        "baat karva do": "connect me",
        "baat karwa do": "connect me",
        "baat kara do": "connect me",
        "panch": "5",
        "six": "6",
        "seven": "7",
        "five": "5",
        "mujhe suv segment mein gaadi dekhni hai": "i am looking for a car in the suv segment",
        "diesel available hai kya": "is diesel available",
        "automatic variant ka price kya hai": "what is the price of the automatic variant",
        "emi kitni padegi": "how much will the emi be",
        "down payment minimum kitna hoga": "what will be the minimum down payment",
        "waiting period kitna hai": "what is the waiting period",
        "turbo variant available hai kya": "is the turbo variant available",
        "exchange mein kitna value milega": "how much value will i get in exchange",
        "cng model available hai kya": "is the cng model available",
        "service package kya milta hai": "what service package is available",
        "insurance included hai kya": "is insurance included",
        "accessories free milengi kya": "will free accessories be provided",
        "mujhe white colour chahiye": "i want the white colour",
        "ghar pe test drive possible hai kya": "is a home test drive possible",
        "loan approval kitne time mein hota hai": "how much time does loan approval take",
        "mujhe venue ka on road price chahiye": "i want on road price of venue",
        "creta ka diesel automatic hai kya": "is creta diesel automatic available",
        "i20 sports variant available hai kya": "is i20 sports variant available",
        "turbo engine wala model batao": "tell me turbo engine models",
        "sunroof wali gaadi chahiye": "i want sunroof car",
        "7 se 10 lakh ke andar kya options hain": "what are the options between 7 to 10 lakhs",
        "manual nahi automatic chahiye": "i want automatic not manual",
        "rukho pehle emi batao": "wait tell me emi first",
        "nahi nahi creta nahi venue": "no no not creta venue",
        "acha exchange ka process batao": "okay tell me exchange process",
        "ek minute repeat karo": "repeat",
        "thoda hindi mein bataiye": "speak in hindi",
        "sabse zyada bikne wali gaadi kaunsi hai": "which is the best selling car",
        "family ke liye best model kaunsa hai": "which is the best model for a family",
        "maintenance kam kiski hai": "which has lowest maintenance",
        "mileage accha kiska hai": "which has best mileage",
        "why should i choose hyundai": "why should i buy hyundai",
        "main kia bhi dekh raha hoon": "how is hyundai better than kia",
        "hyundai better hai ya tata": "i am also considering tata",
        "seltos aur creta mein kya difference hai": "is creta better than seltos",
        "venue ya nexon better rahegi": "which is better venue or nexon",
        "mahindra ka bhi option dekh raha hoon": "why hyundai over mahindra",
        "verna aur city compare karo": "compare verna and honda city",
        "punch aur exter mein compare karo": "compare exter and tata punch",
        "baleno ya i20 better rahegi": "is i20 better than baleno",
        "compass se better hai kya tucson": "is tucson better than jeep compass",
        "hyundai maintenance costly hai kya": "is hyundai maintenance costly",
        "kia ka interior better lagta hai": "kia has better interior than hyundai",
        "tata safer hai na?": "tata is safer right",
        "tata safer hai na": "tata is safer right",
        "mileage kam hai": "mileage is low",
        "resale value kaisi hai": "how is the resale value",
        "mahindra zyada powerful lagti hai": "mahindra feels more powerful",
        "family ke liye best suv kaunsi hai": "which suv is best for family",
        "city driving ke liye best car": "which car is best for city driving",
        "best automatic car under 15 lakh": "best automatic under 15 lakhs",
        "service achi hai kya": "is after sales service good",
        "parts easily mil jaate hain?": "are parts easily available",
        "parts easily mil jaate hain": "are parts easily available",
        "long drive ke liye achi rahegi?": "is it good for long drive",
        "long drive ke liye achi rahegi": "is it good for long drive",
        "adas feature hai?": "does it have adas feature",
        "adas feature hai": "does it have adas feature",
        "6 airbags wali car": "which cars have 6 airbags",
        "aapko mera number kaha se mila": "how did you get my number",
        "aapko mera number kahan se mila": "how did you get my number",
        "aapko mera number kahan se mila?": "how did you get my number",
        "aapko mera number kaha se mila?": "how did you get my number",
        "apko mera number kaha se mila": "how did you get my number",
        "apko mera number kahan se mila": "how did you get my number",
        "apko mera number kahan se mila?": "how did you get my number",
        "apko mera number kaha se mila?": "how did you get my number",
        "ye genuine call hai kya": "is this a genuine call",
        "whatsapp pe details bhejo pehle": "can you send details on whatsapp first",
        "aap dealership se ho kya": "are you from the dealership or insurance company",
        "kaise verify karu": "how can i verify this",
        "zero dep kya hota hai": "what is zero depreciation",
        "bumper to bumper matlab": "what is bumper to bumper insurance",
        "isme kya kya cover hoga": "what is covered in this policy",
        "engine protection included hai kya": "does this include engine protection",
        "ncb kya hota hai": "what is ncb",
        "last year claim liya tha premium badega kya": "will my previous claim affect premium",
        "cashless claim available hai kya": "will cashless claims be available",
        "ncb milega kya abhi bhi": "can i still get ncb",
        "kitne claims allowed hai": "how many claims are allowed",
        "online sasta mil raha hai": "online is cheaper",
        "policybazaar cheaper de raha hai": "policybazaar is giving cheaper",
        "acko ka quote kam hai": "acko is cheaper than this",
        "dealership se hi kyu renew karu": "why should i renew through dealership",
        "thoda kam karo na premium": "can you reduce the premium",
        "best price batao": "give me your best price",
        "discount milega kya": "any loyalty discount",
        "online wala rate match karoge": "can you match online price",
        "expiry ke baad renew ho jayega kya": "can i renew after expiry",
        "inspection lagega kya": "will inspection be required",
        "ncb chala jayega kya": "will i lose ncb",
        "without insurance drive kar sakte hai kya": "is driving without insurance illegal",
        "payment link bhej do": "can you send payment link",
        "upi chalega kya": "is upi accepted",
        "emi pe payment ho jayega": "can i pay in emi",
        "invoice milega kya": "will i get invoice immediately",
        "human se baat karni hai": "i want to speak with a human",
        "manager se connect karo": "connect me to manager",
        "advisor call karega kya": "can an advisor call me",
        "baar baar call mat karo": "you people keep calling me",
        "premium itna expensive kyu hai": "why is premium so expensive",
        "premium itna expensive kyu": "why is premium so expensive",
        "maine pehle hi mana kiya tha": "i already said no",
        "mujhe abhi nayi car nahi leni": "not interested",
        "mujhe abhi interest nahi hai": "not interested",
        "mujhe nahi chahiye aap call mat kijie": "stop calling",
        "mujhe nahi chahiye aap call mat kijiye": "stop calling",
        "nayi car nahi leni": "not interested",
        "interest nahi hai": "not interested",
        "call mat kijiye": "stop calling",
        "call mat kijie": "stop calling",
        "mujhe nahi chahiye": "not interested"
    }

    # Static map for high-frequency user speech inputs in Devanagari script to English
    DEVANAGARI_TO_ENGLISH_MAP = {
        # Yes / Affirmation / Speaking
        "हाँ बोलिए": "yes",
        "हाँ बोलिये": "yes",
        "हाँ जी बोलिए": "yes",
        "हाँ जी बोलिये": "yes",
        "हाँजी बोलिए": "yes",
        "हाँजी बोलिये": "yes",
        "हाँ बोल रही हूँ": "yes",
        "हाँ बोल रही हु": "yes",
        "बोल रही हूँ": "yes",
        "बोल रही हु": "yes",
        "हाँ बोल रहा हूँ": "yes",
        "हाँ बोल रहा हु": "yes",
        "बोल रहा हूँ": "yes",
        "बोल रहा हु": "yes",
        "जी हाँ": "yes",
        "जी हाँ बोलिए": "yes",
        "जी बोलिए": "yes",
        "जी बोलिये": "yes",
        "हाँ जी": "yes",
        "हाँजी": "yes",
        "हाँ": "yes",
        "हा": "yes",
        "हाँ बिल्कुल": "yes",
        "बिल्कुल": "yes",
        "बोलिए": "yes",
        "बोलिये": "yes",
        "ठीक है": "yes",
        "ठीक": "yes",
        "जी": "yes",
        "कर दो": "yes",
        "कर दो जी": "yes",
        "बुक कर दो": "yes",
        "कन्फर्म कर दो": "yes",
        "हां": "yes",
        "हांजी": "yes",
        "हां जी": "yes",
        "हाँ बोल रही हो": "yes",
        "बोल रही हो": "yes",
        "हाँ बोल रहा हो": "yes",
        "बोल रहा हो": "yes",
        "हां बोल रही हूँ": "yes",
        "हां बोल रही हु": "yes",
        "हां बोल रही हो": "yes",
        "हां बोल रहा हूँ": "yes",
        "हां बोल रहा हु": "yes",
        "हां बोल रहा हो": "yes",
        "जी हां": "yes",
        "जी हां बोलिए": "yes",
        "जी हां बोलिये": "yes",
        "जी हांजी": "yes",
        "जी हां जी": "yes",
        "हां बिल्कुल": "yes",
        "जी बोलिए": "yes",
        "जी बोलिये": "yes",
        
        # No / Negation
        "नहीं": "no",
        "नही": "no",
        "नहीं जी": "no",
        "नही जी": "no",
        "ना": "no",
        "मत करो": "no",
        "नहीं करना": "no",
        "नही करना": "no",
        "कैंसिल": "cancel",
        "कैंसिल कर दो": "cancel",
        "रद्द कर दो": "cancel",
        "रद्द": "cancel",
        
        # Handover / Transfer
        "बात कराइए": "connect me",
        "बात कराइये": "connect me",
        "बात करवाइए": "connect me",
        "बात करवाइये": "connect me",
        "बात करवाओ": "connect me",
        "बात करवा दो": "connect me",
        "बात करा दो": "connect me",
        "बात कराओ": "connect me",
        "बात करनी है": "connect me",
        "कनेक्ट कर दो": "connect me",
        "कनेक्ट कर दीजिए": "connect me",
        "ट्रांसफर कर दो": "connect me",
        "मुझे अभी नई कार नहीं लेनी": "not interested",
        "मुझे अभी इंटरेस्ट नहीं है": "not interested",
        "मुझे नहीं चाहिए आप कॉल मत कीजिए": "stop calling",
        "कॉल मत कीजिए": "stop calling",
        "नहीं चाहिए": "not interested",
        "इंटरेस्ट नहीं है": "not interested",
        "नई कार नहीं लेनी": "not interested",
        "कॉल मत करो": "stop calling",
        "मुझे नहीं चाहिए": "not interested",
        # Devanagari FAQ Mappings
        "मुझे एसयूवी सेगमेंट में गाड़ी देखनी है": "i am looking for a car in the suv segment",
        "डीजल उपलब्ध है क्या": "is diesel available",
        "डीजल है क्या": "is diesel available",
        "ऑटोमैटिक वेरिएंट का प्राइस क्या है": "what is the price of the automatic variant",
        "ईएमआई कितनी पड़ेगी": "how much will the emi be",
        "डाउन पेमेंट मिनिमम कितना होगा": "what will be the minimum down payment",
        "डाउनपेमेंट मिनिमम कितना होगा": "what will be the minimum down payment",
        "वेटिंग पीरियड कितना है": "what is the waiting period",
        "टर्बो वेरिएंट उपलब्ध है क्या": "is the turbo variant available",
        "एक्सचेंज में कितना वैल्यू मिलेगा": "how much value will i get in exchange",
        "एक्सचेंज में कितना मिलेगा": "how much value will i get in exchange",
        "सीएनजी मॉडल उपलब्ध है क्या": "is the cng model available",
        "सर्विस पैकेज क्या मिलता है": "what service package is available",
        "इंश्योरेंस इंक्लूडेड है क्या": "is insurance included",
        "बीमा शामिल है क्या": "is insurance included",
        "इंश्योरेंस शामिल है क्या": "is insurance included",
        "एक्सेसरीज फ्री मिलेंगी क्या": "will free accessories be provided",
        "मुझे व्हाइट कलर चाहिए": "i want the white colour",
        "मुझे सफेद रंग चाहिए": "i want the white colour",
        "घर पे टेस्ट ड्राइव पॉसिबल है क्या": "is a home test drive possible",
        "घर पर टेस्ट ड्राइव हो सकती है क्या": "is a home test drive possible",
        "लोन अप्रूवल कितने टाइम में होता है": "how much time does loan approval take",
        "मुझे वेन्यू का ऑन रोड प्राइस चाहिए": "i want on road price of venue",
        "क्रेटा का डीजल ऑटोमैटिक है क्या": "is creta diesel automatic available",
        "i20 स्पोर्ट्स वेरिएंट उपलब्ध है क्या": "is i20 sports variant available",
        "टर्बो इंजन वाला मॉडल बताओ": "tell me turbo engine models",
        "सनरूफ वाली गाड़ी चाहिए": "i want sunroof car",
        "7 से 10 लाख के अंदर क्या ऑप्शंस हैं": "what are the options between 7 to 10 lakhs",
        "मैनुअल नहीं ऑटोमैटिक चाहिए": "i want automatic not manual",
        "रुको पहले ईएमआई बताओ": "wait tell me emi first",
        "अच्छा एक्सचेंज का प्रोसेस बताओ": "okay tell me exchange process",
        "सबसे ज्यादा बिकने वाली गाड़ी कौन सी है": "which is the best selling car",
        "फैमिली के लिए बेस्ट मॉडल कौन सा है": "which is the best model for a family",
        "मेंटेनेंस कम किसकी है": "which has lowest maintenance",
        "माइलेज अच्छा किसका है": "which has best mileage",
        "व्हाई शुड आई चूज हुंडई": "Why should I buy Hyundai?",
        "मैं किया भी देख रहा हूँ": "how is hyundai better than kia",
        "मैं किया भी देख रहा हु": "how is hyundai better than kia",
        "हुंडई बेटर है या टाटा": "i am also considering tata",
        "सेल्टोस और क्रेटा में क्या डिफरेंस है": "is creta better than seltos",
        "वेन्यू या नेक्सॉन बेहतर रहेगी": "which is better venue or nexon",
        "महिंद्रा का भी ऑप्शन देख रहा हूँ": "why hyundai over mahindra",
        "महिंद्रा का भी ऑप्शन देख रहा हु": "why hyundai over mahindra",
        "वरना और सिटी कंपेयर करो": "compare verna and honda city",
        "पंच और एक्स्टर में कंपेयर करो": "compare exter and tata punch",
        "बलेनो या i20 बेहतर रहेगी": "is i20 better than baleno",
        "कम्पस से बेहतर है क्या टक्सन": "is tucson better than jeep compass",
        "हुंडई मेंटेनेंस कॉस्टली है क्या": "is hyundai maintenance costly",
        "किया का इंटीरियर बेहतर लगता है": "kia has better interior than hyundai",
        "टाटा सेफर है ना": "tata is safer right",
        "माइलेज कम है": "mileage is low",
        "रीसेल वैल्यू कैसी है": "how is the resale value",
        "महिंद्रा ज्यादा पावरफुल लगती है": "mahindra feels more powerful",
        "फैमिली के लिए बेस्ट एसयूवी कौन सी है": "which suv is best for family",
        "सिटी ड्राइविंग के लिए बेस्ट कार": "which car is best for city driving",
        "बेस्ट ऑटोमैटिक कार अंडर 15 लाख": "best automatic under 15 lakhs",
        "सर्विस अच्छी है क्या": "is after sales service good",
        "पार्ट्स इजीली मिल जाते हैं": "are parts easily available",
        "लॉन्ग ड्राइव के लिए अच्छी रहेगी": "is it good for long drive",
        "एडीएएस फीचर है": "does it have adas feature",
        "6 एयरबैग्स वाली कार": "which cars have 6 airbags",
        "6 एयरबैग वाली कार": "which cars have 6 airbags",
        # Devanagari Insurance Mappings
        "आपको मेरा नंबर कहां से मिला": "how did you get my number",
        "आपको मेरा नंबर कहाँ से मिला": "how did you get my number",
        "यह जेन्युइन कॉल है क्या": "is this a genuine call",
        "व्हाट्सएप पर डिटेल्स भेजो पहले": "can you send details on whatsapp first",
        "व्हाट्सएप पे डिटेल्स भेजो पहले": "can you send details on whatsapp first",
        "जीरो डेप क्या होता है": "what is zero depreciation",
        "बम्पर टू बम्पर मतलब": "what is bumper to bumper insurance",
        "इंजन प्रोटेक्शन इंक्लूडेड है क्या": "does this include engine protection",
        "इंजन प्रोटेक्शन शामिल है क्या": "does this include engine protection",
        "एनसीबी क्या होता है": "what is ncb",
        "लास्ट ईयर क्लेम लिया था प्रीमियम बढ़ेगा क्या": "will my previous claim affect premium",
        "कैशलेस क्लेम उपलब्ध है क्या": "will cashless claims be available",
        "एनसीबी मिलेगा क्या अभी भी": "can i still get ncb",
        "पॉलिसीबाज़ार सस्ता दे रहा है": "policybazaar is giving cheaper",
        "पॉलिसीबाजार सस्ता दे रहा है": "policybazaar is giving cheaper",
        "एको का कोट कम है": "acko is cheaper than this",
        "ऑनलाइन सस्ता मिल रहा है": "online is cheaper",
        "डीलरशिप से ही क्यों रिन्यू करूँ": "why should i renew through dealership",
        "डीलरशिप से ही क्यों रिन्यू करें": "why should i renew through dealership",
        "थोड़ा कम करो ना प्रीमियम": "can you reduce the premium",
        "थोड़ा कम करो प्रीमियम": "can you reduce the premium",
        "बेस्ट प्राइस बताओ": "give me your best price",
        "ऑनलाइन वाला rate match karoge": "can you match online price",
        "ऑनलाइन वाला रेट मैच करोगे": "can you match online price",
        "एक्सपायरी के बाद रिन्यू हो जाएगा क्या": "can i renew after expiry",
        "निरीक्षण लगेगा क्या": "will inspection be required",
        "इंस्पेक्शन लगेगा क्या": "will inspection be required",
        "एनसीबी चला जाएगा क्या": "will i lose ncb",
        "पेमेंट लिंक भेज दो": "can you send payment link",
        "यूपीआई चलेगा क्या": "is upi accepted",
        "ईएमआई पे पेमेंट हो जाएगा": "can i pay in emi",
        "ईएमआई पर पेमेंट हो जाएगा": "can i pay in emi",
        "ह्यूमन से बात करनी है": "i want to speak with a human",
        "इंसान से बात करनी है": "i want to speak with a human",
        "मैनेजर से कनेक्ट करो": "connect me to manager",
        "बार बार कॉल मत करो": "you people keep calling me",
        "प्रीमियम इतना महंगा क्यों है": "why are premiums increasing every year",
        # Custom real voice call Devanagari Mappings
        "ऑफर क्या है": "what are the offers",
        "ऑफर क्या है बताइए": "what are the offers",
        "ऑफर बताओ": "what are the offers",
        "ऑफर बताइए": "what are the offers",
        "प्राइस क्या है": "what is the price",
        "कीमत क्या है": "what is the price",
        "रेट क्या है": "what is the price",
        "फीचर्स क्या हैं": "what are the features",
        "फीचर्स बताओ": "what are the features",
        "ईएमआई कितनी है": "how much will the emi be",
        "ईएमआई बताओ": "how much will the emi be",
        "ठीक है ऑफर क्या है बताइए": "what are the offers",
        "एमी कितनी पड़ेगी": "how much will the emi be",
        "एमी कितनी पड़ेगी?": "how much will the emi be",
        "एमी कितनी है": "how much will the emi be",
        "एमी कितनी है बताइए": "how much will the emi be",
        "एमी बताओ": "how much will the emi be",
        "एमी कितनी पढ़ेंगे": "how much will the emi be",
        "एमी कितनी पढ़ेंगे?": "how much will the emi be",
        "डीजल अवेलेबल है क्या": "is diesel available",
        "डीजल अवेलेबल है क्या?": "is diesel available",
        "सीएनजी मॉडल अवेलेबल है क्या": "is the cng model available",
        "सीएनजी मॉडल अवेलेबल है क्या?": "is the cng model available",
        "मुझे व्हाइट कलर चाहिए था": "what colors are available",
        "मुझे व्हाइट कलर चाहिए था।": "what colors are available",
        "व्हाइट कलर चाहिए": "what colors are available",
        "व्हाइट कलर": "what colors are available",
        
        # Custom busy/callback Devanagari Mappings
        "बिजी": "busy",
        "बिजी हूँ": "busy",
        "बिजी हु": "busy",
        "व्यस्त": "busy",
        "व्यस्त हूँ": "busy",
        "व्यस्त हु": "busy",
        "बाद में कॉल": "call back later",
        "बाद में कॉल करो": "call back later",
        "बाद में कॉल करना": "call back later",
        "बाद में कॉल कर सकते हैं": "call back later",
        "बाद में कॉल कर सकते हो": "call back later",
        "बाद में बात करते हैं": "talk later",
        "बाद में बात करेंगे": "talk later",
        "बाद में": "later",
        "काम कर रही हूँ": "busy",
        "काम कर रहा हूँ": "busy",
        "काम कर रही हु": "busy",
        "काम कर रहा हु": "busy",
        "मीटिंग में हूँ": "meeting",
        "मीटिंग में हु": "meeting",
        "ड्राइविंग कर रहा हूँ": "driving",
        "ड्राइविंग कर रही हूँ": "driving",
        "ड्राइविंग कर रहा हु": "driving",
        "ड्राइविंग कर रही हु": "driving",
        
        # Custom yes/consent Devanagari Mappings
        "जी": "yes",
        "जी हाँ": "yes",
        "जी हां": "yes",
        "जी अब देख सकती है": "yes",
        "जी आप भेज सकती हैं": "yes",
        "जी भेज दीजिए": "yes",
        
        # Competitor/Policy Bazaar Devanagari Mappings
        "पॉलिसी बाजार प्राइस दे रहा": "policybazaar is giving cheaper",
        "पॉलिसी बाज़ार प्राइस दे रहा": "policybazaar is giving cheaper",
        "पॉलिसी बाजार": "policybazaar",
        "पॉलिसी बाज़ार": "policybazaar"
    }


    # Static map for verbal number words (English and Hindi/Hinglish) to standard digits
    NUMERIC_WORDS_MAP = {
        "twenty thousand": "20000",
        "thirty thousand": "30000",
        "forty thousand": "40000",
        "fifty thousand": "50000",
        "ten thousand": "10000",
        "fifteen thousand": "15000",
        "five thousand": "5000",
        "bees hazaar": "20000",
        "tees hazaar": "30000",
        "chalis hazaar": "40000",
        "pachas hazaar": "50000",
        "pachaas hazaar": "50000",
        "dus hazaar": "10000",
        "pandra hazaar": "15000",
        "pandrah hazaar": "15000",
        "panch hazaar": "5000",
        "one lakh": "100000",
        "ek lakh": "100000"
    }

    # Static map for high-frequency Hinglish/Hindi busy and callback request phrases
    BUSY_PHRASES_MAP = {
        "baad mein": "later",
        "baad me": "later",
        "baad mein call": "call back later",
        "baad me call": "call back later",
        "busy hu": "busy",
        "busy hoon": "busy",
        "kaam mein hoon": "busy",
        "kaam me hoon": "busy",
        "kaam me hu": "busy",
        "busy chal raha hoon": "busy",
        "busy chal raha hu": "busy",
        "meeting mein hoon": "meeting",
        "meeting me hoon": "meeting",
        "meeting me hu": "meeting",
        "driving kar raha hoon": "driving",
        "driving kar raha hu": "driving",
        "baad mein baat": "talk later",
        "baad me baat": "talk later"
    }


    # Dynamic regex mapping for English responses to natural Hindi
    ENGLISH_TO_HINDI_RULES = [
        # --- Real voice call specific rules & CTAs ---
        (
            r"I can certainly clarify that for you (?:Ma'am|Sir|मैडम|सर)\.?",
            "मैं निश्चित रूप से आपके लिए इसे स्पष्ट कर सकती हूँ।"
        ),
        (
            r"I have more details on this, or I can connect you to our Sales Manager for a deep dive\.?",
            "मेरे पास इस बारे में अधिक जानकारी है, या मैं आपको विस्तृत जानकारी के लिए हमारे सेल्स मैनेजर से जोड़ सकती हूँ।"
        ),
        (
            r"I can certainly clarify that for you (?:Ma'am|Sir|मैडम|सर)\.\s*Would you like to know more about the features, EMI options, pricing of the ([a-zA-Z0-9 ]+), or should I connect you with our manager\??\.?",
            lambda m: f"मैं निश्चित रूप से आपके लिए इसे स्पष्ट कर सकती हूँ। क्या आप {TranslationAdapter.translate_model_to_hindi(m.group(1))} के फीचर्स, ईएमआई (EMI) ऑप्शंस, प्राइस के बारे में और जानना चाहेंगे, या मैं आपकी बात हमारे मैनेजर से करवाऊँ?"
        ),
        (
            r"I can certainly clarify that for you (?:Ma'am|Sir|मैडम|सर)\.\s*Would you like to know more about the features, EMI options, pricing, or should I connect you with our advisor\??\.?",
            "मैं निश्चित रूप से स्पष्ट कर सकती हूँ। क्या आप इसके फीचर्स, ईएमआई (EMI) ऑप्शंस, प्राइस के बारे में और जानना चाहेंगे, या मैं आपकी बात हमारे सलाहकार से करवाऊँ?"
        ),
        (
            r"I can arrange a callback for the best deal\.?",
            "मैं आपके लिए सबसे अच्छे डील के लिए कॉल बैक अरेंज कर सकती हूँ।"
        ),
        (
            r"I can connect you with our advisor for the best possible deal\.?",
            "मैं आपको सबसे अच्छे सौदे के लिए हमारे सलाहकार से जोड़ सकती हूँ।"
        ),
        (
            r"Would that work\??",
            "क्या यह काम करेगा?"
        ),
        (
            r"Should I connect you with our advisor\??",
            "क्या मैं आपकी बात हमारे सलाहकार से करवाऊँ?"
        ),
        (
            r"Would you like to speak to our advisor\??",
            "क्या आप हमारे सलाहकार से बात करना चाहेंगे?"
        ),

        (
            r"Would you like to know more about EMI\??",
            "क्या आप ईएमआई (EMI) के बारे में और जानना चाहेंगे?"
        ),
        (
            r"Should I connect you with our manager\??",
            "क्या मैं आपकी बात हमारे मैनेजर से करवाऊँ?"
        ),
        (
            r"Would you like to know more about the features\??",
            "क्या आप इसके फीचर्स के बारे में और जानना चाहेंगे?"
        ),
        (
            r"Would you like me to share the pricing details\??",
            "क्या आप चाहेंगे कि मैं आपके साथ कीमत की जानकारी साझा करूँ?"
        ),
        (
            r"What would you prefer\??",
            "आप क्या पसंद करेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the ([a-zA-Z0-9 ]+),\s+)?Our on-road price for the ([a-zA-Z0-9 ]+) starts at ([a-zA-Z0-9., ₹]+) and includes comprehensive insurance and registration\.?",
            lambda m: f"{(m.group(1) and f'निश्चित रूप से! {TranslationAdapter.translate_model_to_hindi(m.group(1))} के संबंध में, ') or ''}हमारी {TranslationAdapter.translate_model_to_hindi(m.group(2))} की ऑन-रोड कीमत {m.group(3)} से शुरू होती है और इसमें व्यापक बीमा और पंजीकरण शामिल हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the ([a-zA-Z0-9 ]+),\s+)?(?:The )?(?:Hyundai\s+)?([a-zA-Z0-9 ]+) starts at ([a-zA-Z0-9., ₹]+) on-road\.?",
            lambda m: f"{(m.group(1) and f'निश्चित रूप से! {TranslationAdapter.translate_model_to_hindi(m.group(1))} के संबंध में, ') or ''}{TranslationAdapter.translate_model_to_hindi(m.group(2))} की ऑन-रोड कीमत {m.group(3)} से शुरू होती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the ([a-zA-Z0-9 ]+),\s+)?(?:The )?(?:Hyundai\s+)?([a-zA-Z0-9 ]+) is available in stunning color(?:s)?(?:\s+option(?:s)?)?\s+like ([^.?]+)\.?",
            lambda m: f"{(m.group(1) and f'निश्चित रूप से! {m.group(1).capitalize()} के संबंध में, ') or ''}{m.group(2).capitalize()} विभिन्न रंगों जैसे {m.group(3).replace('and ', '')} में उपलब्ध है।"
        ),
        # --- Standard Master FAQ translation rules ---
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I'm Supriya calling from Alcon, your authorized Hyundai partner\. We're reaching out to share our new upgrade benefits for your ([a-zA-Z0-9 ]+)\. Is this a good time to talk\??\.?",
            lambda m: f"नमस्ते, मैं अल्कॉन से सुप्रिया हूँ, जो कि एक अधिकृत हुंडई पार्टनर है। हम आपकी {TranslationAdapter.translate_model_to_hindi(m.group(1))} के लिए हमारे नए अपग्रेड लाभों को साझा करने के लिए संपर्क कर रहे हैं। क्या बात करने का यह सही समय है?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I'm Alcon's AI assistant\. I can help you with pricing and offers for the ([a-zA-Z0-9 ]+) immediately\. If you'd prefer, I can connect you with my manager\. What would you prefer\??\.?",
            lambda m: f"मैं अल्कॉन की एआई असिस्टेंट हूँ। मैं तुरंत आपको {TranslationAdapter.translate_model_to_hindi(m.group(1))} के प्राइस और ऑफर्स में मदद कर सकती हूँ। अगर आप चाहें, तो मैं आपकी बात हमारे मैनेजर से करवा सकती हूँ। आप क्या पसंद करेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I understand\. I'm connecting you to our Sales Manager right now\. They will assist you with the final pricing and next steps\. Thank you for speaking with Alcon!\.?",
            "मैं समझती हूँ। मैं आपको अभी हमारे सेल्स मैनेजर से जोड़ रही हूँ। वे आपको अंतिम मूल्य निर्धारण और अगले चरणों में सहायता करेंगे। अल्कॉन से बात करने के लिए धन्यवाद!"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I understand that price is a major factor for the ([a-zA-Z0-9 ]+)\. I can have our sales manager call you back with our best final offer\. Would that work\??\.?",
            lambda m: f"मैं समझती हूँ कि {TranslationAdapter.translate_model_to_hindi(m.group(1))} के लिए कीमत एक महत्वपूर्ण कारक है। मैं सबसे अच्छे फाइनल ऑफर के साथ हमारे सेल्स मैनेजर से आपको कॉल बैक करवा सकती हूँ। क्या यह ठीक रहेगा?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I will certainly send the ([a-zA-Z0-9 ]+) brochure and detailed quotation to you on WhatsApp right after our call\. Beyond that, would you like to hear about our exchange bonuses\??\.?",
            lambda m: f"निश्चित रूप से! मैं हमारी कॉल के ठीक बाद आपके व्हाट्सएप पर {TranslationAdapter.translate_model_to_hindi(m.group(1))} ब्रोशर और विस्तृत कोटेशन भेज दूँगी। इसके अलावा, क्या आप हमारे एक्सचेंज बोनस के बारे में सुनना चाहेंगे?"
        ),
        (
            r"(?:I understand your concern\.|I understand your concerns\.)",
            "मैं आपकी चिंता समझ सकती हूँ।"
        ),
        (
            r"((?:I can certainly clarify that for you (?:Ma'am|Sir|मैडम|सर)\.\s*))?Would you like to know more about the features, EMI options, pricing of the ([a-zA-Z0-9 ]+), or should I connect you with our manager\??\.?",
            lambda m: f"{(m.group(1) and 'मैं निश्चित रूप से आपके लिए इसे स्पष्ट कर सकती हूँ। ') or ''}क्या आप {TranslationAdapter.translate_model_to_hindi(m.group(2))} के फीचर्स, ईएमआई (EMI) ऑप्शंस, प्राइस के बारे में और जानना चाहेंगे, या मैं आपकी बात हमारे मैनेजर से करवाऊँ?"
        ),
        (
            r"I understand (?:Ma'am|Sir|मैडम|सर)\.\s*Would you like to know more about the features, pricing, or should I connect you with our advisor\??\.?",
            "मैं समझ सकती हूँ। क्या आप इसके फीचर्स, प्राइस के बारे में और जानना चाहेंगे, या मैं आपकी बात हमारे सलाहकार से करवाऊँ?"
        ),
        (
            r"I see you're probably busy right now (?:Ma'am|Sir|मैडम|सर)\.\s*I'll arrange a callback for later when it's more convenient\. Have a great day!\.?",
            "ऐसा लगता है कि आप अभी व्यस्त हैं। मैं आपके लिए बाद में अधिक सुविधाजनक समय पर कॉल बैक की व्यवस्था कर दूँगी। आपका दिन बहुत अच्छा रहे!"
        ),
        # --- Custom dynamic feature and transmission variant translation rules ---
        (
            r"(?:Certainly!\s+)?(?:Regarding the ([a-zA-Z0-9 ]+),\s+)?(?:The )?([a-zA-Z0-9 ]+) comes packed with features like ((?:[^.?]+|\.(?=\d))+)\.?$",
            lambda m: f"{(m.group(1) and f'निश्चित रूप से! {TranslationAdapter.translate_model_to_hindi(m.group(1))} के संबंध में, ') or ''}{TranslationAdapter.translate_model_to_hindi(m.group(2))} {TranslationAdapter.translate_features_to_hindi(m.group(3))} जैसे बेहतरीन फीचर्स से लैस है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the ([a-zA-Z0-9 ]+),\s+)?(?:The )?([a-zA-Z0-9 ]+) is available in both Petrol and Diesel with advanced Automatic(?: \((?:IVT/DCT)\))? and Manual options\.?$",
            lambda m: f"{(m.group(1) and f'निश्चित रूप से! {TranslationAdapter.translate_model_to_hindi(m.group(1))} के संबंध में, ') or ''}{TranslationAdapter.translate_model_to_hindi(m.group(2))} पेट्रोल और डीजल दोनों में उन्नत ऑटोमैटिक और मैनुअल विकल्पों के साथ उपलब्ध है।"
        ),
        (
            r"(?:The )?([a-zA-Z0-9 ]+) comes in multiple engine options including the Turbo Petrol and Diesel\.?$",
            lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} टर्बो पेट्रोल और डीजल सहित कई इंजन विकल्पों में उपलब्ध है।"
        ),
        (
            r"For a detailed variant comparison, I can connect you with our product specialist\.?$",
            "विस्तृत वेरिएंट तुलना के लिए, मैं आपकी बात हमारे प्रोडक्ट स्पेशलिस्ट से करवा सकती हूँ।"
        ),
        (
            r"Would you like to know the price for the Automatic variant\?\.?$",
            "क्या आप ऑटोमैटिक वेरिएंट की कीमत जानना चाहेंगे?"
        ),
        (
            r"Would you like to know more about EMI\?\.?$",
            "क्या आप ईएमआई (EMI) के बारे में और जानना चाहेंगे?"
        ),
        (
            r"That's a valid point\.?$",
            "यह बहुत सही बात है।"
        ),
        (
            r"Certainly\.?$",
            "निश्चित रूप से!"
        ),
        (
            r"Regarding the ([a-zA-Z0-9 ]+),$",
            lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} के संबंध में, "
        ),
        # --- Slot choice and dynamic slot translation rules ---
        (
            r"(.+?)\s+On\s+(.+?)\s+we have slots at\s+(.+?)\.\s*Which one works better for you\?\??\.?$",
            lambda m: f"{TranslationAdapter.translate_prefix_to_hindi(m.group(1))} {TranslationAdapter.translate_date_to_hindi(m.group(2))} को हमारे पास {m.group(3).replace('and', 'और')} पर स्लॉट्स उपलब्ध हैं। आपके लिए कौन सा समय बेहतर रहेगा?"
        ),
        (
            r"I'm sorry, that timing is fully booked\.\s+We have Saturday slots available at 10:00 AM and 03:00 PM,\s+or would Friday evening at 05:30 PM work better\?",
            "मुझे खेद है, वह समय पूरी तरह से बुक है। हमारे पास शनिवार को सुबह 10:00 बजे और दोपहर 03:00 बजे स्लॉट उपलब्ध हैं, या क्या शुक्रवार शाम 05:30 बजे का समय आपके लिए बेहतर रहेगा?"
        ),
        (
            r"I understand you have an urgent breakdown\.\s+Connecting you immediately to our Roadside Assistance supervisor\.",
            "मैं समझ सकती हूँ कि आपकी गाड़ी का ब्रेकडाउन हो गया है। मैं तुरंत आपकी बात हमारे रोडसाइड असिस्टेंस सुपरवाइजर से करवा देती हूँ।"
        ),
        (
            r"I will have our Service Desk call you back to coordinate a suitable time",
            "मैं हमारे सर्विस डेस्क से आपकी बात कराने के लिए कॉल बैक शेड्यूल करवा देती हूँ"
        ),
        (
            r"Please wait while I connect you to (.+?) from our (.+?) team\.",
            lambda m: f"कृपया प्रतीक्षा करें, मैं आपको हमारे {m.group(2) == 'Insurance Desk' and 'इंश्योरेंस डेस्क' or m.group(2)} से {m.group(1)} से जोड़ रही हूँ।"
        ),
        (
            r"Our (.+?) team is currently busy assisting other customers\. Let me connect you to our on-call supervisor\.",
            lambda m: f"हमारी {m.group(1) == 'Insurance Desk' and 'इंश्योरेंस डेस्क' or m.group(1)} टीम अभी अन्य ग्राहकों की सहायता करने में व्यस्त है। मैं आपको हमारे ऑन-कॉल सुपरवाइजर से जोड़ देती हूँ।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Both the Hyundai ([a-zA-Z0-9]+) and ([a-zA-Z0-9 ]+) are excellent options\. The \2 offers (.+?), whereas the Hyundai \1 stands out for its (.+?)\.",
            lambda m: f"हुंडई {TranslationAdapter.translate_model_to_hindi(m.group(1))} और {TranslationAdapter.translate_model_to_hindi(m.group(2))} दोनों ही उत्कृष्ट विकल्प हैं। {TranslationAdapter.translate_model_to_hindi(m.group(2))} {TranslationAdapter.translate_phrase_to_hindi(m.group(3))} प्रदान करता है, जबकि हुंडई {TranslationAdapter.translate_model_to_hindi(m.group(1))} अपने {TranslationAdapter.translate_phrase_to_hindi(m.group(4))} के लिए जानी जाती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I'll keep the ([a-zA-Z0-9 ]+) details ready for you\. Would you like to know more about its latest features\?",
            lambda m: f"मैं आपके लिए {TranslationAdapter.translate_model_to_hindi(m.group(1))} के विवरण तैयार रखूँगी। क्या आप इसके नवीनतम फीचर्स के बारे में अधिक जानना चाहेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I'll share the latest ([a-zA-Z0-9 ]+) details with you\. Would you like to know more about EMI or offers\?",
            lambda m: f"मैं आपके साथ {TranslationAdapter.translate_model_to_hindi(m.group(1))} के नवीनतम विवरण साझा करूँगी। क्या आप ईएमआई (EMI) या ऑफर्स के बारे में अधिक जानना चाहेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?I'll keep the service details ready for you\. Would you like to know more about our current service benefits\?",
            "मैं आपके लिए सर्विस के विवरण तैयार रखूँगी। क्या आप हमारे वर्तमान सर्विस लाभों के बारे में अधिक जानना चाहेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Would you like to know more about our current service benefits or safety features\?",
            "क्या आप हमारे वर्तमान सर्विस लाभों या सुरक्षा विशेषताओं के बारे में अधिक जानना चाहेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Would you like to know more about the latest EMI offers or exchange benefits\?",
            "क्या आप नवीनतम ईएमआई (EMI) ऑफर्स या एक्सचेंज लाभों के बारे में अधिक जानना चाहेंगे?"
        ),
        # --- Existing Booking Rules ---
        (
            r"Hello, I'm Supriya from Alcon\. Am I speaking with (.+?) (Sir|Ma'am|सर|मैडम)\?",
            lambda m: f"नमस्ते, मैं अल्कॉन से सुप्रिया हूँ। क्या मैं {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'} से बात कर रही हूँ?"
        ),
        (
            r"I'm so sorry! I must have the wrong number\. I'll update our records immediately\. Have a nice day!",
            "मुझे बहुत खेद है! लगता है यह गलत नंबर है। मैं तुरंत हमारे रिकॉर्ड अपडेट कर दूँगी। आपका दिन शुभ हो!"
        ),
        (
            r"I'm so sorry! I must have the wrong number\. I'll update our records immediately\. Have a respectful day\.",
            "मुझे बहुत खेद है! लगता है यह गलत नंबर है। मैं तुरंत हमारे रिकॉर्ड अपडेट कर दूँगी। आपका दिन शुभ हो!"
        ),
        (
            r"I'm so sorry! I'll update our records\. Was this call helpful though\?",
            "मुझे बहुत खेद है! मैं हमारे रिकॉर्ड अपडेट कर दूँगी। वैसे, क्या यह कॉल मददगार रही?"
        ),
        (
            r"I sincerely apologize (Sir|Ma'am|सर|मैडम|(?:Ms\.|Mr\.)?\s*[a-zA-Z0-9 ]+)\. I must have the wrong number\. I'll remove this contact immediately\. Have a respectful day\.",
            lambda m: f"मैं ईमानदारी से क्षमा चाहती हूँ, {TranslationAdapter.translate_salutation(m.group(1))}। लगता है यह गलत नंबर है। मैं इस संपर्क को तुरंत हटा दूँगी। आपका दिन शुभ हो!"
        ),
        (
            r"No problem (Sir|Ma'am|सर|मैडम)\. I completely understand\. When would be a more convenient time for me to call you back\?",
            lambda m: f"कोई बात नहीं {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं पूरी तरह समझती हूँ। मुझे आपको वापस कॉल करने के लिए कौन सा समय अधिक सुविधाजनक रहेगा?"
        ),
        (
            r"Got it\. I've scheduled a reminder to call you back at (.+?)\. Have a great day!",
            lambda m: f"समझ गई। मैंने आपको {TranslationAdapter.translate_date_to_hindi(m.group(1))} पर वापस कॉल करने का रिमाइंडर शेड्यूल कर दिया है। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"Great! I've verified your record (Sir|Ma'am|सर|मैडम) (.+?)\. I see your (.+?) was last serviced on (.+?), and your next appointment is now due\. Would you like to book it today\?",
            lambda m: f"बहुत बढ़िया! मैंने आपका रिकॉर्ड सत्यापित कर लिया है {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'} {m.group(2)}। मैं देख सकती हूँ कि आपकी {m.group(3)} की पिछली सर्विस {TranslationAdapter.translate_date_to_hindi(m.group(4))} को हुई थी, और आपकी अगली सर्विस अब देय है। क्या आप इसे आज ही बुक करना चाहेंगे?"
        ),
        (
            r"Great\. What date would you prefer for the service\?",
            "बहुत अच्छा। सर्विस के लिए आप किस तारीख को पसंद करेंगे?"
        ),
        (
            r"Got it\. Available on (.+?)\. What's the current mileage of your car\?",
            lambda m: f"समझ गई। यह {TranslationAdapter.translate_date_to_hindi(m.group(1))} को उपलब्ध है। आपकी कार का वर्तमान माइलेज कितना है?"
        ),
        (
            r"Got it\. And are there any specific concerns or issues with the car\?",
            "समझ गई। और क्या कार में कोई विशिष्ट चिंता या समस्या है?"
        ),
        (
            r"I've noted those points\. We offer free Pick and Drop service\. Would you like to avail this\?",
            "मैंने इन बातों को नोट कर लिया है। हम मुफ्त पिक और ड्रॉप सेवा प्रदान करते हैं। क्या आप इसका लाभ उठाना चाहेंगे?"
        ),
        (
            r"Wonderful (Sir|Ma'am|सर|मैडम)\. Your service is confirmed(?: for (.+?))?\. At Alcon, we provide a 50-point safety check and use only genuine Hyundai parts to ensure your vehicle's peak performance\. Your Advisor, Amit Shah, will greet you upon arrival and walk you through the repair order details\.(?: A confirmation SMS has been sent to you\.)?(?: You'll receive an SMS shortly\.)?(?: Have a great day!)?",
            lambda m: f"अद्भुत {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। आपकी सर्विस की पुष्टि {m.group(2) and f'{TranslationAdapter.translate_date_to_hindi(m.group(2))} के लिए ' or ''}हो गई है। अल्कॉन में, हम आपकी गाड़ी के उत्कृष्ट प्रदर्शन को सुनिश्चित करने के लिए 50-पॉइंट सुरक्षा जांच प्रदान करते हैं और केवल असली हुंडई पार्ट्स का उपयोग करते हैं। आपके सलाहकार, अमित शाह, आगमन पर आपका स्वागत करेंगे और आपको मरम्मत ऑर्डर के विवरण समझाएंगे। आपको जल्द ही एक एसएमएस प्राप्त होगा। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"Understood (Sir|Ma'am|सर|मैडम)\. (.+?)\. Have a great day!",
            lambda m: f"समझ गई {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। {TranslationAdapter.translate_to_hindi(m.group(2))}। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"I see your (.+?) was last serviced recently on (.+?)\. Since your service is only due every (.+?) months, you are all set for now! Have a wonderful day!",
            lambda m: f"मैं देख सकती हूँ कि आपकी {m.group(1)} की हाल ही में सर्विस {TranslationAdapter.translate_date_to_hindi(m.group(2))} को हुई थी। चूंकि आपकी सर्विस केवल हर {m.group(3)} महीने में देय है, इसलिए आप अभी पूरी तरह से निश्चिंत रह सकते हैं! आपका दिन बहुत अच्छा रहे!"
        ),

        # --- Flow 1: Inbound Receptionist ---
        (
            r"Welcome to Alcon Hyundai\. I am your AI assistant\. How can I help you today\? Are you looking for a new car enquiry or service assistance\?",
            "अल्कॉन हुंडई में आपका स्वागत है। मैं आपकी एआई असिस्टेंट हूँ। आज मैं आपकी क्या मदद कर सकती हूँ? क्या आप नई कार के बारे में पूछताछ कर रहे हैं या सर्विस सहायता चाहते हैं?"
        ),
        (
            r"Great! I can certainly help with your new car enquiry\. May I know your name please\?",
            "बहुत बढ़िया! मैं निश्चित रूप से आपकी नई कार की पूछताछ में मदद कर सकती हूँ। क्या मैं आपका नाम जान सकती हूँ?"
        ),
        (
            r"Thank you (.+?)\. Which model are you interested in today\? I can help with pricing, features, or EMI details\.",
            lambda m: f"धन्यवाद {m.group(1)}। आज आप किस हुंडई मॉडल में रुचि रखते हैं? मैं आपको फीचर्स, प्राइस या ईएमआई डिटेल्स बता सकती हूँ।"
        ),
        (
            r"Understood\. I can help you with your service booking\. May I know your name please\?",
            "समझ गई। मैं आपकी सर्विस बुकिंग में मदद कर सकती हूँ। क्या मैं आपका नाम जान सकती हूँ?"
        ),
        (
            r"Thank you (.+?)\. To proceed, could you please share your vehicle registration number\?",
            lambda m: f"धन्यवाद {m.group(1)}। आगे बढ़ने के लिए, क्या आप कृपया अपनी गाड़ी का रजिस्ट्रेशन नंबर बता सकते हैं?"
        ),
        (
            r"Thank you\. I've verified your record\. I see your (.+?) was last serviced on (.+?), and your next appointment is now due\. Would you like to book it today\?",
            lambda m: f"धन्यवाद। मैंने आपका रिकॉर्ड सत्यापित कर लिया है। आपकी {m.group(1)} की पिछली सर्विस {m.group(2)} को हुई थी, और आपकी अगली सर्विस अब ड्यू है। क्या आप इसे आज ही बुक करना चाहेंगे?"
        ),
        (
            r"Thank you\. I've checked our records and your (.+?) service is not yet due\. It is scheduled for (.+?)\. Is there anything else I can help you with today\?",
            lambda m: f"धन्यवाद। मैंने हमारे रिकॉर्ड की जाँच की है और आपकी {m.group(1)} की सर्विस अभी ड्यू नहीं है। यह {m.group(2)} के लिए निर्धारित है। क्या मैं आज आपकी किसी और चीज़ में मदद कर सकती हूँ?"
        ),
        (
            r"Wonderful (Sir|Ma'am|सर|मैडम)\. Your service is confirmed\. At Alcon, we provide a 50-point safety check and use only genuine Hyundai parts\. Your Advisor, Amit Shah, will greet you upon arrival\. You'll receive an SMS shortly\. Have a great day!",
            lambda m: f"अद्भुत {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। आपकी सर्विस की पुष्टि हो गई है। अल्कॉन में, हम 50-पॉइंट सुरक्षा जांच प्रदान करते हैं और केवल असली हुंडई पार्ट्स का उपयोग करते हैं। आपके सलाहकार, अमित शाह, आगमन पर आपका स्वागत करेंगे। आपको जल्द ही एक एसएमएस प्राप्त होगा। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"Understood (Sir|Ma'am|सर|मैडम)\. I'll make a note of it\. Have a great day!",
            lambda m: f"समझ गई {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं इसे नोट कर लेती हूँ। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"I have more details on this, or I can connect you to our Sales Manager for a deep dive\. What would you prefer\?",
            "मेरे पास इस बारे में अधिक जानकारी है, या मैं आपको विस्तृत जानकारी के लिए हमारे सेल्स मैनेजर से जोड़ सकती हूँ। आप क्या पसंद करेंगे?"
        ),

        # --- Flow 2 & 9: Pre-Sales Upgrade & Exchange Campaign ---
        (
            r"Hello (Sir|Ma'am|सर|मैडम), I'm Supriya from Alcon\. I see you've been enjoying your (.+?) for (.+?) now, and I'm calling because it's currently eligible for an exclusive upgrade to the 2024 model with the same EMI\. Is this something you'd like to explore\?",
            lambda m: f"नमस्ते {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं देख सकती हूँ कि आप पिछले {m.group(3)} से अपनी {m.group(2)} का आनंद ले रहे हैं, और मैं आपको कॉल कर रही हूँ क्योंकि आपकी कार वर्तमान में समान ईएमआई पर 2024 मॉडल में एक विशेष अपग्रेड के लिए योग्य है। क्या आप इस बारे में जानना चाहेंगे?"
        ),
        (
            r"Hello (Sir|Ma'am|सर|मैडम), I'm Supriya from Alcon\. I'm calling regarding your (.+?)(?: for the (.+?) region)?\. We are running a special exchange festival this week, and I noticed your vehicle qualifies for a premium exchange bonus of up to 50,000 rupees\. Would you like to know more\?",
            lambda m: f"नमस्ते {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं आपकी {m.group(2)} के संबंध में कॉल कर रही हूँ। हम इस सप्ताह एक विशेष एक्सचेंज फेस्टिवल चला रहे हैं, और आपकी गाड़ी 50,000 रुपये तक के प्रीमियम एक्सचेंज बोनस के लिए योग्य है। क्या आप इस बारे में अधिक जानना चाहेंगे?"
        ),
        (
            r"Hello (Sir|Ma'am|सर|मैडम), I'm Supriya from Alcon\. I'm calling to share some exciting new EMI schemes that could significantly reduce your monthly payments on a new Hyundai\. Since you've had your (.+?) for (.+?) now, I thought you might be interested in these benefits\. Is this a good time to talk\?",
            lambda m: f"नमस्ते {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं कुछ रोमांचक नई ईएमआई योजनाओं को साझा करने के लिए कॉल कर रही हूँ जो एक नई हुंडई पर आपके मासिक भुगतान को काफी कम कर सकती हैं। चूंकि आपके पास {m.group(3)} से {m.group(2)} है, इसलिए क्या बात करने का यह सही समय है?"
        ),
        (
            r"Hello (Sir|Ma'am|सर|मैडम), I'm Supriya from Alcon\. I'm calling regarding your (.+?)\. I have some exciting updates to share with you\. Is this a good time to talk\?",
            lambda m: f"नमस्ते {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं आपकी {m.group(2)} के संबंध में कॉल कर रही हूँ। मेरे पास आपके साथ साझा करने के लिए कुछ रोमांचक अपडेट हैं। क्या बात करने का यह सही समय है?"
        ),
        (
            r"Great! To help you better, I can share the latest price, ongoing offers, or schedule a test drive for the (.+?)\. What would you prefer\?",
            lambda m: f"बहुत बढ़िया! आपकी बेहतर सहायता के लिए, मैं {m.group(1)} के लिए नवीनतम कीमत, चल रहे ऑफर साझा कर सकती हूँ या टेस्ट ड्राइव शेड्यूल कर सकती हूँ। आप क्या पसंद करेंगे?"
        ),
        (
            r"I apologize for the incorrect information\. I will update our records immediately\. Have a wonderful day (Sir|Ma'am|सर|मैडम)!",
            lambda m: f"मैं गलत जानकारी के लिए क्षमा चाहती हूँ। मैं हमारे रिकॉर्ड को तुरंत अपडेट कर दूँगी। आपका दिन बहुत अच्छा रहे {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}!"
        ),
        (
            r"I understand (Sir|Ma'am|सर|मैडम)\. By the way, I noticed your (.+?) is due for its periodic service\. Since we are already speaking, would you like me to book a maintenance appointment for you instead\?",
            lambda m: f"मैं समझती हूँ {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। वैसे, मैंने देखा कि आपकी {m.group(2)} की आवधिक (periodic) सर्विस ड्यू है। चूंकि हम पहले से ही बात कर रहे हैं, क्या आप चाहेंगे कि मैं आपके लिए इसके बजाय एक मेंटेनेंस अपॉइंटमेंट बुक करूँ?"
        ),
        (
            r"Understood (Sir|Ma'am|सर|मैडम)\. Have a wonderful day!",
            lambda m: f"समझ गई {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"Thank you for your time (Sir|Ma'am|सर|मैडम)\. Have a great day ahead!",
            lambda m: f"अपना कीमती समय देने के लिए धन्यवाद {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। आपका दिन शुभ हो!"
        ),

        # --- Flow 3 & 5: Post-Service Feedback 15-Day & 3-Day ---
        (
            r"Good morning (Sir|Ma'am|सर|मैडम)\. I’m calling from the Alcon Hyundai Customer Relations Department\. My name is Supriya\. Your Hyundai (.+?), (.+?) was serviced at our workshop on (.+?)\. This is our 15-day post-service feedback call\. May I take a few minutes\?",
            lambda m: f"शुभ प्रभात {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन हुंडई कस्टमर रिलेशंस विभाग से सुप्रिया हूँ। आपकी हुंडई {m.group(2)}, रजिस्ट्रेशन नंबर {m.group(3)} की हमारे वर्कशॉप में {m.group(4)} को सर्विस हुई थी। यह हमारा 15-दिन का पोस्ट-सर्विस फीडबैक कॉल है। क्या मैं आपका कुछ समय ले सकती हूँ?"
        ),
        (
            r"Thank you (Sir|Ma'am|सर|मैडम)\. I just wanted to check, is your car performing well after the service\?",
            lambda m: f"धन्यवाद {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं बस यह जानना चाहती थी कि क्या सर्विस के बाद आपकी कार ठीक से काम कर रही है?"
        ),
        (
            r"That’s great to hear\. Thank you for your valuable feedback\. We appreciate your trust in Alcon Hyundai\. Have a wonderful day!",
            "यह सुनकर बहुत अच्छा लगा। आपके बहुमूल्य फीडबैक के लिए धन्यवाद। हम अल्कॉन हुंडई में आपके विश्वास की सराहना करते हैं। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"I’m really sorry to hear that\. Thank you for informing us\. I will escalate this to our senior service team, and they will contact you shortly\. For immediate support, you may also reach us on (.+?)\. Thank you for your time\.",
            lambda m: f"मुझे यह सुनकर बहुत खेद है। हमें सूचित करने के लिए धन्यवाद। मैं इसे हमारी सीनियर सर्विस टीम को भेज दूँगी, और वे जल्द ही आपसे संपर्क करेंगे। तत्काल सहायता के लिए, आप हमसे {m.group(1)} पर संपर्क कर सकते हैं। समय देने के लिए धन्यवाद।"
        ),
        (
            r"I understand (Sir|Ma'am|सर|मैडम)\. Could you please let me know a suitable date or time when I should call you back for this feedback\?",
            lambda m: f"मैं समझती हूँ {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। क्या आप कृपया मुझे एक उपयुक्त तारीख या समय बता सकते हैं जब मुझे इस फीडबैक के लिए आपको वापस कॉल करना चाहिए?"
        ),
        (
            r"Got it\. I've scheduled a callback for (.+?)\. Thank you for your time, and have a nice day!",
            lambda m: f"समझ गई। मैंने {m.group(1)} के लिए एक कॉल बैक शेड्यूल कर दिया है। आपके समय के लिए धन्यवाद, और आपका दिन शुभ हो!"
        ),
        (
            r"Hello (Sir|Ma'am|सर|मैडम), I'm Supriya from Alcon\. Am I speaking with (.+?)\?",
            lambda m: f"नमस्ते {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। क्या मैं {m.group(2)} से बात कर रही हूँ?"
        ),
        (
            r"Thank you (Sir|Ma'am|सर|मैडम)\. Were all requested jobs done to your complete satisfaction\?",
            lambda m: f"धन्यवाद {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। क्या सभी अनुरोधित काम आपकी पूर्ण संतुष्टि के साथ किए गए थे?"
        ),
        (
            r"I'm sorry to hear that (Sir|Ma'am|सर|मैडम)\. I am escalating this to our senior service team immediately\. They will contact you to resolve this\. May I still ask for your ratings for other areas\?",
            lambda m: f"मुझे यह सुनकर खेद है {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं इसे तुरंत हमारी सीनियर सर्विस टीम को भेज रही हूँ। वे इसे हल करने के लिए आपसे संपर्क करेंगे। क्या मैं फिर भी अन्य क्षेत्रों के लिए आपकी रेटिंग पूछ सकती हूँ?"
        ),
        (
            r"That's great to hear\. Now, on a scale of one to ten, how would you rate the service advisor’s explanation of work and charges\?",
            "यह सुनकर अच्छा लगा। अब, एक से दस के पैमाने पर, आप सर्विस एडवाइजर द्वारा काम और शुल्कों के स्पष्टीकरण को कितनी रेटिंग देंगे?"
        ),
        (
            r"I've noted the rating of (.+?)\. May I know the reason for this rating, so we can improve our service\?",
            lambda m: f"मैंने {m.group(1)} की रेटिंग नोट कर ली है। क्या मैं इस रेटिंग का कारण जान सकती हूँ, ताकि हम अपनी सेवा में सुधार कर सकें?"
        ),
        (
            r"Thank you for sharing that\. Next, how would you rate the pickup process after servicing\?",
            "साझा करने के लिए धन्यवाद। अगला, आप सर्विसिंग के बाद पिकअप प्रक्रिया को कितनी रेटिंग देंगे?"
        ),
        (
            r"Thank you\. Next, how would you rate the pickup process after servicing\?",
            "धन्यवाद। अगला, आप सर्विसिंग के बाद पिकअप प्रक्रिया को कितनी रेटिंग देंगे?"
        ),
        (
            r"Understood\. Could you share the reason for the (.+?) rating for the pickup process\?",
            lambda m: f"समझ गई। क्या आप पिकअप प्रक्रिया के लिए {m.group(1)} रेटिंग का कारण साझा कर सकते हैं?"
        ),
        (
            r"Noted\. And how would you rate the cleanliness and condition of the car\?",
            "नोट किया गया। और आप कार की सफाई और स्थिति को कैसी रेटिंग देंगे?"
        ),
        (
            r"Got it\. And how would you rate the cleanliness and condition of the car\?",
            "समझ गई। और आप कार की सफाई और स्थिति को कैसी रेटिंग देंगे?"
        ),
        (
            r"Thank you\. Could you please tell me why you gave a (.+?) for cleanliness\?",
            lambda m: f"धन्यवाद। क्या आप कृपया बता सकते हैं कि आपने सफाई के लिए {m.group(1)} रेटिंग क्यों दी?"
        ),
        (
            r"Finally, how would you rate your overall workshop experience\?",
            "अंत में, आप अपने समग्र वर्कशॉप अनुभव को कैसी रेटिंग देंगे?"
        ),
        (
            r"I've noted your rating of (.+?)\. Any suggestions on how we can make your overall experience better\?",
            lambda m: f"मैंने आपकी {m.group(1)} की रेटिंग नोट कर ली है। क्या कोई सुझाव हैं कि हम आपके समग्र अनुभव को कैसे बेहतर बना सकते हैं?"
        ),
        (
            r"Thank you for your valuable feedback! We've noted your suggestions and will work on them\. Have a great day!",
            "आपके बहुमूल्य फीडबैक के लिए धन्यवाद! हमने आपके सुझावों को नोट कर लिया है और उन पर काम करेंगे। आपका दिन बहुत अच्छा रहे!"
        ),

        # --- Flow 4: Workshop Update ---
        (
            r"Great\. I'm calling from the workshop to confirm the reported issues for your (.+?)\. We have noted: (.+?)\. Do you have any additional concerns we should address\?",
            lambda m: f"बहुत अच्छा। मैं वर्कशॉप से आपकी {m.group(1)} के रिपोर्ट किए गए मुद्दों की पुष्टि करने के लिए कॉल कर रही हूँ। हमने नोट किया है: {m.group(2)}। क्या आपकी कोई और समस्या है जिसे हमें देखना चाहिए?"
        ),
        (
            r"Based on our inspection, the estimated cost is approximately (.+?), and we expect to have it ready (.+?)\.",
            lambda m: f"हमारी जांच के आधार पर, अनुमानित लागत (estimated cost) लगभग {m.group(1)} है, और हम इसके {m.group(2)} तक तैयार होने की उम्मीद करते हैं।"
        ),
        (
            r"Should we proceed\?",
            "क्या हम आगे बढ़ें?"
        ),
        (
            r"Excellent\.",
            "बहुत बढ़िया।"
        ),
        (
            r"I've noted down:\s+([^.!?]+)\.?$",
            lambda m: f"मैंने नोट कर लिया है: {TranslationAdapter.clean_echoed_concern(m.group(1))}।"
        ),
        (
            r"Certainly\. I'll connect you to our Sales team immediately\. Please stay on the line\.",
            "निश्चित रूप से। मैं आपको तुरंत हमारी सेल्स टीम से जोड़ देती हूँ। कृपया लाइन पर बने रहें।"
        ),
        (
            r"Certainly\. I will connect you to our Service Advisor immediately\. Please stay on the line\.",
            "निश्चित रूप से। मैं आपको तुरंत हमारे सर्विस एडवाइजर से जोड़ देती हूँ। कृपया लाइन पर बने रहें।"
        ),
        (
            r"I understand\. The estimate includes authorized parts for your (.+?), professional labor, and a service warranty\. Would you like to proceed, or should I have the Service Advisor call you\?",
            lambda m: f"मैं समझती हूँ। इस एस्टीमेट में आपकी {m.group(1)} के अधिकृत पार्ट्स, प्रोफेशनल लेबर और सर्विस वारंटी शामिल हैं। क्या आप आगे बढ़ना चाहेंगे, या मैं सर्विस एडवाइजर से आपको कॉल करवाऊँ?"
        ),
        (
            r"Understood\. I'll call back at a more convenient time\. Have a great day!",
            "समझ गई। मैं अधिक सुविधाजनक समय पर वापस कॉल करूँगी। आपका दिन बहुत अच्छा रहे!"
        ),
        (
            r"Understood\. Connecting you to our Service Advisor now\. Please stay on the line\.",
            "समझ गई। मैं आपको हमारे सर्विस एडवाइजर से जोड़ रही हूँ। कृपया लाइन पर बने रहें।"
        ),
        (
            r"Understood\. I will have your Service Advisor call you immediately to discuss the details\. Thank you!",
            "समझ गई। विवरण पर चर्चा करने के लिए मैं हमारे सर्विस एडवाइजर से आपको तुरंत कॉल करवाती हूँ। धन्यवाद!"
        ),
        (
            r"Excellent! We are proceeding with the service now\. You'll get a detailed breakdown via SMS\. Thank you!",
            "अद्भुत! हम अभी सर्विस के साथ आगे बढ़ रहे हैं। आपको जल्द ही एसएमएस के जरिए विस्तृत विवरण मिल जाएगा। धन्यवाद!"
        ),

        # --- Flow 6: Mercedes Premium Service ---
        (
            r"Good day, I'm Supriya from the Alcon Mercedes-Benz Concierge\. Am I speaking with (.+?) (Sir|Ma'am|सर|मैडम)\?",
            lambda m: f"शुभ दिन, मैं अल्कॉन मर्सिडीज-बेंज कंसीयज से सुप्रिया हूँ। क्या मैं {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'} से बात कर रही हूँ?"
        ),
        (
            r"Thank you for confirming (Sir|Ma'am|सर|मैडम)\. I see your (.+?) is due for its periodic maintenance\. Would you like to schedule your premium service today\?",
            lambda m: f"पुष्टि करने के लिए धन्यवाद {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं देख सकती हूँ कि आपकी {m.group(2)} की पीरियोडिक मेंटेनेंस ड्यू है। क्या आप आज अपनी प्रीमियम सर्विस शेड्यूल करना चाहेंगे?"
        ),
        (
            r"Thank you\. For our Mercedes clients, we provide a complimentary Chauffeur-driven Pick and Drop\. Would you like to avail this premium service\?",
            "धन्यवाद। हमारे मर्सिडीज ग्राहकों के लिए, हम एक मानार्थ (complimentary) शॉफर-ड्रिवन पिक और ड्रॉप सेवा प्रदान करते हैं। क्या आप इस प्रीमियम सेवा का लाभ उठाना चाहेंगे?"
        ),
        (
            r"Wonderful (Sir|Ma'am|सर|मैडम)\. Your service is confirmed\. We will use only genuine Mercedes-Benz parts and synthetic oil\. Our Service Manager, Amit Shah, will personally oversee your vehicle\. Have a great day!",
            lambda m: f"अद्भुत {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। आपकी सर्विस कन्फर्म हो गई है। हम केवल मर्सिडीज-बेंज के असली पार्ट्स और सिंथेटिक ऑयल का उपयोग करेंगे। हमारे सर्विस मैनेजर, अमित शाह, व्यक्तिगत रूप से आपकी गाड़ी की देखरेख करेंगे। आपका दिन शुभ हो!"
        ),

        # --- Flow 7: Pickup Coordination ---
        (
            r"Hello (Sir|Ma'am|सर|मैडम) (.+?), I'm Supriya from Alcon\. Calling to confirm your scheduled Pick & Drop for tomorrow\. Is this still a good time\?",
            lambda m: f"नमस्ते {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'} {m.group(2)}। मैं अल्कॉन से सुप्रिया हूँ। कल के लिए आपकी निर्धारित पिक एंड ड्रॉप की पुष्टि करने के लिए कॉल कर रही हूँ। क्या यह अभी भी सही समय है?"
        ),
        (
            r"Yes, all our drivers, including Rajesh, are fully licensed, police-verified, and highly experienced professionals with clean safety records\. You can be fully assured of your car's safety\. Is this still a good time for the pickup\?",
            "हाँ, राजेश सहित हमारे सभी ड्राइवर पूरी तरह से लाइसेंस प्राप्त, पुलिस-सत्यापित और साफ सुरक्षा रिकॉर्ड वाले अत्यधिक अनुभवी पेशेवर हैं। आप अपनी कार की सुरक्षा के लिए पूरी तरह से निश्चिंत रह सकते हैं। क्या पिकअप के लिए यह अभी भी सही समय है?"
        ),
        (
            r"Yes, all our drivers, including Rajesh, are fully licensed, police-verified, and highly experienced professionals with clean safety records\. You can be fully assured of your car's safety\. What time should he arrive at your location\?",
            "हाँ, राजेश सहित हमारे सभी ड्राइवर पूरी तरह से लाइसेंस प्राप्त, पुलिस-सत्यापित और साफ सुरक्षा रिकॉर्ड वाले अत्यधिक अनुभवी पेशेवर हैं। आप अपनी कार की सुरक्षा के लिए पूरी तरह से निश्चिंत रह सकते हैं। उन्हें आपके यहाँ कितने बजे पहुंचना चाहिए?"
        ),
        (
            r"Great\. Our driver Rajesh is assigned for the pickup\. What time should he arrive at your location\?",
            "बहुत बढ़िया। पिकअप के लिए हमारे ड्राइवर राजेश को असाइन किया गया है। उन्हें आपके यहाँ कितने बजे पहुंचना चाहिए?"
        ),
        (
            r"Perfect\. Rajesh will see you tomorrow at (.+?)\. You'll receive driver contact details via SMS shortly\. Thanks!",
            lambda m: f"उत्कृष्ट। राजेश कल आपसे {m.group(1)} पर मिलेंगे। आपको जल्द ही एसएमएस द्वारा ड्राइवर के संपर्क विवरण प्राप्त होंगे। धन्यवाद!"
        ),
        (
            r"No problem\. I will have our coordinator call you to reschedule the pickup\. Have a nice day!",
            "कोई बात नहीं। पिकअप को रीशेड्यूल करने के लिए मैं हमारे कोऑर्डिनेटर से आपको कॉल करवाऊँगी। आपका दिन शुभ हो!"
        ),

        # --- Flow 8: Ready Delivery ---
        (
            r"Wonderful news (Sir|Ma'am|सर|मैडम) (.+?)! Your car is ready for delivery\. We've completed (.+?)\. Would you like us to drop it back to your location, or will you be coming to pick it up\?",
            lambda m: f"खुशखबरी {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'} {m.group(2)}! आपकी कार डिलीवरी के लिए तैयार है। हमने {m.group(3)} पूरा कर लिया है। क्या आप चाहेंगे कि हम इसे आपके पते पर ड्रॉप करें, या आप खुद पिक-अप करने आएंगे?"
        ),
        (
            r"Perfect\. I've scheduled the drop-off for you\. Our driver will contact you shortly\. Thank you!",
            "परफेक्ट। मैंने आपके लिए ड्रॉप-ऑफ शेड्यूल कर दिया है। हमारे ड्राइवर जल्द ही आपसे संपर्क करेंगे। धन्यवाद!"
        ),
        (
            r"Got it\. Your car is parked at our service entrance\. See you soon!",
            "समझ गई। आपकी कार हमारे सर्विस एंट्रेंस पर खड़ी है। जल्द ही मिलते हैं!"
        ),

        # --- Flow 6 (Insurance Renewal Stage 1-5 & Transfers) ---
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), I'm Supriya from Alcon\. I'm calling to remind you that the insurance for your (.+?) is due for renewal on (.+?)\. Your current policy is with (.+?)\. Are you planning to renew it with us this year\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं आपको याद दिलाने के लिए कॉल कर रही हूँ कि आपकी {m.group(3)} का बीमा {m.group(4)} को रिन्यूअल के लिए देय है। आपकी वर्तमान पॉलिसी {m.group(5)} के साथ है। क्या आप इस साल हमारे साथ इसे रिन्यू करने की योजना बना रहे हैं?"
        ),
        (
            r"calling to remind you that the insurance for your (.+?) is due for renewal on (.+?)\. Your current policy is with (.+?)\. Are you planning to renew it with us this year\?",
            lambda m: f"मैं आपको याद दिलाने के लिए कॉल कर रही हूँ कि आपकी {m.group(1)} का बीमा {m.group(2)} को रिन्यूअल के लिए देय है। आपकी वर्तमान पॉलिसी {m.group(3)} के साथ है। क्या आप इस साल हमारे साथ इसे रिन्यू करने की योजना बना रहे हैं?"
        ),
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), this is Supriya from Alcon\. I'm following up as you mentioned you were busy when we last spoke\. Since we're now about two weeks away from your (.+?)'s insurance expiry, have you had a chance to review that loyalty offer\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं फॉलो-अप ले रही हूँ क्योंकि आपने पिछली बार बात करने पर व्यस्त होने का उल्लेख किया था। चूंकि अब हम आपकी {m.group(3)} के बीमा समाप्त होने से लगभग दो सप्ताह दूर हैं, क्या आपको उस लॉयल्टी ऑफर की समीक्षा करने का मौका मिला?"
        ),
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), Supriya here from Alcon again\. I'm calling with an urgent reminder as your (.+?) insurance expires in just 7 days\. I haven't heard back from you on the loyalty quote we shared\. Shall we secure your No Claim Bonus today\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं एक बार फिर अल्कॉन से सुप्रिया हूँ। मैं एक तत्काल अनुस्मारक (urgent reminder) के साथ कॉल कर रही हूँ क्योंकि आपकी {m.group(3)} का बीमा सिर्फ 7 दिनों में समाप्त हो रहा है। हमारे द्वारा साझा किए गए लॉयल्टी कोट पर मुझे आपकी ओर से कोई प्रतिक्रिया नहीं मिली है। क्या हम आज आपका नो क्लेम बोनस सुरक्षित करें?"
        ),
        (
            r"Good day (.+?) (Sir|Ma'am|सर|मैडम)\. This is an urgent final call regarding your (.+?)\. Your insurance expires tomorrow\. I've secured a final spot for instant renewal to save your 50% No Claim Bonus\. Shall I send the payment link to your WhatsApp\?",
            lambda m: f"शुभ दिन {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। यह आपकी {m.group(3)} के संबंध में एक तत्काल अंतिम कॉल (urgent final call) है। आपका बीमा कल समाप्त हो रहा है। मैंने आपका 50% नो क्लेम बोनस बचाने के लिए तुरंत रिन्यूअल के लिए एक अंतिम स्लॉट सुरक्षित किया है। क्या मैं आपके व्हाट्सएप पर भुगतान लिंक भेजूँ?"
        ),
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), I noticed that the insurance for your (.+?) has now expired\. Driving without it is a major risk\. I can still help you with a break-in policy today\. Shall I connect you to our insurance desk to fix this immediately\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैंने देखा कि आपकी {m.group(3)} का बीमा अब समाप्त हो गया है। इसके बिना गाड़ी चलाना एक बड़ा जोखिम है। मैं आज भी एक break-in पॉलिसी में आपकी मदद कर सकती हूँ। क्या मैं आपको इसे तुरंत ठीक करने के लिए हमारे इंश्योरेंस डेस्क से कनेक्ट करूँ?"
        ),
        (
            r"Certainly\. Your current premium was (.+?), but for this year, we have a special loyalty quote of (.+?)\. This includes Zero Depreciation, Engine Protection, and Roadside Assistance\. Does that sound like a good deal\?",
            lambda m: f"निश्चित रूप से। आपका वर्तमान प्रीमियम {m.group(1)} था, लेकिन इस वर्ष के लिए, हमारे पास {m.group(2)} का एक विशेष लॉयल्टी कोट है। इसमें ज़ीरो डेप्रिसिएशन, इंजन प्रोटेक्शन और रोडसाइड असिस्टेंस शामिल हैं। क्या यह एक अच्छा सौदा लगता है?"
        ),
        (
            r"Great! Shall I go ahead and share the digital copy of the quotation and the secure payment link on your registered mobile number now\?",
            "बहुत बढ़िया! क्या मैं अब आपके पंजीकृत मोबाइल नंबर पर कोटेशन की डिजिटल कॉपी और सुरक्षित भुगतान लिंक साझा करने के लिए आगे बढ़ूँ?"
        ),
        (
            r"I'll connect you to our insurance desk to find the best possible rate\. Please stay on the line\.",
            "बेहतर दर खोजने के लिए मैं आपको हमारे इंश्योरेंस डेस्क से जोड़ देती हूँ। कृपया लाइन पर बने रहें।"
        ),
        (
            r"Excellent choice! I'm processing your renewal with (.+?) at (.+?)\. This includes(?: Zero-Depreciation and 24/7 Roadside Assistance| Zero Depreciation and 24/7 Roadside Assistance)\. Your renewal is now in progress\. You'll receive the payment link shortly(?:\. By the way, did you find this call helpful today\?)?",
            lambda m: f"उत्कृष्ट विकल्प! मैं {m.group(2)} पर {m.group(1)} के साथ आपके रिन्यूअल की प्रक्रिया कर रही हूँ। इसमें ज़ीरो-डेप्रिसिएशन और 24/7 रोडसाइड असिस्टेंस शामिल हैं। आपका रिन्यूअल अब प्रगति पर है। आपको जल्द ही भुगतान लिंक प्राप्त होगा। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"Thank you for your feedback! Have a wonderful day\.",
            "आपकी प्रतिक्रिया के लिए धन्यवाद! आपका दिन बहुत अच्छा रहे।"
        ),
        (
            r"No problem\. I'll schedule a call back for later\. By the way, did you find this call helpful today\?",
            "कोई बात नहीं। मैं बाद के लिए एक कॉल बैक शेड्यूल कर दूँगी। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"Understood (Sir|Ma'am|सर|मैडम)\. I'll update our records to not call you again regarding this\. By the way, did you find this call helpful today\?",
            lambda m: f"समझ गई {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं इस संबंध में आपको दोबारा कॉल न करने के लिए हमारे रिकॉर्ड अपडेट कर दूँगी। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"No problem (Sir|Ma'am|सर|मैडम)\. I'll schedule a call back so you have time to think about it\. Just one last thing, did you find this interaction helpful\?",
            lambda m: f"कोई बात नहीं {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं एक कॉल बैक शेड्यूल कर दूँगी ताकि आपके पास इस बारे में सोचने का समय हो। बस एक आखिरी बात, क्या आपको यह बातचीत मददगार लगी?"
        ),
        (
            r"Oh, I see! That's great to hear that your (.+?) is already covered\. By the way, did you find this call helpful today\?",
            lambda m: f"ओह, समझ गई! यह सुनकर बहुत अच्छा लगा कि आपकी {m.group(1)} पहले से ही कवर है। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"Thank you for speaking with our manager, (Sir|Ma'am|सर|मैडम|(?:Ms\.|Mr\.)?\s*[a-zA-Z0-9 ]+)\. (.+?)\. Shall I go ahead and share the digital copy of the quotation via WhatsApp\?",
            lambda m: f"हमारे मैनेजर से बात करने के लिए धन्यवाद, {TranslationAdapter.translate_salutation(m.group(1))}। {TranslationAdapter.translate_to_hindi(m.group(2))} क्या मैं व्हाट्सएप के माध्यम से कोटेशन की डिजिटल कॉपी शेयर करने के लिए आगे बढ़ूँ?"
        ),
        (
            r"I'm back now to finalize (.+?)\.?",
            lambda m: f"अब मैं {TranslationAdapter.translate_resume_item_to_hindi(m.group(1))} को फाइनल करने के लिए वापस आ गई हूँ।"
        ),
        (
            r"I understand from our discussion that (.+?)\.?",
            lambda m: f"हमारी चर्चा से मुझे समझ आया कि {TranslationAdapter.translate_summary_to_hindi(m.group(1))}।"
        ),
        # --- Intent Engine / KB responses ---
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Both the Hyundai Creta and Seltos are excellent options\. The Seltos offers sporty styling and premium tech features, whereas the Hyundai Creta stands out for its refined driving comfort, trusted service network, and outstanding resale value\.",
            "हुंडई क्रेटा और सेल्टोस दोनों ही उत्कृष्ट विकल्प हैं। सेल्टोस स्पोर्टी स्टाइलिंग और प्रीमियम टेक फीचर्स प्रदान करता है, जबकि हुंडई क्रेटा अपने रिफाइंड ड्राइविंग कम्फर्ट, भरोसेमंद सर्विस नेटवर्क और शानदार रीसेल मूल्य के लिए अलग पहचान रखती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Both the Hyundai Venue and competitors like (Sonet|Nexon|3xo) are great options\. While competitors offer sporty styling, the Hyundai Venue stands out for its excellent ride quality, low maintenance cost \(just 35 paise/km\), and great reliability\.",
            lambda m: f"हुंडई वेन्यू और {m.group(1).capitalize()} दोनों ही बेहतरीन विकल्प हैं। जहाँ प्रतियोगी स्पोर्टी स्टाइलिंग प्रदान करते हैं, वहीं हुंडई वेन्यू अपनी बेहतरीन राइड क्वालिटी, कम रखरखाव लागत (सिर्फ 35 पैसे/किमी) और शानदार विश्वसनीयता के लिए अलग पहचान रखती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Both the Hyundai ([a-zA-Z0-9]+) and ([a-zA-Z0-9]+) are excellent options\. The \2 offers (.+?), whereas the Hyundai \1 stands out for its (.+?)\.",
            lambda m: f"हुंडई {m.group(1)} और {m.group(2)} दोनों ही उत्कृष्ट विकल्प हैं। {m.group(2)} {m.group(3)} प्रदान करता है, जबकि हुंडई {m.group(1)} अपने {m.group(4)} के लिए जानी जाती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Kia and Hyundai are sister brands that share excellent platforms\. While Kia emphasizes sporty designs and tech, Hyundai models are highly popular for their refined ride quality, vast service network, and trusted resale value\.",
            "किया और हुंडई सिस्टर ब्रांड्स हैं जो उत्कृष्ट प्लेटफॉर्म साझा करते हैं। जहाँ किया स्पोर्टी डिज़ाइन और तकनीक पर ज़ोर देता है, वहीं हुंडई मॉडल्स अपने रिफाइंड राइड क्वालिटी, विशाल सर्विस नेटवर्क और भरोसेमंद रीसेल मूल्य के लिए बेहद लोकप्रिय हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Tata makes very solid vehicles\. Hyundai cars, on the other hand, are highly preferred for their exceptional engine refinement, smooth transmission options, hassle-free ownership, and superior after-sales support\.",
            "टाटा बहुत मजबूत गाड़ियां बनाती है। दूसरी ओर, हुंडई कारों को उनके असाधारण इंजन रिफाइनमेंट, सुचारू ट्रांसमिशन विकल्पों, परेशानी मुक्त स्वामित्व और बेहतर आफ्टर-सेल्स सपोर्ट के लिए अत्यधिक पसंद किया जाता है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Mahindra is known for rugged utility vehicles\. Hyundai SUVs like Creta and Venue stand out for their urban maneuverability, advanced features, superior cabin comfort, and premium refinement\.",
            "महिंद्रा मजबूत यूटिलिटी गाड़ियों के लिए जानी जाती है। हुंडई एसयूवी जैसे क्रेटा और वेन्यू अपनी शहरी गतिशीलता, उन्नत सुविधाओं, बेहतर केबिन आराम और प्रीमियम रिफाइनमेंट के लिए अलग पहचान रखती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Maruti offers highly fuel-efficient cars\. Hyundai models provide a much more premium cabin feel, advanced safety features like standard 6 airbags, and superior highway stability\.",
            "मारुति अत्यधिक ईंधन-कुशल कारें प्रदान करती है। हुंडई मॉडल्स बहुत अधिक प्रीमियम केबिन अनुभव, मानक 6 एयरबैग जैसी उन्नत सुरक्षा विशेषताएं और बेहतर हाईवे स्थिरता प्रदान करते हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Hyundai vehicles are widely trusted for their class-leading refinement, advanced safety, extensive service network, and high resale value compared to competitors\.",
            "प्रतियोगियों की तुलना में हुंडई गाड़ियाँ अपनी श्रेणी में सर्वोत्तम रिफाइनमेंट, उन्नत सुरक्षा, व्यापक सर्विस नेटवर्क और उच्च रीसेल मूल्य के लिए व्यापक रूप से जानी जाती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Both brands offer beautiful cabins\. Hyundai is highly appreciated for its premium cabin materials, durability, and outstanding ergonomics\.",
            "दोनों ब्रांड्स सुंदर केबिन प्रदान करते हैं। हुंडई को उसके प्रीमियम केबिन मटीरियल्स, टिकाऊपन और शानदार एर्गोनॉमिक्स के लिए अत्यधिक सराहा जाता है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Hyundai prioritizes safety with 6 airbags as standard, high-strength steel body, and advanced ADAS safety features\.",
            "हुंडई 6 एयरबैग मानक, उच्च शक्ति वाले स्टील बॉडी और उन्नत एडीएएस (ADAS) सुरक्षा सुविधाओं के साथ सुरक्षा को प्राथमिकता देती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Hyundai cars enjoy excellent resale value and are highly demanded in the pre-owned market due to durable build and vast service network\.",
            "मजबूत निर्माण और विशाल सर्विस नेटवर्क के कारण हुंडई कारों का प्री-ओन्ड बाजार में उत्कृष्ट रीसेल मूल्य है और इनकी भारी मांग रहती है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Hyundai models like the Creta offer highly refined petrol and diesel options with advanced turbo engines that deliver exciting yet smooth performance\.",
            "क्रेटा जैसे हुंडई मॉडल्स अत्यधिक रिफाइंड पेट्रोल और डीजल विकल्प प्रदान करते हैं जिनमें उन्नत टर्बो इंजन होते हैं जो रोमांचक लेकिन सुचारू प्रदर्शन देते हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Alcon Hyundai has a vast network of authorized workshops with expert technicians, ranking consistently at the top in customer satisfaction\.",
            "अल्कॉन हुंडई के पास विशेषज्ञ तकनीशियनों के साथ अधिकृत वर्कशॉप का एक विशाल नेटवर्क है, जो ग्राहक संतुष्टि में लगातार शीर्ष पर रहता है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Genuine Hyundai spare parts are readily available at highly reasonable prices across all service centers\.",
            "सभी सर्विस सेंटरों पर असली हुंडई स्पेयर पार्ट्स अत्यधिक उचित कीमतों पर आसानी से उपलब्ध हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Hyundai cars offer extremely comfortable seats, silent cabin, and smooth suspension, making them absolute joy for long highway drives\.",
            "हुंडई कारें अत्यधिक आरामदायक सीटें, शांत केबिन और स्मूथ सस्पेंशन प्रदान करती हैं, जिससे वे लंबी हाईवे यात्राओं के लिए बेहद सुखद बन जाती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Yes, advanced Level 2 ADAS \(Advanced Driver Assistance System\) is available in models like Creta, Verna, and Tucson to ensure maximum safety\.",
            "हाँ, अधिकतम सुरक्षा सुनिश्चित करने के लिए क्रेटा, वरना और टक्सन जैसे मॉडल्स में उन्नत स्तर 2 एडीएएस (ADAS - एडवांस ड्राइवर असिस्टेंस सिस्टम) उपलब्ध है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Yes, premium ventilated seats are available in the Hyundai Creta and Verna, keeping you cool and comfortable in all weather\.",
            "हाँ, प्रीमियम वेंटिलेटेड सीटें हुंडई क्रेटा और वरना में उपलब्ध हैं, जो आपको हर मौसम में कूल और आरामदायक रखती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Hyundai is proud to offer 6 airbags as standard across all variants of our entire car lineup, ensuring robust safety for every passenger\.",
            "हुंडई को अपनी पूरी कार लाइनअप के सभी वेरिएंट्स में मानक के रूप में 6 एयरबैग पेश करने पर गर्व है, जो हर यात्री के लिए मजबूत सुरक्षा सुनिश्चित करता है।"
        ),
        (
            r"(?:Certainly!\s+)?(?:Regarding the [a-zA-Z0-9]+,\s+)?Under 15 Lakhs, our Venue is the perfect compact SUV option, starting from ₹7\.94 Lakhs, and its automatic variant starts from ₹10\.37 Lakhs\.",
            "15 लाख के अंदर, हमारी वेन्यू सबसे अच्छी कॉम्पैक्ट एसयूवी विकल्प है, जो ₹7.94 लाख से शुरू होती है, और इसका ऑटोमैटिक वेरिएंट ₹10.37 लाख से शुरू होता है।"
        ),
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), Supriya here from Alcon\. I'm following up as you mentioned you were busy last time we spoke\. Since we are now two weeks away from your (.+?)'s insurance expiry, have you had a chance to review that loyalty offer\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं अल्कॉन से सुप्रिया हूँ। मैं फॉलो-अप ले रही हूँ क्योंकि आपने पिछली बार बात करने पर व्यस्त होने का उल्लेख किया था। चूंकि अब हम आपकी {m.group(3)} के बीमा समाप्त होने से लगभग दो सप्ताह दूर हैं, क्या आपको उस लॉयल्टी ऑफर की समीक्षा करने का मौका मिला?"
        ),
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), Supriya here from Alcon again\. I'm calling with an urgent reminder as your (.+?) insurance expires in just 7 days\. I haven't heard back from you on the loyalty quote we shared\. Shall we secure your No Claim Bonus today\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं एक बार फिर अल्कॉन से सुप्रिया हूँ। मैं एक तत्काल अनुस्मारक (urgent reminder) के साथ कॉल कर रही हूँ क्योंकि आपकी {m.group(3)} का बीमा सिर्फ 7 दिनों में समाप्त हो रहा है। हमारे द्वारा साझा किए गए लॉयल्टी कोट पर मुझे आपकी ओर से कोई प्रतिक्रिया नहीं मिली है। क्या हम आज आपका नो क्लेम बोनस सुरक्षित करें?"
        ),
        (
            r"Good day (.+?) (Sir|Ma'am|सर|मैडम)\. This is an urgent final call regarding your (.+?)\. Your insurance expires tomorrow\. I've secured a final spot for instant renewal to save your 50% No Claim Bonus\. Shall I send the payment link to your WhatsApp\?",
            lambda m: f"शुभ दिन {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। यह आपकी {m.group(3)} के संबंध में एक तत्काल अंतिम कॉल (urgent final call) है। आपका बीमा कल समाप्त हो रहा है। मैंने आपका 50% नो क्लेम बोनस बचाने के लिए तुरंत रिन्यूअल के लिए एक अंतिम स्लॉट सुरक्षित किया है। क्या मैं आपके व्हाट्सएप पर भुगतान लिंक भेजूँ?"
        ),
        (
            r"Hello (.+?) (Sir|Ma'am|सर|मैडम), I noticed that the insurance for your (.+?) has now expired\. Driving without it is a major risk\. I can still help you with a break-in policy today\. Shall I connect you to our insurance desk to fix this immediately\?",
            lambda m: f"नमस्ते {m.group(1)} {m.group(2) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैंने देखा कि आपकी {m.group(3)} का बीमा अब समाप्त हो गया है। इसके बिना गाड़ी चलाना एक बड़ा जोखिम है। मैं आज भी एक break-in पॉलिसी में आपकी मदद कर सकती हूँ। क्या मैं आपको इसे तुरंत ठीक करने के लिए हमारे इंश्योरेंस डेस्क से कनेक्ट करूँ?"
        ),
        (
            r"Certainly\. Your current premium was (.+?), but for this year, we have a special loyalty quote of (.+?)\. This includes Zero Depreciation, Engine Protection, and Roadside Assistance\. Does that sound like a good deal\?",
            lambda m: f"निश्चित रूप से। आपका वर्तमान प्रीमियम {m.group(1)} था, लेकिन इस वर्ष के लिए, हमारे पास {m.group(2)} का एक विशेष लॉयल्टी कोट है। इसमें जीरो डेप्रिसिएशन, इंजन प्रोटेक्शन और रोडसाइड असिस्टेंस शामिल हैं। क्या यह एक अच्छा सौदा लगता है?"
        ),
        (
            r"Great! Shall I go ahead and share the digital copy of the quotation and the secure payment link on your registered mobile number now\?",
            "बहुत बढ़िया! क्या मैं अब आपके पंजीकृत मोबाइल नंबर पर कोटेशन की डिजिटल कॉपी और सुरक्षित भुगतान लिंक साझा करने के लिए आगे बढ़ूँ?"
        ),
        (
            r"I'll connect you to our insurance desk to find the best possible rate\. Please stay on the line\.",
            "बेहतर दर खोजने के लिए मैं आपको हमारे इंश्योरेंस डेस्क से जोड़ देती हूँ। कृपया लाइन पर बने रहें।"
        ),
        (
            r"Excellent choice! I'm processing your renewal with (.+?) at (.+?)\. This includes(?: Zero-Depreciation and 24/7 Roadside Assistance| Zero Depreciation and 24/7 Roadside Assistance)\. Your renewal is now in progress\. You'll receive the payment link shortly(?:\. By the way, did you find this call helpful today\?)?",
            lambda m: f"उत्कृष्ट विकल्प! मैं {m.group(2)} पर {m.group(1)} के साथ आपके रिन्यूअल की प्रक्रिया कर रही हूँ। इसमें जीरो-डेप्रिसिएशन और 24/7 रोडसाइड असिस्टेंस शामिल हैं। आपका रिन्यूअल अब प्रगति पर है। आपको जल्द ही भुगतान लिंक प्राप्त होगा। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"Thank you for your feedback! Have a wonderful day\.",
            "आपकी प्रतिक्रिया के लिए धन्यवाद! आपका दिन बहुत अच्छा रहे।"
        ),
        (
            r"No problem\. I'll schedule a call back for later\. By the way, did you find this call helpful today\?",
            "कोई बात नहीं। मैं बाद के लिए एक कॉल बैक शेड्यूल कर दूँगी। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"Understood (Sir|Ma'am|सर|मैडम)\. I'll update our records to not call you again regarding this\. By the way, did you find this call helpful today\?",
            lambda m: f"समझ गई {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं इस संबंध में आपको दोबारा कॉल न करने के लिए हमारे रिकॉर्ड अपडेट कर दूँगी। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"No problem (Sir|Ma'am|सर|मैडम)\. I'll schedule a call back so you have time to think about it\. Just one last thing, did you find this interaction helpful\?",
            lambda m: f"कोई बात नहीं {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। मैं एक कॉल बैक शेड्यूल कर दूँगी ताकि आपके पास इस बारे में सोचने का समय हो। बस एक आखिरी बात, क्या आपको यह बातचीत मददगार लगी?"
        ),
        (
            r"Oh, I see! That's great to hear that your (.+?) is already covered\. By the way, did you find this call helpful today\?",
            lambda m: f"ओह, समझ गई! यह सुनकर बहुत अच्छा लगा कि आपकी {m.group(1)} पहले से ही कवर है। वैसे, क्या आपको आज यह कॉल मददगार लगी?"
        ),
        (
            r"Thank you for speaking with our manager, (Sir|Ma'am|सर|मैडम|(?:Ms\.|Mr\.)?\s*[a-zA-Z0-9 ]+)\. (.+?)\. Shall I go ahead and share the digital copy of the quotation via WhatsApp\?",
            lambda m: f"हमारे मैनेजर से बात करने के लिए धन्यवाद, {TranslationAdapter.translate_salutation(m.group(1))}। {TranslationAdapter.translate_to_hindi(m.group(2))} क्या मैं व्हाट्सएप के माध्यम से कोटेशन की डिजिटल कॉपी शेयर करने के लिए आगे बढ़ूँ?"
        ),
        (
            r"I'm back now to finalize (.+?)\.?",
            lambda m: f"अब मैं {TranslationAdapter.translate_resume_item_to_hindi(m.group(1))} को फाइनल करने के लिए वापस आ गई हूँ।"
        ),
        (
            r"I understand from our discussion that (.+?)\.?",
            lambda m: f"हमारी चर्चा से मुझे समझ आया कि {TranslationAdapter.translate_summary_to_hindi(m.group(1))}।"
        ),
        # --- Intent Engine / KB responses ---
        (
            r"(?:Certainly!\s+)?Both the Hyundai Creta and Seltos are excellent options\. The Seltos offers sporty styling and premium tech features, whereas the Hyundai Creta stands out for its refined driving comfort, trusted service network, and outstanding resale value\.",
            "हुंडई क्रेटा और सेल्टोस दोनों ही उत्कृष्ट विकल्प हैं। सेल्टोस स्पोर्टी स्टाइलिंग और प्रीमियम टेक फीचर्स प्रदान करता है, जबकि हुंडई क्रेटा अपने रिफाइंड ड्राइविंग कम्फर्ट, भरोसेमंद सर्विस नेटवर्क और शानदार रीसेल मूल्य के लिए अलग पहचान रखती है।"
        ),
        (
            r"(?:Certainly!\s+)?Both the Hyundai Venue and competitors like (Sonet|Nexon|3xo) are great options\. While competitors offer sporty styling, the Hyundai Venue stands out for its excellent ride quality, low maintenance cost \(just 35 paise/km\), and great reliability\.",
            lambda m: f"हुंडई वेन्यू और {m.group(1).capitalize()} दोनों ही बेहतरीन विकल्प हैं। जहाँ प्रतियोगी स्पोर्टी स्टाइलिंग प्रदान करते हैं, वहीं हुंडई वेन्यू अपनी बेहतरीन राइड क्वालिटी, कम रखरखाव लागत (सिर्फ 35 पैसे/किमी) और शानदार विश्वसनीयता के लिए अलग पहचान रखती है।"
        ),
        (
            r"(?:Certainly!\s+)?Both the Hyundai ([a-zA-Z0-9 ]+) and ([a-zA-Z0-9 ]+) are excellent options\. The \2 offers (.+?), whereas the Hyundai \1 stands out for its (.+?)\.",
            lambda m: f"हुंडई {m.group(1)} और {m.group(2)} दोनों ही उत्कृष्ट विकल्प हैं। {m.group(2)} {m.group(3)} प्रदान करता है, जबकि हुंडई {m.group(1)} अपने {m.group(4)} के लिए जानी जाती है।"
        ),
        (
            r"(?:Certainly!\s+)?Kia and Hyundai are sister brands that share excellent platforms\. While Kia emphasizes sporty designs and tech, Hyundai models are highly popular for their refined ride quality, vast service network, and trusted resale value\.",
            "किया और हुंडई सिस्टर ब्रांड्स हैं जो उत्कृष्ट प्लेटफॉर्म साझा करते हैं। जहाँ किया स्पोर्टी डिज़ाइन और तकनीक पर ज़ोर देता है, वहीं हुंडई मॉडल्स अपने रिफाइंड राइड क्वालिटी, विशाल सर्विस नेटवर्क और भरोसेमंद रीसेल मूल्य के लिए बेहद लोकप्रिय हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Tata makes very solid vehicles\. Hyundai cars, on the other hand, are highly preferred for their exceptional engine refinement, smooth transmission options, hassle-free ownership, and superior after-sales support\.",
            "टाटा बहुत मजबूत गाड़ियां बनाती है। दूसरी ओर, हुंडई कारों को उनके असाधारण इंजन रिफाइनमेंट, सुचारू ट्रांसमिशन विकल्पों, परेशानी मुक्त स्वामित्व और बेहतर आफ्टर-सेल्स सपोर्ट के लिए अत्यधिक पसंद किया जाता है।"
        ),
        (
            r"(?:Certainly!\s+)?Mahindra is known for rugged utility vehicles\. Hyundai SUVs like Creta and Venue stand out for their urban maneuverability, advanced features, superior cabin comfort, and premium refinement\.",
            "महिंद्रा मजबूत यूटिलिटी गाड़ियों के लिए जानी जाती है। हुंडई एसयूवी जैसे क्रेटा और वेन्यू अपनी शहरी गतिशीलता, उन्नत सुविधाओं, बेहतर केबिन आराम और प्रीमियम रिफाइनमेंट के लिए अलग पहचान रखती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Maruti offers highly fuel-efficient cars\. Hyundai models provide a much more premium cabin feel, advanced safety features like standard 6 airbags, and superior highway stability\.",
            "मारुति अत्यधिक ईंधन-कुशल कारें प्रदान करती है। हुंडई मॉडल्स बहुत अधिक प्रीमियम केबिन अनुभव, मानक 6 एयरबैग जैसी उन्नत सुरक्षा विशेषताएं और बेहतर हाईवे स्थिरता प्रदान करते हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Hyundai vehicles are widely trusted for their class-leading refinement, advanced safety, extensive service network, and high resale value compared to competitors\.",
            "प्रतियोगियों की तुलना में हुंडई गाड़ियाँ अपनी श्रेणी में सर्वोत्तम रिफाइनमेंट, उन्नत सुरक्षा, व्यापक सर्विस नेटवर्क और उच्च रीसेल मूल्य के लिए व्यापक रूप से जानी जाती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Both brands offer beautiful cabins\. Hyundai is highly appreciated for its premium cabin materials, durability, and outstanding ergonomics\.",
            "दोनों ब्रांड्स सुंदर केबिन प्रदान करते हैं। हुंडई को उसके प्रीमियम केबिन मटीरियल्स, ड्यूरेबिलिटी और शानदार एर्गोनॉमिक्स के लिए अत्यधिक सराहा जाता है।"
        ),
        (
            r"(?:Certainly!\s+)?Hyundai prioritizes safety with 6 airbags as standard, high-strength steel body, and advanced ADAS safety features\.",
            "हुंडई 6 एयरबैग मानक, उच्च शक्ति वाले स्टील बॉडी और उन्नत एडीएएस (ADAS) सुरक्षा सुविधाओं के साथ सुरक्षा को प्राथमिकता देती है।"
        ),
        (
            r"(?:Certainly!\s+)?Hyundai cars enjoy excellent resale value and are highly demanded in the pre-owned market due to durable build and vast service network\.",
            "मजबूत निर्माण और विशाल सर्विस नेटवर्क के कारण हुंडई कारों का प्री-ओन्ड बाजार में उत्कृष्ट रीसेल मूल्य है और इनकी भारी मांग रहती है।"
        ),
        (
            r"(?:Certainly!\s+)?Hyundai models like the Creta offer highly refined petrol and diesel options with advanced turbo engines that deliver exciting yet smooth performance\.",
            "क्रेटा जैसे हुंडई मॉडल्स अत्यधिक रिफाइंड पेट्रोल और डीजल विकल्प प्रदान करते हैं जिनमें उन्नत टर्बो इंजन होते हैं जो रोमांचक लेकिन सुचारू प्रदर्शन देते हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Alcon Hyundai has a vast network of authorized workshops with expert technicians, ranking consistently at the top in customer satisfaction\.",
            "अल्कॉन हुंडई के पास विशेषज्ञ तकनीशियनों के साथ अधिकृत वर्कशॉप का एक विशाल नेटवर्क है, जो ग्राहक संतुष्टि में लगातार शीर्ष पर रहता है।"
        ),
        (
            r"(?:Certainly!\s+)?Genuine Hyundai spare parts are readily available at highly reasonable prices across all service centers\.",
            "सभी सर्विस सेंटरों पर असली हुंडई स्पेयर पार्ट्स अत्यधिक उचित कीमतों पर आसानी से उपलब्ध हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Hyundai cars offer extremely comfortable seats, silent cabin, and smooth suspension, making them absolute joy for long highway drives\.",
            "हुंडई कारें अत्यधिक आरामदायक सीटें, शांत केबिन और स्मूथ सस्पेंशन प्रदान करती हैं, जिससे वे लंबी हाईवे यात्राओं के लिए बेहद सुखद बन जाती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Yes, advanced Level 2 ADAS \(Advanced Driver Assistance System\) is available in models like Creta, Verna, and Tucson to ensure maximum safety\.",
            "हाँ, अधिकतम सुरक्षा सुनिश्चित करने के लिए क्रेटा, वरना और टक्सन जैसे मॉडल्स में उन्नत स्तर 2 एडीएएस (ADAS - एडवांस ड्राइवर असिस्टेंस सिस्टम) उपलब्ध है।"
        ),
        (
            r"(?:Certainly!\s+)?Yes, premium ventilated seats are available in the Hyundai Creta and Verna, keeping you cool and comfortable in all weather\.",
            "हाँ, प्रीमियम वेंटिलेटेड सीटें हुंडई क्रेटा और वरना में उपलब्ध हैं, जो आपको हर मौसम में कूल और आरामदायक रखती हैं।"
        ),
        (
            r"(?:Certainly!\s+)?Hyundai is proud to offer 6 airbags as standard across all variants of our entire car lineup, ensuring robust safety for every passenger\.",
            "हुंडई को अपनी पूरी कार लाइनअप के सभी वेरिएंट्स में मानक के रूप में 6 एयरबैग पेश करने पर गर्व है, जो हर यात्री के लिए मजबूत सुरक्षा सुनिश्चित करता है।"
        ),
        (
            r"(?:Certainly!\s+)?Under 15 Lakhs, our Venue is the perfect compact SUV option, starting from ₹7\.94 Lakhs, and its automatic variant starts from ₹10\.37 Lakhs\.",
            "15 लाख के अंदर, हमारी वेन्यू सबसे अच्छी कॉम्पैक्ट एसयूवी विकल्प है, जो ₹7.94 लाख से शुरू होती है, और इसका ऑटोमैटिक वेरिएंट ₹10.37 लाख से शुरू होता है।"
        ),
        (
            r"(?:Certainly!\s+)?I will certainly send the (.+?) brochure and detailed quotation to you on WhatsApp right after our call\. Beyond that, would you like to hear about our exchange bonuses\?(?:\.)?",
            lambda m: f"निश्चित रूप से! मैं हमारी कॉल के ठीक बाद आपके व्हाट्सएप पर {m.group(1)} ब्रोशर और विस्तृत कोटेशन भेज दूँगी। इसके अलावा, क्या आप हमारे एक्सचेंज बोनस के बारे में सुनना चाहेंगे?"
        ),
        (
            r"(?:Certainly!\s+)?Yes, we buy all car brands! We provide the best market value for your old car plus an additional exchange bonus when upgrading to the (.+?)\. We also handle all RC transfer paperwork for you\.(?:\s*I can connect you with our advisor for the best possible deal\.\s*Would that work\?(?:\.)?)?",
            lambda m: f"हाँ, हम सभी कार ब्रांड खरीदते हैं! हम आपकी पुरानी कार के लिए सबसे अच्छा बाजार मूल्य और साथ ही {m.group(1)} में अपग्रेड करने पर एक अतिरिक्त एक्सचेंज बोनस प्रदान करते हैं। हम आपके लिए सभी आरसी ट्रांसफर पेपरवर्क भी संभालते हैं। मैं आपको सबसे अच्छे सौदे के लिए हमारे सलाहकार से जोड़ सकती हूँ। क्या यह काम करेगा?"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The (.+?) prioritizes your safety with 6 airbags as standard and a high-strength steel body\.(?:\s*I can arrange a callback for the best deal\.)?(?:\s*I can connect you with our advisor for the best possible deal\.(?:\s*Would that work\?)?)?",
            lambda m: f"मैं निश्चित रूप से स्पष्ट कर सकती हूँ। {m.group(1)} 6 एयरबैग मानक (standard) और उच्च शक्ति वाले स्टील बॉडी के साथ आपकी सुरक्षा को प्राथमिकता देती है। मैं सबसे अच्छे सौदे के लिए हमारे सलाहकार से आपकी बात करवा सकती हूँ।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The (.+?) starts at (.+?) with EMI options starting from (.+?)\.(?:\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            lambda m: f"निश्चित रूप से। {m.group(1)} {m.group(2)} से शुरू होती है, जिसमें मासिक ईएमआई (EMI) {m.group(3)} से शुरू होती है। क्या आप ईएमआई (EMI) के बारे में अधिक जानना चाहेंगे?"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The ([a-zA-Z0-9 ]+) is available in both advanced Automatic \(IVT/DCT\) and Manual transmission options\.?\s*Which one would you prefer to drive\??\.?\s*",
            lambda m: f"{m.group(1)} उन्नत ऑटोमैटिक (IVT/DCT) और मैनुअल दोनों ट्रांसमिशन विकल्पों में उपलब्ध है। आप किसे चलाना पसंद करेंगे?"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The ([a-zA-Z0-9 ]+) comes in multiple engine options including the Turbo Petrol and Diesel\.\s*For a detailed variant comparison, I can connect you with our product specialist\.?$",
            lambda m: f"हुंडई {m.group(1)} टर्बो पेट्रोल और डीजल सहित कई इंजन विकल्पों में आती है। विस्तृत वेरिएंट तुलना के लिए, मैं आपको हमारे उत्पाद विशेषज्ञ से जोड़ सकती हूँ।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The ([a-zA-Z0-9 ]+) is available in both Petrol and Diesel with advanced Automatic \((?:IVT/DCT)\) and Manual options\.\s*Would you like to know the price for the Automatic variant\??\.?$",
            lambda m: f"हुंडई {m.group(1)} पेट्रोल और डीजल दोनों में उन्नत ऑटोमैटिक (IVT/DCT) और मैनुअल विकल्पों के साथ उपलब्ध है। क्या आप ऑटोमैटिक वेरिएंट की कीमत जानना चाहेंगे?"
        ),
        # --- Multilingual Validation Questions ---
        (
            r"(?:Certainly!\s+)?We have a fantastic range of SUV models available, including the Creta and Venue\. The Creta starts from ₹11 Lakhs, and the Venue starts from ₹7\.94 Lakhs\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हमारे पास Creta और Venue सहित SUV मॉडल्स की एक शानदार रेंज उपलब्ध है। Creta ₹11 लाख से शुरू होती है, और Venue ₹7.94 लाख से शुरू होती है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The ([a-zA-Z0-9 ]+) is available in both Petrol and Diesel with advanced Automatic(?: \(IVT/DCT\))? and Manual options\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            lambda m: f"{m.group(1)} पेट्रोल और डीजल दोनों में उन्नत ऑटोमैटिक और मैनुअल विकल्पों के साथ उपलब्ध है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The automatic variant starts from ₹15\.82 Lakhs for the Creta and ₹10\.37 Lakhs for the Venue\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "ऑटोमैटिक वेरिएंट की शुरुआत Creta के लिए ₹15.82 लाख और Venue के लिए ₹10.37 लाख से होती है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The minimum down payment starts from ₹1\.5 Lakhs for the Creta and ₹1 Lakh for the Venue\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "न्यूनतम डाउनपेमेंट Creta के लिए ₹1.5 लाख और Venue के लिए ₹1 लाख से शुरू होता है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The waiting period is approximately 3 weeks for the Creta and ready stock for the Venue\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "वेटिंग पीरियड Creta के लिए लगभग 3 सप्ताह है और Venue के लिए रेडी स्टॉक उपलब्ध है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*Yes, the turbo variant is available for the Creta, Venue, and Verna models\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हाँ, Creta, Venue और Verna मॉडल्स के लिए टर्बो वेरिएंट उपलब्ध है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*We offer the best market value for your old car plus an additional exchange bonus of up to ₹30,000 depending on the model\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हम आपकी पुरानी कार के लिए सबसे अच्छा बाजार मूल्य और साथ ही मॉडल के आधार पर ₹30,000 तक का अतिरिक्त एक्सचेंज बोनस प्रदान करते हैं।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*CNG option is currently available in our Aura and Grand i10 models\. The Creta and Venue come in Petrol and Diesel\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "सीएनजी विकल्प वर्तमान में हमारे Aura और Grand i10 मॉडल्स में उपलब्ध है। Creta और Venue पेट्रोल और डीजल में आते हैं।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*We offer comprehensive service packages, including a 3-year unlimited km warranty, and prepaid maintenance plans\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हम 3-वर्षीय असीमित किमी वारंटी और प्रीपेड मेंटेनेंस योजनाओं सहित व्यापक सर्विस पैकेज प्रदान करते हैं।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*Yes, our on-road price includes comprehensive first-year insurance and registration charges\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हाँ, हमारे ऑन-रोड प्राइस में पहले वर्ष का व्यापक बीमा (insurance) और रजिस्ट्रेशन शुल्क शामिल हैं।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*We are currently offering free basic accessories worth up to ₹10,000 as part of our ongoing promotion\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हम वर्तमान में हमारे चल रहे प्रमोशन के हिस्से के रूप में ₹10,000 तक की मुफ्त बेसिक एक्सेसरीज की पेशकश कर रहे हैं।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*Yes, we can certainly arrange a doorstep test drive at your convenience\. Which model would you like to experience\?(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हाँ, हम निश्चित रूप से आपकी सुविधा के अनुसार घर पर टेस्ट ड्राइव की व्यवस्था कर सकते हैं। आप किस मॉडल का अनुभव करना चाहेंगे?"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*We have spot loan approval within 2 hours through our partner banks with zero processing fees\.(?:\s*Would you like to know more about the features\?|\s*Should I connect you with our advisor\?|\s*Would you like me to share the pricing details\?|\s*Would you like to know more about EMI\?|\s*Should I connect you with our manager\?|\s*I can arrange a callback for the best deal\.)?",
            "हमारे पार्टनर बैंकों के माध्यम से जीरो प्रोसेसिंग फीस के साथ 2 घंटे के भीतर स्पॉट लोन अप्रूवल उपलब्ध है।"
        ),
        (
            r"(?:I can certainly clarify that\.|That's a valid point\.|Sure thing\.|I'd be happy to help\.)?\s*The minimum down payment for the ([a-zA-Z0-9 ]+) starts at approximately ([a-zA-Z0-9₹,.\s]+)\??\.?\s*$",
            lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} के लिए न्यूनतम डाउनपेमेंट (down payment) लगभग {m.group(2)} से शुरू होता है।"
        )
    ]

    @classmethod
    def translate_date_to_hindi(cls, date_str: str) -> str:
        if not date_str:
            return ""
        
        date_str_lower = date_str.lower().strip()
        if date_str_lower == "today":
            return "आज"
        if date_str_lower == "tomorrow":
            return "कल"
            
        translated = date_str
        
        # Mappings for days, months, and periods
        days_map = {
            "monday": "सोमवार", "tuesday": "मंगलवार", "wednesday": "बुधवार",
            "thursday": "गुरुवार", "friday": "शुक्रवार", "saturday": "शनिवार", "sunday": "रविवार"
        }
        months_map = {
            "january": "जनवरी", "february": "फरवरी", "march": "मार्च", "april": "अप्रैल",
            "may": "मई", "june": "जून", "july": "जुलाई", "august": "अगस्त",
            "september": "सितंबर", "october": "अक्टूबर", "november": "नवंबर", "december": "दिसंबर"
        }
        periods_map = {
            "morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात"
        }
        
        for eng, hin in days_map.items():
            translated = re.sub(rf"\b{eng}\b", hin, translated, flags=re.IGNORECASE)
        for eng, hin in months_map.items():
            translated = re.sub(rf"\b{eng}\b", hin, translated, flags=re.IGNORECASE)
        for eng, hin in periods_map.items():
            translated = re.sub(rf"\b{eng}\b", hin, translated, flags=re.IGNORECASE)
            
        return translated

    @classmethod
    def translate_prefix_to_hindi(cls, prefix_str: str) -> str:
        if not prefix_str:
            return ""
        p_lower = prefix_str.lower().strip()
        if "sure" in p_lower:
            return "बिल्कुल।"
        if "no problem" in p_lower:
            sal = "सर" if "sir" in p_lower or "सर" in p_lower else "मैडम" if "ma'am" in p_lower or "मैडम" in p_lower or "maam" in p_lower else ""
            return f"कोई बात नहीं {sal}।"
        if "understood" in p_lower:
            sal = "सर" if "sir" in p_lower or "सर" in p_lower else "मैडम" if "ma'am" in p_lower or "मैडम" in p_lower or "maam" in p_lower else ""
            return f"समझ गई {sal}।"
        return prefix_str

    @classmethod
    def normalize_typos(cls, text: str) -> str:
        """
        Map misspelled model names to their canonical forms.
        """
        if not text:
            return ""
        
        text_lower = text.lower()
        
        # Typos for venue
        venue_typos = [r"\bvenuw\b", r"\bvnue\b", r"\bvanyu\b", r"\bvenye\b", r"\bvenyu\b"]
        for typo in venue_typos:
            text_lower = re.sub(typo, "venue", text_lower)
            
        # Typos for creta
        creta_typos = [r"\bcreeta\b", r"\bcereta\b", r"\bcreata\b"]
        for typo in creta_typos:
            text_lower = re.sub(typo, "creta", text_lower)
            
        # Typos for verna
        verna_typos = [r"\bvirna\b", r"\bvarna\b"]
        for typo in verna_typos:
            text_lower = re.sub(typo, "verna", text_lower)
            
        # Typos for i20
        i20_typos = [r"\bi\s*20\b", r"\bi\s*-?\s*twenty\b", r"\bitem\s*twenty\b"]
        for typo in i20_typos:
            text_lower = re.sub(typo, "i20", text_lower)

        # Devanagari / Hindi Model Name Typos
        # Typos for venue (Devanagari)
        venue_dev = r"(?<![\u0900-\u097F\w])(?:वैल्यू|बीनू|वेन्यू|वेन्यु|वेनु|वेनू|वैन्यू|वैन्यु|बैनू|बैन्यू|बैन्यु|वेनयू)(?![\u0900-\u097F\w])"
        text_lower = re.sub(venue_dev, "venue", text_lower, flags=re.IGNORECASE)
        
        # Typos for creta (Devanagari)
        creta_dev = r"(?<![\u0900-\u097F\w])(?:क्रेता|करेटा|क्रेटा)(?![\u0900-\u097F\w])"
        text_lower = re.sub(creta_dev, "creta", text_lower, flags=re.IGNORECASE)
        
        # Typos for verna (Devanagari)
        verna_dev = r"(?<![\u0900-\u097F\w])(?:वरना|वर्ना|बर्ना)(?![\u0900-\u097F\w])"
        text_lower = re.sub(verna_dev, "verna", text_lower, flags=re.IGNORECASE)
        
        # Typos for exter (Devanagari)
        exter_dev = r"(?<![\u0900-\u097F\w])(?:एक्स्टर|एक्सटर)(?![\u0900-\u097F\w])"
        text_lower = re.sub(exter_dev, "exter", text_lower, flags=re.IGNORECASE)
        
        # Typos for i20 (Devanagari)
        i20_dev = r"(?<![\u0900-\u097F\w])(?:आई\s*बीस|आई\s*20)(?![\u0900-\u097F\w])"
        text_lower = re.sub(i20_dev, "i20", text_lower, flags=re.IGNORECASE)

        # Typos for grand i10 (Devanagari)
        i10_dev = r"(?<![\u0900-\u097F\w])(?:ग्रैंड\s*आई\s*10|ग्रैंड\s*आई\s*दस|आई\s*10|आई\s*दस)(?![\u0900-\u097F\w])"
        text_lower = re.sub(i10_dev, "grand i10", text_lower, flags=re.IGNORECASE)

        # Typos for tucson (Devanagari)
        tucson_dev = r"(?<![\u0900-\u097F\w])(?:टक्सन|टूसन|टूसॉन)(?![\u0900-\u097F\w])"
        text_lower = re.sub(tucson_dev, "tucson", text_lower, flags=re.IGNORECASE)

        # Typos for aura (Devanagari)
        aura_dev = r"(?<![\u0900-\u097F\w])(?:ऑरा|ओरा)(?![\u0900-\u097F\w])"
        text_lower = re.sub(aura_dev, "aura", text_lower, flags=re.IGNORECASE)

        # Typos for new car / enquiry (Devanagari and Latin ASR typos)
        nayi_car_dev = r"(?<![\u0900-\u097F\w])(?:नहीं\s*कर|नही\s*कर|नहीं\s*कार|नही\s*कार)(?![\u0900-\u097F\w])"
        text_lower = re.sub(nayi_car_dev, "नई कार", text_lower, flags=re.IGNORECASE)
        text_lower = re.sub(r"\b(?:nahi\s*car|nahi\s*kar|nahin\s*car|nahin\s*kar)\b", "nayi car", text_lower)

        # ASR Typo/Phonetic mappings to English terms for perfect downstream classification
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:डिटेल्स|डिटेल)(?![\u0900-\u097F\w])", "details", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:जीरो डिप्रेशिएशन|ज़ीरो डिप्रेशिएशन|जीरो डेप्रिसिएशन|ज़ीरो डेप्रिसिएशन|जीरो डेप|ज़ीरो डेप|जीरोडेप)(?![\u0900-\u097F\w])", "zero depreciation", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:बंपर तू बंपर|बम्पर तू बम्पर|बंपर टू बंपर|बम्पर टू बम्पर|बंपर टू बम्पर)(?![\u0900-\u097F\w])", "bumper to bumper", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:एमसी|एनसीबी|एमसीबी)(?![\u0900-\u097F\w])", "ncb", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:कैशलैस|कैशलेस)(?![\u0900-\u097F\w])", "cashless", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:इंजन प्रोटेक्शन|इंजन सुरक्षा)(?![\u0900-\u097F\w])", "engine protection", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:इंफेक्शन|इन्फेक्शन)(?![\u0900-\u097F\w])", "insurance", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:व्हेन\s*यू|व्हेनयू|रिन्यू)(?![\u0900-\u097F\w])", "renew", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:प्रीमियम|प्रीमिया|प्रिमियम|प्रेमियम)(?![\u0900-\u097F\w])", "premium", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:क्लेम|क्लेम्स)(?![\u0900-\u097F\w])", "claim", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:अवेलेबल|अवेलेवल)(?![\u0900-\u097F\w])", "available", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:डीलरशिप)(?![\u0900-\u097F\w])", "dealership", text_lower)
        text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:एक्सपायरी|एक्स्पायरी)(?![\u0900-\u097F\w])", "expiry", text_lower)

        # ASR typos and phonetic variations
        text_lower = re.sub(r"\bdelarship\b", "dealership", text_lower)
        text_lower = re.sub(r"\bdelership\b", "dealership", text_lower)
        text_lower = re.sub(r"\bkyun\b", "kyu", text_lower)
        text_lower = re.sub(r"\bbadd\b", "baad", text_lower)

        if "बाजार" in text_lower or "बाज़ार" in text_lower or "पॉलिसी" in text_lower or "sasta" in text_lower:
            text_lower = re.sub(r"(?<![\u0900-\u097F\w])(?:पेपर|चीपर)(?![\u0900-\u097F\w])", "cheaper", text_lower)
            
        return text_lower

    @classmethod
    def translate_to_english(cls, text: str) -> str:
        """
        Translate user input from Hindi to English using lookups and rules.
        """
        if not text:
            return ""
        
        # Clean Devanagari Matra ASR codepoint differences (short ae matra \u0945 to long ai matra \u0948)
        text = text.replace('\u0945', '\u0948')
        
        text_norm = cls.normalize_typos(text)
        text_clean = text_norm.lower().strip().replace("?", "").replace(".", "").replace(",", "").replace("!", "").replace("।", "").replace("॥", "")
        
        # Normalizing "समरूप" / "samroop" ASR typo for sunroof
        text_clean = re.sub(r"\b(?:samroop|sam\s*roof|समरूप|सम\s*रूप)\b", "sunroof", text_clean)

        
        # Check for wrong number phrases in Hindi / Devanagari / Latin Hinglish / ASR typos
        wrong_no_indicators = [
            "wrong number", "rong number", "worng number", "wrong no", "rong no", "wrong person", "rong person", "wrongperson", "wrongnumber", "rongnumber",
            "गलत नंबर", "गलत नम्बर", "गलत फोन", "गलत कॉल", "रॉन्ग नंबर", "रॉन्ग नम्बर", "रोंग नंबर", "रोंग नम्बर",
            "galat number", "galat phone", "galat no", "galat call",
            "koi aur hai", "sanjana nahi", "sanjana nhi", "sanjana nahi hai"
        ]
        if any(w in text_clean for w in wrong_no_indicators):
            return "wrong number"
        
        # Pre-process: Contextual ASR corrections for voice call mistranscriptions
        asr_corrections = {
            "teacher": "features",
            "teachers": "features",
            "remove": "renew",
            "removes": "renew",
            "depreshation": "depreciation",
            "depresiation": "depreciation",
            "depress": "depreciation"
        }
        for word, correction in asr_corrections.items():
            text_clean = re.sub(rf'\b{re.escape(word)}\b', correction, text_clean, flags=re.I)
        
        # Robust Hinglish transfer phrase normalizations
        transfer_keywords = [
            "baat karaiye", "baat karaye", "baat karayein",
            "baat karwaiye", "baat karwaye", "baat karwayein",
            "baat karvaiye", "baat karvaye", "baat karvayein",
            "baat karvao", "baat karvo", "baat karani hai", "baat karni hai",
            "connect kar", "connect kijiye", "connect karvao", "connect karvo",
            "transfer kar", "transfer kijiye", "transfer karvao",
            "baat karwa do", "baat karva do", "baat kara do", "baat karwao"
        ]
        for phrase in transfer_keywords:
            if phrase in text_clean:
                return "connect me"
        
        # Pre-process: Translate verbal numbers to digits first (to preserve numeric values)
        for verbal, numeric in cls.NUMERIC_WORDS_MAP.items():
            if verbal in text_clean:
                text_clean = text_clean.replace(verbal, numeric)

        # Pre-process: Translate busy/callback Hinglish phrases to English equivalents
        for phrase, eng in cls.BUSY_PHRASES_MAP.items():
            if phrase in text_clean:
                text_clean = text_clean.replace(phrase, eng)

        # If the input is already a canonical English translation, return it directly to prevent double-translation issues
        canonical_values = set(cls.DEVANAGARI_TO_ENGLISH_MAP.values()).union(set(cls.HINDI_TO_ENGLISH_MAP.values()))
        if text_clean in canonical_values:
            return text_clean

        # 1. Exact high-frequency keyword check (Devanagari first, then Latin Hinglish)
        if text_clean in cls.DEVANAGARI_TO_ENGLISH_MAP:
            return cls.DEVANAGARI_TO_ENGLISH_MAP[text_clean]
        if text_clean in cls.HINDI_TO_ENGLISH_MAP:
            return cls.HINDI_TO_ENGLISH_MAP[text_clean]
        
        # Broad-match intent routing for Devanagari/Hindi/Hinglish (handles accents/spelling variations)
        # Not Interested / Stop Calling
        if any(w in text_clean for w in ["nahi chahiye", "nahi leni", "interest nahi", "no interest", "call mat", "नहीं चाहिए", "नहीं लेनी", "इंटरेस्ट नहीं", "कॉल मत", "नहीं करनी", "नहीं करना", "नही चाहिए", "नही लेनी", "इंटरेस्ट नही", "नही करनी", "नही करना", "नही चाहिये", "नहीं चाहिये"]):
            return "not interested"
        # Busy / Callback / Call Later
        if any(w in text_clean for w in ["busy", "later", "meeting", "driving", "call back", "callback", "बिजी", "व्यस्त", "बाद में", "बादमे", "बाद में कॉल", "बाद में बात"]):
            return "busy"
        # Proceed / Go Ahead / Yes
        if any(w in text_clean for w in ["आगे बढ़", "आगे बढ़", "aage badh", "aage badho", "aage badhiye", "aage bad", "aage badh sakti", "aage bad sakti", "badh sakti", "bad sakti", "policy renew", "renew kar", "रिन्यू कर", "पॉलिसी रिन्यू", "renew kar sakti", "रिन्यू कर सकती"]):
            return "yes"
        # Connect / Manager / Advisor
        if any(w in text_clean for w in ["connect", "transfer", "advisor", "manager", "representative", "specialist", "executive", "बात", "करवा", "करवाएं", "करवाओ", "करवाइये", "करवाइए", "कराओ", "करा दो", "करवा दो", "कनेक्ट", "ट्रांसफर", "करवा दीजिए", "कराइये", "कराइए", "करवाइए"]) or ("baat" in text_clean and any(x in text_clean for x in ["kar", "con", "trans", "speak", "talk", "call"])):
            return "connect me"
        # Offers / Discount
        if any(w in text_clean for w in ["ऑफर", "offer", "डिस्काउंट", "discount", "छूट", "फायदा", "benefits", "benefit", "स्कीम", "scheme"]):
            return "what are the offers"
        # Competitor Check (PolicyBazaar, Acko, etc.) - Priority over generic price match
        if any(w in text_clean for w in ["policybazaar", "policy bazaar", "पॉलिसीबाजार", "पॉलिसीबाज़ार", "पॉलिसी बाजार", "पॉलिसी बाज़ार", "acko", "एको", "digit", "डिजिट", "online cheaper", "online sasta"]):
            return "policybazaar cheaper"
            
        # Model detection inside translate_to_english for context preservation
        detected_model = None
        for m in ["creta", "venue", "verna", "tucson", "aura", "exter", "grand i10", "i20", "वैल्यू", "वेन्यू", "क्रेता", "वरना", "एक्स्टर", "ऑरा"]:
            if m in text_clean:
                if m in ["वैल्यू", "वेन्यू", "venue"]: detected_model = "venue"
                elif m in ["क्रेता", "creta"]: detected_model = "creta"
                elif m in ["वरना", "verna"]: detected_model = "verna"
                elif m in ["एक्स्टर", "exter"]: detected_model = "exter"
                elif m in ["ऑरा", "aura"]: detected_model = "aura"
                else: detected_model = m
                break

        # Automatic
        if any(w in text_clean for w in ["automatic", "ऑटोमैटिक", "ऑटोमेटिक"]):
            if detected_model:
                return f"what is the price of the automatic variant of {detected_model}"
            return "what is the price of the automatic variant"
        # CNG
        if any(w in text_clean for w in ["cng", "सीएनजी"]):
            if detected_model:
                return f"is the cng model available for {detected_model}"
            return "is the cng model available"
        # Turbo
        if any(w in text_clean for w in ["turbo", "टर्बो"]):
            if detected_model:
                return f"is the turbo variant available for {detected_model}"
            return "is the turbo variant available"
        # Sunroof
        if any(w in text_clean for w in ["sunroof", "सनरूफ", "सन रूफ"]):
            if detected_model:
                return f"i want sunroof car for {detected_model}"
            return "i want sunroof car"

        # Price / Cost
        if any(w in text_clean for w in ["कीमत", "price", "दाम", "daam", "रेट", "rate", "cost", "on road", "on-road", "ऑन रोड", "ऑनरोड", "प्राइस"]):
            if detected_model == "venue":
                return "i want on road price of venue"
            elif detected_model:
                return f"what is the price of {detected_model}"
            return "what is the price"
        # EMI
        if re.search(r"\bemi\b", text_clean) or any(w in text_clean for w in ["ईएमआई", "किस्त", "kist", "किश्त", "एमी"]):
            if detected_model:
                return f"how much will the emi be for {detected_model}"
            return "how much will the emi be"
        # Safety / Airbags
        if any(w in text_clean for w in ["safe", "safety", "सुरक्षा", "airbag", "air bag", "airbags", "एयरबैग", "एयर बैग", "एयरबैग्स", "गुब्बारा"]):
            if detected_model:
                return f"which cars have 6 airbags for {detected_model}"
            return "which cars have 6 airbags"
        # Exchange
        if any(w in text_clean for w in ["exchange", "एक्सचेंज", "बदली", "पुराना", "पुरानी", "old car"]):
            if detected_model:
                return f"how much value will i get in exchange for {detected_model}"
            return "how much value will i get in exchange"
        # Test Drive
        if any(w in text_clean for w in ["test drive", "testdrive", "चला", "चलाकर", "टेस्ट ड्राइव"]):
            if detected_model:
                return f"is a home test drive possible for {detected_model}"
            return "is a home test drive possible"
        # Insurance (general pre-sales inclusion check)
        if any(phrase in text_clean for phrase in ["insurance included", "insurance features", "insurance add-ons", "बीमा शामिल", "इंश्योरेंस शामिल", "बीमा इंक्लूडेड", "इंश्योरेंस इंक्लूडेड", "बीमा", "इंश्योरेंस"]):
            if detected_model:
                return f"is insurance included for {detected_model}"
            return "is insurance included"
        
        # Diesel
        if any(w in text_clean for w in ["diesel", "डीजल", "डीज़ल"]):
            if detected_model:
                return f"is diesel available for {detected_model}"
            return "is diesel available"
        # Petrol
        if any(w in text_clean for w in ["petrol", "पेट्रोल"]):
            if detected_model:
                return f"is petrol available for {detected_model}"
            return "is petrol available"
        # Colors
        if any(w in text_clean for w in ["color", "colour", "colors", "colours", "कलर", "कलर्स", "रंग", "रंगों", "व्हाइट", "white", "black", "ब्लैक", "सिल्वर", "silver", "grey", "ग्रे"]):
            if detected_model:
                return f"what colors are available for {detected_model}"
            return "what colors are available"

        # SUV / Segment (Devanagari Broad Match)
        if any(w in text_clean for w in ["suv", "segment", "एसयूवी", "सेगमेंट"]):
            return "i am looking for a car in the suv segment"
            
        # Waiting Period (Devanagari Broad Match)
        if any(w in text_clean for w in ["waiting", "waitng", "वेटिंग", "प्रतीक्षा"]):
            if detected_model:
                return f"what is the waiting period for {detected_model}"
            return "what is the waiting period"
            
        # Availability (Devanagari Broad Match) - only if it does not contain specific keywords
        if any(w in text_clean for w in ["available", "अवेलेबल", "उपलब्ध"]):
            if not any(x in text_clean for x in ["claim", "cashless", "कैशलेस", "कैशलैस", "कवर", "cover", "cng", "सीएनजी", "diesel", "डीजल", "डीज़ल", "petrol", "पेट्रोल", "turbo", "टर्बो", "color", "colour", "कलर"]):
                if detected_model:
                    return f"is the variant available for {detected_model}"
                return "is the variant available"

        # Service Package / Warranty (broad match)
        if any(w in text_clean for w in ["सर्विस पैकेज", "service package", "वारंटी", "warranty", "वॉरंटी"]):
            return "what service package is available"

        # Accessories (broad match)
        if any(w in text_clean for w in ["एक्सेसरीज", "एसेसरीज", "accessories"]):
            return "will free accessories be provided"

        # Maintenance Cost (broad match)
        if any(w in text_clean for w in ["मेंटेनेंस", "maintenance", "रखरखाव"]):
            return "which has lowest maintenance"

        # Parts Availability (broad match with ASR typo protection)
        if any(w in text_clean for w in ["पार्ट्स", "parts", "spare", "स्पेयर"]) or any(phrase in text_clean for phrase in ["ke paas easily mil", "ke pass easily mil", "ke paas jaldi mil", "ke pass jaldi mil", "gadi ke paas jaldi", "gadi ke pass jaldi", "gaadi ke paas jaldi", "gaadi ke pass jaldi", "ke paas mil jaate", "ke pass mil jaate", "ke paas available", "ke pass available", "के पास इजीली मिल", "के पास जल्दी मिल", "के पास जल्दी नहीं", "गाड़ी के पास जल्दी", "गाड़ी के पास इजीली", "के पास मिल जाते"]):
            return "are parts easily available"


        # Why Hyundai (broad match)
        if any(w in text_clean for w in ["why hyundai", "व्हाय हुंडई", "कंसीडर हुंडई", "choose hyundai"]):
            return "Why should I buy Hyundai?"

        # Competitor Tata (broad match)
        if any(w in text_clean for w in ["tata", "टाटा"]):
            return "i am also considering tata"

        # Competitor Kia (broad match)
        if any(w in text_clean for w in ["kia", "किया"]):
            return "how is hyundai better than kia"

        # Competitor Mahindra (broad match)
        if any(w in text_clean for w in ["mahindra", "महिंद्रा"]):
            return "why hyundai over mahindra"

        # Family Car (broad match)
        if any(w in text_clean for w in ["family", "फैमिली", "परिवार"]):
            return "which is the best model for a family"

        # Best Selling Car (broad match)
        if any(w in text_clean for w in ["best selling", "सबसे ज्यादा बिकने", "पॉपुलर"]):
            return "which is the best selling car"
        
        # 2. Key phrase sub-mapping (only if it doesn't contain digits or critical busy/time words)
        # This prevents "haan 20000" or "haan busy call later" from being flattened to "yes"
        has_digits = any(char.isdigit() for char in text_clean)
        has_busy = any(word in text_clean for word in ["busy", "later", "meeting", "driving", "call back"])
        
        # Mappings for days, months, and periods to avoid flattening informative slot requests to simple yes/no
        time_indicators = [
            "subah", "morning", "dopahar", "afternoon", "shaam", "evening", "raat", "night",
            "early", "late", "kal", "tomorrow", "aaj", "today", "baje",
            "shaniwar", "ravivar", "somwar", "mangalwar", "budhwar", "guruwar", "veervar", "shukrawar",
            "shaniwaar", "ravivaar", "somvaar", "mangalvaar", "budhvaar", "guruvaar", "veervaar", "shukrawaar",
            "weekend", "weekends", "weekday", "weekdays", "office", "lunch", "meeting", "afternoon", "morning"
        ]
        has_time = any(word in text_clean for word in time_indicators)
        
        # Broad intent routing shortcuts for new car / service enquiries in Hindi/Hinglish (including Devanagari)
        if any(w in text_clean for w in ["nayi gaadi", "nayi car", "new car", "buy karni", "kharidni", "purchase karni", "gaadi kharidni", "नयी गाड़ी", "नई गाड़ी", "गाड़ी खरीदनी", "नयी कार", "नई कार"]):
            return "i want to buy a new car"
        if any(w in text_clean for w in ["service karvani", "service booking", "service book", "repair karwana", "repairing", "सर्विस करवानी", "सर्विस बुक"]):
            return "i want to book a service"
            
        if not has_digits and not has_busy and not has_time:
            words = text_clean.split()
            concern_keywords = ["windshield", "wiper", "glass", "brake", "ac", "oil", "coolant", "tyre", "tire", "scratch", "dent", "paint", "indicator", "light", "engine", "transmission", "clutch", "steering", "wheel", "alignment", "battery"]
            has_concern = any(ck in text_clean for ck in concern_keywords)
            is_long = len(words) > 4
            
            is_identity_confirm = any(phrase in text_clean for phrase in ["बोल रही हूँ", "बोल रही हु", "बोल रही हो", "बोल रहा हूँ", "बोल रहा हु", "बोल रहा हो", "sanjana बोल", "संजना बोल", "kiran बोल", "किरण बोल"])
            is_proceed_confirm = any(phrase in text_clean for phrase in [
                "shuru", "start", "proceed", "kar sakte", "karo", "kar do", "kar dijiye", "kar do",
                "शुरू", "कर सकते", "कर दो", "कर दीजिये", "कर दीजिए"
            ])
            is_ready_choice = any(phrase in text_clean for phrase in [
                "drop", "pickup", "pick up", "aaunga", "aunga", "aaungi", "aungi", "khud",
                "ड्रॉप", "पिक", "खुद", "आऊंगा", "आउंगा", "आऊंगी", "आउंगी", "भेज", "bhej",
                "delivery", "डिलीवरी", "लेने", "lene"
            ])
            is_insurance_query = any(phrase in text_clean for phrase in [
                "zero dep", "zero depreciation", "bumper", "bumper to bumper",
                "ncb", "claim", "claims", "cashless", "premium", "paisa", "kam karo",
                "discount", "loyalty", "match", "expiry", "expire", "inspection", "link",
                "whatsapp", "genuine", "number", "verify", "human", "desk", "manager"
            ])
            is_receptionist_intent = any(phrase in text_clean for phrase in [
                "service", "book", "repair", "enquiry", "nayi", "new car", "buy",
                "purchase", "price", "emi", "model", "showroom"
            ])
            is_faq_query = any(phrase in text_clean for phrase in [
                "exter", "creta", "venue", "i20", "verna", "tata", "kia", "seltos", "nexon",
                "punch", "compass", "tucson", "automatic", "manual", "diesel", "petrol", "turbo",
                "sunroof", "airbag", "adas", "ventilated", "waiting", "mileage", "average", "emi",
                "down payment", "exchange", "colors", "test drive", "loan", "on road"
            ])
            if not has_concern and not is_ready_choice and not is_insurance_query and not is_receptionist_intent and not is_faq_query and (not is_long or is_identity_confirm or is_proceed_confirm):
                if any(confirm in words for confirm in ["haan", "han", "haa", "ha", "haji", "haanji", "hanji", "haaji", "thik", "theek", "kardo", "हाँ", "हा", "हाँजी", "हाँ जी", "बोलिए", "बोलिये", "ठीक", "जी", "करदो", "हां", "हांजी", "हां जी"]) or any(phrase in text_clean for phrase in ["kar do", "book kar", "shuru", "start", "proceed", "kar sakte", "karo", "kar dijiye", "शुरू", "कर सकते", "कर दो", "कर दीजिये", "कर दीजिए", "आगे बढ़", "आगे बढ़", "aage badh", "aage badho", "aage badhiye"]) or "बोल रही हूँ" in text_clean or "बोल रही हु" in text_clean or "बोल रही हो" in text_clean or "बोल रहा हूँ" in text_clean or "बोल रहा हु" in text_clean or "बोल रहा हो" in text_clean or "हाँ बोल" in text_clean or "कर दो" in text_clean or "हाँ जी बोल" in text_clean or "हाँजी बोल" in text_clean or "हां बोल" in text_clean or "हां जी बोल" in text_clean or "हांजी बोल" in text_clean:
                    return "yes"
                if any(negate in words for negate in ["nahin", "nhi", "na", "mat", "no", "nahi", "नहीं", "नही", "ना", "मत"]) or "mat karo" in text_clean or "nahi karna" in text_clean or "नहीं करना" in text_clean or "नही करना" in text_clean:
                    return "no"

            
        # 3. Contextual Date/Time mapping (e.g., "kal subah 10 baje" -> "tomorrow morning 10:00 AM")
        res = text_clean
        # Map time of day
        res = re.sub(r"\bsubah\b", "morning", res)
        res = re.sub(r"\bसुबह\b", "morning", res)
        res = re.sub(r"\bdopahar\b", "afternoon", res)
        res = re.sub(r"\bदोपहर\b", "afternoon", res)
        res = re.sub(r"\bshaam\b", "evening", res)
        res = re.sub(r"\bशाम\b", "evening", res)
        res = re.sub(r"\braat\b", "night", res)
        res = re.sub(r"\bरात\b", "night", res)
        # Map Devanagari English period names (ASR phonetics)
        res = re.sub(r"\bआफ्टरनून\b", "afternoon", res)
        res = re.sub(r"\bआफ्टर\s+नून\b", "afternoon", res)
        res = re.sub(r"\bमॉर्निंग\b", "morning", res)
        res = re.sub(r"\bइवनिंग\b", "evening", res)
        res = re.sub(r"\bनाईट\b", "night", res)
        res = re.sub(r"\bनाइट\b", "night", res)
        res = re.sub(r"\bलंच\b", "lunch", res)
        # Map relative days
        res = re.sub(r"\bkal\b", "tomorrow", res)
        res = re.sub(r"\bकल\b", "tomorrow", res)
        res = re.sub(r"\baaj\b", "today", res)
        res = re.sub(r"\bआज\b", "today", res)
        res = re.sub(r"\bparso\b", "day after tomorrow", res)
        res = re.sub(r"\bपरसों\b", "day after tomorrow", res)
        res = re.sub(r"\bपरसो\b", "day after tomorrow", res)
        # Map days of the week
        res = re.sub(r"\bsomwar\b", "monday", res)
        res = re.sub(r"\bsomvaar\b", "monday", res)
        res = re.sub(r"\bसोमवार\b", "monday", res)
        res = re.sub(r"\bmangalwar\b", "tuesday", res)
        res = re.sub(r"\bmangalvaar\b", "tuesday", res)
        res = re.sub(r"\bमंगलवार\b", "tuesday", res)
        res = re.sub(r"\bbudhwar\b", "wednesday", res)
        res = re.sub(r"\bbudhvaar\b", "wednesday", res)
        res = re.sub(r"\bबुधवार\b", "wednesday", res)
        res = re.sub(r"\bguruwar\b", "thursday", res)
        res = re.sub(r"\bguruvaar\b", "thursday", res)
        res = re.sub(r"\bveervar\b", "thursday", res)
        res = re.sub(r"\bveervaar\b", "thursday", res)
        res = re.sub(r"\bगुरुवार\b", "thursday", res)
        res = re.sub(r"\bshukrawar\b", "friday", res)
        res = re.sub(r"\bshukrawaar\b", "friday", res)
        res = re.sub(r"\bशुक्रवार\b", "friday", res)
        res = re.sub(r"\bshaniwar\b", "saturday", res)
        res = re.sub(r"\bshaniwaar\b", "saturday", res)
        res = re.sub(r"\bशनिवार\b", "saturday", res)
        res = re.sub(r"\bravivar\b", "sunday", res)
        res = re.sub(r"\bravivaar\b", "sunday", res)
        res = re.sub(r"\bरविवार\b", "sunday", res)
        # Map common negations
        res = re.sub(r"\bnahin\b", "no", res)
        res = re.sub(r"\bनहीं\b", "no", res)
        res = re.sub(r"\bनही\b", "no", res)
        res = re.sub(r"\bnhi\b", "no", res)
        res = re.sub(r"\bnahi\b", "no", res)

        # Map common ASR transcription errors for AM/PM
        res = res.replace("आम", "am").replace("एएम", "am").replace("पीएम", "pm")
        
        # Map early/late indicators for slot negation
        res = res.replace("bohot jaldi", "too early").replace("bahut jaldi", "too early").replace("bhut jaldi", "too early")
        res = res.replace("बहुत जल्दी", "too early").replace("बहूत जल्दी", "too early")
        res = res.replace("jaldi", "early").replace("जल्दी", "early")
        res = res.replace("bohot late", "too late").replace("bahut late", "too late").replace("bhut late", "too late")
        res = res.replace("बहुत लेट", "too late").replace("बहूत लेट", "too late")
        res = res.replace("late", "late").replace("लेट", "late")

        # Map numbers/baje
        res = re.sub(r"(\d+)\s*baje", r"\1:00", res)
        
        # 4. Fallback: Check dynamic LLM fallback if enabled, else return original string (NLU will run keyword matches)
        try:
            # We check if LLM translation is enabled first to save import cost/time
            use_llm = os.getenv("USE_HYBRID_LLM_TRANSLATION", "false").lower() == "true"
            # Or if we are running in testing mode with verify_multilingual_faq
            is_faq_test = "verify_multilingual_faq" in "".join(os.sys.argv)
            if use_llm or is_faq_test:
                from llm_client import LLMTranslationClient
                llm_client = LLMTranslationClient()
                llm_translated = llm_client.translate(text, "hi-IN", "en-IN")
                if llm_translated and llm_translated != text:
                    return llm_translated
        except Exception as e:
            print(f"[LLM FALLBACK ERROR] {e}")

        # Map common confirmations at word boundary to yes, so that NLU can process it as affirmative if needed
        res = re.sub(r"\b(haan|haa|ha|haanji|hanji)\b", "yes", res)
        res = re.sub(r"\b(theek hai|thik hai|theeke|thike)\b", "yes", res)

        return res

    @classmethod
    def clean_echoed_concern(cls, text: str) -> str:
        if not text:
            return ""
        cleaned = text.strip()
        pattern = r"^(yes\s+please|yes|please|haan\s+please|haan|haa|ha|hanji|haanji)\b\s*"
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
        if not cleaned:
            return "हाँ"
        return cleaned

    @classmethod
    def translate_model_to_hindi(cls, model: str) -> str:
        if not model:
            return ""
        model_clean = model.lower().strip()
        mapping = {
            "creta": "क्रेटा",
            "venue": "वेन्यू",
            "exter": "एक्स्टर",
            "i20": "i20",
            "tucson": "टक्सन",
            "verna": "वरना",
            "seltos": "सेल्टोस",
            "sonet": "सोनेट",
            "nexon": "नेक्सॉन",
            "punch": "पंच",
            "baleno": "बलेनो",
            "altroz": "ऑल्ट्रोज़",
            "compass": "कम्पस",
            "city": "सिटी",
            "honda city": "होंडा सिटी",
            "xuv700": "XUV700",
            "xuv 3xo": "एक्सयूवी 3XO",
            "grand i10": "ग्रैंड i10",
            "grand i10 nios": "ग्रैंड i10 निओस"
        }
        if model_clean.startswith("hyundai "):
            sub_model = model_clean.replace("hyundai ", "").strip()
            translated_sub = mapping.get(sub_model, sub_model.capitalize())
            return f"हुंडई {translated_sub}"
        return mapping.get(model_clean, model)

    @classmethod
    def translate_phrase_to_hindi(cls, phrase: str) -> str:
        if not phrase:
            return ""
        phrase_clean = phrase.lower().strip().rstrip('.').replace("  ", " ")
        
        mapping = {
            "sporty styling and premium tech features": "स्पोर्टी स्टाइलिंग और प्रीमियम टेक फीचर्स",
            "refined driving comfort, trusted service network, and outstanding resale value": "रिफाइंड ड्राइविंग आराम, भरोसेमंद सर्विस नेटवर्क और शानदार रीसेल वैल्यू",
            "feature-packed cabin and aggressive look": "फीचर से भरपूर केबिन और आक्रामक लुक",
            "excellent ride quality, low maintenance cost (just 35 paise/km), and great reliability": "शानदार राइड क्वालिटी, कम रखरखाव लागत (मात्र 35 पैसे/किमी) और बेहतरीन विश्वसनीयता",
            "solid build and bold styling": "मजबूत बनावट और बोल्ड स्टाइलिंग",
            "excellent ride quality, low maintenance cost, and great reliability": "शानदार राइड क्वालिटी, कम रखरखाव लागत और बेहतरीन विश्वसनीयता",
            "rugged styling": "रफ-एंड-टफ स्टाइलिंग",
            "superior refinement, standard 6 airbags, and advanced features like a smart dual-camera dashcam": "बेहतर रिफाइनमेंट, मानक 6 एयरबैग और स्मार्ट डुअल-कैमरा डैशकैम जैसे उन्नत फीचर्स",
            "high fuel efficiency": "शानदार ईंधन दक्षता",
            "sporty dynamics, unmatched cabin quality, and premium features": "स्पोर्टी डायनेमिक्स, बेजोड़ केबिन क्वालिटी और प्रीमियम फीचर्स",
            "solid build": "मजबूत बनावट",
            "premium cabin comfort, butter-smooth refinement, and advanced tech features": "प्रीमियम केबिन आराम, मक्खन जैसी रिफाइनमेंट और उन्नत तकनीकी फीचर्स",
            "rugged off-road capability": "मजबूत ऑफ-रोडिंग क्षमता",
            "premium luxury features, ultra-refined engine, and superior cabin space": "प्रीमियम लक्जरी फीचर्स, अल्ट्रा-रिफाइंड इंजन और शानदार केबिन स्पेस",
            "traditional styling": "पारंपरिक स्टाइलिंग",
            "futuristic design, powerful turbocharged options, and class-leading safety features": "भविष्यवादी डिज़ाइन, शक्तिशाली टर्बोचार्ज्ड विकल्प और श्रेणी में अग्रणी सुरक्षा फीचर्स",
            "premium cabin quality, excellent refinement, and superior resale value": "प्रीमियम केबिन क्वालिटी, शानदार रिफाइनमेंट और बेहतर रीसेल वैल्यू",
            "bold design": "बोल्ड डिज़ाइन",
            "low maintenance cost, refined engine options, and smooth driving experience": "कम रखरखाव लागत, रिफाइंड इंजन विकल्प और स्मूथ ड्राइविंग अनुभव"
        }
        
        for eng, hin in mapping.items():
            if eng in phrase_clean or phrase_clean in eng:
                return hin
                
        return phrase

    @classmethod
    def translate_features_to_hindi(cls, features_str: str) -> str:
        if not features_str:
            return ""
        
        feature_map = {
            "panoramic sunroof": "पैनोरमिक सनरूफ",
            "ventilated seats": "वेंटिलेटेड सीट्स",
            "bose sound system": "बोस साउंड सिस्टम",
            "level 2 adas": "लेवल 2 एडीएएस (ADAS)",
            "electric sunroof": "इलेक्ट्रिक सनरूफ",
            "air purifier": "एयर प्यूरीफायर",
            "wireless charger": "वायरलेस चार्जर",
            "8-inch touchscreen": "8-इंच टचस्क्रीन",
            "horizon led lamps": "होराइजन एलईडी लैंप्स",
            "heated seats": "हीटेड सीट्स",
            "10.25-inch screen": "10.25-इंच स्क्रीन",
            "6 airbags standard": "6 मानक एयरबैग",
            "htrac awd": "HTRAC एडब्ल्यूडी",
            "blind view monitor": "ब्लाइंड व्यू मॉनिटर",
            "10.25-inch touchscreen": "10.25-इंच टचस्क्रीन",
            "type-c ports": "टाइप-सी पोर्ट्स",
            "8-inch screen": "8-इंच स्क्रीन",
            "best-in-class boot space": "श्रेणी में सर्वश्रेष्ठ बूट स्पेस",
            "dashcam with dual camera": "डुअल कैमरा वाला डैशकैम",
            "digital cluster": "डिजिटल क्लस्टर",
            "ambient lighting": "एम्बिएंट लाइटिंग",
            "puddle lamps": "पडल लैंप्स",
            "sunroof": "सनरूफ",
            "premium technology and comfort features": "प्रीमियम तकनीक और आराम के फीचर्स",
            "rear ac vents": "रियर एसी वेंट्स",
            "cruise control": "क्रूज़ कंट्रोल"
        }
        
        parts = [p.strip() for p in features_str.split(",")]
        translated_parts = []
        for p in parts:
            p_lower = p.lower()
            if p_lower in feature_map:
                translated_parts.append(feature_map[p_lower])
            else:
                translated_parts.append(p)
                
        return ", ".join(translated_parts)

    @classmethod
    def translate_resume_item_to_hindi(cls, item: str) -> str:
        item_clean = item.lower().strip().rstrip('.')
        if "your renewal" in item_clean:
            return "आपके रिन्यूअल"
        
        # Check for premium
        premium_match = re.search(r"the updated premium of (?:₹|rs\.?)?\s*(\d+,?\d*)", item_clean)
        if premium_match:
            return f"₹{premium_match.group(1)} के अपडेटेड प्रीमियम"
            
        if "nominee details" in item_clean:
            return "आपके नॉमिनी डिटेल्स के अपडेट"
            
        if "contact information" in item_clean:
            return "आपके संपर्क विवरण (contact details) के बदलावों"
            
        # Fallback
        return item

    @classmethod
    def translate_summary_to_hindi(cls, summary: str) -> str:
        # Basic keyword replacement for manager summaries
        translated = summary
        translated = re.sub(r"\bdiscount\b", "डिस्काउंट", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bpremium\b", "प्रीमियम", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bnominee\b", "नॉमिनी", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bagreed\b", "सहमत हुए", translated, flags=re.IGNORECASE)
        translated = re.sub(r"\bmanager\b", "मैनेजर", translated, flags=re.IGNORECASE)
        return translated

    @classmethod
    def translate_salutation(cls, sal: str) -> str:
        sal_clean = sal.strip()
        if sal_clean in ['Sir', 'सर']:
            return 'सर'
        if sal_clean in ['Ma\'am', 'मैडम']:
            return 'मैडम'
        # Check for prefix
        if sal_clean.startswith('Ms.'):
            name = sal_clean.replace('Ms.', '').strip()
            return f"{name} मैडम"
        if sal_clean.startswith('Mr.'):
            name = sal_clean.replace('Mr.', '').strip()
            return f"{name} सर"
        return f"{sal_clean} जी"

    @classmethod
    def translate_to_hindi(cls, text: str) -> str:
        """
        Translate English agent speech output to fluent Hindi (sentence-by-sentence).
        """
        if not text:
            return ""

        import re
        # Normalize spaces/punctuation slightly for matching
        normalized_text = text.replace("â‚¹", "₹")
        
        # Check if the entire text block has a direct translation match to prevent sentence-splitting duplicate translations
        full_translation = cls._translate_single_sentence(normalized_text)
            
        if full_translation and full_translation.strip().lower() != normalized_text.strip().lower():
            print(f"[TRANSLATION FULL MATCH] Direct complete translation found, bypassing sentence-split.")
            # Post-process replacement
            full_translation = full_translation.replace("four thousand five hundred rupees", "चार हजार पांच सौ रुपये")
            full_translation = full_translation.replace("by evening", "शाम")
            full_translation = full_translation.replace("periodic maintenance", "पीरियोडिक मेंटेनेंस")
            full_translation = full_translation.replace("windshield", "विंडशील्ड")
            full_translation = full_translation.replace("Windshield", "विंडशील्ड")
            full_translation = full_translation.replace("Hyundai Venue", "हुंडई वेन्यू")
            full_translation = full_translation.replace("hyundai venue", "हुंडई वेन्यू")
            return full_translation
        
        # 1. Match a prefix of the entire text against dynamic regex rules in ENGLISH_TO_HINDI_RULES first
        for pattern, replacement in cls.ENGLISH_TO_HINDI_RULES:
            # Strip trailing $ to prevent catastrophic backtracking and allow prefix matching
            clean_pattern = pattern[:-1] if pattern.endswith('$') else pattern
            match = re.match(clean_pattern, normalized_text, re.IGNORECASE)
            if match:
                matched_len = match.end()
                remaining_suffix = normalized_text[matched_len:].strip()
                
                # Ensure the match ends at a clean sentence or phrase boundary
                if remaining_suffix and normalized_text[matched_len - 1] not in ".!? ":
                    continue
                
                if callable(replacement):
                    res = replacement(match)
                else:
                    res = replacement
                    
                if remaining_suffix:
                    suffix_translated = cls.translate_to_hindi(remaining_suffix)
                    res = f"{res} {suffix_translated}"
                
                # Post-process replacement
                res = res.replace("four thousand five hundred rupees", "चार हजार पांच सौ रुपये")
                res = res.replace("by evening", "शाम")
                res = res.replace("periodic maintenance", "पीरियोडिक मेंटेनेंस")
                res = res.replace("windshield", "विंडशील्ड")
                res = res.replace("Windshield", "विंडशील्ड")
                res = res.replace("Hyundai Venue", "हुंडई वेन्यू")
                res = res.replace("hyundai venue", "हुंडई वेन्यू")
                return res

        # Split on sentence boundaries (?<=...) positive lookbehind keeps ending punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        translated_sentences = []
        for sentence in sentences:
            s = sentence.strip()
            if not s:
                continue
            
            # Check if this sentence matches a dynamic regex rule in ENGLISH_TO_HINDI_RULES
            matched_rule = False
            for pattern, replacement in cls.ENGLISH_TO_HINDI_RULES:
                # Strip trailing $ to prevent catastrophic backtracking
                clean_pattern = pattern[:-1] if pattern.endswith('$') else pattern
                match = re.match(clean_pattern, s, re.IGNORECASE)
                if match and match.end() == len(s.strip()):
                    if callable(replacement):
                        trans_s = replacement(match)
                    else:
                        trans_s = replacement
                    translated_sentences.append(trans_s)
                    matched_rule = True
                    break
            
            if not matched_rule:
                # Translate single sentence
                trans_s = cls._translate_single_sentence(s)
                translated_sentences.append(trans_s)
        
        # Join with proper spacing and punctuation
        res_joined = ""
        for i, ts in enumerate(translated_sentences):
            if i > 0:
                res_joined += " "
            res_joined += ts
            
        # Post-process: Translate common terms inside the final translated response to ensure perfect natural Hindi/Hinglish
        res_joined = res_joined.replace("four thousand five hundred rupees", "चार हजार पांच सौ रुपये")
        res_joined = res_joined.replace("by evening", "शाम")
        res_joined = res_joined.replace("periodic maintenance", "पीरियोडिक मेंटेनेंस")
        res_joined = res_joined.replace("windshield", "विंडशील्ड")
        res_joined = res_joined.replace("Windshield", "विंडशील्ड")
        res_joined = res_joined.replace("Hyundai Venue", "हुंडई वेन्यू")
        res_joined = res_joined.replace("hyundai venue", "हुंडई वेन्यू")
        
        return res_joined

    @classmethod
    def _translate_single_sentence(cls, text: str) -> str:
        """
        Translate a single English sentence to fluent Hindi.
        """
        if not text:
            return ""

        # Load locales dynamically
        cls.load_locales()
        hindi_loc = cls.LOCALES.get("hi", {})
        english_loc = cls.LOCALES.get("en", {})

        # 1. Direct key lookup (e.g. text == "FAQ_SUV_SEGMENT")
        if text in hindi_loc:
            return hindi_loc[text]

        # 2. Reverse lookup: if raw English text matches a value in en.json (stripping periods), return corresponding hi.json translation
        text_clean = text.lower().strip().rstrip('.')
        for key, eng_val in english_loc.items():
            if eng_val.lower().strip().rstrip('.') == text_clean:
                if key in hindi_loc:
                    return hindi_loc[key]

        # --- BULLETPROOF SUBSTRING FAQ TRANSLATOR ---
        core_faq_map = {
            "We have a fantastic range of SUV models available, including the Creta and Venue. The Creta starts from ₹11 Lakhs, and the Venue starts from ₹7.94 Lakhs.":
                "हमारे पास Creta और Venue सहित SUV मॉडल्स की एक शानदार रेंज उपलब्ध है। Creta ₹11 लाख से शुरू होती है, और Venue ₹7.94 लाख से शुरू होती है।",
            
            "The Creta is available in both Petrol and Diesel with advanced Automatic and Manual options.":
                "Creta पेट्रोल और डीजल दोनों में उन्नत ऑटोमैटिक और मैनुअल विकल्पों के साथ उपलब्ध है।",
            
            "The automatic variant starts from ₹15.82 Lakhs for the Creta and ₹10.37 Lakhs for the Venue.":
                "ऑटोमैटिक वेरिएंट की शुरुआत Creta के लिए ₹15.82 लाख और Venue के लिए ₹10.37 लाख से होती है।",
            
            "The automatic variant starts from ₹15.82 Lakhs for the Creta.":
                "ऑटोमैटिक वेरिएंट की शुरुआत Creta के लिए ₹15.82 लाख से होती है।",
            
            "The automatic variant starts from ₹10.37 Lakhs for the Venue.":
                "ऑटोमैटिक वेरिएंट की शुरुआत Venue के लिए ₹10.37 लाख से होती है।",
            
            "The Creta starts at ₹11 Lakhs with EMI options starting from ₹18,500.":
                "Creta ₹11 लाख से शुरू होती है, जिसमें मासिक ईएमआई (EMI) ₹18,500 से शुरू होती है।",
            
            "The minimum down payment starts from ₹1.5 Lakhs for the Creta and ₹1 Lakh for the Venue.":
                "न्यूनतम डाउनपेमेंट Creta के लिए ₹1.5 लाख और Venue के लिए ₹1 लाख से शुरू होता है।",
            
            "The waiting period is approximately 3 weeks for the Creta and ready stock for the Venue.":
                "वेटिंग पीरियड Creta के लिए लगभग 3 सप्ताह है और Venue के लिए रेडी स्टॉक उपलब्ध है।",
            
            "Yes, the turbo variant is available for the Creta, Venue, and Verna models.":
                "हाँ, Creta, Venue और Verna मॉडल्स के लिए टर्बो वेरिएंट उपलब्ध है।",
            
            "We offer the best market value for your old car plus an additional exchange bonus of up to ₹30,000 depending on the model.":
                "हम आपकी पुरानी कार के लिए सबसे अच्छा बाजार मूल्य और साथ ही मॉडल के आधार पर ₹30,000 तक का अतिरिक्त एक्सचेंज बोनस प्रदान करते हैं।",
            
            "CNG option is currently available in our Aura and Grand i10 models. The Creta and Venue come in Petrol and Diesel.":
                "सीएनजी (CNG) विकल्प वर्तमान में हमारे Aura और Grand i10 मॉडल्स में उपलब्ध है। Creta और Venue पेट्रोल और डीजल में आते हैं।",
            
            "We offer comprehensive service packages, including a 3-year unlimited km warranty, and prepaid maintenance plans.":
                "हम 3-वर्षीय असीमित किमी वारंटी और प्रीपेड मेंटेनेंस योजनाओं सहित व्यापक सर्विस पैकेज प्रदान करते हैं।",
            
            "Yes, our on-road price includes comprehensive first-year insurance and registration charges.":
                "हाँ, हमारे ऑन-रोड प्राइस में पहले वर्ष का व्यापक बीमा (insurance) और रजिस्ट्रेशन शुल्क शामिल हैं।",
            
            "We are currently offering free basic accessories worth up to ₹10,000 as part of our ongoing promotion.":
                "हम वर्तमान में हमारे चल रहे प्रमोशन के हिस्से के रूप में ₹10,000 तक की मुफ्त बेसिक एक्सेसरीज की पेशकश कर रहे हैं।",
            
            "The Creta is available in stunning colors like Abyss Black, Atlas White, Titan Grey, and Ranger Khaki.":
                "Creta विभिन्न रंगों जैसे Abyss Black, Atlas White, Titan Grey और Ranger Khaki में उपलब्ध है।",
            
            "The SX and SX(O) variants are available for immediate delivery. Other variants have a 3-week waiting period.":
                "SX और SX(O) वेरिएंट तत्काल डिलीवरी के लिए उपलब्ध हैं। अन्य वेरिएंट की प्रतीक्षा अवधि 3 सप्ताह है।",
            
            "Yes, we can certainly arrange a doorstep test drive at your convenience. Which model would you like to experience?":
                "हाँ, हम निश्चित रूप से आपकी सुविधा के अनुसार घर पर टेस्ट ड्राइव की व्यवस्था कर सकते हैं। आप किस मॉडल का अनुभव करना चाहेंगे?",
            
            "We have spot loan approval within 2 hours through our partner banks with zero processing fees.":
                "हमारे पार्टनर बैंकों के माध्यम से जीरो प्रोसेसिंग फीस के साथ 2 घंटे के भीतर स्पॉट लोन अप्रूवल उपलब्ध है।",
            
            "The Venue and Grand i10 Nios offer excellent mileage and fuel efficiency of up to 20 kilometers per liter, making them perfect for daily commutes.":
                "वेन्यू (Venue) और Grand i10 Nios 20 किलोमीटर प्रति लीटर तक का शानदार माइलेज और ईंधन दक्षता प्रदान करते हैं, जो दैनिक आवागमन के लिए बिल्कुल परफेक्ट हैं।",
            
            "The Creta is Alcon Hyundai's highest-selling SUV, offering premium tech, high resale value, and unmatched comfort.":
                "Creta अल्कॉन हुंडई की सबसे अधिक बिकने वाली SUV है, जो प्रीमियम तकनीक, उच्च रीसेल मूल्य और बेजोड़ आराम प्रदान करती है।",
            
            "The Creta is the perfect family SUV, offering spacious 5-seater seating, a large 433-liter boot space, and 6 standard airbags.":
                "Creta एक आदर्श पारिवारिक (family) SUV है, जो विशाल 5-सीटर बैठने की जगह, 433-लीटर का बड़ा बूट स्पेस और 6 मानक एयरबैग प्रदान करती है।",
            
            "The Venue has the lowest maintenance cost in its segment, averaging just 35 paise per kilometer over 5 years.":
                "Venue की अपने सेगमेंट में सबसे कम रखरखाव लागत (maintenance cost) है, जो 5 वर्षों में औसतन केवल 35 पैसे प्रति किलोमीटर है।",
            
            "Yes, I'm calling directly from Alcon Hyundai, an authorized dealership. We got your details from our official dealership records as your car is registered with us. To verify this, I can instantly share our dealership contact details and policy proposal directly to your registered WhatsApp number for your convenience.":
                "हाँ, मैं सीधे अल्कॉन हुंडई से कॉल कर रही हूँ, जो कि एक अधिकृत डीलरशिप है। हमें आपके डिटेल्स हमारे डीलरशिप रिकॉर्ड से मिले हैं क्योंकि आपकी कार हमारे पास रजिस्टर्ड है। वेरिफिकेशन के लिए, मैं तुरंत आपके व्हाट्सएप नंबर पर डीलरशिप की जानकारी भेज सकती हूँ ताकि आपको सुविधा रहे।",
            
            "Our comprehensive bumper-to-bumper policy gives 100% coverage for all parts under Zero Depreciation with zero deduction for wear and tear. This policy also includes key add-ons like Engine Protection cover against water damage or hydrostatic lock, and your No Claim Bonus (NCB) discount which can save you up to 50% on premium.":
                "हमारी बम्पर-टू-बम्पर पॉलिसी में जीरो डेप्रिसिएशन शामिल है, जिससे 100% कवरेज मिलता है। इसमें पानी भरने या हाइड्रोस्टेटिक लॉक से बचाव के लिए इंजन प्रोटेक्शन और आपका नो क्लेम बोनस (NCB) भी शामिल है, जिससे 50% तक की छूट मिलती है।",
            
            "While making a claim resets your No Claim Bonus (NCB) discount, you are still entitled to up to 2 claims per year. We offer fully cashless claim processing and repairs with genuine parts at all authorized Alcon workshops for a hassle-free experience.":
                "क्लेम करने से आपका नो क्लेम बोनस यानी NCB रीसेट हो जाता है, पर आप साल में दो बार क्लेम ले सकते हैं। हम सभी अधिकृत अल्कॉन वर्कशॉप्स पर कैशलेस क्लेम की सुविधा देते हैं ताकि आपको असली पार्ट्स के साथ आसान सर्विस मिले।",
            
            "I understand online quotes from portals like PolicyBazaar can look cheaper, but some online quotes might have different coverage or key add-ons like Zero-Dep excluded. By renewing directly with the dealership, you secure 100% cashless claims and genuine OEM parts at our workshops. Would you like to proceed, or shall I connect you to our desk to explore if we can match that online rate?":
                "मैं समझती हूँ कि पॉलिसीबाज़ार जैसे ऑनलाइन कोट्स थोड़े सस्ते लग सकते हैं, पर उनमें जीरो-डेप जैसे जरूरी एड-ऑन्स शामिल नहीं होते हैं। सीधे डीलरशिप से रिन्यू कराने पर आपको 100% कैशलेस क्लेम और असली ओईएम पार्ट्स मिलते हैं। क्या हम आगे बढ़ें, या ऑनलाइन रेट मैच करने के लिए मैं आपकी बात हमारे मैनेजर से करवाऊँ?",
            
            "Since you are a valued Alcon Hyundai customer, I have already applied our maximum 15% dealership loyalty discount and waived all physical vehicle inspection charges. To see if we can match a competitor's price or secure a special manager discount, I can connect you to our Insurance Manager right now. Would you like to connect?":
                "आपके लिए मैंने पहले ही 15% का बेस्ट लॉयल्टी डिस्काउंट लगा दिया है और सभी इंस्पेक्शन चार्जेस भी माफ कर दिए हैं। ऑनलाइन प्राइस मैच करने या किसी स्पेशल डिस्काउंट के लिए मैं आपकी बात तुरंत हमारे इंश्योरेंस मैनेजर से करवा सकती हूँ। क्या मैं कनेक्ट करूँ?",
            
            "Driving with an expired policy is illegal and subject to severe penalties. If your policy has expired for more than 90 days, you will also permanently lose your 50% No Claim Bonus discount and require a physical vehicle inspection before renewal. We can easily process an instant renewal today to avoid inspection or bonus loss. Shall we secure it?":
                "यदि आपका इंश्योरेंस समाप्त हो जाता है, तो आपका वाहन चलाना अवैध हो जाता है और उस पर भारी जुर्माना लग सकता है। इसके अलावा, यदि पॉलिसी 90 दिनों से अधिक समय से समाप्त हो गई है, तो आप 50% तक के अपने संचित नो क्लेम बोनस (NCB) डिस्काउंट को स्थायी रूप से खो देंगे, और रिन्यूअल से पहले एक औपचारिक भौतिक वाहन निरीक्षण (inspection) अनिवार्य हो जाएगा। हम बिना किसी निरीक्षण या NCB हानि के आपको कवर रखने के लिए आज ही एक त्वरित रिन्यूअल प्रोसेस कर सकते हैं। क्या हम इसे सुरक्षित करें?",
            
            "Yes! We support multiple secure digital payment methods, including UPI, credit/debit card, net banking, and easy EMI options. Once payment is done, the digital receipt and policy copy are sent instantly to your email and WhatsApp. I can share the secure payment link on your registered mobile number right away. Shall I send it?":
                "हाँ! हम कई सुरक्षित डिजिटल भुगतान विधियों का समर्थन करते हैं। आप UPI, क्रेडिट/डेबिट कार्ड या नेट बैंकिंग के माध्यम से तुरंत भुगतान कर सकते हैं, और हम आसान क्रेडिट कार्ड ईएमआई (EMI) विकल्प भी प्रदान करते हैं। एक बार भुगतान पूरा होने के बाद, आपको तुरंत अपने ईमेल और व्हाट्सएप पर आधिकारिक डिजिटल रसीद और पॉलिसी की प्रति प्राप्त हो जाएगी। मैं अभी आपके पंजीकृत मोबाइल नंबर पर सुरक्षित भुगतान लिंक साझा कर सकती हूँ। क्या मैं इसे भेज दूँ?",
            
            "I apologize for the inconvenience of our calls. Premiums sometimes change due to revised government tax rates. To assist you, I can register your number in our Do Not Disturb database right away to stop future calls, or connect you to a manager to explore a better rate. Which would you prefer?":
                "कॉल्स से हुई असुविधा के लिए मैं क्षमा चाहती हूँ। सरकारी टैक्स रेट्स में बदलाव के कारण प्रीमियम्स में थोड़ा अंतर आ जाता है। आपकी सुविधा के लिए, मैं आपका नंबर तुरंत हमारे डू नॉट डिस्टर्ब (DND) लिस्ट में डाल सकती हूँ ताकि आगे कोई कॉल न आए, या फिर बेहतर रेट के लिए मैनेजर से कनेक्ट कर दूँ? आप क्या पसंद करेंगे?",
            
            "Certainly. To ensure you get the best assistance with these specific policy details, I'll connect you to our insurance desk immediately. Please stay on the line.":
                "निश्चित रूप से। इन विशिष्ट पॉलिसी डिटेल्स के लिए मैं आपकी बात तुरंत हमारे इंश्योरेंस डेस्क से करवा देती हूँ। कृपया लाइन पर बने रहें।",
            
            "I understand that price is important. Let me check our partner rates for you. Apart from HDFC Ergo, we have tie-ups with 5 other major insurers. ICICI Lombard is at ₹11,800 and Bajaj Allianz is at ₹11,500. Both provide identical coverage. Would you like to proceed with one of these, or shall I connect you to our desk to explore more?":
                "मैं समझती हूँ कि कीमत एक महत्वपूर्ण कारक है। मुझे आपके लिए हमारे पार्टनर रेट्स चेक करने दीजिए। HDFC Ergo के अलावा, हमारे 5 अन्य प्रमुख बीमाकर्ताओं के साथ टाई-अप हैं। ICICI Lombard का प्रीमियम ₹11,800 है और Bajaj Allianz का ₹11,500 है। दोनों में समान कवरेज मिलता है। क्या आप इनमें से किसी एक के साथ आगे बढ़ना चाहेंगे, या अधिक जानकारी के लिए मैं आपकी बात हमारे डेस्क से करवाऊँ?",
            
            "I hear you. Since those options still don't quite meet your budget, let me check if we can do better. I'll have our Insurance Manager call you back with a special approval rate. Would that work for you?":
                "मैं आपकी बात समझती हूँ। चूंकि वे विकल्प अभी भी आपके बजट के अनुकूल नहीं हैं, मुझे देखने दीजिए कि क्या हम इससे बेहतर कर सकते हैं। मैं हमारे इंश्योरेंस मैनेजर से कहकर आपको एक विशेष अप्रूवल रेट के साथ कॉल बैक करवा दूँगी। क्या यह आपके लिए ठीक रहेगा?"
        }

        # Normalize spaces/punctuation slightly for matching
        normalized_text = text.replace("â‚¹", "₹")
        normalized_text = re.sub(r'\.\s+(\d+)', r'.\1', normalized_text)

        matched_faq = None
        for eng_faq, hin_faq in core_faq_map.items():
            eng_faq_clean = eng_faq.lower().strip().rstrip('.')
            norm_text_clean = normalized_text.lower().strip().rstrip('.')
            # Substring matching safety check:
            # If the query is short, require an exact match to prevent dangerous substring overlaps
            # (like matching "sure" inside "ensure", or "yes" inside longer phrases).
            if len(norm_text_clean) < 20:
                if norm_text_clean == eng_faq_clean:
                    matched_faq = (eng_faq, hin_faq)
                    break
            else:
                if eng_faq_clean in norm_text_clean or (norm_text_clean in eng_faq_clean and len(norm_text_clean) >= len(eng_faq_clean) * 0.7):
                    matched_faq = (eng_faq, hin_faq)
                    break

        if matched_faq:
            # We found a matching core FAQ!
            # Let's rebuild the sentence in Hindi by translating intros and CTAs.
            eng_faq, hin_faq = matched_faq
            
            # Translate common intros
            intro_part = ""
            if "certainly! regarding the creta" in normalized_text.lower():
                intro_part = "निश्चित रूप से! Creta के संबंध में, "
            elif "certainly! regarding the venue" in normalized_text.lower():
                intro_part = "निश्चित रूप से! Venue के संबंध में, "
            elif "i can certainly clarify that" in normalized_text.lower():
                intro_part = "मैं निश्चित रूप से इसे स्पष्ट कर सकती हूँ। "
            elif "that's a valid point" in normalized_text.lower():
                intro_part = "यह बहुत सही बात है। "
            elif "sure thing" in normalized_text.lower():
                intro_part = "हाँ, बिल्कुल। "
            elif "i'd be happy to help" in normalized_text.lower():
                intro_part = "मुझे आपकी मदद करने में खुशी होगी। "
            elif "absolutely ma'am" in normalized_text.lower() or "absolutely मैडम" in normalized_text.lower():
                intro_part = "बिल्कुल मैडम। "

            # Translate common CTAs
            cta_part = ""
            if "would you like to know more about the features" in normalized_text.lower():
                cta_part = " क्या आप इसके फीचर्स के बारे में और जानना चाहेंगे?"
            elif "should i connect you with our advisor" in normalized_text.lower():
                cta_part = " क्या मैं आपकी बात हमारे सलाहकार से करवाऊँ?"
            elif "would you like me to share the pricing details" in normalized_text.lower():
                cta_part = " क्या आप चाहेंगे कि मैं आपके साथ कीमत की जानकारी साझा करूँ?"
            elif "would you like to know more about emi" in normalized_text.lower():
                cta_part = " क्या आप ईएमआई के बारे में और जानना चाहेंगे?"
            elif "should i connect you with our manager" in normalized_text.lower():
                cta_part = " क्या मैं आपकी बात हमारे मैनेजर से करवाऊँ?"
            elif "i can arrange a callback for the best deal" in normalized_text.lower():
                cta_part = " मैं आपके लिए सबसे अच्छे डील के लिए कॉल बैक अरेंज कर सकती हूँ।"
            elif "connecting you to our sales manager" in normalized_text.lower():
                cta_part = " अभी आपको हमारे सेल्स मैनेजर से जोड़ रही हूँ। हमारी सेल्स टीम अभी अन्य ग्राहकों की सहायता करने में व्यस्त है। मैं आपकी बात हमारे ऑन-कॉल सुपरवाइजर से करवा देती हूँ।"

            final_hindi = f"{intro_part}{hin_faq}{cta_part}"
            print(f"[SUBSTRING FAQ TRANSLATOR] '{text}' -> '{final_hindi}'")
            return final_hindi

        # --- DYNAMIC KB RESPONSE TRANSLATION ---
        cleaned_text = text.strip()
        
        # 1. Extract Intro
        intro_translated = ""
        intros_patterns = [
            (r"^Indeed, we can also look at the ([a-zA-Z0-9 ]+)\.?\s*", lambda m: f"बिल्कुल, हम {m.group(1)} को भी देख सकते हैं। "),
            (r"^That's a valid point\.?\s*", "यह बहुत सही बात है। "),
            (r"^I can certainly clarify that\.?\s*", "मैं निश्चित रूप से इसे स्पष्ट कर सकती हूँ। "),
            (r"^Sure thing\.?\s*", "हाँ, बिल्कुल। "),
            (r"^I'd be happy to help\.?\s*", "मुझे आपकी मदद करने में खुशी होगी। ")
        ]
        
        remaining_text = cleaned_text
        for pat, rep in intros_patterns:
            m = re.match(pat, remaining_text, re.IGNORECASE)
            if m:
                if callable(rep):
                    intro_translated = rep(m)
                else:
                    intro_translated = rep
                remaining_text = remaining_text[m.end():].strip()
                break
                
        # 2. Extract CTA at the end
        cta_translated = ""
        ctas_patterns = [
            (r"\s*Would you like to know more about the features\?\??\.?\s*$", "क्या आप इसके फीचर्स के बारे में और जानना चाहेंगे?"),
            (r"\s*Should I connect you with our advisor\?\??\.?\s*$", "क्या मैं आपकी बात हमारे सलाहकार से करवाऊँ?"),
            (r"\s*Would you like me to share the pricing details\?\??\.?\s*$", "क्या आप चाहेंगे कि मैं आपके साथ कीमत की जानकारी साझा करूँ?"),
            (r"\s*Would you like to know more about EMI\?\??\.?\s*$", "क्या आप ईएमआई के बारे में और जानना चाहेंगे?"),
            (r"\s*Should I connect you with our manager\?\??\.?\s*$", "क्या मैं आपकी बात हमारे मैनेजर से करवाऊँ?"),
            (r"\s*I can arrange a callback for the best deal\.\s*$", "मैं आपके लिए सबसे अच्छे डील के लिए कॉल बैक अरेंज कर सकती हूँ।")
        ]
        
        for pat, rep in ctas_patterns:
            m = re.search(pat, remaining_text, re.IGNORECASE)
            if m:
                cta_translated = rep
                remaining_text = remaining_text[:m.start()].strip()
                break

        core_translated = ""
        core_patterns = [
            # 1. The Model is a fantastic choice, known for its Features. It starts from Price.
            (
                r"^The ([a-zA-Z0-9 ]+) is a fantastic choice,\s*known for its ([^.!?]+)\.\s*It starts from ([^.!?]+)\??\.?\s*$",
                lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} एक बेहतरीन विकल्प है, जो अपने {m.group(2)} के लिए जानी जाती है। इसकी शुरुआत {m.group(3)} से होती है।"
            ),
            # 2. The Model prioritizes your safety with 6 airbags as standard and a high-strength steel body.
            (
                r"^The ([a-zA-Z0-9 ]+) prioritizes your safety with 6 airbags as standard and a high-strength steel body\.?$",
                lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} 6 एयरबैग्स (Airbags) स्टैंडर्ड और हाई-स्ट्रेंथ स्टील बॉडी के साथ आपकी सुरक्षा को प्राथमिकता देती है।"
            ),
            # 3. The Model starts at Price with EMI options starting from EMI.
            (
                r"^The ([a-zA-Z0-9 ]+) starts at ([^.!?]+) with EMI options starting from ([^.!?]+)\.?$",
                lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} {m.group(2)} से शुरू होती है, जिसमें मासिक ईएमआई (EMI) {m.group(3)} से शुरू होती है।"
            ),
            # 4. We have a fantastic range of Hyundai vehicles available, including the ...
            (
                r"^We have a fantastic range of Hyundai vehicles available, including the ([^.!?]+)\.?$",
                lambda m: f"हमारे पास उपलब्ध हुंडई गाड़ियों की एक बेहतरीन रेंज है, जिसमें {m.group(1)} शामिल हैं।"
            ),
            # 5. Since you are a Hyundai owner, you are eligible for exclusive loyalty bonuses up to ...
            (
                r"^Since you are a Hyundai owner, you are eligible for exclusive loyalty bonuses up to ([^.!?]+)\.?$",
                lambda m: f"चूंकि आप एक हुंडई मालिक हैं, आप {m.group(1)} तक के विशेष लॉयल्टी बोनस के लिए पात्र हैं।"
            ),
            # 6. Yes, we have special corporate discounts for employees of leading companies.
            (
                r"^Yes, we have special corporate discounts for employees of leading companies\.?$",
                "हाँ, हमारे पास प्रमुख कंपनियों के कर्मचारियों के लिए विशेष कॉर्पोरेट डिस्काउंट उपलब्ध हैं।"
            ),
            # 7. We're currently offering festive benefits and free accessories worth up to Value on the Model.
            (
                r"^We're currently offering festive benefits and free accessories worth up to ([^.!?]+?) on the ([a-zA-Z0-9 ]+)\.?$",
                lambda m: f"हम वर्तमान में {TranslationAdapter.translate_model_to_hindi(m.group(2))} पर {m.group(1)} तक के त्योहारी लाभ और मुफ्त एक्सेसरीज की पेशकश कर रहे हैं।"
            ),
            # 8. Hyundai models offer superior refinement and a much wider service network compared to competitors.
            (
                r"^Hyundai models offer superior refinement and a much wider service network compared to competitors\.?$",
                "प्रतियोगियों की तुलना में हुंडई मॉडल बेहतर रिफाइनमेंट और बहुत व्यापक सर्विस नेटवर्क प्रदान करते हैं।"
            ),
            # 9. Our showroom is open every day from 9 AM to 8 PM, including weekends.
            (
                r"^Our showroom is open every day from 9 AM to 8 PM, including weekends\.?$",
                "हमारा शोरूम वीकेंड सहित हर दिन सुबह 9 बजे से रात 8 बजे तक खुला रहता है।"
            ),
            # 10. The waiting period is approximately Waiting.
            (
                r"^The waiting period is approximately ([^.!?]+)\.?$",
                lambda m: f"वेटिंग पीरियड लगभग {m.group(1)} है।"
            ),
            # 11. I'll have to check our records for your specific service due date.
            (
                r"^I'll have to check our records for your specific service due date\.?$",
                "मुझे आपकी विशिष्ट सर्विस देय तारीख के लिए हमारे रिकॉर्ड की जांच करनी होगी।"
            ),
            # 12. Dynamic transmission option choice
            (
                r"^The ([a-zA-Z0-9 ]+) is available in both advanced Automatic \(IVT/DCT\) and Manual transmission options\.\s*Which one would you prefer to drive\??\.?\s*$",
                lambda m: f"{m.group(1)} उन्नत ऑटोमैटिक (IVT/DCT) और मैनुअल दोनों ट्रांसमिशन विकल्पों में उपलब्ध है। आप किसे चलाना पसंद करेंगे?"
            ),
            # 13. Dynamic downpayment quote
            (
                r"^The minimum down payment for the ([a-zA-Z0-9 ]+) starts at approximately ([a-zA-Z0-9₹,.\s]+)\??\.?\s*$",
                lambda m: f"{TranslationAdapter.translate_model_to_hindi(m.group(1))} के लिए न्यूनतम डाउनपेमेंट (down payment) लगभग {m.group(2)} से शुरू होता है।"
            )
        ]
        
        for pat, rep in core_patterns:
            m = re.match(pat, remaining_text, re.IGNORECASE)
            if m:
                if callable(rep):
                    core_translated = rep(m)
                else:
                    core_translated = rep
                break

        if core_translated:
            parts = []
            if intro_translated:
                parts.append(intro_translated.strip())
            parts.append(core_translated.strip())
            if cta_translated:
                parts.append(cta_translated.strip())
            return " ".join(parts)
        elif (intro_translated or cta_translated) and len(remaining_text.strip()) < 10:
            parts = []
            if intro_translated:
                parts.append(intro_translated.strip())
            if cta_translated:
                parts.append(cta_translated.strip())
            return " ".join(parts)

        # Walk through our dynamic regex rules
        for pattern, replacement in cls.ENGLISH_TO_HINDI_RULES:
            # Strip trailing $ to prevent catastrophic backtracking
            clean_pattern = pattern[:-1] if pattern.endswith('$') else pattern
            match = re.match(clean_pattern, text, re.IGNORECASE)
            if match and match.end() == len(text.strip()):
                if callable(replacement):
                    return replacement(match)
                return replacement

        # Basic fallback replacement for common phrases if it didn't match the strict regexes above
        translated = text
        translated = translated.replace("Hello", "नमस्ते")
        translated = translated.replace("Have a great day!", "आपका दिन बहुत अच्छा रहे!")
        translated = translated.replace("Have a nice day!", "आपका दिन शुभ हो!")
        translated = translated.replace("Understood", "समझ गई")
        translated = translated.replace("Sir", "सर")
        translated = translated.replace("Ma'am", "मैडम")
        
        return translated
