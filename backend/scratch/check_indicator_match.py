import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

text = "no, i’ll be busy in the morning."

has_date_indicator = (
    any(w in text for w in [
        "today", "tomorrow", "monday", "tuesday", "wednesday", "thursday", 
        "friday", "saturday", "sunday", "mon", "tue", "wed", "thu", "fri", 
        "sat", "sun", "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", 
        "sep", "oct", "nov", "dec", "shaniwar", "ravivar", "somwar", "somvaar", 
        "mangalwar", "mangalvaar", "budhwar", "budhvaar", "guruwar", "guruvaar", 
        "veervar", "veervaar", "shukrawar", "shukrawaar", "shaniwar", "shaniwaar", 
        "ravivar", "ravivaar", "weekdays", "weekday", "weekend", "weekends"
    ])
    or any(char.isdigit() for char in text)
)
print("has_date_indicator:", has_date_indicator)
