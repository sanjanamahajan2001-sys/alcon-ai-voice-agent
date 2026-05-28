import re
from datetime import datetime, timedelta

def parse_date_phrase(input_text):
    today = datetime.now().date()
    input_text = input_text.lower()
    
    # Day and Month names
    day_names = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    month_names = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
    
    # 1. Relative dates
    if 'today' in input_text or 'aaj' in input_text:
        return today
    if 'tomorrow' in input_text or 'kal' in input_text:
        return today + timedelta(days=1)
    if 'parso' in input_text or 'parsoon' in input_text:
        return today + timedelta(days=2)
    
    # 1b. Handle "after X hours/hrs" or "in X hours/hrs"
    if any(word in input_text for word in ['hour', 'hr']):
        return today

    # 1c. Handle parts of the day
    if 'morning' in input_text and 'tomorrow' not in input_text:
        return today
    if 'afternoon' in input_text or 'after noon' in input_text:
        return today
    if 'evening' in input_text:
        return today
    
    # 2. Days of week
    for i, name in enumerate(day_names):
        if name in input_text:
            # datetime.now().weekday() is 0 for Monday, 6 for Sunday
            # day_names is 0 for Sunday
            current_weekday = (datetime.now().weekday() + 1) % 7 # Adjust to Sunday=0
            days_until = (i - current_weekday + 7) % 7
            if days_until == 0:
                days_until = 7 # Assume next week
            return today + timedelta(days=days_until)
            
    # 3. Specific dates like "18th", "19th April"
    # If there's a month name, prioritize it as a date
    has_month = any(m in input_text for m in month_names)
    
    # If time indicators are present and NO month name, it's likely just a time for 'today'
    time_indicators = r'(hr|min|pm|am|at|morning|afternoon|evening|o\'clock|baje|bajein|बजे|बजें)'
    if not has_month:
        if re.search(r'\d+\s*' + time_indicators, input_text) or re.search(time_indicators + r'\s*\d+', input_text):
            return today

    # Pre-filter to ignore obvious times and years when searching for day numbers
    text_for_day = input_text
    # 1. Remove standard colon time formats like "11:00" or "09:30"
    text_for_day = re.sub(r'\b\d{1,2}:\d{2}\s*(am|pm)?\b', '', text_for_day)
    # 2. Remove 4-digit years like "2026"
    text_for_day = re.sub(r'\b20\d{2}\b', '', text_for_day)
    # 3. Remove digits followed by time indicators (e.g. "11 baje", "11pm", "5 pm", "10 am")
    text_for_day = re.sub(r'\b\d+\s*' + time_indicators + r'\b', '', text_for_day)
    text_for_day = re.sub(time_indicators + r'\s*\d+\b', '', text_for_day)

    day_match = re.search(r'(\d+)(st|nd|rd|th)?', text_for_day)
    if day_match:
        day = int(day_match.group(1))
        month = today.month
        
        for i, name in enumerate(month_names):
            if name in input_text:
                month = i + 1
                break
        
        try:
            target_date = datetime(today.year, month, day).date()
            if target_date < today and month == today.month and name not in input_text:
                # If date is in past and month wasn't explicitly mentioned, assume next month
                if month == 12:
                    target_date = datetime(today.year + 1, 1, day).date()
                else:
                    target_date = datetime(today.year, month + 1, day).date()
            return target_date
        except ValueError:
            return None
            
    return None

def format_date_full(target_date):
    """Format a date object into a human-readable string."""
    if not target_date:
        return "Unknown date"
    # Format: Monday, April 18
    return target_date.strftime("%A, %B %d")

def calculate_age(reg_date_str):
    """Calculate vehicle age in years from registration date string."""
    try:
        reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
        today = datetime.now()
        # Simple year difference
        age = today.year - reg_date.year - ((today.month, today.day) < (reg_date.month, reg_date.day))
        return max(0, age)
    except Exception:
        return 0
