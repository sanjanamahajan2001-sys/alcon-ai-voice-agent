import re
import json
from typing import Dict, Any, Optional

class IntentEngine:
    def __init__(self, kb_data):
        self.kb = kb_data
        self.config = {
            "HOT_KEYWORDS": ["price", "cost", "how much", "rate", "cheap", "expensive", "value", "budget", "shell out", "pay", "bill", "test drive", "drive", "buy", "purchase", "exchange", "upgrade", "discount", "offer", "benefit", "bonus", "valuation", "on road", "connect", "representative", "specialist", "talk to", "adas", "safety", "sunroof", "downpayment", "down payment", "warranty", "feature", "features", "details", "emi", "loan", "kia", "tata", "maruti", "mahindra", "better", "cheaper", "expensive", "finance", "options", "showroom", "location", "colors", "loyalty", "years", "old customer", "hidden", "catch", "fee", "enquiry", "inquiry", "new", "car", "vehicle", "model", "booking", "nayi", "nai", "gaadi", "gadi", "puchtach"],
            "WARM_KEYWORDS": ["whatsapp", "later", "details", "tomorrow", "message", "send me", "email", "after", "morning", "evening", "next week", "next month", "maybe", "not sure", "thinking", "discuss", "discuss with family", "talk to family", "ask family", "family check", "check", "nashik", "mumbai", "pune", "delhi", "bangalore", "day after tomorrow"],
            "NEG_SENTIMENT_KEYWORDS": ["bad", "horrible", "stupid", "annoying", "waste", "useless", "irritated", "angry", "frustrated", "worst", "unhelpful"],
            "HELP_KEYWORDS": ["help", "human", "person", "agent", "manager", "support", "representative", "somebody", "anyone", "talk to", "connect me", "transfer"],
            "TECHNICAL_KEYWORDS": ["turbo", "engine", "bhp", "torque", "diesel", "petrol", "dct", "automatic", "manual", "transmission", "variants", "ivt", "specs", "specifications"]
        }

    def explain_decision(self, user_input, lang=None):
        """Analyze user input against keywords with negation handling and whole-word matching."""
        user_input_lower = user_input.lower()
        
        # Determine keywords configuration based on language
        # Default to checking both English and Hindi/Hinglish in parallel if lang is None or hi-IN
        hot_keywords = list(self.config["HOT_KEYWORDS"])
        warm_keywords = list(self.config["WARM_KEYWORDS"])
        neg_sentiment_keywords = list(self.config["NEG_SENTIMENT_KEYWORDS"])
        help_keywords = list(self.config["HELP_KEYWORDS"])
        
        if lang is None or lang == "hi-IN" or any(hk in user_input_lower for hk in ["hai", "kya", "daam", "gadi", "gaadi", "नयी", "नई", "कार", "गाड़ी", "गाड़ी", "पूछताछ"]):
            hindi_hot = ["daam", "bhugtan", "kharid", "buy kar", "book kar", "mileage kitna", "gadi", "gaadi", "car le", "automatic ka", "discount", "cng", "insurance", "loan", "downpayment", "down payment", "kist", "emi", "एमी", "नयी", "नई", "कार", "गाड़ी", "गाड़ी", "पूछताछ"]

            hindi_warm = ["kal", "parso", "subah", "shaam", "dopahar", "whatsapp pe", "message kar", "detail bhej", "बिजी", "व्यस्त", "बाद में"]
            hindi_neg = ["bakwaas", "gussa", "irritate", "kharab", "worse", "annoy"]
            hindi_help = ["baat karva", "manager se", "representative", "insan se", "insaan"]
            
            hot_keywords.extend(hindi_hot)
            warm_keywords.extend(hindi_warm)
            neg_sentiment_keywords.extend(hindi_neg)
            help_keywords.extend(hindi_help)
        
        # Whole-word matching (with optional plural 's', safe for Devanagari)
        def safe_search(pattern_word, text):
            if any(ord(c) > 127 for c in pattern_word):
                pat = rf'(?<![a-zA-Z0-9\u0900-\u097F]){re.escape(pattern_word)}(?![a-zA-Z0-9\u0900-\u097F])'
            else:
                pat = rf'\b{re.escape(pattern_word)}s?\b'
            return bool(re.search(pat, text, re.I))

        matched_hot = [k for k in hot_keywords if safe_search(k, user_input_lower)]
        matched_warm = [k for k in warm_keywords if safe_search(k, user_input_lower)]

        # Negation and Exit handling
        negations = ["no", "not", "don't", "don't", "never", "won't", "can't"]
        exit_phrases = ["wrong number", "worng number", "rong number", "not me", "not maahi", "not sanjana", "wrong person", "rong person", "not my car", "galat number", "wrong no", "rong no"]
        
        is_wrong_number = any(re.search(rf'\b{re.escape(p)}\b', user_input_lower) for p in exit_phrases)
        
        # Check if any hot keyword is negated
        is_negated = False
        for hot_k in matched_hot:
            pattern = rf'({ "|".join(negations) })\s+(?:\w+\s+){0,2}{re.escape(hot_k)}'
            if re.search(pattern, user_input_lower):
                is_negated = True
                break
 
        # Explicit rejection check
        explicit_no = any(re.search(rf'\b{n}\b', user_input_lower) for n in negations) and ("interest" in user_input_lower or "want" in user_input_lower)
        
        # Sentiment Scoring
        neg_score = sum(1 for k in neg_sentiment_keywords if re.search(rf'\b{re.escape(k)}\b', user_input_lower))
        sentiment_score = min(neg_score * 0.3, 1.0) # Simple heuristic for demo
        
        # Help Detection
        wants_help = any(re.search(rf'\b{re.escape(k)}\b', user_input_lower) for k in help_keywords)

        decision = "COLD"
        if is_wrong_number:
            decision = "EXIT"
        elif sentiment_score > 0.6:
            decision = "FRUSTRATION"
        elif wants_help and "not" not in user_input_lower:
            decision = "HELP_REQUEST"
        elif matched_hot and not is_negated:
            decision = "HOT"
        elif matched_hot and is_negated:
            decision = "COLD"
        elif matched_warm:
            decision = "WARM"
        
        if explicit_no:
            decision = "COLD"

        return {
            "decision": decision,
            "matched_hot": matched_hot,
            "matched_warm": matched_warm,
            "is_negated": is_negated,
            "sentiment_score": sentiment_score,
            "wants_help": wants_help,
            "input_length": len(user_input)
        }

    def normalize_typos(self, text: str) -> str:
        """Map misspelled model names to their canonical forms."""
        if not text:
            return ""
        text_lower = text.lower()
        
        venue_typos = [r"\bvenuw\b", r"\bvnue\b", r"\bvanyu\b", r"\bvenye\b", r"\bvenyu\b"]
        for typo in venue_typos:
            text_lower = re.sub(typo, "venue", text_lower)
            
        creta_typos = [r"\bcreeta\b", r"\bcereta\b", r"\bcreata\b"]
        for typo in creta_typos:
            text_lower = re.sub(typo, "creta", text_lower)
            
        verna_typos = [r"\bvirna\b", r"\bvarna\b"]
        for typo in verna_typos:
            text_lower = re.sub(typo, "verna", text_lower)
            
        i20_typos = [r"\bi\s*20\b", r"\bi\s*-?\s*twenty\b", r"\bitem\s*twenty\b"]
        for typo in i20_typos:
            text_lower = re.sub(typo, "i20", text_lower)
            
        i10_typos = [r"\bgrand\s*i\s*10\b", r"\bi\s*10\b", r"\bgrand\s*i10\b", r"\bi-10\b"]
        for typo in i10_typos:
            text_lower = re.sub(typo, "grand i10", text_lower)

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

        return text_lower

    def extract_data(self, text):
        """Extract entities like location and models from text."""
        text_norm = self.normalize_typos(text)
        text_lower = text_norm.lower()
        extracted = {"location": None, "model": None}
        
        # Simple location detection for demo (Expandable)
        cities = ["nashik", "mumbai", "pune", "delhi", "bangalore", "nagpur"]
        for city in cities:
            if city in text_lower:
                extracted["location"] = city.capitalize()
                break
                
        # Model detection (rfind right-to-left scan to find last mentioned model for switches)
        last_pos = -1
        detected_model = None
        for model in self.kb.get("models", {}).keys():
            pos = text_lower.rfind(model)
            if pos > last_pos:
                last_pos = pos
                detected_model = model
        extracted["model"] = detected_model
        
        return extracted

    def handle_query(self, text: str, info: Dict[str, Any], variables: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Unified Master FAQ handler with Priority Routing."""
        text = text.lower().strip()
        
        # --- [NEW] PREDICTIVE CONTEXT SWITCHING ---
        extracted = self.extract_data(text)
        detected_model = extracted.get("model")
        
        # If user mentioned a DIFFERENT model, override the context
        current_model = variables.get("car_model", "creta") if variables else "creta"
        switched = False
        if detected_model and detected_model != current_model:
            print(f"[INTENT ENGINE] Context switch detected: {current_model} -> {detected_model}")
            # Update info to the new model's info from KB
            new_info = self.kb.get("models", {}).get(detected_model)
            if new_info:
                info = new_info
                current_model = detected_model
                switched = True
                if variables:
                    variables["car"] = detected_model.capitalize()
                    variables["car_model"] = detected_model
        
        target_model = current_model.capitalize()
        car_cap = target_model
        
        # --- Acknowledgement Bridge for Switches ---
        switch_bridge = f"Certainly! Regarding the {car_cap}, " if switched else ""
        
        # --- PRIORITY 0: Explicit Rejection / Negative Intent ---
        rejection_words = [
            "not interested", "no thanks", "no i dont", "dont want", "never", "stop calling", "not buying", "nuying",
            "do not want", "don't want", "no interest", "not looking", "don't call", "do not call",
            "nayi car nahi leni", "interest nahi hai", "nahi chahiye", "call mat kijiye", "call mat kijie", "call mat karo",
            "नहीं लेनी", "नहीं चाहिए", "कॉल मत कीजिए", "कॉल मत करो", "इंटरेस्ट नहीं है"
        ]
        if any(word in text for word in rejection_words):
             return {
                "text": "I understand. I'll make a note that you're not looking to upgrade at this moment. Before I go, is there anything else I can help you with?",
                "intent": "rejection", "model": target_model
            }

        # --- PRIORITY 0.5: Intercept trust, identity, and insurance queries to delegate to InsuranceFlow ---
        insurance_keywords = [
            'number', 'genuine', 'calling from', 'who is this', 'who are you', 
            'kaha se mila', 'kahan se mila', 'real person', 'are you ai', 'bot', 'robot',
            'zero dep', 'zero depreciation', 'bumper to bumper', 'ncb', 'no claim bonus', 
            'cashless', 'policybazaar', 'acko', 'lombard', 'allianz', 'insurance', 
            'policy', 'premium', 'claim', 'stop calling', 'don\'t call', 'do not call', 
            'remove', 'dnd', 'baar baar', 'bar bar', 'said no',
            'नंबर कहाँ से', 'नंबर कहां से', 'कहाँ से मिला', 'कहां से मिला', 'किसने दिया', 'नंबर मिला',
            'रोबोट', 'एआई', 'बॉट', 'ज़ीरो डेप्रिसिएशन', 'जीरो डेप्रिसिएशन', 'जीरो डेप', 'बंपर',
            'प्रीमियम कम', 'कम करो', 'कम करो प्रीमियम', 'कम करो ना', 'प्रीमियम कम करो', 'कम कीजिये', 'कम कीजिए',
            'कम करो प्रीमियम', 'थोड़ा कम', 'डिस्काउंट', 'छूट', 'एक्सीडेंट', 'दुर्घटना', 'क्लेम', 'कैशलेस', 'गैरेज',
            'किस्त', 'किश्त', 'ईएमआई', 'यूपीआई', 'पेमेंट लिंक', 'पेमेंट', 'कौन सी कंपनी', 'किस कंपनी', 'कौन कंपनी'
        ]
        flow_type = variables.get("flow_type") if variables else None
        is_insurance_flow = flow_type and str(flow_type).startswith("insurance")
        if is_insurance_flow and any(word in text for word in insurance_keywords):
            from flows.insurance_flow import InsuranceFlow
            cust_data = dict(variables) if isinstance(variables, dict) else {}
            if "car_model" not in cust_data:
                cust_data["car_model"] = info.get("name") if isinstance(info, dict) else "Creta"
            if "car" not in cust_data:
                cust_data["car"] = cust_data["car_model"]
            if "current_premium" not in cust_data:
                cust_data["current_premium"] = "₹12,500"
            if "loyalty_premium" not in cust_data:
                cust_data["loyalty_premium"] = "₹11,800"
            
            stage = int(cust_data.get("stage", 1))
            comp_offered = cust_data.get("comparison_offered", False)
            
            high_fidelity_ans = InsuranceFlow.handle_query(text, cust_data, stage=stage, comparison_offered=comp_offered)
            if high_fidelity_ans:
                intent = "query"
                if "connect" in high_fidelity_ans or "hand-off" in high_fidelity_ans or "connecting you" in high_fidelity_ans.lower():
                    intent = "transfer"
                elif "remove" in high_fidelity_ans or "do not call" in high_fidelity_ans or "apologize for the inconvenience" in high_fidelity_ans.lower():
                    intent = "rejection"
                return {"text": high_fidelity_ans, "intent": intent, "model": target_model}

        # --- PRIORITY 1: Identity & Process ---
        if any(word in text for word in ["who is this", "who are you", "calling from", "get my number", "your name", "which showroom", "कौन बात", "कौन हो", "कहाँ से", "कहां से", "नंबर कहाँ", "नंबर कहां", "कहाँ से मिला", "कहां से मिला", "नंबर किसने"]):
            return {
                "text": f"{switch_bridge}I'm Supriya calling from Alcon, your authorized Hyundai partner. We're reaching out to share our new upgrade benefits for your {target_model}. Is this a good time to talk?",
                "intent": "identity", "model": target_model
            }
        
        if any(word in text for word in ["real person", "are you ai", "bot", "robot", "artificial", "रोबोट", "एआई", "मशीन", "कंप्यूटर", "असली इंसान", "बॉट"]):
            return {
                "text": f"{switch_bridge}I'm Alcon's AI assistant. I can help you with pricing and offers for the {target_model} immediately. If you'd prefer, I can connect you with my manager. What would you prefer?",
                "intent": "ai_check", "model": target_model
            }

        # --- PRIORITY 2: Human Transfer / Handoff ---
        transfer_keywords = ["connect", "manager", "specialist", "agent", "talk to", "sales", "executive", "representative", "मैनेजर", "एजेंट", "सलाहकार", "अधिकारी", "बात करवा", "बात करा", "कनेक्ट", "ट्रांसफर"]
        is_transfer_request = False
        for word in transfer_keywords:
            if word in text:
                if word == "sales" and ("after sales" in text or "after-sales" in text):
                    continue
                is_transfer_request = True
                break
        is_human_request = ("person" in text or "human" in text) and not ("are you" in text or "real" in text)
        
        if is_transfer_request or is_human_request:
             return {
                "text": "I understand. I'm connecting you to our Sales Manager right now. They will assist you with the final pricing and next steps. Thank you for speaking with Alcon!",
                "intent": "transfer", "model": target_model
            }

        # --- PRIORITY 3: Objections ---
        if any(word in text for word in ["too high", "expensive", "too much", "high price", "महंगी", "महंगा", "बहुत ज्यादा"]):
            return {
                "text": f"{switch_bridge}I understand that price is a major factor for the {target_model}. I can have our sales manager call you back with our best final offer. Would that work?",
                "intent": "price_objection", "model": target_model
            }

        # --- PRIORITY 2: Digital & Follow-up ---
        if any(word in text for word in ["whatsapp", "brochure", "quotation", "send", "details", "message", "व्हाट्सएप", "व्हाट्सऐप", "भेज", "डिटेल्स", "मैसेज"]):
            return {
                "text": f"{switch_bridge}I will certainly send the {target_model} brochure and detailed quotation to you on WhatsApp right after our call. Beyond that, would you like to hear about our exchange bonuses?",
                "intent": "digital", "model": target_model
            }

        # --- PRIORITY 3: Exchange & Old Car (Fix Overlap) ---
        if any(word in text for word in ["exchange", "old car", "value for my car", "my current car", "rc transfer", "buy non-hyundai", "documents", "एक्सचेंज", "पुरानी कार", "बदली"]):
            return {
                "text": f"{switch_bridge}Yes, we buy all car brands! We provide the best market value for your old car plus an additional exchange bonus when upgrading to the {target_model}. We also handle all RC transfer paperwork for you.",
                "intent": "exchange", "model": target_model
            }

        # --- SPECIFIC OBJECTIONS & TRUST & FEATURES & RECOMMENDATIONS ---
        if "maintenance" in text and ("costly" in text or "expensive" in text or "high" in text or "is hyundai maintenance" in text or "रखरखाव" in text or "मेंटेनेंस" in text):
            msg = "The Venue has the lowest maintenance cost in its segment, averaging just 35 paise per kilometer over 5 years."
            return {"text": f"{switch_bridge}{msg}", "intent": "maintenance_cost", "model": target_model}

        if "interior" in text and ("better" in text or "interior than hyundai" in text or "kia" in text):
            msg = "Both brands offer beautiful cabins. Hyundai is highly appreciated for its premium cabin materials, durability, and outstanding ergonomics."
            return {"text": f"{switch_bridge}{msg}", "intent": "interior_objection", "model": target_model}

        if any(word in text for word in ["driver", "rajesh"]):
            msg = "Yes, all our drivers, including Rajesh, are fully licensed, police-verified, and highly experienced professionals with clean safety records. You can be fully assured of your car's safety."
            return {"text": f"{switch_bridge}{msg}", "intent": "driver_safety_faq", "model": target_model}

        if any(w in text for w in ["safety", "safe", "safey", "airbag", "air bag", "air bags", "सुरक्षा", "सेफ", "एयरबैग", "गुब्बारा", "एयर बैग"]):
            # Check if it's a specific standard airbag request or general safety
            if any(w in text for w in ["airbag", "air bag", "air bags", "एयरबैग", "एयर बैग"]) and any(w in text for w in ["6 airbags", "6 air bags", "6 airbag", "6 air bag", "how many", "which cars", "which car", "aate hai", "aate hain", "6", "६", "कितने"]):
                msg = "Hyundai is proud to offer 6 airbags as standard across all variants of our entire car lineup, ensuring robust safety for every passenger."
                return {"text": f"{switch_bridge}{msg}", "intent": "airbags_feature", "model": target_model}
            msg = "Hyundai prioritizes safety with 6 airbags as standard, high-strength steel body, and advanced ADAS safety features."
            return {"text": f"{switch_bridge}{msg}", "intent": "safety_faq", "model": target_model}

        if "resale" in text:
            msg = "Hyundai cars enjoy excellent resale value and are highly demanded in the pre-owned market due to durable build and vast service network."
            return {"text": f"{switch_bridge}{msg}", "intent": "resale_faq", "model": target_model}

        if "power" in text or "powerful" in text:
            msg = "Hyundai models like the Creta offer highly refined petrol and diesel options with advanced turbo engines that deliver exciting yet smooth performance."
            return {"text": f"{switch_bridge}{msg}", "intent": "power_objection", "model": target_model}

        if "service" in text and ("good" in text or "after sales" in text or "after-sales" in text or "achi" in text or "bad" in text):
            msg = "Alcon Hyundai has a vast network of authorized workshops with expert technicians, ranking consistently at the top in customer satisfaction."
            return {"text": f"{switch_bridge}{msg}", "intent": "service_trust", "model": target_model}

        if "part" in text or "spare" in text:
            msg = "Genuine Hyundai spare parts are readily available at highly reasonable prices across all service centers."
            return {"text": f"{switch_bridge}{msg}", "intent": "parts_trust", "model": target_model}

        if "long drive" in text or "highway" in text:
            msg = "Hyundai cars offer extremely comfortable seats, silent cabin, and smooth suspension, making them absolute joy for long highway drives."
            return {"text": f"{switch_bridge}{msg}", "intent": "long_drive_trust", "model": target_model}

        if "adas" in text or "एडीएएस" in text or "एडस" in text:
            msg = "Yes, advanced Level 2 ADAS (Advanced Driver Assistance System) is available in models like Creta, Verna, and Tucson to ensure maximum safety."
            return {"text": f"{switch_bridge}{msg}", "intent": "adas_feature", "model": target_model}

        if "ventilated" in text or "हवादार" in text or "वेंटिलेटेड" in text:
            msg = "Yes, premium ventilated seats are available in the Hyundai Creta and Verna, keeping you cool and comfortable in all weather."
            return {"text": f"{switch_bridge}{msg}", "intent": "ventilated_seats", "model": target_model}

        if "under 15 lakh" in text or "15 lakh ke under" in text or "under 15" in text or "१५ लाख" in text or "15 लाख" in text or "15 lakh" in text:
            msg = "Under 15 Lakhs, our Venue is the perfect compact SUV option, starting from ₹7.94 Lakhs, and its automatic variant starts from ₹10.37 Lakhs."
            return {"text": f"{switch_bridge}{msg}", "intent": "budget_options", "model": target_model}

        if "city driving" in text or "city traffic" in text or "शहर" in text:
            msg = "The Venue and Grand i10 Nios offer excellent mileage and fuel efficiency of up to 20 kilometers per liter, making them perfect for daily commutes."
            return {"text": f"{switch_bridge}{msg}", "intent": "mileage_faq", "model": target_model}

        # --- SPECIFIC COMPETITOR MODEL COMPARISONS ---
        comp_model = None
        for comp in ["seltos", "sonet", "nexon", "punch", "baleno", "altroz", "compass", "city", "xuv", "3xo"]:
            if comp in text:
                # Avoid matching "city driving" as Honda City comparison
                if comp == "city" and ("driving" in text or "traffic" in text or "best car" in text):
                    continue
                comp_model = comp
                break
                
        if comp_model:
            comp_map = {
                "seltos": ("Creta", "Seltos", "refined driving comfort, trusted service network, and outstanding resale value", "sporty styling and premium tech features"),
                "sonet": ("Venue", "Sonet", "excellent ride quality, low maintenance cost (just 35 paise/km), and great reliability", "feature-packed cabin and aggressive look"),
                "nexon": ("Venue", "Nexon", "excellent ride quality, low maintenance cost, and great reliability", "solid build and bold styling"),
                "punch": ("Exter", "Punch", "superior refinement, standard 6 airbags, and advanced features like a smart dual-camera dashcam", "rugged styling"),
                "baleno": ("i20", "Baleno", "sporty dynamics, unmatched cabin quality, and premium features", "high fuel efficiency"),
                "altroz": ("i20", "Altroz", "premium cabin comfort, butter-smooth refinement, and advanced tech features", "solid build"),
                "compass": ("Tucson", "Compass", "premium luxury features, ultra-refined engine, and superior cabin space", "rugged off-road capability"),
                "city": ("Verna", "City", "futuristic design, powerful turbocharged options, and class-leading safety features", "traditional styling"),
                "xuv": ("Creta", "XUV700", "premium cabin quality, excellent refinement, and superior resale value", "rugged styling"),
                "3xo": ("Venue", "XUV 3XO", "low maintenance cost, refined engine options, and smooth driving experience", "bold design")
            }
            our_model, their_model, our_strength, their_strength = comp_map[comp_model]
            msg = f"Both the Hyundai {our_model} and {their_model.capitalize()} are excellent options. The {their_model.capitalize()} offers {their_strength}, whereas the Hyundai {our_model} stands out for its {our_strength}."
            return {"text": f"{switch_bridge}{msg}", "intent": "comparison", "model": target_model}

        # --- GENERAL BRAND COMPARISONS ---
        if "kia" in text:
            msg = "Kia and Hyundai are sister brands that share excellent platforms. While Kia emphasizes sporty designs and tech, Hyundai models are highly popular for their refined ride quality, vast service network, and trusted resale value."
            return {"text": f"{switch_bridge}{msg}", "intent": "comparison", "model": target_model}
            
        if "tata" in text:
            msg = "Tata makes very solid vehicles. Hyundai cars, on the other hand, are highly preferred for their exceptional engine refinement, smooth transmission options, hassle-free ownership, and superior after-sales support."
            return {"text": f"{switch_bridge}{msg}", "intent": "comparison", "model": target_model}
            
        if "mahindra" in text:
            msg = "Mahindra is known for rugged utility vehicles. Hyundai SUVs like Creta and Venue stand out for their urban maneuverability, advanced features, superior cabin comfort, and premium refinement."
            return {"text": f"{switch_bridge}{msg}", "intent": "comparison", "model": target_model}
            
        if "maruti" in text:
            msg = "Maruti offers highly fuel-efficient cars. Hyundai models provide a much more premium cabin feel, advanced safety features like standard 6 airbags, and superior highway stability."
            return {"text": f"{switch_bridge}{msg}", "intent": "comparison", "model": target_model}
            
        if "why should i buy hyundai" in text or "why should i choose hyundai" in text or "why hyundai" in text:
            msg = "Hyundai vehicles are widely trusted for their class-leading refinement, advanced safety, extensive service network, and high resale value compared to competitors."
            return {"text": f"{switch_bridge}{msg}", "intent": "comparison", "model": target_model}

        # --- MULTILINGUAL CUSTOM FAQ MATCHES ---
        if "speak in hindi" in text or "hindi" in text:
            msg = "Sure! I will speak in Hindi now. How can I help you today? Are you looking for a new car or service assistance?"
            return {"text": f"{switch_bridge}{msg}", "intent": "language_switch", "model": target_model}

        if "best selling" in text or "popular" in text:
            msg = "The Creta is Alcon Hyundai's highest-selling SUV, offering premium tech, high resale value, and unmatched comfort."
            return {"text": f"{switch_bridge}{msg}", "intent": "best_selling", "model": target_model}

        if "family" in text:
            msg = "The Creta is the perfect family SUV, offering spacious 5-seater seating, a large 433-liter boot space, and 6 standard airbags."
            return {"text": f"{switch_bridge}{msg}", "intent": "family_car", "model": target_model}

        if "lowest maintenance" in text or "maintenance cost" in text or "maintenance" in text:
            msg = "The Venue has the lowest maintenance cost in its segment, averaging just 35 paise per kilometer over 5 years."
            return {"text": f"{switch_bridge}{msg}", "intent": "maintenance_cost", "model": target_model}

        if "best mileage" in text or "mileage" in text or "average" in text:
            msg = "The Venue and Grand i10 Nios offer excellent mileage and fuel efficiency of up to 20 kilometers per liter, making them perfect for daily commutes."
            return {"text": f"{switch_bridge}{msg}", "intent": "mileage_faq", "model": target_model}

        if "sunroof" in text:
            msg = "We offer electric sunroofs in the Venue and Exter, and a premium panoramic sunroof in the Creta."
            return {"text": f"{switch_bridge}{msg}", "intent": "sunroof_faq", "model": target_model}

        if "budget" in text or "between 7 to 10" in text or "7 se 10" in text or "7 to 10" in text:
            msg = "In the ₹7 to ₹10 Lakhs budget, our Venue is the perfect compact SUV option, starting from ₹7.94 Lakhs."
            return {"text": f"{switch_bridge}{msg}", "intent": "budget_options", "model": target_model}

        if "automatic" in text and "manual" in text:
            msg = f"The {car_cap} is available in both advanced Automatic (IVT/DCT) and Manual transmission options. Which one would you prefer to drive?"
            return {"text": f"{switch_bridge}{msg}", "intent": "transmission_choice", "model": target_model}

        if "automatic" in text and ("price" in text or "cost" in text or "how much" in text):
            # Model-aware automatic variant pricing
            if "venue" in text or current_model == "venue":
                msg = "The automatic variant starts from ₹10.37 Lakhs for the Venue."
            elif "creta" in text or current_model == "creta":
                msg = "The automatic variant starts from ₹15.82 Lakhs for the Creta."
            else:
                msg = "The automatic variant starts from ₹15.82 Lakhs for the Creta and ₹10.37 Lakhs for the Venue."
            return {"text": f"{switch_bridge}{msg}", "intent": "automatic_price", "model": target_model}

        if "turbo" in text:
            msg = "Yes, the turbo variant is available for the Creta, Venue, and Verna models."
            return {"text": f"{switch_bridge}{msg}", "intent": "turbo_variant", "model": target_model}

        if "suv" in text or "s.u.v" in text:
            msg = "We have a fantastic range of SUV models available, including the Creta and Venue. The Creta starts from ₹11 Lakhs, and the Venue starts from ₹7.94 Lakhs."
            return {"text": f"{switch_bridge}{msg}", "intent": "suv_segment", "model": target_model}

        if "variant" in text and ("avail" in text or "ready" in text or "delivery" in text):
            msg = info.get("availability") or "Various variants are available with short waiting periods."
            return {"text": f"{switch_bridge}{msg}", "intent": "variant_availability", "model": target_model}

        if "service package" in text or "warranty" in text:
            msg = "We offer comprehensive service packages, including a 3-year unlimited km warranty, and prepaid maintenance plans."
            return {"text": f"{switch_bridge}{msg}", "intent": "service_package", "model": target_model}

        if "loan approval" in text or "approval time" in text or any(w in text for w in ["लोन अप्रूवल", "लोन अप्रूव", "लोन पास", "loan approve"]):
            msg = "We have spot loan approval within 2 hours through our partner banks with zero processing fees."
            return {"text": f"{switch_bridge}{msg}", "intent": "loan_approval", "model": target_model}


        if "down payment" in text or "downpayment" in text:
            msg = "The minimum down payment starts from ₹1.5 Lakhs for the Creta and ₹1 Lakh for the Venue."
            return {"text": f"{switch_bridge}{msg}", "intent": "down_payment", "model": target_model}

        if "waiting period" in text or ("waiting" in text and "period" in text):
            msg = "The waiting period is approximately 3 weeks for the Creta and ready stock for the Venue."
            return {"text": f"{switch_bridge}{msg}", "intent": "waiting_period", "model": target_model}

        if "diesel" in text:
            msg = "The Creta is available in both Petrol and Diesel with advanced Automatic and Manual options."
            return {"text": f"{switch_bridge}{msg}", "intent": "diesel_avail", "model": target_model}

        if "exchange" in text or "value in exchange" in text:
            msg = "We offer the best market value for your old car plus an additional exchange bonus of up to ₹30,000 depending on the model."
            return {"text": f"{switch_bridge}{msg}", "intent": "exchange_value", "model": target_model}

        if "cng" in text:
            msg = "CNG option is currently available in our Aura and Grand i10 models. The Creta and Venue come in Petrol and Diesel."
            return {"text": f"{switch_bridge}{msg}", "intent": "cng_model", "model": target_model}

        if "insurance" in text:
            msg = "Yes, our on-road price includes comprehensive first-year insurance and registration charges."
            return {"text": f"{switch_bridge}{msg}", "intent": "insurance_faq", "model": target_model}

        if "accessories" in text:
            msg = "We are currently offering free basic accessories worth up to ₹10,000 as part of our ongoing promotion."
            return {"text": f"{switch_bridge}{msg}", "intent": "accessories_faq", "model": target_model}

        if "white" in text or "colour" in text or "color" in text:
            color_list = info.get("colors") or "Abyss Black, Atlas White, Titan Grey, and Ranger Khaki"
            msg = f"The {car_cap} is available in stunning colors like {color_list}."
            return {"text": f"{switch_bridge}{msg}", "intent": "color_faq", "model": target_model}

        if "test drive" in text or "testdrive" in text:
            msg = "Yes, we can certainly arrange a doorstep test drive at your convenience. Which model would you like to experience?"
            return {"text": f"{switch_bridge}{msg}", "intent": "test_drive_faq", "model": target_model}

        if "emi" in text:
            price_raw = str(info.get("price") or "₹11 Lakhs")
            price_clean = price_raw.replace("Starting from ", "")
            emi_starts = info.get("emi_starts") or "₹18,500"
            msg = f"The {car_cap} starts at {price_clean} with EMI options starting from {emi_starts}."
            return {"text": f"{switch_bridge}{msg}", "intent": "emi_faq", "model": target_model}

        # --- PRIORITY 4: Technical & Variants ---
        if any(word in text for word in ["automatic", "manual", "transmission", "variant", "petrol", "diesel", "cng", "ev", "ऑटोमैटिक", "ऑटोमेटिक", "मैनुअल", "मैन्युअल", "ट्रांसमिशन", "वेरिएंट", "वेरियंट", "पेट्रोल", "डीजल", "डीज़ल", "सीएनजी"]):
            if "cng" in text or "सीएनजी" in text:
                msg = f"Currently, the {car_cap} comes in Petrol and Diesel. CNG is available in our Aura and Grand i10 models."
            else:
                msg = f"The {car_cap} is available in both Petrol and Diesel with advanced Automatic (IVT/DCT) and Manual options. Would you like to know the price for the Automatic variant?"
            return {"text": f"{switch_bridge}{msg}", "intent": "variants", "model": target_model}

        # --- PRIORITY 5: General KB (Price, Mileage, etc) ---
        answers = []
        categories_answered = set()
        detected_intent = None
        
        if any(word in text for word in ["safety", "safe", "airbag", "rating", "crash", "standard", "सुरक्षा", "सेफ", "एयरबैग", "गुब्बारा", "रेटिंग", "क्रैश"]):
            answers.append(f"The {car_cap} prioritizes your safety with 6 airbags as standard and a high-strength steel body.")
            categories_answered.add("safety")
            detected_intent = "safety"

        if any(word in text for word in ["insurance", "policy", "expiry", "expire", "बीमा", "पॉलिसी", "इंश्योरेंस"]):
            flow_type = variables.get("flow_type") if variables else None
            
            if flow_type in ["pre_sales", "reception"]:
                answers.append(f"We provide comprehensive insurance packages with zero-depreciation and cashless repair facilities at all Alcon Hyundai centers. We partner with top providers like ICICI Lombard and Bajaj Allianz to ensure you get the best coverage.")
            else:
                expiry = variables.get("insurance_expiry_date") if variables else None
                provider = variables.get("insurance_provider") if variables else None
                if expiry:
                    msg = f"Your insurance policy with {provider or 'our partner'} is set to expire on {expiry}."
                    if "renew" in text or "how to" in text:
                        msg += " I can have our insurance desk call you to assist with the renewal process."
                    answers.append(msg)
                else:
                    answers.append(f"I'll have our insurance team check your policy status and get back to you with the exact expiry date.")
            categories_answered.add("insurance")
            detected_intent = "insurance"

        is_loan_approval = any(w in text for w in ["loan approval", "approval time", "लोन अप्रूवल", "लोन अप्रूव", "लोन पास", "loan approve"])
        if not is_loan_approval and any(word in text for word in ["price", "cost", "how much", "rate", "on road", "emi", "finance", "loan", "interest", "down payment", "budget", "कीमत", "दाम", "रेट", "लाख", "किस्त", "किश्त", "ईएमआई", "एमी", "लोन", "डाउन पेमेंट", "डाउनपेमेंट"]):

            price_raw = str(info.get("price") or "₹11 Lakhs")
            price_clean = price_raw.replace("Starting from ", "")
            
            if "interest" in text:
                answers.append(f"We offer competitive interest rates starting from 8.5% through our partner banks.")
            elif "down payment" in text or "minimum" in text or "डाउन पेमेंट" in text or "डाउनपेमेंट" in text:
                answers.append(f"The minimum down payment for the {car_cap} starts at approximately ₹1.5 Lakhs.")
            elif any(word in text for word in ["emi", "finance", "loan", "ईएमआई", "एमी", "किस्त", "किश्त", "लोन"]):
                current_emi = variables.get("current_emi") if variables else None
                if current_emi and any(word in text for word in ["my emi", "my loan", "current"]):
                    answers.append(f"Our records show your current monthly EMI is {current_emi}.")
                else:
                    answers.append(f"The {car_cap} starts at {price_clean} with EMI options starting from {info.get('emi_starts', '₹18,500')}.")
            elif "on road" in text or "on-road" in text or "ऑन रोड" in text or "ऑनरोड" in text:
                answers.append(f"Our on-road price for the {car_cap} starts at {price_clean} and includes comprehensive insurance and registration.")
            else:
                if "price" in categories_answered: pass # Already handled insurance/emi
                else: answers.append(f"The {car_cap} starts at {price_clean} on-road.")
            categories_answered.add("price")
            detected_intent = "price"

        if any(word in text for word in ["feature", "features", "spec", "specs", "specification", "specifications", "sunroof", "adas", "screen", "ventilated", "bose", "sound", "tech", "technology", "फीचर्स", "फीचर", "टीचर्स", "खूबी", "खूबियां", "सनरूफ", "एडीएएस", "स्क्रीन", "बोस", "साウンド", "टेक", "टेक्नोलॉजी", "सुविधा"]):
            feat_list = info.get("features") or "premium technology and comfort features"
            answers.append(f"The {car_cap} comes packed with features like {feat_list}.")
            categories_answered.add("features")
            detected_intent = "features"

        if any(word in text for word in ["color", "colors", "colour", "colours", "shade", "shades", "रंग", "रंगों", "कलर", "कलर्स"]):
            color_list = info.get("colors") or "several premium colors"
            answers.append(f"The {car_cap} is available in stunning color options like {color_list}.")
            categories_answered.add("colors")
            detected_intent = "colors"

        if any(word in text for word in ["mileage", "average", "fuel", "economy", "माइलेज", "एवरेज"]):
            answers.append(f"The {car_cap} offers an impressive mileage of {info.get('mileage', '18 kmpl')}.")
            categories_answered.add("mileage")
            detected_intent = "mileage"

        if any(word in text for word in ["waiting", "delivery", "when", "time", "showroom", "visit", "weekend", "open", "service due", "next service", "वेटिंग", "डिलीवरी", "समय", "शोरूम"]):
            # Priority Check: Skip if this was specifically an insurance/emi 'when' query
            if "insurance" in categories_answered or "price" in categories_answered:
                pass 
            elif any(w in text for w in ["service due", "next service", "when is my service"]):
                due_date = variables.get("service_due_date") if variables else None
                if due_date:
                    answers.append(f"Your {car_cap} service is scheduled for {due_date}.")
                else:
                    answers.append(f"I'll have to check our records for your specific service due date.")
            elif any(w in text for w in ["weekend", "time", "showroom"]):
                answers.append(f"Our showroom is open every day from 9 AM to 8 PM, including weekends.")
            else:
                waiting = info.get("availability") or "2 to 4 weeks"
                answers.append(f"The waiting period is approximately {waiting}.")
            categories_answered.add("waiting")
            detected_intent = "waiting"

        if any(word in text for word in ["offer", "discount", "benefit", "bonus", "loyalty", "corporate", "accessories", "ऑफर", "डिस्काउंट", "छूट", "फायदा", "स्कीम"]):
            if "loyalty" in text or "लोयल्टी" in text:
                answers.append("Since you are a Hyundai owner, you are eligible for exclusive loyalty bonuses up to ₹20,000.")
            elif "corporate" in text:
                answers.append("Yes, we have special corporate discounts for employees of leading companies.")
            else:
                answers.append(f"We're currently offering festive benefits and free accessories worth up to ₹50,000 on the {car_cap}.")
            categories_answered.add("offers")
            detected_intent = "offers"

        if any(word in text for word in ["compare", "better", "choose", "tata", "maruti", "kia", "तुलना", "बेहतर"]):
            answers.append(f"Hyundai models offer superior refinement and a much wider service network compared to competitors.")
            categories_answered.add("comparison")
            detected_intent = "comparison"

        if any(word in text for word in [
            "which model", "what model", "which car", "what car", 
            "available model", "available option", "list of model", 
            "range of model", "model option", "which vehicle", "what vehicle", 
            "vehicles do you have", "cars do you have", "models do you have",
            "list of car", "list the car", "list the model", "show me the model",
            "show me the car", "models available", "cars available", "options do you have",
            "गाड़ी", "गाड़ियां", "कार", "मॉडल", "गाड़ी"
        ]):
            models_list = [m.capitalize() for m in self.kb.get("models", {}).keys()]
            if len(models_list) > 1:
                models_str = ", ".join(models_list[:-1]) + f", and {models_list[-1]}"
            else:
                models_str = models_list[0] if models_list else "Creta, Venue, and Verna"
            answers.append(f"We have a fantastic range of Hyundai vehicles available, including the {models_str}.")
            categories_answered.add("available_models")
            detected_intent = "available_models"

        # --- PRIORITY 6: Model Mention Fallback ---
        if (switched or detected_model) and not answers:
            # User mentioned a model but asked no specific question
            # Provide a high-level summary from KB
            feat_list = info.get("features") or "premium technology and comfort features"
            price_raw = str(info.get("price") or "₹11 Lakhs")
            price_clean = price_raw.replace("Starting from ", "")
            answers.append(f"The {car_cap} is a fantastic choice, known for its {feat_list}. It starts from {price_clean}.")
            detected_intent = "model_info"

        import random
        is_reception = variables.get("flow_type") == "reception" if variables else False
        
        intros = ["That's a valid point.", "I can certainly clarify that.", "Sure thing.", "I'd be happy to help."]
        base_intro = random.choice(intros)
        
        ack_intents = variables.get("acknowledged_intents", []) if variables else []
        if is_reception:
            ctas = []
            if "features" not in ack_intents:
                ctas.append("Would you like to know more about the features?")
            if "price" not in ack_intents and "pricing" not in ack_intents:
                ctas.append("Would you like me to share the pricing details?")
            ctas.append("Should I connect you with our advisor?")
        else:
            ctas = []
            if "emi" not in ack_intents and "emi_faq" not in ack_intents:
                ctas.append("Would you like to know more about EMI?")
            ctas.append("Should I connect you with our manager?")
            ctas.append("I can arrange a callback for the best deal.")
        cta = ""


        if answers:
            intro = switch_bridge if switched else f"{base_intro} "
            return {"text": f"{intro}{' '.join(answers)}".strip(), "intent": detected_intent, "model": target_model}

        
        return None
        
        return None
        
    def is_metadata_fresh(self, customer_data, threshold_days=30):
        """Check if CRM metadata is fresh enough for proactive pivoting."""
        sync_at = customer_data.get("metadata_last_synced_at")
        if not sync_at:
            return False
        
        try:
            from datetime import datetime
            last_sync = datetime.fromisoformat(sync_at)
            delta = (datetime.now() - last_sync).days
            return delta <= threshold_days
        except:
            return False
