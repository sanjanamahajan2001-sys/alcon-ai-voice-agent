import sys

filepath = "/home/sanjana/Alcon/poc/backend/flows/translation_utils.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# Locate the core_faq_map definition start and end in translation_utils.py
# and replace it with our verified concise Hinglish mapping
start_marker = '        core_faq_map = {'
end_marker = '        }'

start_idx = content.find(start_marker)
if start_idx == -1:
    print("Error: Could not find core_faq_map start marker")
    sys.exit(1)

# Find the corresponding end bracket for core_faq_map
# Since core_faq_map is lines 1146 to 1230, let's find the closing bracket
end_idx = content.find(end_marker, start_idx + len(start_marker))
if end_idx == -1:
    print("Error: Could not find core_faq_map end marker")
    sys.exit(1)

# Reconstruct the core_faq_map block with the new verified short Hinglish maps
new_core_faq_map = """        core_faq_map = {
            "We have a fantastic range of SUV models available, including the Creta and Venue. The Creta starts from ₹11 Lakhs, and the Venue starts from ₹7.94 Lakhs.":
                "हमारे पास Creta और Venue सहित SUV मॉडल्स की एक शानदार रेंज उपलब्ध है। Creta ₹11 लाख से शुरू होती है, और Venue ₹7.94 लाख से शुरू होती है।",
            
            "The Creta is available in both Petrol and Diesel with advanced Automatic and Manual options.":
                "Creta पेट्रोल और डीजल दोनों में उन्नत ऑटोमैटिक और मैनुअल विकल्पों के साथ उपलब्ध है।",
            
            "The automatic variant starts from ₹15.82 Lakhs for the Creta and ₹10.37 Lakhs for the Venue.":
                "ऑटोमैटिक वेरिएंट की शुरुआत Creta के लिए ₹15.82 लाख और Venue के लिए ₹10.37 लाख से होती है।",
            
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
                "निश्चित रूप से। इन विशिष्ट पॉलिसी डिटेल्स के लिए मैं आपकी बात तुरंत हमारे इंश्योरेंस डेस्क से करवा देती हूँ। कृपया लाइन पर बने रहें।"
        }"""

# Perform replacement
content = content[:start_idx] + new_core_faq_map + content[end_idx + 1:]

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Successfully replaced core_faq_map in translation_utils.py with verified Hinglish versions.")
