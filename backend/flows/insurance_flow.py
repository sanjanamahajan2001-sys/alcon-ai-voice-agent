from typing import Dict, Any, Optional
import re

class InsuranceFlow:
    @staticmethod
    def get_greeting(salutation: str, name: str, car: str, provider: str, expiry: str, stage: int = 1) -> str:
        """Memory-aware greeting based on stage."""
        if stage == 1:
            return f"Hello {name} {salutation}, I'm Supriya from Alcon. I'm calling to remind you that the insurance for your {car} is due for renewal on {expiry}. Your current policy is with {provider}. Are you planning to renew it with us this year?"
        elif stage == 2:
            return f"Hello {name} {salutation}, this is Supriya from Alcon. I'm following up as you mentioned you were busy when we last spoke. Since we're now about two weeks away from your {car}'s insurance expiry, have you had a chance to review that loyalty offer?"
        elif stage == 3:
            return f"Hello {name} {salutation}, Supriya here from Alcon again. I'm calling with an urgent reminder as your {car} insurance expires in just 7 days. I haven't heard back from you on the loyalty quote we shared. Shall we secure your No Claim Bonus today?"
        elif stage == 4:
            return f"Good day {name} {salutation}. This is an urgent final call regarding your {car}. Your insurance expires tomorrow. I've secured a final spot for instant renewal to save your 50% No Claim Bonus. Shall I send the payment link to your WhatsApp?"
        else:
            return f"Hello {name} {salutation}, I noticed that the insurance for your {car} has now expired. Driving without it is a major risk. I can still help you with a break-in policy today. Shall I connect you to our insurance desk to fix this immediately?"

    @staticmethod
    def handle_query(user_input_lower: str, customer_data: Dict[str, Any], stage: int = 1, comparison_offered: bool = False) -> Optional[str]:
        """Handle specific customer questions about provider, policy, or premium."""
        
        # 1. Already Renewed (Highest Priority)
        if any(word in user_input_lower for word in ['already renewed', 'done it', 'renewed already', 'got it from elsewhere', 'renewed elsewhere', 'done already', 'पहले ही', 'करा लिया', 'करा ली', 'पहले से ही']):
            return (f"Oh, I see! That's great to hear that your {customer_data['car_model']} is already covered. "
                    f"I'll update our records. We look forward to serving you in the future. Have a wonderful day!")

        # 2. Help / Human / Update Request (Priority for Hybrid Transfers)
        words = re.findall(r'\b\w+\b', user_input_lower)
        if any(w in words for w in ['help', 'person', 'human', 'agent', 'manager', 'transfer', 'update', 'change', 'advisor', 'मैनेजर', 'एजेंट', 'सलाहकार', 'अधिकारी', 'बात करवा', 'बात करा', 'कनेक्ट', 'ट्रांसफर']) or 'speak to someone' in user_input_lower or 'बात करनी' in user_input_lower or 'बात करवाओ' in user_input_lower:
            return ("Certainly. To ensure you get the best assistance with these specific policy details, I'll connect you to our insurance desk immediately. Please stay on the line.")

        # 3. Competitor / Online Comparison Questions (e.g., PolicyBazaar, Acko, Digit, Dealership vs Online USP)
        if any(word in user_input_lower for word in ['policybazaar', 'policy bazaar', 'acko', 'digit', 'online is cheaper', 'online sasta', 'online cheaper', 'online sasta mil', 'cheaper de raha', 'why should i renew through dealership', 'dealership se hi kyu renew karu', 'dealership se kyu', 'why dealership', 'why should i renew', 'kyu renew', 'why renew', 'पॉलिसीबाजार', 'पॉलिसी बाजार', 'एको', 'डिजिट', 'ऑनलाइन', 'सस्ता', 'ऑनलाइन सस्ता', 'बाहर से']) or ('dealership' in user_input_lower and ('kyu' in user_input_lower or 'क्यों' in user_input_lower or 'renew' in user_input_lower)):
            return ("I understand online quotes from portals like PolicyBazaar can look cheaper, but some online quotes might have different coverage or key add-ons like Zero-Dep excluded. By renewing directly with the dealership, you secure 100% cashless claims and genuine OEM parts at our workshops. Would you like to proceed, or shall I connect you to our desk to explore if we can match that online rate?")

        # 4. Identity / Trust Verification Questions
        if any(word in user_input_lower for word in ['how did you get my number', 'get my number', 'kaha se mila', 'kahan se mila', 'genuine call', 'calling from hyundai', 'directly from hyundai', 'genuine', 'whatsapp pe details', 'details on whatsapp', 'verify this', 'verify karu', 'dealership', 'insurance company', 'नंबर कहाँ से', 'नंबर कहां से', 'कहाँ से मिला', 'कहां से मिला', 'किसने दिया', 'नंबर मिला']):
            return ("Yes, I'm calling directly from Alcon Hyundai, an authorized dealership. We got your details from our official dealership records as your car is registered with us. To verify this, I can instantly share our dealership contact details and policy proposal directly to your registered WhatsApp number for your convenience.")

        # 5. Policy Understanding Questions
        if any(word in user_input_lower for word in ['zero depreciation', 'zero dep', 'bumper to bumper', 'what is covered', 'cover hoga', 'engine protection', 'add-ons', 'what is ncb', 'ncb kya', 'ncb', 'matlab', 'ज़ीरो डेप्रिसिएशन', 'जीरो डेप्रिसिएशन', 'जीरो डेप', 'बंपर', 'इंजन प्रोटेक्शन', 'कवर']):
            return ("Our comprehensive bumper-to-bumper policy gives 100% coverage for all parts under Zero Depreciation with zero deduction for wear and tear. This policy also includes key add-ons like Engine Protection cover against water damage or hydrostatic lock, and your No Claim Bonus (NCB) discount which can save you up to 50% on premium.")

        # 6. Claim & Accident Related Questions
        if any(word in user_input_lower for word in ['previous claim', 'accident last year', 'accident', 'still get ncb', 'claims are allowed', 'claims allowed', 'cashless claims', 'cashless', 'garages are supported', 'garages', 'एक्सीडेंट', 'दुर्घटना', 'क्लेम', 'कैशलेस', 'गैरेज']):
            return ("While making a claim resets your No Claim Bonus (NCB) discount, you are still entitled to up to 2 claims per year. We offer fully cashless claim processing and repairs with genuine parts at all authorized Alcon workshops for a hassle-free experience.")

        # 7. Discount Negotiation Questions
        if any(word in user_input_lower for word in ['reduce the premium', 'reduce premium', 'thoda kam', 'best price', 'loyalty discount', 'match online', 'waive inspection', 'any discount', 'rate match', 'waive', 'प्रीमियम कम', 'कम करो', 'कम करो प्रीमियम', 'कम करो ना', 'प्रीमियम कम करो', 'कम कीजिये', 'कम कीजिए', 'कम करो प्रीमियम', 'थोड़ा कम', 'डिस्काउंट', 'छूट']):
            return ("Since you are a valued Alcon Hyundai customer, I have already applied our maximum 15% dealership loyalty discount and waived all physical vehicle inspection charges. To see if we can match a competitor's price or secure a special manager discount, I can connect you to our Insurance Manager right now. Would you like to connect?")

        # 8. Expiry & Risk Questions
        if any(word in user_input_lower for word in ['insurance expires', 'expire ho', 'renew after expiry', 'lose ncb', 'ncb chala', 'without insurance', 'driving without', 'expire ho gaya', 'expiry', 'expired', 'expire', 'वेटिंग', 'प्रतीक्षा']) or ('inspection' in user_input_lower and not any(w in user_input_lower for w in ['waive', 'charges', 'remove', 'discount'])):
            return ("Driving with an expired policy is illegal and subject to severe penalties. If your policy has expired for more than 90 days, you will also permanently lose your 50% No Claim Bonus discount and require a physical vehicle inspection before renewal. We can easily process an instant renewal today to avoid inspection or bonus loss. Shall we secure it?")

        # 9. Payment & Transaction Questions
        if any(word in user_input_lower for word in ['pay in emi', 'emi pe', 'upi accepted', 'upi chalega', 'payment link', 'invoice immediately', 'pay later', 'invoice milega', 'किस्त', 'किश्त', 'ईएमआई', 'यूपीआई', 'पेमेंट लिंक', 'पेमेंट']):
            return ("Yes! We support multiple secure digital payment methods, including UPI, credit/debit card, net banking, and easy EMI options. Once payment is done, the digital receipt and policy copy are sent instantly to your email and WhatsApp. I can share the secure payment link on your registered mobile number right away. Shall I send it?")

        # 10. Frustrated / Angry Customer Scenarios
        if any(word in user_input_lower for word in ['keep calling', 'already said no', 'said no', 'mana kiya', 'mana kiya tha', 'bar-bar call', 'baar baar call', 'why are premiums increasing', 'premiums increasing', 'expensive kyu', 'too expensive', 'bar bar call', 'कॉल मत करो', 'बंद करो', 'परेशान', 'बार-बार', 'डीएनडी', 'कॉल मत करना', 'कॉल नहीं चाहिए']):
            return ("I apologize for the inconvenience of our calls. Premiums sometimes change due to revised government tax rates. To assist you, I can register your number in our Do Not Disturb database right away to stop future calls, or connect you to a manager to explore a better rate. Which would you prefer?")

        # 11. What happens if I don't renew? (Consequences/Risk - legacy)
        if any(word in user_input_lower for word in ['what happens', 'dont renew', 'don\'t renew', 'not renew', 'if i don\'t', 'penalty', 'risk', 'why urgent', 'consequence']):
            return ("If the insurance expires, you risk losing your No Claim Bonus discount, which can be up to 50%. More importantly, driving without insurance is a legal offense and could lead to heavy fines. I can help you avoid this by processing your renewal instantly. Shall we proceed?")
        
        if ("dont" in user_input_lower or "don't" in user_input_lower or "not" in user_input_lower) and "renew" in user_input_lower:
            if any(word in user_input_lower for word in ['what', 'happen', 'if', 'why', 'consequence']):
                 return ("If the insurance expires, you risk losing your No Claim Bonus discount, which can be up to 50%. More importantly, driving without insurance is a legal offense and could lead to heavy fines. I can help you avoid this by processing your renewal instantly. Shall we proceed?")

        # 12. Question about Provider
        if any(word in user_input_lower for word in ['who is the provider', 'which company', 'current insurer', 'whose policy']):
            provider = customer_data.get('insurance_provider', 'our partner insurer')
            return f"Your current policy is with {provider}. We can renew it with them instantly, or I can show you a comparison with 5 other major providers to see if we can get you a better rate. Which would you prefer?"

        # 13. Too Expensive / Cheaper Options (Comparison Engine & Escalation) - HIGHER PRIORITY
        if any(word in user_input_lower for word in ['expensive', 'high', 'too much', 'costly', 'cheaper', 'better price', 'lower', 'online']):
            if comparison_offered:
                 return ("I hear you. Since those options still don't quite meet your budget, let me check if we can do better. I'll have our Insurance Manager call you back with a special approval rate. Would that work for you?")
            
            return ("I understand that price is important. Let me check our partner rates for you. Apart from HDFC Ergo, we have tie-ups with 5 other major insurers. ICICI Lombard is at ₹11,800 and Bajaj Allianz is at ₹11,500. Both provide identical coverage. Would you like to proceed with one of these, or shall I connect you to our desk to explore more?")

        # 14. Question about Premium/Price/Discount (Context Aware)
        if any(word in user_input_lower for word in ['how much', 'premium', 'cost', 'price', 'quote', 'details', 'tell me more', 'cost more', 'cost extra', 'will it be more', 'discount', 'offer', 'any deal']):
            current = customer_data.get('current_premium', 'TBD')
            loyalty = customer_data.get('loyalty_premium', 'TBD')
            
            if stage == 5: # Post-Expiry
                return (f"Since the policy has expired, there might be a small inspection fee. However, I can still offer you a special rate of {loyalty} if we process it today. This includes Zero Depreciation and Roadside Assistance. Shall I connect you to our coordinator to finalize?")
            
            return (f"Certainly. Your current premium was {current}, but for this year, we have a special loyalty quote of {loyalty}. This includes Zero Depreciation, Engine Protection, and Roadside Assistance. Does that sound like a good deal?")

        # 15. Why choose Alcon? (USP)
        if any(word in user_input_lower for word in ['why should i', 'why choose you', 'advantage', 'benefit of alcon', 'special about you']):
            return ("Choosing Alcon means you get a hassle-free, cashless claim experience across our entire network. We provide 100% OEM support with genuine parts and handle all documentation paperlessly for you. Does that sound like the kind of service you're looking for?")

        # 16. Question about Coverage/Benefits
        if any(word in user_input_lower for word in ['coverage', 'benefit', 'include', 'what do i get', 'protection', 'depreciation', 'zero dep', 'cashless']):
            return ("Our renewal package is very comprehensive. It includes Zero Depreciation, 24-hour roadside assistance and cashless repairs at all Alcon workshops. Shall I send you the detailed brochure on WhatsApp?")

        return None


        return None

    @staticmethod
    def get_confirmation_question() -> str:
        """Ask for explicit permission before sending the link."""
        return "Great! Shall I go ahead and share the digital copy of the quotation and the secure payment link on your registered mobile number now?"

    @staticmethod
    def get_confirmation_summary(customer_data: Dict[str, Any]) -> str:
        """Return a professional summary of the renewal for final confirmation."""
        provider = customer_data.get('insurance_provider', 'Partner Insurer')
        premium = customer_data.get('loyalty_premium', 'TBD')
        return (f"Excellent choice! I'm processing your renewal with {provider} at {premium}. "
                f"This includes Zero-Depreciation and 24/7 Roadside Assistance. "
                f"Your renewal is now in progress. You'll receive the payment link shortly.")

    @staticmethod
    def handle_consent(user_input_lower: str) -> str:
        """Categorize intent into INTERESTED, BUSY, REJECTED, or ALREADY_RENEWED."""
        if not user_input_lower or len(user_input_lower.strip()) == 0:
            return "NO_RESPONSE"
            
        # Already Renewed
        if any(word in user_input_lower for word in ['already renewed', 'done it', 'renewed already']):
            return "ALREADY_RENEWED"
            
        # Busy / Call Later (Check BUSY before REJECTED to catch "no later", "not now")
        if any(word in user_input_lower for word in ['busy', 'meeting', 'later', 'call back', 'driving', 'some time', 'to think', 'thinking', 'decide', 'time to decide', 'no later', 'not now']):
            return "BUSY"
            
        # Rejected / Not Interested (Regex for phrase matching with word boundaries)
        rejection_phrases = [
            r'\bnot interested\b', r'\bstop calling\b', r'\bdont call\b', r'\bdon\'t call\b', 
            r'\bno thanks\b', r'\bwrong number\b', r'\bno\b', r'\bnope\b', r'\bnot want\b', 
            r'\bwhy are you calling\b', r'\bagain and again\b', r'\bdon\'t want\b', r'\bremove me\b'
        ]
        if any(re.search(phrase, user_input_lower) for phrase in rejection_phrases):
            return "REJECTED"
            
        # Interested (Granular mapping)
        if any(word in user_input_lower for word in ['send', 'share', 'whatsapp', 'link']):
            return "INTERESTED_QUOTE_SHARED"
            
        if any(word in user_input_lower for word in ['talk', 'connect', 'manager', 'special', 'approval', 'discount']):
            return "INTERESTED_NEGOTIATING"

        positive = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'interested', 'proceed', 'good', 'fine', 'do it', 'go ahead', 'confirm']
        if any(re.search(rf'\b{word}\b', user_input_lower) for word in positive) or "lets do it" in user_input_lower or "please do" in user_input_lower:
            return "INTERESTED"
        
        if re.search(r'\brenew\b', user_input_lower) and not re.search(r'\b(don\'t|dont|not)\b', user_input_lower):
            return "INTERESTED"
            
        return "UNKNOWN"

    @staticmethod
    def is_comparison_requested(text: str) -> bool:
        """Detect if user wants to compare rates or mentioned a competitor/price objection."""
        text_lower = text.lower()
        competitors = ['policybazaar', 'policy bazaar', 'acko', 'digit', 'online', 'externally', 'outside', 'competitor', 'other company']
        keywords = ['compare', 'cheaper', 'expensive', 'too high', 'lower rate', 'discount', 'reduction', 'pricey', 'better price', 'different company']
        
        return any(k in text_lower for k in keywords) or any(c in text_lower for c in competitors)

    @staticmethod
    def get_contextual_resume(salutation: str, agent_summary: Optional[str] = None, pending_data: Optional[Dict] = None) -> str:
        """Generate a resume greeting that acknowledges the human conversation and specific data updates."""
        prefix = f"Thank you for speaking with our manager, {salutation}."
        
        # Build a string of updates to acknowledge
        updates_ack = []
        if pending_data:
            if "premium" in pending_data:
                updates_ack.append(f"the updated premium of ₹{pending_data['premium']}")
            if "nominee" in pending_data:
                updates_ack.append("the update to your nominee details")
            if "email" in pending_data or "mobile" in pending_data:
                updates_ack.append("the changes to your contact information")

        updates_text = " and ".join(updates_ack) if updates_ack else "your renewal"
        
        if agent_summary:
            summary_clean = agent_summary.replace("Summary:", "").strip()
            text = f"{prefix} I understand from our discussion that {summary_clean}. I'm back now to finalize {updates_text}."
        else:
            text = f"{prefix} I'm back now to finalize {updates_text}."
            
        return text + " Shall I go ahead and share the digital copy of the quotation via WhatsApp?"

    @staticmethod
    def handle_feedback(user_input_lower: str) -> Optional[int]:
        """Categorize feedback into numeric score (1-5 scale)."""
        positive = ['yes', 'helpful', 'good', 'great', 'awesome', 'nice', 'yeah', 'helpful', 'okay', 'ok', 'sounds good', 'fine', 'perfect']
        negative = ['no', 'bad', 'useless', 'not helpful', 'annoying', 'too much']
        
        if any(word in user_input_lower for word in positive):
            return 5
        if any(word in user_input_lower for word in negative):
            return 1
        return 3 # Neutral
