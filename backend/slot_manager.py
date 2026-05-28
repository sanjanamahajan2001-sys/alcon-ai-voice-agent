import re
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Tuple, Optional

class AbstractDMSAdapter:
    def get_available_slots(self, target_date: date) -> List[str]:
        raise NotImplementedError()
        
    def book_slot(self, target_date: date, slot_time: str) -> bool:
        raise NotImplementedError()

class MockJsonDMSAdapter(AbstractDMSAdapter):
    """
    Mock DMS adapter that reads and writes to data/slots.json.
    """
    def __init__(self, slots_file: str = "data/slots.json"):
        import os
        base_dir = os.path.dirname(__file__)
        self.slots_file = os.path.join(base_dir, slots_file)

    def _load_slots(self) -> Dict[str, List[str]]:
        import json
        import os
        if os.path.exists(self.slots_file):
            try:
                with open(self.slots_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[SLOT MANAGER ERROR] Failed to read {self.slots_file}: {e}")
        return {"default": ["09:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"]}

    def _save_slots(self, slots_data: Dict[str, List[str]]):
        import json
        try:
            with open(self.slots_file, "w") as f:
                json.dump(slots_data, f, indent=4)
        except Exception as e:
            print(f"[SLOT MANAGER ERROR] Failed to write {self.slots_file}: {e}")

    def get_available_slots(self, target_date: date) -> List[str]:
        date_str = target_date.strftime("%Y-%m-%d")
        slots_data = self._load_slots()
        slots = slots_data.get(date_str)
        if slots is None:
            return slots_data.get("default", [])
        return slots

    def book_slot(self, target_date: date, slot_time: str) -> bool:
        date_str = target_date.strftime("%Y-%m-%d")
        slots_data = self._load_slots()
        
        # If date key doesn't exist, initialize it from default
        if date_str not in slots_data:
            slots_data[date_str] = list(slots_data.get("default", []))
            
        if slot_time in slots_data[date_str]:
            slots_data[date_str].remove(slot_time)
            self._save_slots(slots_data)
            return True
        return False

class SlotParser:
    TIME_PERIODS = {
        "morning": ("08:00 AM", "12:00 PM"),
        "afternoon": ("12:00 PM", "05:00 PM"),  # Extended to 05:00 PM to naturally cover 04:00 PM slots
        "evening": ("04:00 PM", "07:00 PM"),
        "night": ("07:00 PM", "10:00 PM")
    }

    @staticmethod
    def parse_time_period(input_text: str) -> Optional[str]:
        text = input_text.lower()
        if any(w in text for w in ["morning", "subah", "subha", "subh", "early"]):
            return "morning"
        if any(w in text for w in ["afternoon", "after noon", "dopahar", "dophar", "dopahr", "lunch", "after slot", "after slots"]) or (re.search(r'\bafter\b', text) and not "office" in text):
            return "afternoon"
        if any(w in text for w in ["evening", "shaam", "sham", "late", "office ke baad", "after office", "office ke bad"]):
            return "evening"
        if any(w in text for w in ["night", "raat"]):
            return "night"
        return None

    @staticmethod
    def parse_specific_time(input_text: str) -> Optional[str]:
        # Handle formats like "1:30 PM", "1:30", "10 AM", "09:00"
        for match in re.finditer(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', input_text.lower()):
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            period = match.group(3)
            
            # Sanity check hours
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

    @staticmethod
    def parse_vague_time(input_text: str) -> Optional[Tuple[str, str]]:
        """Maps vague customer times to start/end search windows."""
        text = input_text.lower()
        if "late morning" in text or "subah late" in text:
            return "10:30 AM", "12:00 PM"
        if "after lunch" in text or "khana khane ke baad" in text or "khana khane ke bad" in text:
            return "02:00 PM", "04:00 PM"
        if "office ke baad" in text or "after office" in text or "office ke bad" in text:
            return "05:00 PM", "07:00 PM"
        return None

    @staticmethod
    def is_within_range(time_str: str, start_str: str, end_str: str) -> bool:
        try:
            t = datetime.strptime(time_str, "%I:%M %p").time()
            start = datetime.strptime(start_str, "%I:%M %p").time()
            end = datetime.strptime(end_str, "%I:%M %p").time()
            return start <= t < end
        except Exception:
            return False

class SlotManager:
    def __init__(self, adapter: AbstractDMSAdapter = MockJsonDMSAdapter()):
        self.adapter = adapter

    def get_upcoming_weekend(self, base_date: date) -> Tuple[date, date]:
        days_until_sat = (5 - base_date.weekday() + 7) % 7
        if days_until_sat == 0:
            days_until_sat = 7
        sat = base_date + timedelta(days=days_until_sat)
        sun = sat + timedelta(days=1)
        return sat, sun

    def get_next_monday(self, base_date: date) -> date:
        days_until_mon = (0 - base_date.weekday() + 7) % 7
        if days_until_mon == 0:
            days_until_mon = 7
        return base_date + timedelta(days=days_until_mon)

    def find_slots_for_date_and_period(self, target_date: date, period: Optional[str] = None, range_override: Optional[Tuple[str, str]] = None) -> List[str]:
        slots = self.adapter.get_available_slots(target_date)
        if range_override:
            return [s for s in slots if SlotParser.is_within_range(s, range_override[0], range_override[1])]
        if not period:
            return slots
        
        start_time, end_time = SlotParser.TIME_PERIODS.get(period, ("08:00 AM", "08:00 PM"))
        return [s for s in slots if SlotParser.is_within_range(s, start_time, end_time)]

    def get_alternate_suggestions(self, target_date: date, requested_period: Optional[str]) -> List[Tuple[date, str]]:
        suggestions = []
        
        # 1. Check same day, other slots
        same_day_slots = self.adapter.get_available_slots(target_date)
        for s in same_day_slots:
            # Avoid duplicating slots if they are in the requested period (since that was already checked and empty)
            if requested_period:
                start_time, end_time = SlotParser.TIME_PERIODS.get(requested_period, ("08:00 AM", "08:00 PM"))
                if SlotParser.is_within_range(s, start_time, end_time):
                    continue
            suggestions.append((target_date, s))
            if len(suggestions) >= 2:
                break
                
        # 2. Check next few days
        for i in range(1, 10):
            next_day = target_date + timedelta(days=i)
            day_slots = self.find_slots_for_date_and_period(next_day, requested_period)
            if not day_slots:
                day_slots = self.adapter.get_available_slots(next_day)
            
            for s in day_slots:
                suggestions.append((next_day, s))
                if len(suggestions) >= 4:
                    return suggestions[:3]
                    
        return suggestions[:3]

    def parse_counter_proposal(self, user_input: str, base_date: date, current_period: Optional[str]) -> Tuple[Optional[date], Optional[str], Optional[str], Optional[Tuple[str, str]], List[str]]:
        """
        Extracts corrected target parameters when the customer corrects or negotiates.
        """
        text = user_input.lower().strip()
        target_date = base_date
        target_period = current_period
        specific_time = None
        range_override = None
        negated_times = []
        
        # 0. Check for specific date phrase (only if text contains a date indicator/digit to avoid false matches on "morning")
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
        if has_date_indicator:
            from date_utils import parse_date_phrase
            parsed_dt = parse_date_phrase(text)
            if parsed_dt:
                # Only overwrite the date if it's a real date change,
                # not a fallback to 'today' due to time indicators (unless they explicitly said 'today' or 'aaj' or current weekday/day number)
                today = datetime.now().date()
                if parsed_dt == today:
                    today_terms = ["today", "aaj", today.strftime("%A").lower(), today.strftime("%a").lower(), str(today.day), f"{today.day}th", f"{today.day}st", f"{today.day}nd", f"{today.day}rd"]
                    if any(term in text for term in today_terms):
                        target_date = parsed_dt
                else:
                    target_date = parsed_dt

        # Check for negations of dates/weekdays (e.g. "not thursday", "actually not on thursday", "thursday ko nahi")
        negated_dates = []
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                        "somwar", "mangalwar", "budhwar", "guruwar", "veervar", "shukrawar", "shaniwar", "ravivar",
                        "somvaar", "mangalvaar", "budhvaar", "guruvaar", "veervaar", "shukrawaar", "shaniwaar", "ravivaar",
                        "thrusday", "wedensday", "wednsday", "tuesay", "teusday", "satruday"]
        
        matched_day = None
        for day in days_of_week:
            if day in text:
                matched_day = day
                break
                
        neg_words_d = ["not", "busy", "no", "nahi", "dont", "don't", "avoid", "cant", "can't", "cancel", "nhi"]
        is_neg_d = False
        if matched_day:
            for neg in neg_words_d:
                pattern = r'\b' + re.escape(neg) + r'\s+(?:\w+\s+){0,3}' + re.escape(matched_day) + r'\b'
                pattern2 = r'\b' + re.escape(matched_day) + r'\s+(?:\w+\s+){0,3}' + re.escape(neg) + r'\b'
                if re.search(pattern, text) or re.search(pattern2, text):
                    is_neg_d = True
                    break
            
            if is_neg_d:
                negated_dates.append(target_date)

        # Check if they are negating the day number of the target date (e.g. "not on 28th", "28 ko nahi")
        if not is_neg_d and target_date:
            day_num = target_date.day
            day_str_variants = [str(day_num), f"{day_num}th", f"{day_num}st", f"{day_num}nd", f"{day_num}rd"]
            matched_day_num = None
            for variant in day_str_variants:
                if re.search(r'\b' + re.escape(variant) + r'\b', text):
                    matched_day_num = variant
                    break
            if matched_day_num:
                is_neg_num = False
                for neg in neg_words_d:
                    pattern = r'\b' + re.escape(neg) + r'\s+(?:\w+\s+){0,3}' + re.escape(matched_day_num) + r'\b'
                    pattern2 = r'\b' + re.escape(matched_day_num) + r'\s+(?:\w+\s+){0,3}' + re.escape(neg) + r'\b'
                    if re.search(pattern, text) or re.search(pattern2, text):
                        is_neg_num = True
                        break
                if is_neg_num:
                    negated_dates.append(target_date)

        if target_date in negated_dates:
            found_new_date = False
            for i in range(1, 10):
                next_day = target_date + timedelta(days=i)
                if next_day not in negated_dates:
                    slots = self.adapter.get_available_slots(next_day)
                    if slots:
                        target_date = next_day
                        found_new_date = True
                        break
            if not found_new_date:
                target_date = datetime.now().date() + timedelta(days=1)

        # Parse specific times and classify them as negated or accepted
        time_matches = []
        for m in re.finditer(r'\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', text):
            hour = int(m.group(1))
            minute = int(m.group(2)) if m.group(2) else 0
            period = m.group(3) if m.group(3) else None
            
            if hour > 24 or minute > 59:
                continue
                
            if period:
                if period == 'pm' and hour < 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
            else:
                if hour < 8:
                    hour += 12
                period = "pm" if hour >= 12 else "am"
                
            display_hour = hour - 12 if hour > 12 else (12 if hour == 0 else hour)
            display_period = "PM" if hour >= 12 else "AM"
            t_str = f"{display_hour:02d}:{minute:02d} {display_period}"
            time_matches.append((m.start(), m.end(), t_str))

        accepted_times = []
        neg_words = ["not", "busy", "no", "nahi", "dont", "don't", "cant", "can't", "too early", "too ealr", "early", "avoid", "late", "too late", "नहीं", "नही", "ना", "मत"]
        booking_words = ["book", "confirm", "take", "choose", "want", "prefer", "better", "slot", "theek", "बुक", "करदो", "ठीक", "जी"]
        
        for idx, (start, end, t_str) in enumerate(time_matches):
            prev_end = time_matches[idx-1][1] if idx > 0 else 0
            next_start = time_matches[idx+1][0] if idx < len(time_matches) - 1 else len(text)
            
            segment_before = text[prev_end:start]
            segment_after = text[end:next_start]
            
            # Split segments by clause boundaries (., । , ?, !, ;, comma)
            # to prevent negation leakage across different sentences/clauses
            clauses_before = re.split(r'[.,।?!;,]', segment_before)
            clause_before = clauses_before[-1] if clauses_before else ""
            
            clauses_after = re.split(r'[.,।?!;,]', segment_after)
            clause_after = clauses_after[0] if clauses_after else ""
            
            is_negated = False
            for neg in neg_words:
                if neg in clause_before or neg in clause_after:
                    is_negated = True
                    break
                    
            if is_negated:
                for bw in booking_words:
                    if bw in clause_before:
                        is_negated = False
                        break
                        
            if is_negated:
                negated_times.append(t_str)
            else:
                accepted_times.append(t_str)

        if accepted_times:
            specific_time = accepted_times[0]
        
        # Determine if it is a question about availability (Hinglish positive inquiry)
        # e.g., "available nahi hai?", "slots nahi hai kya?"
        # In Hinglish/Hindi, asking "dopahar ke slots nahi hai kya" is actually a REQUEST for afternoon slots.
        is_period_inquiry = False
        if any(term in text for term in ["kya", "available", "khali", "khaali", "empty", "hai?", "kya?", "h kya"]):
            is_period_inquiry = True

        # Check for negations of periods (e.g. "not morning", "busy in the morning")
        negated_periods = []
        for p in ["morning", "afternoon", "evening", "night"]:
            period_terms = [p]
            if p == "morning":
                period_terms.extend(["subah", "subha", "subh", "morning"])
            elif p == "afternoon":
                period_terms.extend(["dopahar", "dophar", "dopahr", "afternoon", "lunch", "after"])
            elif p == "evening":
                period_terms.extend(["shaam", "sham", "evening", "office"])
            elif p == "night":
                period_terms.extend(["raat", "night"])
            
            matched_term = None
            for term in period_terms:
                if term in text:
                    matched_term = term
                    break
            
            if matched_term:
                # Find the clause containing this period term to isolate analysis
                clauses = re.split(r'[.,।?!;,]', text)
                matched_clause = ""
                for clause in clauses:
                    if matched_term in clause:
                        matched_clause = clause
                        break
                
                # Check for positive inquiry in the matched clause only
                is_p_inquiry = any(term in matched_clause for term in ["kya", "available", "khali", "khaali", "empty", "hai?", "kya?", "h kya", "क्या", "कया", "खाली", "खालि", "है क्या", "है क्या?", "कया?", "क्या?"])
                if is_p_inquiry:
                    continue
                    
                neg_words_p = ["not", "busy", "no", "nahi", "na", "avoid", "dont", "don't", "cant", "can't", "unable", "occupied", "engaged", "nhi"]
                is_neg = False
                for neg in neg_words_p:
                    pattern1 = r'\b' + re.escape(neg) + r'\s+(?:\w+\s+){0,3}' + re.escape(matched_term) + r'\b'
                    pattern2 = r'\b' + re.escape(matched_term) + r'\s+(?:\w+\s+){0,3}' + re.escape(neg) + r'\b'
                    if re.search(pattern1, matched_clause) or re.search(pattern2, matched_clause) or neg in matched_clause:
                        is_neg = True
                        break
                if is_neg:
                    negated_periods.append(p)

        # If user says "too early" or "early", morning is naturally negated (unless they specified a specific time to negate instead)
        if any(w in text for w in ["too early", "too ealr", "early", "very early", "bohot jaldi", "bahut jaldi"]):
            if not negated_times:
                negated_periods.append("morning")

        # 1. Shift to weekend
        if any(w in text for w in ["weekend", "saturday", "sunday", "shaniwar", "ravivar", "weekends", "weekdays", "weekday"]):
            sat, sun = self.get_upcoming_weekend(datetime.now().date())
            target_date = sat
            target_period = target_period or "morning"
            
        # 2. Shift to next Monday
        elif any(w in text for w in ["next monday", "monday ko", "somwar"]):
            target_date = self.get_next_monday(datetime.now().date())
            
        # 3. Shift to specific time of day
        proposed_period = None
        for p in ["morning", "afternoon", "evening", "night"]:
            period_terms = [p]
            if p == "morning":
                period_terms.extend(["subah", "subha", "subh", "morning"])
            elif p == "afternoon":
                period_terms.extend(["dopahar", "dophar", "dopahr", "afternoon", "lunch", "after"])
            elif p == "evening":
                period_terms.extend(["shaam", "sham", "evening", "office"])
            elif p == "night":
                period_terms.extend(["raat", "night"])
            
            if any(term in text for term in period_terms):
                if p not in negated_periods:
                    proposed_period = p
                    break
        
        if proposed_period:
            target_period = proposed_period
        else:
            new_period = SlotParser.parse_time_period(text)
            if new_period and new_period not in negated_periods:
                target_period = new_period
            
        # 4. Vague time period (e.g. "after lunch")
        vague_range = SlotParser.parse_vague_time(text)
        if vague_range:
            range_override = vague_range

        # If any period is negated, filter out negated periods and find alternative available periods on the same day
        if negated_periods:
            all_slots = self.adapter.get_available_slots(target_date)
            available_periods = []
            for p in ["morning", "afternoon", "evening", "night"]:
                if p not in negated_periods:
                    start_t, end_t = SlotParser.TIME_PERIODS.get(p, ("08:00 AM", "08:00 PM"))
                    slots_in_p = [s for s in all_slots if SlotParser.is_within_range(s, start_t, end_t)]
                    if slots_in_p:
                        available_periods.append(p)
            
            if available_periods:
                if not target_period or target_period in negated_periods or (current_period in negated_periods and target_period == current_period):
                    target_period = available_periods[0]
            else:
                target_period = None

        return target_date, target_period, specific_time, range_override, negated_times
