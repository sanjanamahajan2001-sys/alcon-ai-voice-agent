import re

pattern = r"(?:I can certainly clarify that for you (?:Ma'am|Sir|मैडम|सर)\.\s*)?Would you like to know more about the features, EMI options, pricing of the ([a-zA-Z0-9 ]+), or should I connect you with our manager\??\.?"
text = "I can certainly clarify that for you मैडम. Would you like to know more about the features, EMI options, pricing of the Hyundai creta, or should I connect you with our manager?"

match = re.match(pattern, text, re.IGNORECASE)
print("Match found:", match is not None)
if match:
    print("Group 1:", match.group(1))
