text = "no, i’ll be busy in the morning."
indicators = [
    "today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", 
    "friday", "saturday", "sunday", "mon", "tue", "wed", "thu", "fri", 
    "sat", "sun", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", 
    "sep", "oct", "nov", "dec", "shaniwar", "ravivar", "somwar", "somvaar", 
    "mangalwar", "mangalvaar", "budhwar", "budhvaar", "guruwar", "guruvaar", 
    "veervar", "veervaar", "shukrawar", "shukrawaar", "shaniwar", "shaniwaar", 
    "ravivar", "ravivaar", "weekdays", "weekday", "weekend", "weekends"
]

for w in indicators:
    if w in text:
        print(f"Matched indicator: '{w}'")
