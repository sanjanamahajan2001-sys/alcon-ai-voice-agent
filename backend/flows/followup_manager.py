from datetime import datetime, timedelta
import re


class FollowupManager:
    @staticmethod
    def should_schedule_callback(user_input_lower: str, interest_level: str) -> bool:
        """Requirement 4: Detect if a callback should be scheduled. 
        Only triggers if user is explicitly busy (using whole-word regex) OR if interest is WARM.
        """
        import re
        busy_signals = ['busy', 'meeting', 'later', 'call back', 'after some time', 'tomorrow', 'driving']
        is_busy = any(re.search(rf'\b{word}\b', user_input_lower) for word in busy_signals)
        
        if is_busy:
            return True
        if interest_level == "WARM":
            return True
            
        return False

    @staticmethod
    def get_callback_prompt() -> str:
        return "Would you like me to schedule a callback from our specialist? What time would be convenient for you?"

    @staticmethod
    def get_confirmation_message(time_str: str, is_whatsapp: bool = False) -> str:
        whatsapp_note = " and send that brochure to your WhatsApp right away" if is_whatsapp else ""
        return f"Excellent. I've scheduled a callback for {time_str}{whatsapp_note}. Our specialist will contact you then. Have a wonderful day!"

    @staticmethod
    def record_callback(db, call_sid: str, time_str: str, customer_id: str = "Unknown"):
        """Store the scheduled callback in the database using high-precision NLP parsing."""
        from datetime import datetime, timedelta
        from date_utils import parse_date_phrase, format_date_full
        import re
        
        now = datetime.now()
        parsed_dt = parse_date_phrase(time_str)
        if not parsed_dt:
            parsed_dt = now.date() + timedelta(days=1)
            
        # Determine time suffix
        time_suffix = "11:00 AM" # Standard default
        time_str_lower = time_str.lower()
        if "evening" in time_str_lower:
            time_suffix = "06:00 PM"
        elif "afternoon" in time_str_lower or "after noon" in time_str_lower:
            time_suffix = "02:00 PM"
        elif "morning" in time_str_lower:
            time_suffix = "10:00 AM"
        else:
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str_lower)
            if time_match:
                hh = int(time_match.group(1))
                mm = time_match.group(2) or "00"
                period = time_match.group(3).upper()
                time_suffix = f"{hh:02d}:{mm} {period}"
                
        # Parse time_suffix back into a datetime object for storing in DB
        try:
            match = re.match(r'(\d{2}):(\d{2})\s*(AM|PM)', time_suffix)
            if match:
                hh = int(match.group(1))
                mm = int(match.group(2))
                period = match.group(3)
                if period == "PM" and hh < 12:
                    hh += 12
                elif period == "AM" and hh == 12:
                    hh = 0
                scheduled_time = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day, hh, mm)
            else:
                scheduled_time = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day, 11, 0)
        except Exception:
            scheduled_time = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day, 11, 0)
            
        time_iso = scheduled_time.isoformat()
        formatted_human = f"{format_date_full(parsed_dt)} at {time_suffix}"
        
        # Save both formatted and raw ISO to DB
        db.update_lead_state(call_sid, follow_up_time=time_iso, last_action=f"Scheduled Callback for {formatted_human}")
        db.schedule_followup(customer_id, call_sid, formatted_human)
        print(f"DEBUG: Callback recorded for {customer_id} at {formatted_human} (ISO: {time_iso})")
