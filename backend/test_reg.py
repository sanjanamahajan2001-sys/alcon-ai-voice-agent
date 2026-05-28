import re

# Test Rule 140 with the updated regex pattern
pattern = r"Wonderful (Sir|Ma'am|सर|मैडम)\. Your service is confirmed\. At Alcon, we provide a 50-point safety check and use only genuine Hyundai parts to ensure your vehicle's peak performance\. Your Advisor, Amit Shah, will greet you upon arrival and walk you through the repair order details\.(?: You'll receive an SMS shortly\.)?(?: Have a great day!)?"

lambda_repl = lambda m: f"अद्भुत {m.group(1) in ['Sir', 'सर'] and 'सर' or 'मैडम'}। आपकी सर्विस की पुष्टि हो गई है। अल्कॉन में, हम आपकी गाड़ी के उत्कृष्ट प्रदर्शन को सुनिश्चित करने के लिए 50-पॉइंट सुरक्षा जांच प्रदान करते हैं और केवल असली हुंडई पार्ट्स का उपयोग करते हैं। आपके सलाहकार, अमित शाह, आगमन पर आपका स्वागत करेंगे और आपको मरम्मत ऑर्डर के विवरण समझाएंगे। आपको जल्द ही एक एसएमएस प्राप्त होगा। आपका दिन बहुत अच्छा रहे!"

text = "Wonderful मैडम. Your service is confirmed. At Alcon, we provide a 50-point safety check and use only genuine Hyundai parts to ensure your vehicle's peak performance. Your Advisor, Amit Shah, will greet you upon arrival and walk you through the repair order details."

match = re.match(pattern, text, re.IGNORECASE)
if match:
    print("Match successful!")
    print("Result:", lambda_repl(match)[:100])
else:
    print("Match failed!")
