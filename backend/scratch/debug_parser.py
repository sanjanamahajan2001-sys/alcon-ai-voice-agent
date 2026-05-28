import re
from typing import Optional

class SlotParser:
    @staticmethod
    def parse_specific_time(input_text: str) -> Optional[str]:
        for match in re.finditer(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', input_text.lower()):
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            period = match.group(3)
            
            # Skip invalid hours/minutes
            if hour > 24 or minute > 59:
                continue
                
            # Skip if it is likely a day of the month (e.g. 1st-31st) when AM/PM is not present
            match_str = match.group(0)
            start_idx = match.start()
            suffix_match = re.match(r'^\d+(st|nd|rd|th)', input_text[start_idx:].lower())
            if suffix_match and not period:
                continue
                
            if period == 'pm' and hour < 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
                
            if not period:
                if hour < 8:
                    hour += 12  # Assume PM for low digits like 1, 2, 4
                period = "PM" if hour >= 12 else "AM"
                
            display_hour = hour - 12 if hour > 12 else (12 if hour == 0 else hour)
            display_period = "PM" if hour >= 12 else "AM"
            return f"{display_hour:02d}:{minute:02d} {display_period}"
        return None

user_input = "28th May at 10 AM"
specific_time = SlotParser.parse_specific_time(user_input)
print(f"Input: {user_input}")
print(f"Parsed specific time: {specific_time}")
