import sys

filepath = "/home/sanjana/Alcon/poc/backend/flows/translation_utils.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

replacements = [
    (
        '"Yes, I\'m calling directly from Alcon Hyundai, an authorized dealership. We got your details from our official dealership records as your car is registered with us. To verify this, I can instantly share our contact details and policy proposal directly to your registered WhatsApp number for your convenience.":\n                "हाँ, मैं सीधे अल्कॉन हुंडई से कॉल कर रही हूँ, जो कि एक अधिकृत डीलरशिप है। आपकी कार हमारे पास रजिस्टर्ड होने के कारण हमारे सिस्टम में आपके डिटेल्स हैं। वेरिफिकेशन के लिए, मैं तुरंत आपके व्हाट्सएप नंबर पर हमारी डीलरशिप की जानकारी भेज सकती हूँ ताकि आपको सुविधा रहे।",',
        '"Yes, I\'m calling directly from Alcon Hyundai, an authorized dealership. We got your details from our official dealership records as your car is registered with us. To verify this, I can instantly share our dealership contact details and policy proposal directly to your registered WhatsApp number for your convenience.":\n                "हाँ, मैं सीधे अल्कॉन हुंडई से कॉल कर रही हूँ, जो कि एक अधिकृत डीलरशिप है। हमें आपके डिटेल्स हमारे डीलरशिप रिकॉर्ड से मिले हैं क्योंकि आपकी कार हमारे पास रजिस्टर्ड है। वेरिफिकेशन के लिए, मैं तुरंत आपके व्हाट्सएप पर डीलरशिप की जानकारी भेज सकती हूँ ताकि आपको सुविधा रहे।",'
    ),
    (
        '"Our comprehensive bumper-to-bumper policy covers 100% of all parts under Zero Depreciation with zero deduction for wear and tear. This policy also includes key add-ons like Engine Protection cover against water damage, and your No Claim Bonus (NCB) discount which can save you up to 50% on premium.":\n                "हमारी बम्पर-टू-बम्पर पॉलिसी में जीरो डेप्रिसिएशन शामिल है, जिससे पार्ट्स पर कोई डिडक्शन नहीं होता और 100% कवरेज मिलता है। इसमें वाटर डैमेज से बचाव के लिए  प्रोटेक्शन और आपका नो क्लेम बोनस (NCB) भी शामिल है, जिससे आपको 50% तक का डिस्काउंट मिलता है।",',
        '"Our comprehensive bumper-to-bumper policy gives 100% coverage for all parts under Zero Depreciation with zero deduction for wear and tear. This policy also includes key add-ons like Engine Protection cover against water damage or hydrostatic lock, and your No Claim Bonus (NCB) discount which can save you up to 50% on premium.":\n                "हमारी बम्पर-टू-बम्पर पॉलिसी में जीरो डेप्रिसिएशन शामिल है, जिससे 100% कवरेज मिलता है। इसमें पानी भरने या हाइड्रोस्टेटिक लॉक से बचाव के लिए इंजन प्रोटेक्शन और आपका नो क्लेम बोनस (NCB) भी शामिल है, जिससे 50% तक की छूट मिलती है।",'
    ),
    (
        '"While making a claim resets your No Claim Bonus (NCB) discount, you are still entitled to up to 2 claims per year. We offer fully cashless claim processing and repairs with genuine parts at all authorized Alcon workshops for a hassle-free experience.":\n                "क्लेम करने से आपका नो क्लेम बोनस रीसेट हो जाता है, लेकिन आप साल में दो बार क्लेम ले सकते हैं। बिना किसी परेशानी के असली पार्ट्स के साथ रिपेयर के लिए, हम सभी अधिकृत अल्कॉन वर्कशॉप पर कैशलेस प्रोसेसिंग ऑफर करते हैं।",',
        '"While making a claim resets your No Claim Bonus (NCB) discount, you are still entitled to up to 2 claims per year. We offer fully cashless claim processing and repairs with genuine parts at all authorized Alcon workshops for a hassle-free experience.":\n                "क्लेम करने से आपका नो क्लेम बोनस यानी NCB रीसेट हो जाता है, पर आप साल में दो बार क्लेम ले सकते हैं। हम सभी अधिकृत अल्कॉन वर्कशॉप्स पर कैशलेस क्लेम की सुविधा देते हैं ताकि आपको असली पार्ट्स के साथ आसान सर्विस मिले।",'
    ),
    (
        '"I understand online quotes can look cheaper, but some online quotes might have different coverage or key add-ons like Zero-Dep excluded. By renewing directly with the dealership, you secure 100% cashless claims and genuine OEM parts at our workshops. Would you like to proceed, or shall I connect you to our desk to explore if we can match that online rate?":\n                "मैं समझती हूँ कि ऑनलाइन कोट्स थोड़े सस्ते लग सकते हैं, पर उनमें जीरो-डेप जैसे जरूरी एड-ऑन्स शामिल नहीं होते हैं। सीधे डीलरशिप से रिन्यू कराने पर आपको हमारे वर्कशॉप्स पर 100% कैशलेस क्लेम्स और असली पार्ट्स मिलते हैं। क्या हम इसे आगे बढ़ाएं, या ऑनलाइन रेट मैच करने के लिए मैं आपकी बात हमारे मैनेजर से करवाऊँ?",',
        '"I understand online quotes from portals like PolicyBazaar can look cheaper, but some online quotes might have different coverage or key add-ons like Zero-Dep excluded. By renewing directly with the dealership, you secure 100% cashless claims and genuine OEM parts at our workshops. Would you like to proceed, or shall I connect you to our desk to explore if we can match that online rate?":\n                "मैं समझती हूँ कि ऑनलाइन कोट्स थोड़े सस्ते लग सकते हैं, पर उनमें जीरो-डेप जैसे जरूरी एड-ऑन्स शामिल नहीं होते हैं। सीधे डीलरशिप से रिन्यू कराने पर आपको हमारे वर्कशॉप्स पर 100% कैशलेस क्लेम्स और असली पार्ट्स मिलते हैं। क्या हम इसे आगे बढ़ाएं, या ऑनलाइन रेट मैच करने के लिए मैं आपकी बात हमारे मैनेजर से करवाऊँ?",'
    ),
    (
        '"मैं समझती हूँ कि ऑनलाइन कोट्स थोड़े सस्ते लग सकते हैं, पर उनमें जीरो-डेप जैसे जरूरी एड-ऑन्स शामिल नहीं होते हैं। सीधे डीलरशिप से रिन्यू कराने पर आपको हमारे वर्कशॉप्स पर 100% कैशलेस क्लेम्स और असली पार्ट्स मिलते हैं। क्या हम इसे आगे बढ़ाएं, या ऑनलाइन रेट मैच करने के लिए मैं आपकी बात हमारे मैनेजर से करवाऊँ?":\n                "मैं समझती हूँ कि ऑनलाइन कोट्स थोड़े सस्ते लग सकते हैं, पर उनमें जीरो-डेप जैसे जरूरी एड-ऑन्स शामिल नहीं होते हैं। सीधे डीलरशिप से रिन्यू कराने पर आपको हमारे वर्कशॉप्स पर 100% कैशलेस क्लेम्स और असली पार्ट्स मिलते हैं। क्या हम इसे आगे बढ़ाएं, या ऑनलाइन रेट मैच करने के लिए मैं आपकी बात हमारे मैनेजर से करवाऊँ?",',
        '"I understand online quotes from portals like PolicyBazaar can look cheaper, but some online quotes might have different coverage or key add-ons like Zero-Dep excluded. By renewing directly with the dealership, you secure 100% cashless claims and genuine OEM parts at our workshops. Would you like to proceed, or shall I connect you to our desk to explore if we can match that online rate?":\n                "मैं समझती हूँ कि पॉलिसीबाज़ार जैसे ऑनलाइन कोट्स थोड़े सस्ते लग सकते हैं, पर उनमें जीरो-डेप जैसे जरूरी एड-ऑन्स शामिल नहीं होते हैं। सीधे डीलरशिप से रिन्यू कराने पर आपको 100% कैशलेस क्लेम और असली ओईएम पार्ट्स मिलते हैं। क्या हम आगे बढ़ें, या ऑनलाइन रेट मैच करने के लिए मैं आपकी बात हमारे मैनेजर से करवाऊँ?",'
    )
]

replaced_count = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        replaced_count += 1
    else:
        # Fallback key and value updates separately
        old_parts = old.split('":\n                "')
        new_parts = new.split('":\n                "')
        if len(old_parts) == 2 and len(new_parts) == 2:
            old_key, old_val = old_parts[0].strip('"'), old_parts[1].strip('",')
            new_key, new_val = new_parts[0].strip('"'), new_parts[1].strip('",')
            if old_key in content:
                content = content.replace(old_key, new_key)
            if old_val in content:
                content = content.replace(old_val, new_val)
            replaced_count += 1
        else:
            print(f"Failed to find match for replacement #{replacements.index((old, new)) + 1}")

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Successfully performed {replaced_count} out of {len(replacements)} replacements.")
