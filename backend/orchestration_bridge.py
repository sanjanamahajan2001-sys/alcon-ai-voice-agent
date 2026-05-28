import os
import json
import re
import uuid
import threading
import time
import random
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from database import DatabaseManager
from date_utils import parse_date_phrase, format_date_full
from intent_engine import IntentEngine
from flows.intro_flow import IntroFlow
from flows.service_bridge_flow import ServiceBridgeFlow
from slot_manager import SlotManager, SlotParser, MockJsonDMSAdapter
from flows.insurance_flow import InsuranceFlow
from flows.followup_manager import FollowupManager


def mark_customer_dnd_permanent(customer_id):
    """Standalone utility to mark a customer as DND in customers.json."""
    if not customer_id: return
    # Try multiple possible paths for customers.json depending on execution environment
    base_dir = os.path.dirname(__file__)
    possible_paths = [
        os.path.join(base_dir, "data", "customers.json"),
        os.path.join(base_dir, "..", "data", "customers.json"),
        "data/customers.json"
    ]
    
    customers_path = None
    for path in possible_paths:
        if os.path.exists(path):
            customers_path = path
            break
            
    if not customers_path: return
    
    try:
        with open(customers_path, "r") as f:
            customers = json.load(f)
        updated = False
        for c in customers:
            if str(c.get("id")) == str(customer_id):
                c["dnd_status"] = True
                updated = True
                break
        if updated:
            with open(customers_path, "w") as f:
                json.dump(customers, f, indent=4)
            print(f"[COMPLIANCE] Customer {customer_id} marked as DND permanently.")
    except Exception as e:
        print(f"[BRIDGE ERROR] Failed to update DND for {customer_id}: {e}")

class NodeExecutor(ABC):
    @abstractmethod
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass

class MessageNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        text = node_data.get("label", "")
        variables = context.get("variables", {})
        
        # Ensure callback_confirmation is always initialized to a polite default fallback
        if "callback_confirmation" not in variables or not variables.get("callback_confirmation"):
            variables["callback_confirmation"] = "I will have our Service Desk call you back to coordinate a suitable time"
        
        # --- SERVICE BOOKING VARIABLE EXTRACTION ---
        user_input = context.get("user_input")
        node_id = context.get("current_node_id")
        
        print(f"[DEBUG MESSAGE EXECUTOR] node_id: {node_id} | flow_type: {variables.get('flow_type')} | user_input: {user_input}")
        
        if variables.get("flow_type") == "booking" and user_input:
            user_input_lower = user_input.lower().strip()
            
            if node_id == "collect_mileage" and not variables.get("confirmed_date"):
                parsed_date = parse_date_phrase(user_input)
                if parsed_date:
                    date_str = format_date_full(parsed_date)
                    if "at" not in user_input_lower and "am" not in user_input_lower and "pm" not in user_input_lower:
                        date_str += " at 09:00 AM"
                    variables["confirmed_date"] = date_str
                else:
                    variables["confirmed_date"] = "tomorrow at 09:00 AM"
                print(f"[EXTRACT DATE] Extracted: {variables['confirmed_date']}")
                
            elif node_id == "ask_concerns":
                digits = "".join(filter(str.isdigit, user_input))
                if digits:
                    variables["mileage"] = digits
                else:
                    variables["mileage"] = "45000"
                print(f"[EXTRACT MILEAGE] Extracted: {variables['mileage']}")
                
            elif node_id == "pick_drop_offer":
                if len(user_input.split()) > 1:
                    variables["concerns"] = user_input
                else:
                    variables["concerns"] = "General Checkup"
                print(f"[EXTRACT CONCERNS] Extracted: {variables['concerns']}")

        # 1. Resolve Variables (Multi-pass to support nested placeholders like greeting_context)
        for _ in range(3):
            if "{{" not in text:
                break
            for key, value in variables.items():
                if value is not None:
                    text = text.replace(f"{{{{{key}}}}}", str(value))
                else:
                    text = text.replace(f"{{{{{key}}}}}", f"[{key}]")
                
        # 2. Dynamic Option Filtering (Gap Fix)
        # If the AI already answered a query, don't ask if they want to hear it again in the next breath.
        ack_intents = variables.get("acknowledged_intents", [])
        if "latest price, ongoing offers, or schedule a test drive" in text:
            options_map = {
                "price": "latest price",
                "offers": "ongoing offers",
                "test_drive": "schedule a test drive"
            }
            
            # Check which intents were ALREADY handled
            remaining = [v for k, v in options_map.items() if k not in ack_intents]
            
            if len(remaining) < 3 and len(remaining) > 0:
                option_str = ", ".join(remaining[:-1]) + " or " + remaining[-1] if len(remaining) > 1 else remaining[0]
                text = text.replace("latest price, ongoing offers, or schedule a test drive", option_str)
                
                # Cleanup sentence joining (Remove 'Great! ' if we are adding 'Besides that')
                text = text.replace("Great! To help you better, ", "")
                text = text.replace("Great! ", "")
                text = "Besides that, I can " + text[0].lower() + text[1:] if not text.startswith("Besides") else text
                print(f"[DEBUG] Filtered options: {remaining} | New text: {text[:50]}...")

        # 3. Duplicate Suppression (Skip if AI literally just said this exact text in the previous turn)
        history = context.get("history", [])
        ai_msgs = [m for m in history if m.get("role") == "ai"]
        if ai_msgs:
            last_ai_text = ai_msgs[-1].get("text", "")
            def clean_text(t):
                return re.sub(r'[^\w\s]', '', t).lower().strip()
            if clean_text(text) in clean_text(last_ai_text):
                print(f"[DEBUG] Duplicate suppression triggered. Skipping duplicate message node: {text[:30]}...")
                return {
                    "status": "SUCCESS",
                    "action": "speak",
                    "is_bridge": True,
                    "text": None,
                    "logs": "Skipped duplicate message"
                }

        return {
            "status": "SUCCESS",
            "action": "speak",
            "logs": f"Spoke: {text[:30]}...",
            "text": text or " "
        }

class ConditionNodeExecutor(NodeExecutor):
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.tone_profile = "professional_warm"
        self.acknowledgments = {
            "query": ["That's a fair question.", "I understand your concern.", "I'd be happy to clarify that for you.", "Good point."],
            "skeptic": ["I appreciate your transparency.", "That's a valid point.", "I understand why you'd ask that.", "Let me be very clear on that."],
            "loyalty": ["It's wonderful to speak with a long-term owner.", "We truly value your loyalty to Hyundai."],
            "busy": ["Absolutely {salutation}, I'll be very brief then.", "Understood, I'll keep this quick.", "I respect your time, just a quick update."]
        }

    def get_acknowledgment(self, intent: str) -> str:
        return random.choice(self.acknowledgments.get(intent, ["Understood.", "I see."]))

    def log_transition(self, call_sid, prev_node, curr_node, reason, raw_input="", intent="", confidence=1.0):
        query = """
            INSERT INTO orchestration_audit 
            (call_sid, previous_node, current_node, trigger_reason, raw_input, resolved_intent, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_query(query, (call_sid, str(prev_node), str(curr_node), str(reason), str(raw_input), str(intent), float(confidence)))
            print(f"[AUDIT] Logged transition for {call_sid}: {prev_node} -> {curr_node}")
        except Exception as e:
            print(f"[AUDIT ERROR] {e}")

    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        condition = node_data.get("label", "")
        variables = context.get("variables", {})
        session_id = context.get("session_id", "unknown")
        
        # Use explicit user_input from context, fallback to history
        last_msg_raw = context.get("user_input", "") or ""
        last_msg = str(last_msg_raw).lower().strip()
        if not last_msg:
            user_msgs = [m for m in context.get("history", []) if m.get("role") == "user"]
            last_msg = user_msgs[-1].get("text", "").lower().strip() if user_msgs else ""
        
        print(f"[DEBUG] Resolved last_msg: '{last_msg}'")

        # --- SERVICE BOOKING FLOW CONDITIONS ---
        if variables.get("flow_type") == "booking":
            print(f"[DEBUG] Service Booking Condition Check: '{condition}'. Input: '{last_msg}'")
            def check_word(word_list, text):
                for word in word_list:
                    if any(ord(c) > 127 for c in word):
                        # Safe lookaround boundary for Devanagari combining characters
                        pattern = rf'(?<![a-zA-Z0-9\u0900-\u097F]){re.escape(word)}(?![a-zA-Z0-9\u0900-\u097F])'
                    else:
                        pattern = rf'\b{re.escape(word)}\b'
                    if re.search(pattern, text, re.I):
                        return True
                return False
            
            is_busy = check_word(['busy', 'meeting', 'later', 'call back', 'not now', 'driving'], last_msg)
            is_wrong = check_word(["wrong number", "not me", "incorrect", "wrong person", "sold", "no longer have", "don't have that car"], last_msg)
            is_yes = check_word(["yes", "yeah", "correct", "yep", "speaking", "sure", "ok", "okay", "good", "satisfied", "proceed", "hello", "hi", "book"], last_msg)
            is_no = check_word(["no", "nope", "dont", "don't", "not now", "stop", "not interested"], last_msg)

            if condition == "Identity Verification":
                if is_wrong:
                    return {"status": "SUCCESS", "outcome": "wrong_number", "is_bridge": True}
                if is_busy or is_no:
                    return {"status": "SUCCESS", "outcome": "busy", "is_bridge": True}
                
                # Dynamic Service Due Check
                try:
                    svc_status = variables.get("service_status")
                    
                    # Fetch database service_linked or lead_status to see if already booked
                    is_linked = False
                    if session_id and session_id != "unknown":
                        lead_state = self.db.get_lead_state(session_id)
                        if lead_state and (lead_state.get("service_linked") or lead_state.get("lead_status") == "SERVICE_BOOKED"):
                            is_linked = True

                    if svc_status in ["booked", "in-progress", "completed"] or is_linked:
                        is_due = False
                    else:
                        last_service_str = variables.get("last_service_date")
                        due_months = int(variables.get("service_due_months", 6))
                        
                        if last_service_str and last_service_str != "recent date":
                            last_service = datetime.strptime(last_service_str, "%Y-%m-%d").date()
                            today = date.today()
                            delta = (today.year - last_service.year) * 12 + (today.month - last_service.month)
                            is_due = delta >= due_months
                        else:
                            is_due = True
                except Exception as e:
                    print(f"[SERVICE DUE CHECK ERROR] {e}")
                    is_due = True

                if not is_due:
                    return {"status": "SUCCESS", "outcome": "not_due", "is_bridge": True}
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            elif condition == "User says Yes" or context.get("current_node_id") == "pick_drop_check":
                # Check if it's the pick-and-drop valet check
                if context.get("current_node_id") == "pick_drop_check" or "pick_drop" in str(context.get("current_node_id") or ""):
                    is_valet = any(word in last_msg for word in ["yes", "yeah", "sure", "definitely", "please", "valet", "pick"])
                    variables["wants_valet"] = is_valet
                    
                    # --- FINAL SERVICE BOOKING DATABASE SYNC ---
                    cust_id = variables.get("id")
                    if cust_id and cust_id != "Unknown":
                        try:
                            base_dir = os.path.dirname(__file__)
                            customers_path = os.path.join(base_dir, "data", "customers.json")
                            
                            if os.path.exists(customers_path):
                                with open(customers_path, "r") as f:
                                    customers = json.load(f)
                                for c in customers:
                                    if str(c.get("id")) == str(cust_id):
                                        c["last_service_date"] = datetime.now().strftime("%Y-%m-%d")
                                        c["notes"] = variables.get("concerns", "General Checkup")
                                        break
                                with open(customers_path, "w") as f:
                                    json.dump(customers, f, indent=4)
                        except Exception as e:
                            print(f"[BOOKING SYNC ERROR] Failed to update customers.json: {e}")

                    # Update Database Lead State
                    self.db.update_lead_state(session_id, 
                        lead_status="CONVERTED", 
                        disposition="SERVICE_BOOKED", 
                        last_action=f"Booked for {variables.get('confirmed_date', 'TBD')}"
                    )

                    # Send Mock SMS
                    print(f"\n[SMS SENT] To {variables.get('phone')}: Your service for {variables.get('car')} is confirmed for {variables.get('confirmed_date')}. Advisor: Amit Shah.\n")
                    
                    return {"status": "SUCCESS", "outcome": "true" if is_valet else "false", "is_bridge": True}
                
                # Otherwise, it's the check_booking node
                if is_busy:
                    return {"status": "SUCCESS", "outcome": "busy", "is_bridge": True}
                if is_no:
                    return {"status": "SUCCESS", "outcome": "false", "is_bridge": True}
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            elif condition == "Check Counter Proposal":
                manager = SlotManager()
                base_date_str = variables.get("target_date_raw", datetime.now().date().strftime("%Y-%m-%d"))
                base_date = datetime.strptime(base_date_str, "%Y-%m-%d").date()
                current_period = variables.get("target_period")
                
                # --- [EDGE CASE: Let me confirm with family] ---
                if any(w in last_msg for w in ["confirm with family", "puch ke bataunga", "ghar pe puchna", "ask my wife", "ask family", "confirm with my family"]):
                    return {"status": "SUCCESS", "outcome": "pause_for_family", "is_bridge": True}
                    
                # --- [EDGE CASE: Pickup and drop off inquiry] ---
                if any(w in last_msg for w in ["pickup available", "pickup drop", "valet", "drop facility", "pick and drop", "pick & drop"]):
                    variables["wants_valet"] = True
                    # Re-iterate the suggestion but acknowledge pickup
                    return {"status": "SUCCESS", "outcome": "pickup_acknowledged", "is_bridge": True}

                # Parse corrections
                target_date, target_period, specific_time, range_override, negated_times = manager.parse_counter_proposal(last_msg, base_date, current_period)
                
                # --- [EDGE CASE: Latest evening slot requested] ---
                if any(w in last_msg for w in ["latest", "sabse late", "last slot", "late slot", "evening slot", "shaam ko"]):
                    slots = manager.adapter.get_available_slots(target_date)
                    if slots:
                        latest_slot = slots[-1]
                        variables["confirmed_date"] = f"{format_date_full(target_date)} at {latest_slot}"
                        variables["confirmed_time_only"] = latest_slot
                        return {"status": "SUCCESS", "outcome": "accepted", "is_bridge": True}

                # Check if they accepted the first/choice suggestions
                words = last_msg.split()
                is_accept = any(w in words for w in ["yes", "yeah", "sure", "fine", "okay", "ok", "theek", "hao", "kar do", "confirm", "theek hai", "theek h", "haan", "han"])
                
                # A pure acceptance is when they say yes/ok but do not correct the date/time or propose a new specific time
                is_pure_accept = is_accept and not specific_time and target_date == base_date and (target_period == current_period or target_period is None)
                
                if is_pure_accept:
                    alternates = variables.get("alternate_suggestions_raw", [])
                    if alternates:
                        d_str, t = alternates[0]
                        d = datetime.strptime(d_str, "%Y-%m-%d").date()
                        variables["confirmed_date"] = f"{format_date_full(d)} at {t}"
                        variables["confirmed_time_only"] = t
                        return {"status": "SUCCESS", "outcome": "accepted", "is_bridge": True}
                    else:
                        slots = manager.find_slots_for_date_and_period(target_date, target_period, range_override)
                        if slots:
                            variables["confirmed_date"] = f"{format_date_full(target_date)} at {slots[0]}"
                            variables["confirmed_time_only"] = slots[0]
                            return {"status": "SUCCESS", "outcome": "accepted", "is_bridge": True}

                available_slots = manager.find_slots_for_date_and_period(target_date, target_period, range_override)
                if negated_times:
                    available_slots = [s for s in available_slots if s not in negated_times]
                
                if specific_time and specific_time in manager.adapter.get_available_slots(target_date):
                    variables["confirmed_date"] = f"{format_date_full(target_date)} at {specific_time}"
                    variables["confirmed_time_only"] = specific_time
                    return {"status": "SUCCESS", "outcome": "accepted", "is_bridge": True}
                elif not specific_time and available_slots:
                    # Provide options if multiple (e.g. "We have Saturday slots at 10:00 AM and 03:00 PM")
                    if len(available_slots) > 1:
                        variables["matching_period_slots_text"] = " and ".join(available_slots[:2])
                        variables["target_date_raw"] = target_date.strftime("%Y-%m-%d")
                        variables["target_period"] = target_period
                        
                        # Determine relative day phrase
                        today = datetime.now().date()
                        if target_date == today:
                            day_rel = "today"
                        elif target_date == today + timedelta(days=1):
                            day_rel = "tomorrow"
                        else:
                            day_rel = format_date_full(target_date)
                        
                        if target_period:
                            variables["requested_day_rel"] = f"{day_rel} {target_period}"
                        else:
                            variables["requested_day_rel"] = day_rel
                            
                        # Set slot choice prefix dynamically based on rejection/negation
                        is_negating_period = any(w in last_msg for w in ["not", "nahi", "na", "dont", "don't", "cant", "can't"]) and any(p in last_msg for p in ["morning", "afternoon", "evening", "night", "subah", "dopahar", "shaam", "raat"])
                        if is_negating_period or "busy" in last_msg or "no" in words:
                            variables["slot_choice_prefix"] = f"No problem {variables.get('salutation', 'Sir')}."
                        else:
                            variables["slot_choice_prefix"] = "Sure."
                            
                        return {"status": "SUCCESS", "outcome": "suggest_period_choices_loop", "is_bridge": True}
                    else:
                        selected_slot = available_slots[0]
                        variables["confirmed_date"] = f"{format_date_full(target_date)} at {selected_slot}"
                        variables["confirmed_time_only"] = selected_slot
                        return {"status": "SUCCESS", "outcome": "accepted", "is_bridge": True}
                
                # --- [EDGE CASE: Maximum negotiations exceeded / Rejects everything] ---
                negotiation_count = int(variables.get("slot_negotiation_depth", 0)) + 1
                variables["slot_negotiation_depth"] = negotiation_count
                if negotiation_count >= 4:
                    variables["callback_confirmation"] = "I will have our Service Desk call you back to coordinate a suitable time"
                    return {"status": "SUCCESS", "outcome": "max_rejections_escalate", "is_bridge": True}

                # If still unavailable, calculate alternates and continue loop
                alternates = manager.get_alternate_suggestions(target_date, target_period)
                alt_strings = []
                for d, t in alternates:
                    day_rel = "tomorrow" if d == datetime.now().date() + timedelta(days=1) else format_date_full(d)
                    alt_strings.append(f"{day_rel} at {t}")
                
                variables["alternate_suggestions_text"] = " or ".join(alt_strings)
                variables["alternate_suggestions_raw"] = [(d.strftime("%Y-%m-%d"), t) for d, t in alternates]
                variables["target_date_raw"] = target_date.strftime("%Y-%m-%d")
                variables["target_period"] = target_period
                
                return {"status": "SUCCESS", "outcome": "still_unavailable", "is_bridge": True}

        # [RECEPTION HARDENING] Explicitly handle flow routing
        if variables.get("flow_type") == "reception":
            print(f"[DEBUG] Reception Variables: {variables} | Node: {context.get('current_node_id')}")
            # If this is the first check (intent_check), we need intent detection, so we'll let it fall through
            
            # If we are capturing name
            if context.get("current_node_id") in ["capture_name_sales", "capture_name_service"]:
                name = last_msg.strip().title()
                if name and len(name.split()) <= 3: # Basic name validation
                    variables["name"] = name
                    female_names = ["sanjana", "priya", "anika", "kavita", "deepa", "shikha", "neha", "anjali", "sneha", "pooja", "maahi", "sanya", "ananya", "zoya", "ekta", "juhi", "ritu", "richa", "tanvi", "priti", "meera", "shalini"]
                    variables["salutation"] = "Ma'am" if name.lower() in female_names else "Sir"
                    return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            # If we are capturing registration number
            if context.get("current_node_id") == "capture_reg_service":
                # Look for alphanumeric patterns
                reg_match = re.search(r'[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}', last_msg.upper().replace(" ", ""))
                reg_no = reg_match.group(0) if reg_match else "".join(filter(str.isalnum, last_msg)).upper()
                
                if len(reg_no) >= 4 and any(char.isdigit() for char in reg_no):
                    variables["registration_number"] = reg_no
                    # [AUTHENTICATION FIX] Look up customer details if currently unknown
                    phone = variables.get("phone", "Unknown")
                    db = DatabaseManager()
                    try:
                        # Path for customers.json
                        base_dir = os.path.dirname(__file__)
                        customers_path = os.path.join(base_dir, "data", "customers.json")
                        with open(customers_path, "r") as f:
                            customers = json.load(f)
                        
                        clean_reg = reg_no.upper().replace(" ", "").replace("-", "")
                        clean_phone = "".join(filter(str.isdigit, phone))
                        if len(clean_phone) > 10: clean_phone = clean_phone[-10:]
                        
                        found_cust = None
                        for c in customers:
                            target_reg = "".join(filter(str.isalnum, c.get("registration_number", ""))).upper()
                            target_phone = "".join(filter(str.isdigit, c.get("phone", "")))
                            if len(target_phone) > 10: target_phone = target_phone[-10:]
                            
                            if (clean_reg in target_reg or target_reg in clean_reg) and (clean_phone == target_phone or phone == "Unknown"):
                                found_cust = c
                                break
                        
                        if found_cust:
                            print(f"[AUTH] Unknown caller identified as {found_cust['name']} via Reg: {reg_no}")
                            variables.update(found_cust)
                            variables["car"] = found_cust["car_model"]
                            variables["car_model"] = found_cust["car_model"]
                            print(f"[AUTH] Full metadata synced for {found_cust['name']}")
                    except Exception as e:
                        print(f"[AUTH ERROR] {e}")
                    
                    return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            # If we are checking service due status
            if context.get("current_node_id") == "service_due_path":
                is_due = variables.get("is_due", False)
                return {"status": "SUCCESS", "outcome": "true" if is_due else "false", "is_bridge": True}

            # [NEW] Capture Service Date
            if context.get("current_node_id") == "capture_date_service":
                parsed_date = parse_date_phrase(last_msg)
                if parsed_date:
                    date_str = format_date_full(parsed_date)
                    if "at" not in last_msg and "am" not in last_msg and "pm" not in last_msg:
                        date_str += " at 09:00 AM"
                    variables["confirmed_date"] = date_str
                    return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}
                else:
                    variables["confirmed_date"] = "tomorrow at 09:00 AM" # Fallback
                    return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            # [NEW] Capture Mileage
            if context.get("current_node_id") == "capture_mileage_service":
                digits = "".join(filter(str.isdigit, last_msg))
                if digits:
                    variables["mileage"] = digits
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            # [NEW] Capture Concerns
            if context.get("current_node_id") == "capture_concerns_service":
                if len(last_msg.split()) > 1:
                    variables["concerns"] = last_msg
                else:
                    variables["concerns"] = "General Checkup"
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            # [NEW] Pick and Drop Check
            if context.get("current_node_id") == "pick_drop_check":
                is_yes = any(word in last_msg for word in ["yes", "yeah", "sure", "definitely", "please", "valet"])
                variables["wants_valet"] = is_yes
                return {"status": "SUCCESS", "outcome": "true" if is_yes else "false", "is_bridge": True}

            # Handle name-known checks (sales_path, service_path)
            if context.get("current_node_id") in ["sales_path", "service_path"]:
                name = variables.get("name")
                is_known = name not in [None, "Customer", "Unknown"]
                return {"status": "SUCCESS", "outcome": "true" if is_known else "false", "is_bridge": True}

        # 1. Base Intent Detection (Use whole-word matching for accuracy)
        def check_word(word_list, text):
            for word in word_list:
                if any(ord(c) > 127 for c in word):
                    # Safe lookaround boundary for Devanagari combining characters
                    pattern = rf'(?<![a-zA-Z0-9\u0900-\u097F]){re.escape(word)}(?![a-zA-Z0-9\u0900-\u097F])'
                else:
                    pattern = rf'\b{re.escape(word)}\b'
                if re.search(pattern, text, re.I):
                    return True
            return False

        is_busy = check_word(['busy', 'meeting', 'later', 'call back', 'not now', 'driving', 'बिजी', 'व्यस्त', 'बाद में', 'बादमे', 'बाद में कॉल', 'बाद में बात'], last_msg)
        is_rejection = check_word(["no thanks", "dont need", "no interest", "not interested", "dont want", "not looking"], last_msg)
        is_wrong = check_word(["wrong number", "not me", "incorrect", "wrong person", "sold", "no longer have", "don't have that car"], last_msg)
        is_dnd = check_word(['stop', 'don\'t call', 'do not call', 'remove', 'dnd', 'annoying', 'not interested'], last_msg)
        is_angry = check_word(["terrible", "bad experience", "never calls", "complaint", "frustrated", "angry", "poor service", "repairs", "service center"], last_msg)
        is_distrustful = check_word(["scam", "how did you get", "privacy", "consent", "not shared", "number from"], last_msg)
        is_yes = check_word(["yes", "yeah", "correct", "yep", "speaking", "sure", "ok", "okay", "good", "satisfied", "proceed", "hello", "hi", "send", "share", "whatsapp", "bilkul", "हाँ", "हां", "हाँजी", "हांजी", "ठीक", "बोल रही हूँ", "बोल रही हो", "बोल रहा हूँ", "बोल रहा हो", "बोल रही हु", "बोल रहा हु", "आगे बढ़", "आगे बढ़", "aage badh", "aage badho", "aage badhiye", "aage bad", "aage badh sakti", "aage bad sakti", "badh sakti", "bad sakti", "policy renew", "renew kar", "रिन्यू कर", "पॉलिसी रिन्यू", "renew kar sakti", "रिन्यू कर सकती"], last_msg)
        is_no = check_word(["no", "nope", "dont", "don't", "not now", "stop", "not interested"], last_msg)
        is_passive = check_word(["haan", "hmm", "fine", "understood", "okay", "ok", "acha", "thik hai"], last_msg)
        is_transfer = check_word(['advisor', 'manager', 'person', 'human', 'specialist', 'connect', 'transfer', 'speak to someone'], last_msg)
        is_test_drive = check_word(["test drive", "drive", "check out", "see car", "experience"], last_msg)
        is_technical = check_word(["turbo", "engine", "bhp", "torque", "diesel", "petrol", "dct", "automatic", "manual", "transmission", "ivt", "specs"], last_msg)
        is_comparison = check_word(["kia", "tata", "maruti", "mahindra", "seltos", "astor", "safari", "harrier", "nexon", "compare", "better"], last_msg)
        
        # 2. Safety & Competitors (P0: Reduce Fallback)
        target_model = variables.get("car", "Creta")
        # Robust Normalization: Handle "Hyundai Creta" -> "Creta"
        car_cap = target_model.replace("Hyundai ", "").replace("hyundai ", "").capitalize()
        if "creta" in car_cap.lower(): car_cap = "Creta"
        if "venue" in car_cap.lower(): car_cap = "Venue"
        if "verna" in car_cap.lower(): car_cap = "Verna"
        if "tucson" in car_cap.lower(): car_cap = "Tucson"
        if "aura" in car_cap.lower(): car_cap = "Aura"
        
        # 2. Context & Vehicle Switching (Dynamic Entity Extraction)
        engine = context.get("intent_engine")
        switched = False
        if engine:
            extracted = engine.extract_data(last_msg)
            detected_model = extracted.get("model")
            if detected_model and detected_model != variables.get("car_model"):
                variables["car"] = detected_model.capitalize()
                variables["car_model"] = detected_model
                switched = True
                print(f"[CONTEXT SWITCH] AI detected switch to: {detected_model}")
        
        context_bridge = ""
        if switched:
            context_bridge = f"Sure! Let's talk about the {variables['car']} then. "
            # P0: Propagate immediately to intent engine context
            context["active_vehicle"] = variables["car"]

        # 3. Context Reinforcement (Memory)
        memory = variables.get("memory", {})
        
        # Gender/Salutation Detection
        gender_val = variables.get("gender")
        if gender_val == "female":
            salutation = "Ma'am"
        elif gender_val == "male":
            salutation = "Sir"
        else:
            name_val = str(variables.get("name", "Customer")).strip()
            name = name_val.split()[0] if name_val else "Customer"
            female_names = ["sanjana", "priya", "anika", "kavita", "deepa", "shikha", "neha", "anjali", "sneha", "pooja", "maahi", "sanya", "ananya", "zoya", "ekta", "juhi", "ritu", "richa", "tanvi", "priti", "meera", "shalini"]
            salutation = "Ma'am" if name.lower() in female_names else "Sir"
        variables["salutation"] = salutation
        
        # Log to console for transparency
        print(f"[AI ENGINE] Detected Salutation: {salutation} | Current Readiness: {variables.get('readiness_score', 10)}")
        
        if "loyalty" in last_msg or "years" in last_msg: memory["has_loyalty"] = True
        if "catch" in last_msg or "hidden" in last_msg or "fee" in last_msg: memory["transparency_concerned"] = True
        if "loan" in last_msg or "interest" in last_msg or "emi" in last_msg: memory["finance_focused"] = True
        variables["memory"] = memory

        # 4. Engagement & Buyer Readiness Pacing
        engagement = int(variables.get("engagement_depth", 0))
        if len(last_msg.split()) > 5: engagement += 1 
        variables["engagement_depth"] = engagement
        
        # Readiness Scoring: COLD (0-30) -> EVALUATING (31-60) -> READY (61+)
        readiness = int(variables.get("readiness_score", 10))
        if is_technical or is_test_drive or is_comparison: readiness += 20
        if is_yes: readiness += 10
        if is_no or is_rejection: readiness -= 10
        if is_passive: readiness += 2 # Slow crawl
        
        variables["readiness_score"] = max(0, min(100, readiness))
        if readiness > 70: variables["buyer_state"] = "READY"
        elif readiness > 30: variables["buyer_state"] = "EVALUATING"
        else: variables["buyer_state"] = "COLD"
        
        # 4. Intent Priority Hierarchy & Adaptive Pacing
        # Compliance Lock: If user already requested DND or expressed extreme distrust, block everything
        is_compliance_blocked = variables.get("disposition") == "DND_REQUESTED"
        
        # Strict DND or opt-out check: do not treat innocent trust queries as DND requests
        is_explicit_optout = any(word in last_msg for word in ["stop", "remove", "don't call", "do not call", "never", "dnd", "not interested", "opt out"])
        if is_dnd or (is_distrustful and is_explicit_optout):
            variables["lead_status"] = "NOT_INTERESTED"
            variables["disposition"] = "DND_REQUESTED"
            variables["lead_score"] = 0
            variables["sales_nudge_blocked"] = True
            self.db.update_lead_state(session_id, lead_status="NOT_INTERESTED", disposition="DND_REQUESTED")
            context["status"] = "COMPLETED"
            if variables.get("flow_type") == "insurance_start":
                curr_node = context.get("current_node_id")
                outcome = "wrong_number" if curr_node == "check_verification" else "dnd"
                return {
                    "status": "SUCCESS",
                    "outcome": outcome,
                    "logs": "Insurance DND routing to template handler",
                    "is_bridge": False
                }
            return {
                "status": "SUCCESS",
                "outcome": "mark_dnd",
                "text": f"I understand {salutation}. I'll make sure your number is removed from future promotional campaigns. Thank you for your time.",
                "logs": "Compliance: DND Lockdown",
                "is_bridge": False
            }
        
        if is_compliance_blocked:
            context["status"] = "COMPLETED"
            if variables.get("flow_type") == "insurance_start":
                curr_node = context.get("current_node_id")
                outcome = "wrong_number" if curr_node == "check_verification" else "dnd"
                return {
                    "status": "SUCCESS",
                    "outcome": outcome,
                    "logs": "Insurance DND blocked session routing",
                    "is_bridge": False
                }
            return {
                "status": "SUCCESS",
                "outcome": "mark_dnd",
                "text": "As requested, I'm marking your number for no further contact. Thank you.",
                "logs": "Compliance: Blocked Session",
                "is_bridge": False
            }

        # --- FEEDBACK FLOW ADAPTIVE CONDITION EXECUTOR ---
        if variables.get("flow_type") in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day"]:
            print(f"[DEBUG] Feedback Flow Adaptive Condition Check: '{condition}'. Input: '{last_msg}'")
            
            # --- FEEDBACK RATING VARIABLE EXTRACTION ---
            curr_node = context.get("current_node_id")
            if curr_node in ["check_advisor", "check_pickup", "check_cleanliness", "check_overall"]:
                def parse_rating(text):
                    text_lower = text.lower().strip()
                    digits = "".join(filter(str.isdigit, text_lower))
                    if digits:
                        val = int(digits)
                        if 1 <= val <= 10:
                            return val
                    word_map = {
                        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                        "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
                        "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10
                    }
                    for word, num in word_map.items():
                        if re.search(rf"\b{word}\b", text_lower) or word == text_lower:
                            return num
                    if any(w in text_lower for w in ["perfect", "great", "satisfied", "good", "excellent"]):
                        return 10
                    return 9
                
                rating_val = parse_rating(last_msg)
                var_map = {
                    "check_advisor": "advisor_rating",
                    "check_pickup": "pickup_rating",
                    "check_cleanliness": "cleanliness_rating",
                    "check_overall": "overall_rating"
                }
                var_name = var_map.get(curr_node)
                if var_name:
                    variables[var_name] = rating_val
                    print(f"[EXTRACT FEEDBACK RATING] {var_name} extracted: {rating_val} from '{last_msg}'")
            
            if condition in ["Consent/Identity Check", "identity_verified == true"]:
                # Check for complaints/issues first (priority over generic yes/speaking)
                complaint_words = ["issue", "issued", "noise", "problem", "unhappy", "bad", "worst", "complaint", 
                                   "brake", "engine", "cooling", "ac", "parts", "faulty", "defect", "damage", 
                                   "scratch", "vibration", "leak", "not satisfied", "not happy"]
                has_complaint = any(word in last_msg for word in complaint_words)
                
                if has_complaint:
                    print(f"[DEBUG] Feedback -> 'false' matched due to complaint/issue: '{last_msg}'")
                    return {"status": "SUCCESS", "outcome": "false", "is_bridge": True}
                
                if is_busy:
                    print(f"[DEBUG] Feedback -> 'busy' matched")
                    variables["lead_status"] = "WARM_LEAD"
                    variables["disposition"] = "BUSY_RETRY"
                    self.db.update_lead_state(session_id, lead_status="WARM_LEAD", disposition="BUSY_RETRY", last_action="Requested Callback")
                    return {"status": "SUCCESS", "outcome": "busy", "is_bridge": True}
                
                if is_no or is_rejection or is_dnd or is_wrong:
                    print(f"[DEBUG] Feedback -> 'false' matched")
                    return {"status": "SUCCESS", "outcome": "false", "is_bridge": True}
                
                if is_yes:
                    print(f"[DEBUG] Feedback -> 'true' matched")
                    return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}
                
                print(f"[DEBUG] Feedback -> fallback 'true' matched")
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            if condition == "satisfaction_check == true":
                is_satisfied = not (is_no or is_rejection or is_dnd or is_wrong or "not satisfied" in last_msg or "nahi" in last_msg or "no i am not" in last_msg)
                print(f"[DEBUG] Feedback -> satisfaction_check evaluated: {is_satisfied}")
                variables["satisfaction_check"] = is_satisfied
                return {"status": "SUCCESS", "outcome": "true" if is_satisfied else "false", "is_bridge": True}

            if condition == "continue == true":
                is_continue = is_yes and not is_no
                print(f"[DEBUG] Feedback -> continue evaluated: {is_continue}")
                variables["continue"] = is_continue
                return {"status": "SUCCESS", "outcome": "true" if is_continue else "false", "is_bridge": True}

        if is_angry:
            variables["sales_nudge_blocked"] = True 
            self.db.update_lead_state(session_id, lead_status="WARM_LEAD", disposition="SERVICE_COMPLAINT")
            return {
                "status": "SUCCESS", 
                "outcome": "direct_query", 
                "text": "I am truly sorry about your service center experience. I'll ensure this is escalated to our service manager immediately so we can fix this for you.",
                "logs": "Crisis Stabilization"
            }

        if is_technical:
            return {
                "status": "SUCCESS",
                "outcome": "direct_query",
                "text": f"The {variables['car']} comes in multiple engine options including the Turbo Petrol and Diesel. For a detailed variant comparison, I can connect you with our product specialist.",
                "logs": "Technical Query: Specialist Bridge"
            }

        if is_test_drive:
            variables["lead_status"] = "HOT_LEAD"
            variables["engagement_depth"] = engagement + 2
            return {
                "status": "SUCCESS",
                "outcome": "transfer", 
                "text": f"{context_bridge}Absolutely {salutation}. I can arrange a quick test drive for you. Let me connect you with our sales representative to finalize the preferred slot and location.",
                "logs": "HOT Lead: Professional Bypass"
            }

        if is_rejection:
            ack = f"That honestly says a lot about your experience with Hyundai {salutation}."
            return {
                "status": "SUCCESS", 
                "outcome": "direct_query", 
                "text": f"{ack} Most customers upgrading now are mainly looking for newer tech and features. If you'd like, I can have our sales advisor briefly explain what's changed in the latest model.",
                "logs": "Concise Objection Nurturing"
            }

        clean_msg = last_msg.strip(".,?! ")
        is_ambiguous = (len(clean_msg.split()) <= 1 and clean_msg in ["hmm", "fine", "understood", "okay", "ok", "haan"])
        is_family = any(word in clean_msg for word in ["wife", "husband", "spouse", "father", "parent", "family", "ask"])
        is_returning = context.get("is_returning_customer", False) or memory.get("previously_discussed")
        
        # 5. Priority Branching (Adaptive Logic)
        if is_returning and not variables.get("continuation_acknowledged"):
            variables["continuation_acknowledged"] = True
            prev_topic = memory.get("previously_discussed", "your vehicle upgrade")
            return {
                "status": "SUCCESS",
                "outcome": "direct_query",
                "text": f"Welcome back {salutation}! I'm glad we could connect again. Last time we were discussing {prev_topic}. Would you like to pick up where we left off or should I share the latest EMI updates for the {variables['car']}?",
                "logs": "Session Continuation"
            }

        if is_distrustful:
            return {
                "status": "SUCCESS", 
                "outcome": "direct_query", 
                "text": "I understand your concern. I am calling from the official Alcon Hyundai dealership. Would you like me to share our official location or should I mark your number as DND?",
                "logs": "Compliance: Trust Verification"
            }

        if is_family:
            variables["lead_status"] = "WARM_LEAD"
            variables["disposition"] = "FAMILY_CONSULTATION"
            self.db.update_lead_state(session_id, lead_status="WARM_LEAD", disposition="FAMILY_CONSULTATION")
            return {
                "status": "SUCCESS",
                "outcome": "schedule_callback", 
                "target_capability": "callback", # Dynamic jump target
                "text": f"Certainly {salutation}. I'll arrange a callback for you once you've had a chance to discuss it with your family. Have a great day!",
                "logs": "Professional Nurturing: Family Callback"
            }

        # Ambiguous check moved lower to prevent collision with yes/no

        if is_busy:
            variables["lead_status"] = "WARM_LEAD"
            variables["disposition"] = "BUSY_RETRY"
            variables["lead_score"] = 55
            self.db.update_lead_state(session_id, lead_status="WARM_LEAD", disposition="BUSY_RETRY", last_action="Requested Callback")
            if variables.get("flow_type") == "insurance_start":
                return {"status": "SUCCESS", "outcome": "busy"}
            if any(word in last_msg for word in ["evening", "later", "tomorrow", "after", "morning", "5", "6", "pm"]):
                return {
                    "status": "SUCCESS",
                    "outcome": "busy",
                    "target_capability": "callback", # Dynamic jump target
                    "text": f"No problem {salutation}. I'll have our representative call you back at your preferred time. Have a wonderful day!",
                    "is_bridge": True
                }
            return {"status": "SUCCESS", "outcome": "busy", "target_capability": "callback", "is_bridge": True}

        if is_rejection:
            ack = f"That makes complete sense {salutation}. Many long-term owners feel their current {variables['car']} is perfect."
            return {
                "status": "SUCCESS", 
                "outcome": "false", # Pivot to Service Bridge instead of exit
                "text": f"{ack} Since you're enjoying your current car, would you like to know about the current service benefits instead?",
                "logs": "Soft Objection Pivot"
            }

        if is_wrong: 
            self.db.update_lead_state(session_id, lead_status="NOT_INTERESTED", disposition="WRONG_NUMBER", last_action="Incorrect Person")
            mark_customer_dnd_permanent(variables.get("id"))
            self.log_transition(session_id, context.get("current_node_id"), "WRONG_DATA_EXIT", "Wrong person/sold car intent detected", raw_input=last_msg)
            context["status"] = "COMPLETED"
            return {"status": "SUCCESS", "outcome": "wrong_number", "text": "I apologize for the confusion. I'll update our records to ensure you're not contacted again regarding this vehicle. Have a wonderful day!", "logs": "User intent: WRONG_NUMBER", "is_bridge": False}

        is_transfer = any(word in last_msg for word in ['advisor', 'manager', 'person', 'human', 'specialist', 'connect', 'transfer', 'speak to someone', 'sales', 'representative', 'executive'])
        if is_transfer or "connect" in last_msg or "transfer" in last_msg: 
            self.db.update_lead_state(session_id, lead_status="NEGOTIATING", lead_score=85, disposition="TRANSFER_REQUESTED", last_action="Requested Human Expert", escalation_status="IN_PROGRESS", escalation_reason="MANUAL_REQUEST")
            self.log_transition(session_id, context.get("current_node_id"), "TRANSFER_EXIT", "Manual transfer request detected", raw_input=last_msg)
            return {"status": "SUCCESS", "outcome": "transfer", "is_bridge": True, "logs": "User intent: TRANSFER"}
        
        if is_wrong:
            context["status"] = "COMPLETED"
            return {"status": "SUCCESS", "outcome": "wrong_number", "logs": "User intent: WRONG_NUMBER", "is_bridge": False}

        is_thinking = any(word in last_msg for word in ['thinking', 'consider', 'not sure', 'decide', 'later', 'review'])
        if is_thinking: 
            self.db.update_lead_state(session_id, lead_status="WARM_LEAD", lead_score=55, disposition="THINKING", last_action="Needs time to think")
            return {"status": "SUCCESS", "outcome": "thinking", "logs": "User intent: THINKING"}

        if is_dnd: 
            self.db.update_lead_state(session_id, lead_status="DND", lead_score=0, disposition="REJECTED", last_action="Explicit Rejection", next_step="Manual Review")
            mark_customer_dnd_permanent(variables.get("id"))
            context["status"] = "COMPLETED"
            if variables.get("flow_type") == "insurance_start":
                curr_node = context.get("current_node_id")
                outcome = "wrong_number" if curr_node == "check_verification" else "dnd"
                return {"status": "SUCCESS", "outcome": outcome, "logs": "Insurance DND routing", "is_bridge": False}
            return {"status": "SUCCESS", "outcome": "dnd", "logs": "User intent: DND", "is_bridge": False}

        # --- PRE-SALES: Service Bridge Pivot ---
        if condition == "Service Bridge Eligibility":
            is_due = variables.get("is_due", False)
            return {"status": "SUCCESS", "outcome": "is_due" if is_due else "not_due"}
        
        # --- PRE-SALES: Competitor Check (P0 Priority) ---
        if is_comparison:
            return {"status": "SUCCESS", "outcome": "direct_query"} # Let KB Handler deal with the specifics

        # --- PRE-SALES: Persona-Aware Query Bridges ---
        if any(word in last_msg for word in ["catch", "hidden", "fee", "loyalty", "bonus", "years", "price", "cost", "emi", "finance"]):
            variables["is_major_query"] = True # Flag for proactive escalation
            
            intent_type = "general"
            if "loyalty" in last_msg or "years" in last_msg: intent_type = "loyalty"
            elif "catch" in last_msg or "hidden" in last_msg or "fee" in last_msg: intent_type = "transparency"
            elif "emi" in last_msg or "finance" in last_msg or "price" in last_msg: intent_type = "finance"
            
            ack_intents = variables.get("acknowledged_intents", [])
            if intent_type not in ack_intents:
                if intent_type in ["finance", "transparency", "loyalty"]:
                    # P0: Silence standard bridges to avoid double-intros with IntentEngine
                    bridge = "" 
                    if intent_type == "loyalty":
                        bridge = "I see you've been a loyal Hyundai owner for years! "
                    
                    ack_intents.append(intent_type)
                    variables["acknowledged_intents"] = ack_intents
                    return {"status": "SUCCESS", "outcome": "direct_query", "text": bridge, "is_bridge": True}
            else:
                return {"status": "SUCCESS", "outcome": "direct_query"} # Skip redundant bridge

        # --- PRE-SALES: Consent Check ---
        if condition in ["Consent/Identity Check", "identity_verified == true"]:
            if variables.get("flow_type") in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day"]:
                print(f"[DEBUG] Feedback Flow Consent/Performance Check. Input: '{last_msg}'")
                if is_busy:
                    print(f"[DEBUG] Feedback -> 'busy' matched")
                    return {"status": "SUCCESS", "outcome": "busy", "is_bridge": True}
                if is_no or is_rejection or is_dnd or is_wrong:
                    print(f"[DEBUG] Feedback -> 'false' matched")
                    return {"status": "SUCCESS", "outcome": "false", "is_bridge": True}
                if is_yes:
                    print(f"[DEBUG] Feedback -> 'true' matched")
                    return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}
                print(f"[DEBUG] Feedback -> fallback 'true' matched")
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            # 1. Use the unified IntentEngine for explain_decision (negation aware)
            engine = context.get("intent_engine")
            if engine:
                trace = engine.explain_decision(last_msg)
                decision = trace["decision"]
                
                # Audit Log for Intent Classification
                self.log_transition(
                    session_id, 
                    context.get("current_node_id"), 
                    "ConditionEvaluation", 
                    "Intent classification", 
                    raw_input=last_msg, 
                    intent=decision, 
                    confidence=trace.get("sentiment_score", 1.0)
                )

                # P0: Normalize model context (e.g. 'Hyundai Creta' -> 'creta')
                model_ctx = str(variables.get("car_model", "creta") or "creta").lower()
                if "creta" in model_ctx: model_ctx = "creta"
                elif "venue" in model_ctx: model_ctx = "venue"
                elif "verna" in model_ctx: model_ctx = "verna"
                elif "tucson" in model_ctx: model_ctx = "tucson"
                elif "aura" in model_ctx: model_ctx = "aura"

                # Special: If user asks a question instead of saying yes/no, jump to query path IMMEDIATELY
                # This prevents the 'gatekeeping' behavior where AI says 'I can help' but doesn't answer.
                if context.get("query_handled_this_turn"):
                    is_query_loop = "query_loop" in context.get("current_node_id", "")
                    return {
                        "status": "SUCCESS",
                        "outcome": "query" if is_query_loop else "true",
                        "is_bridge": True,
                        "logs": "Query already handled in this turn, skipping text duplication"
                    }
                query_response = engine.handle_query(last_msg, info=engine.kb.get("models", {}).get(model_ctx, {}), variables=variables)
                if query_response:
                    # P0 FIX: Record this intent as acknowledged so MessageNodes can filter it out
                    intent = query_response.get("intent")
                    print(f"[DEBUG] Query Response Intent: {intent} | Text: {query_response.get('text', '')[:30]}")
                    if intent:
                        ack_intents = variables.get("acknowledged_intents", [])
                        if intent not in ack_intents:
                            ack_intents.append(intent)
                            variables["acknowledged_intents"] = ack_intents

                    # We found an answer! 
                    # P0 FIX: If it's a transfer, jump to transfer outcome IMMEDIATELY
                    if intent == "transfer":
                         return {"status": "SUCCESS", "outcome": "transfer", "text": query_response["text"], "is_bridge": True}
                    
                    # P0 FIX: If it's a rejection, exit consent IMMEDIATELY
                    if intent == "rejection":
                         return {"status": "SUCCESS", "outcome": "false", "text": query_response["text"], "is_bridge": True}

                    # P0 FIX: For Query Loops, we MUST return 'query' outcome to match template edges
                    is_query_loop = "query_loop" in context.get("current_node_id", "")
                    return {
                        "status": "SUCCESS", 
                        "outcome": "query" if is_query_loop else "true",
                        "text": query_response["text"],
                        "is_bridge": True,
                        "logs": f"Direct Query Detected: {intent}"
                    }

                if decision == "HOT": 
                    # Silenced for reception to allow template to lead
                    if variables.get("flow_type") == "reception":
                        return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}
                    return {"status": "SUCCESS", "outcome": "true", "text": f"I can definitely help with that {salutation}! Let me give you the key details.", "is_bridge": True}
                if decision == "WARM":
                    if variables.get("flow_type") == "reception":
                        return {"status": "SUCCESS", "outcome": "busy", "is_bridge": True}
                    return {"status": "SUCCESS", "outcome": "busy", "text": f"I see. Would it be better if I call you back later when you have more time {salutation}?", "is_bridge": True}

                # [RECEPTION] Fallthrough for intent classification
                
                # Pivot to rejection/service bridge for COLD intents
                if decision == "COLD":
                    return {"status": "SUCCESS", "outcome": "false", "is_bridge": True}
                
                # Normal HOT/WARM path
                return {"status": "SUCCESS", "outcome": "true", "is_bridge": True}

            if is_busy: return {"status": "SUCCESS", "outcome": "busy"}
            if is_wrong: return {"status": "SUCCESS", "outcome": "wrong_number"}
            if is_dnd: return {"status": "SUCCESS", "outcome": "dnd"}
            if is_no: return {"status": "SUCCESS", "outcome": "false"}
            return {"status": "SUCCESS", "outcome": "unknown"}

        # --- PRE-SALES: Fallback Nudge Logic ---
        if condition == "Turn Nudge Logic":
            f_count = int(variables.get("fallback_count", 0))
            if f_count >= 3:
                return {"status": "SUCCESS", "outcome": "fallback", "logs": f"Fallback limit reached: {f_count}"}
            
            return {"status": "SUCCESS", "outcome": "first_fallback" if f_count <= 1 else "second_fallback"}

        # --- PRE-SALES: Query Intent Check ---
        if condition == "Query Intent Check":
            engine = context.get("intent_engine") # P0 FIX: Define engine to prevent UnboundLocalError
            
            # [RECEPTION FIX] Handle Callback/Busy request in reception flow (where callback capability is not defined in flow template)
            if variables.get("flow_type") == "reception" and (is_busy or any(word in last_msg for word in ["call back", "later", "tomorrow", "evening", "morning", "busy"])):
                return {
                    "status": "SUCCESS",
                    "outcome": "rejection",
                    "text": f"No problem {salutation}. I'll have our representative call you back at your preferred time. Have a wonderful day!",
                    "is_bridge": True
                }

            if is_no: return {"status": "SUCCESS", "outcome": "rejection", "text": "No problem at all. If you change your mind later, we're always here to help. Have a great day!", "is_bridge": True}
            if is_wrong: return {"status": "SUCCESS", "outcome": "wrong_number"}
            
            # [RECEPTION FIX] If user says yes to a transfer/callback offer, route accordingly
            has_offer = any(word in last_msg.lower() for word in ["yes", "yeah", "sure", "ok", "yep"])
            if has_offer:
                history = context.get("history", [])
                last_ai = [m for m in history if m.get("role") == "ai"]
                if last_ai:
                    ai_text = last_ai[-1].get("text", "").lower()
                    if "connect you" in ai_text or "advisor" in ai_text or "manager" in ai_text:
                        return {"status": "SUCCESS", "outcome": "transfer", "is_bridge": True}
                    if "call you back" in ai_text or "later" in ai_text:
                        return {"status": "SUCCESS", "outcome": "busy", "is_bridge": True}

            if is_passive and not any(word in last_msg.lower() for word in ["price", "emi", "insurance", "wait", "feature"]):
                return {
                    "status": "SUCCESS", 
                    "outcome": "false", # Pivot to 'no' path which is now 'end' OR stay
                    "text": f"Great {salutation}. Is there anything else I can clarify for you regarding your service or vehicle?",
                    "is_bridge": True # This will speak and then go to 'end' because e23_svc_rej_f target is 'end'
                }

            if any(word in last_msg for word in ["transfer", "specialist", "agent", "connect", "talk to", "manager", "representative", "sales", "executive"]):
                return {"status": "SUCCESS", "outcome": "transfer", "is_bridge": True}
            
            # P0: Normalize model context (e.g. 'Hyundai Creta' -> 'creta')
            model_ctx = variables.get("car_model", "creta").lower()
            if "creta" in model_ctx: model_ctx = "creta"
            elif "venue" in model_ctx: model_ctx = "venue"
            elif "verna" in model_ctx: model_ctx = "verna"
            elif "tucson" in model_ctx: model_ctx = "tucson"
            elif "aura" in model_ctx: model_ctx = "aura"
            
            if context.get("query_handled_this_turn"):
                return {"status": "SUCCESS", "outcome": "query", "is_bridge": True, "logs": "Query already handled in this turn"}
            model_info = engine.kb.get("models", {}).get(model_ctx, {}) if engine else {}
            query_response = engine.handle_query(last_msg, info=model_info, variables=variables) if engine else None
            if query_response:
                intent = query_response.get("intent")
                if intent == "transfer":
                    return {"status": "SUCCESS", "outcome": "transfer", "text": query_response["text"], "is_bridge": True}
                if intent == "rejection":
                    return {"status": "SUCCESS", "outcome": "rejection", "text": query_response["text"], "is_bridge": True}
                return {"status": "SUCCESS", "outcome": "query", "is_bridge": True}
            
            # Rejection / Transfer / Wrong Number / Callback Logic
            intent = IntroFlow.handle_identity_intent(last_msg)
            if intent == "BUSY": return {"status": "SUCCESS", "outcome": "busy", "target_capability": "callback", "is_bridge": True}
            if intent == "WRONG_NUMBER": return {"status": "SUCCESS", "outcome": "wrong_number"}
            if intent == "NO": return {"status": "SUCCESS", "outcome": "rejection"}
            
            # Explicit Callback request
            if any(word in last_msg for word in ["call back", "later", "tomorrow", "evening", "morning", "busy", "discuss", "family", "wife", "husband", "ask"]):
                return {"status": "SUCCESS", "outcome": "busy", "target_capability": "callback", "is_bridge": True}
            
            if any(word in last_msg for word in ["transfer", "manager", "representative", "specialist", "sales", "executive"]): 
                return {"status": "SUCCESS", "outcome": "transfer", "target_capability": "transfer", "is_bridge": True}

            # [RECEPTION HARDENING] Route unknown inputs as query rather than breaking
            return {"status": "SUCCESS", "outcome": "query", "is_bridge": True}

        if condition == "Feedback Capture":
            score = InsuranceFlow.handle_feedback(last_msg)
            variables["feedback_score"] = score
            variables["feedback_text"] = last_msg_raw # Raw user feedback
            
            # Route outcome dynamically based on the current call's branch/state
            disp = variables.get("disposition", "")
            status = variables.get("lead_status", "")
            if disp in ["DND_REQUESTED", "REJECTED"] or status in ["NOT_INTERESTED", "DND"]:
                return {"status": "SUCCESS", "outcome": "dnd"}
            elif disp in ["BUSY_RETRY", "CALLBACK_SCHEDULED"]:
                return {"status": "SUCCESS", "outcome": "busy"}
            else:
                return {"status": "SUCCESS", "outcome": "true"}

        if condition == "Transfer Consent Check":
            if is_yes: return {"status": "SUCCESS", "outcome": "true"}
            if is_no: return {"status": "SUCCESS", "outcome": "false"}
            return {"status": "SUCCESS", "outcome": "true"} # Default to true for transfer confirmation

        is_already_renewed = any(word in last_msg for word in ['already renewed', 'done already', 'renewed elsewhere'])
        if is_already_renewed: 
            variables["lead_status"] = "RENEWED"
            variables["disposition"] = "ALREADY_RECOVERED"
            variables["lead_score"] = 10
            self.db.update_lead_state(session_id, lead_status="RENEWED", disposition="ALREADY_RECOVERED", last_action="Renewed elsewhere")
            return {"status": "SUCCESS", "outcome": "already_renewed", "logs": "User intent: ALREADY_RENEWED"}

        is_comparison = any(word in last_msg for word in ['compare', 'other company', 'cheaper', 'expensive', 'policybazaar', 'acko', 'digit'])
        if is_comparison: 
            variables["lead_status"] = "NEGOTIATING"
            variables["lead_score"] = 80
            variables["disposition"] = "QUERY_COMPARISON"
            variables["last_action"] = "Requested Comparison"
            self.db.update_lead_state(session_id, lead_status="NEGOTIATING", lead_score=80, disposition="QUERY_COMPARISON", last_action="Requested Comparison")
            return {"status": "SUCCESS", "outcome": "comparison", "is_bridge": True, "logs": "User intent: COMPARISON"}

        try:
            if not condition:
                return {"status": "SUCCESS", "outcome": "false"}
            # [RECEPTION FIX] Make 'variables' available as a variable for template conditions
            eval_ctx = {**variables, "variables": variables, "true": True, "false": False}
            result = eval(condition, {"__builtins__": None}, eval_ctx)
            return {"status": "SUCCESS", "outcome": "true" if result else "false"}
        except:
            is_busy_phrase = any(word in last_msg for word in ["later", "busy", "callback", "busy now", "not now", "बिजी", "व्यस्त", "बाद में", "बादमे", "बाद में कॉल", "बाद में बात"])
            
            # Stage-dependent scoring
            current_stage = int(variables.get("stage", 1))
            interest_score = 70 if current_stage <= 3 else 55
            
            if is_busy_phrase:
                variables["lead_status"] = "WARM_LEAD"
                variables["lead_score"] = 40
                variables["disposition"] = "BUSY_RETRY"
                variables["last_action"] = "Interested but Busy"
                variables["next_step"] = "Wait"
                self.db.update_lead_state(session_id, lead_status="WARM_LEAD", lead_score=40, disposition="BUSY_RETRY", last_action="Interested but Busy", next_step="Wait")
                return {"status": "SUCCESS", "outcome": "busy"}

            if is_yes: 
                variables["lead_status"] = "WARM_LEAD"
                variables["lead_score"] = interest_score
                variables["disposition"] = "ANSWERED_INTERESTED"
                variables["last_action"] = "Requested Callback"
                variables["next_step"] = "Wait"
                self.db.update_lead_state(session_id, lead_status="WARM_LEAD", lead_score=interest_score, disposition="ANSWERED_INTERESTED", last_action="Requested Callback", next_step="Wait")
                return {"status": "SUCCESS", "outcome": "true"}
            if is_no: 
                variables["lead_status"] = "COLD_LEAD"
                variables["lead_score"] = 20
                variables["disposition"] = "REJECTED"
                variables["last_action"] = "Vague Rejection"
                variables["next_step"] = "Manual Review"
                self.db.update_lead_state(session_id, lead_status="COLD_LEAD", lead_score=20, disposition="REJECTED", last_action="Vague Rejection", next_step="Manual Review")
                return {"status": "SUCCESS", "outcome": "false"}

            # Standard Boolean Evaluation fallback
            try:
                result = eval(condition, {"__builtins__": None}, variables)
                return {"status": "SUCCESS", "outcome": "true" if result else "false"}
            except:
                pass

            return {"status": "SUCCESS", "outcome": "true" if is_yes else "false"}

class ApiNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        url = node_data.get("label", "")
        variables = context.get("variables", {})
        
        if "/mock/crm/" in url:
            # In simulation, customer data is already passed in variables
            return {"status": "SUCCESS", "logs": "CRM Lookup Simulation Complete", "is_bridge": True}
        return {"status": "SUCCESS", "logs": f"API call to {url} skipped", "is_bridge": True}

class ContextLogicNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        variables = context.get("variables", {})
        
        # --- PARITY: Pre-Normalize Placeholders ---
        # Ensure provider and car are normalized for template substitution
        if "insurance_provider" in variables:
            variables["provider"] = variables["insurance_provider"]
        if "car_model" in variables:
            variables["car"] = variables["car_model"]
        if "insurance_expiry_date" in variables:
            variables["expiry"] = variables["insurance_expiry_date"]
            variables["expiry_date"] = variables["insurance_expiry_date"]

        # Ensure safe defaults if these variables are missing from customer database (e.g. Sanya or Rohan)
        if "provider" not in variables or not variables.get("provider"):
            variables["provider"] = variables.get("insurance_provider") or "your current provider"
        if "car" not in variables or not variables.get("car"):
            variables["car"] = variables.get("car_model") or "vehicle"
        if "expiry" not in variables or not variables.get("expiry"):
            variables["expiry"] = variables.get("insurance_expiry_date") or "soon"

        expiry_date_str = variables.get("insurance_expiry_date") # From customers.json
        
        # Initialize defaults
        stage = 1
        msg = "calling to remind you that the insurance for your {{car}} is due for renewal on {{expiry}}. Your current policy is with {{provider}}. Are you planning to renew it with us this year?"
        
        # --- PARITY: Allow Simulator Override ---
        forced_stage = variables.get("stage")
        if forced_stage:
            try:
                stage = int(forced_stage)
                if stage == 1: msg = "Hello {{name}} {{salutation}}, I'm Supriya from Alcon. I'm calling to remind you that the insurance for your {{car}} is due for renewal on {{expiry}}. Your current policy is with {{provider}}. Are you planning to renew it with us this year?"
                elif stage == 2: msg = "Hello {{name}} {{salutation}}, this is Supriya from Alcon. I'm following up as you mentioned you were busy when we last spoke. Since we're now about two weeks away from your {{car}}'s insurance expiry, have you had a chance to review that loyalty offer?"
                elif stage == 3: msg = "Hello {{name}} {{salutation}}, Supriya here from Alcon again. I'm calling with an urgent reminder as your {{car}} insurance expires in just 7 days. I haven't heard back from you on the loyalty quote we shared. Shall we secure your No Claim Bonus today?"
                elif stage == 4: msg = "Good day {{name}} {{salutation}}. This is an urgent final call regarding your {{car}}. Your insurance expires tomorrow. I've secured a final spot for instant renewal to save your 50% No Claim Bonus. Shall I send the payment link to your WhatsApp?"
                elif stage == 5: msg = "Hello {{name}} {{salutation}}, I noticed that the insurance for your {{car}} has now expired. Driving without it is a major risk. I can still help you with a break-in policy today. Shall I connect you to our insurance desk to fix this immediately?"
                
                variables["stage"] = stage
                variables["greeting_context"] = msg
                return {"status": "SUCCESS", "logs": f"Forced Stage {stage} used"}
            except Exception as e:
                print(f"[BRIDGE DEBUG] forced_stage error: {e}")

        # --- PARITY: Pre-Sales Greeting Logic ---
        if variables.get("flow_type") in ["pre_sales", "pre_sales_upgrade"]:
            name_val = str(variables.get("name", "Customer")).strip()
            name = name_val.split()[0].title() if name_val else "Customer"
            first_name = name.lower()
            
            gender_val = variables.get("gender")
            if gender_val == "female":
                salutation = "Ma'am"
            elif gender_val == "male":
                salutation = "Sir"
            else:
                female_names = ["sanjana", "priya", "anika", "kavita", "deepa", "shikha", "neha", "anjali", "sneha", "pooja", "maahi", "sanya", "ananya", "zoya", "ekta", "juhi", "ritu", "richa", "tanvi", "priti", "meera", "shalini"]
                salutation = "Ma'am" if first_name in female_names else "Sir"
            
            car = variables.get("car_model", "vehicle")
            campaign = variables.get("campaign_type", "upgrade")
            age = variables.get("vehicle_age")
            
            msg = IntroFlow.get_greeting(salutation, name, car, campaign, vehicle_age=age)
            variables["greeting_context"] = msg
            variables["car"] = car
            variables["salutation"] = salutation
            return {"status": "SUCCESS", "logs": "Pre-Sales greeting calculated"}

        try:
            if expiry_date_str and expiry_date_str != "soon":
                expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                today = datetime.now().date()
                days_until = (expiry_date - today).days
                
                if days_until > 20: 
                    stage, msg = 1, "Hello {{name}} {{salutation}}, I'm Supriya from Alcon. I'm calling to remind you that the insurance for your {{car}} is due for renewal on {{expiry}}. Your current policy is with {{provider}}. Are you planning to renew it with us this year?"
                elif days_until > 10: 
                    stage, msg = 2, "Hello {{name}} {{salutation}}, this is Supriya from Alcon. I'm following up as you mentioned you were busy when we last spoke. Since we're now about two weeks away from your {{car}}'s insurance expiry, have you had a chance to review that loyalty offer?"
                elif days_until > 3: 
                    stage, msg = 3, "Hello {{name}} {{salutation}}, Supriya here from Alcon again. I'm calling with an urgent reminder as your {{car}} insurance expires in just 7 days. I haven't heard back from you on the loyalty quote we shared. Shall we secure your No Claim Bonus today?"
                elif days_until >= 0: 
                    stage, msg = 4, "Good day {{name}} {{salutation}}. This is an urgent final call regarding your {{car}}. Your insurance expires tomorrow. I've secured a final spot for instant renewal to save your 50% No Claim Bonus. Shall I send the payment link to your WhatsApp?"
                else: 
                    stage, msg = 5, "Hello {{name}} {{salutation}}, I noticed that the insurance for your {{car}} has now expired. Driving without it is a major risk. I can still help you with a break-in policy today. Shall I connect you to our insurance desk to fix this immediately?"
            
            variables["stage"] = stage
            variables["greeting_context"] = msg
            
            variables["stage"] = stage
            variables["greeting_context"] = msg
            
            return {"status": "SUCCESS", "logs": f"Stage {stage} calculated"}
        except Exception as e:
            print(f"[BRIDGE ERROR] Context Logic Failed: {e}")
            variables["stage"] = stage
            variables["greeting_context"] = msg
            return {"status": "SUCCESS", "logs": "Context logic fallback used"}

class DashboardBridgeNodeExecutor(NodeExecutor):
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        variables = context.get("variables", {})
        call_sid = context.get("session_id", "unknown")
        
        self.db.update_lead_state(call_sid, 
            lead_status=node_data.get("lead_status", "INTERESTED"),
            lead_score=int(node_data.get("lead_score", 50)),
            disposition=node_data.get("disposition", "ACTIVE_FLOW"),
            last_action=node_data.get("label", "Flow Step Update")
        )
        return {"status": "SUCCESS", "logs": "Dashboard Sync Complete"}

class ActionNodeExecutor(NodeExecutor):
    def __init__(self, db: DatabaseManager):
        self.db = db

    def log_transition(self, call_sid, prev_node, curr_node, reason, raw_input="", intent="", confidence=1.0):
        """Record a granular audit log of the orchestration transition."""
        try:
            conn = self.db._get_conn()
            cursor = conn.cursor()
            p = self.db.placeholder
            cursor.execute(f'''
                INSERT INTO orchestration_audit 
                (call_sid, previous_node, current_node, trigger_reason, raw_input, resolved_intent, confidence_score)
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p})
            ''', (call_sid, str(prev_node), str(curr_node), str(reason), str(raw_input), str(intent), float(confidence)))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[AUDIT ERROR] Failed to log transition: {e}")

    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action_type = node_data.get("action_type")
        variables = context.get("variables", {})
        session_id = context.get("session_id", "sim_session")
        
        if action_type == "log_consent":
            # Only set CONVERTED if we haven't already marked it as REJECTED, RENEWED, or BUSY
            current_status = variables.get("lead_status")
            if current_status not in ["RENEWED", "DND"]:
                variables["lead_status"] = "CONVERTED"
                variables["lead_score"] = 100
                variables["disposition"] = "ANSWERED_INTERESTED"
                variables["last_action"] = "Accepted Loyalty Offer"
                variables["next_step"] = "Payment Received"
                variables["policy_status"] = "PENDING_PAYMENT"
                self.db.update_lead_state(
                    session_id, 
                    lead_status="CONVERTED", 
                    lead_score=100, 
                    disposition="ANSWERED_INTERESTED", 
                    last_action="Accepted Loyalty Offer", 
                    next_step="Payment Received",
                    policy_status="PENDING_PAYMENT"
                )
            return {"status": "SUCCESS", "logs": "Session finalized"}
        
        if action_type == "schedule_callback":
            # 1. Advanced Idempotency Key (call_sid + action + normalized_time)
            normalized_time = "default" # Would be parsed from input in real scenario
            user_msgs = [m for m in context.get("history", []) if m.get("role") == "user"]
            user_input = user_msgs[-1].get("text", "") if user_msgs else ""
            
            # Extract formatted human date to store in session variables
            parsed_dt = parse_date_phrase(user_input)
            if not parsed_dt:
                parsed_dt = datetime.now().date() + timedelta(days=1)
                
            time_suffix = "11:00 AM"
            user_input_lower = user_input.lower()
            if "evening" in user_input_lower:
                time_suffix = "06:00 PM"
            elif "afternoon" in user_input_lower or "after noon" in user_input_lower:
                time_suffix = "02:00 PM"
            elif "morning" in user_input_lower:
                time_suffix = "10:00 AM"
            else:
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', user_input_lower)
                if time_match:
                    hh = int(time_match.group(1))
                    mm = time_match.group(2) or "00"
                    period = time_match.group(3).upper()
                    time_suffix = f"{hh:02d}:{mm} {period}"
            
            formatted_human = f"{format_date_full(parsed_dt)} at {time_suffix}"
            variables["callback_time"] = formatted_human
            variables["confirmed_date"] = formatted_human
            
            job_key = f"{session_id}_callback_{normalized_time}"
            
            variables["lead_status"] = "WARM_LEAD"
            variables["lead_score"] = 55
            variables["disposition"] = "BUSY_RETRY"
            variables["last_action"] = f"Scheduled Callback for {formatted_human}"
            variables["next_step"] = "Retry in 4 Hours"
            self.db.update_lead_state(
                session_id, 
                lead_status="WARM_LEAD", 
                lead_score=55, 
                disposition="BUSY_RETRY", 
                last_action=f"Scheduled Callback for {formatted_human}", 
                next_step="Retry in 4 Hours"
            )
            
            FollowupManager.record_callback(self.db, session_id, user_input, customer_id=variables.get("id", "Unknown"))
            
            return {"status": "SUCCESS", "logs": f"Callback scheduled (Key: {job_key})"}
            
        if action_type == "eval_escalation":
            # Adaptive Escalation Logic
            engagement = int(variables.get("engagement_depth", 0))
            is_major = variables.get("is_major_query", False)
            interest = variables.get("interest_level", "COLD")
            
            # QUALIFICATION LAYER: Don't escalate unless we have minimum engagement depth
            # UNLESS it's an explicit manual request or a HOT intent
            should_escalate = False
            if variables.get("escalation_offered_at"): return {"status": "SUCCESS", "outcome": "continue"} # Cooldown
            
            if interest == "HOT" and engagement >= 2:
                should_escalate = True
            elif is_major and engagement >= 3: # Major queries need a bit more depth before pushy escalation
                should_escalate = True
            
            if should_escalate:
                variables["escalation_offered_at"] = time.time()
                self.db.update_lead_state(session_id, lead_status="NEGOTIATING", escalation_status="IN_PROGRESS", disposition="QUALIFIED_ESCALATION")
                return {"status": "SUCCESS", "outcome": "offer_transfer"}
            
            return {"status": "SUCCESS", "outcome": "continue"}

        if action_type == "mark_dnd":
            variables["lead_status"] = "NOT_INTERESTED"
            variables["lead_score"] = 0
            variables["disposition"] = "REJECTED"
            variables["last_action"] = "Explicit Rejection"
            variables["next_step"] = "No Further Action"
            variables["policy_status"] = "REJECTED"
            self.db.update_lead_state(
                session_id, 
                lead_status="NOT_INTERESTED", 
                lead_score=0, 
                disposition="REJECTED", 
                last_action="Explicit Rejection",
                next_step="No Further Action",
                policy_status="REJECTED"
            )
            mark_customer_dnd_permanent(variables.get("id"))
            return {"status": "SUCCESS", "logs": "Marked as DND"}
            
        if action_type == "mark_renewed":
            variables["lead_status"] = "RENEWED"
            variables["lead_score"] = 10
            variables["disposition"] = "ALREADY_RENEWED"
            variables["last_action"] = "Already Renewed Externally"
            variables["next_step"] = "No Further Action"
            variables["policy_status"] = "RENEWED"
            self.db.update_lead_state(
                session_id, 
                lead_status="RENEWED", 
                lead_score=10, 
                disposition="ALREADY_RENEWED", 
                last_action="Already Renewed Externally",
                next_step="No Further Action",
                policy_status="RENEWED"
            )
            return {"status": "SUCCESS", "logs": "Marked as already renewed"}

        if action_type == "record_feedback_positive":
            variables["feedback_score"] = 5
            variables["feedback_text"] = "Car performing well"
            variables["lead_status"] = "COMPLETED"
            variables["disposition"] = "POSITIVE_FEEDBACK"
            self.db.update_lead_state(
                session_id, 
                lead_status="COMPLETED", 
                disposition="POSITIVE_FEEDBACK",
                feedback_score=5,
                feedback_text="Car performing well",
                last_action="Recorded positive 15-day feedback"
            )
            return {"status": "SUCCESS", "logs": "Recorded positive feedback"}
            
        if action_type == "record_feedback_negative":
            variables["feedback_score"] = 1
            variables["feedback_text"] = "Car not performing well"
            variables["lead_status"] = "NEGOTIATING"
            variables["disposition"] = "NEGATIVE_FEEDBACK"
            self.db.update_lead_state(
                session_id, 
                lead_status="NEGOTIATING", 
                disposition="NEGATIVE_FEEDBACK",
                feedback_score=1,
                feedback_text="Car not performing well",
                last_action="Recorded negative 15-day feedback"
            )
            return {"status": "SUCCESS", "logs": "Recorded negative feedback"}

        if action_type == "inc_query":
            variables["query_count"] = int(variables.get("query_count", 0)) + 1
            return {"status": "SUCCESS", "logs": f"Query count: {variables['query_count']}"}

        if action_type == "inc_fallback":
            variables["fallback_count"] = int(variables.get("fallback_count", 0)) + 1
            return {"status": "SUCCESS", "logs": f"Fallback count: {variables['fallback_count']}"}

        if action_type == "check_service_due":
            # [RECEPTION FIX] Use the registration-based customer if found, otherwise session-level
            last_date_str = variables.get("last_service_date")
            if not last_date_str:
                # Try to pull from authenticated customer data
                cust_id = variables.get("id")
                if cust_id and cust_id != "Unknown":
                    db = DatabaseManager()
                    # In a real scenario we'd query the DB or customers.json again
                    # But variables should already have it if found_customer_by_reg was called
                    pass

            last_date_str = last_date_str or "2024-01-01"
            try:
                last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
                # Use customer-specific interval or fallback to 6 months
                interval_months = int(variables.get("service_due_months", 6))
                due_date = last_date + timedelta(days=interval_months * 30) 
                variables["service_due_date"] = due_date.strftime("%d %B %Y")
                
                is_due = datetime.now().date() > due_date.date()
                variables["is_due"] = is_due
                print(f"[SERVICE CHECK] Last: {last_date_str} | Due: {variables['service_due_date']} | Is Due: {is_due}")
                return {"status": "SUCCESS", "outcome": "true" if is_due else "false"}
            except Exception as e:
                print(f"[SERVICE CHECK ERROR] {e}")
                variables["is_due"] = True # Fallback to assume due
                return {"status": "SUCCESS", "outcome": "true"}

        if action_type == "final_booking_sync":
            # 0. Consume Slot in mock slots.json
            try:
                date_str = variables.get("target_date_raw")
                time_str = variables.get("confirmed_time_only")
                if date_str and time_str:
                    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    adapter = MockJsonDMSAdapter()
                    adapter.book_slot(target_date, time_str)
                    print(f"[SLOT CONSUMED] {date_str} at {time_str}")
            except Exception as e:
                print(f"[SLOT CONSUME ERROR] {e}")

            # 1. Update Customer Record in data/customers.json (Mock)
            cust_id = variables.get("id")
            if cust_id and cust_id != "Unknown":
                try:
                    # Search multiple possible paths for customers.json
                    base_dir = os.path.dirname(__file__)
                    customers_path = os.path.join(base_dir, "data", "customers.json")
                    
                    with open(customers_path, "r") as f:
                        customers = json.load(f)
                    for c in customers:
                        if str(c.get("id")) == str(cust_id):
                            c["last_service_date"] = datetime.now().strftime("%Y-%m-%d")
                            c["notes"] = variables.get("concerns", "")
                            break
                    with open(customers_path, "w") as f:
                        json.dump(customers, f, indent=4)
                except Exception as e:
                    print(f"[BOOKING SYNC ERROR] Failed to update customers.json: {e}")

            # 2. Update Database Lead State
            self.db.update_lead_state(session_id, 
                lead_status="CONVERTED", 
                disposition="SERVICE_BOOKED", 
                last_action=f"Booked for {variables.get('confirmed_date', 'TBD')}"
            )

            # 3. Send Mock SMS
            print(f"\n[SMS SENT] To {variables.get('phone')}: Your service for {variables.get('car')} is confirmed for {variables.get('confirmed_date')}. Advisor: Amit Shah.\n")
            
            # 4. Determine outcome based on pick/drop choice
            outcome = "true" if variables.get("wants_valet", True) else "false"
            return {"status": "SUCCESS", "outcome": outcome, "is_bridge": True}

        if action_type == "transfer_sales":
            self.db.update_lead_state(session_id, lead_status="NEGOTIATING", disposition="TRANSFER_REQUESTED", last_action="Handed over to Manager")
            return {
                "status": "SUCCESS", 
                "outcome": "transferred", 
                "text": "Connecting you to our Sales Manager now. They will help you with the best offers and next steps. Thank you for speaking with Alcon!",
                "logs": "Sales Transfer Initiated"
            }

        if action_type == "validate_slot_request":
            
            # Reset slot negotiation depth and set a polite callback confirmation fallback
            variables["slot_negotiation_depth"] = 0
            variables["callback_confirmation"] = "I will have our Service Desk call you back to coordinate a suitable time"
            variables["slot_choice_prefix"] = "Sure."
            
            manager = SlotManager()
            user_input = variables.get("user_input", "") or context.get("user_input", "") or ""
            user_input_lower = user_input.lower().strip()
            
            # --- [EDGE CASE: Urgent Breakdown / Breakdown Support] ---
            if any(w in user_input_lower for w in ["breakdown", "accident", "emergency", "kharab", "accident ho gaya", "kam nahi kar rahi"]):
                return {
                    "status": "SUCCESS", 
                    "outcome": "breakdown_urgent", 
                    "text": "I'm so sorry to hear that you had a breakdown! Let me connect you immediately with our Roadside Assistance Desk for emergency support.",
                    "is_bridge": True
                }
                
            # --- [EDGE CASE: Earliest Available / Cancellation Slot] ---
            if any(w in user_input_lower for w in ["earliest", "cancellation", "first slot", "jaldi se jaldi", "pehle", "pehla", "cancellation slot"]):
                target_date = datetime.now().date()
                # Scan next 10 days for first available slot
                for i in range(10):
                    curr = target_date + timedelta(days=i)
                    slots = manager.adapter.get_available_slots(curr)
                    if slots:
                        variables["target_date_raw"] = curr.strftime("%Y-%m-%d")
                        variables["confirmed_date"] = f"{format_date_full(curr)} at {slots[0]}"
                        variables["confirmed_time_only"] = slots[0]
                        return {"status": "SUCCESS", "outcome": "available"}
            
            # Standard Date and Period Parsing
            target_date = parse_date_phrase(user_input) or datetime.now().date() + timedelta(days=1)
            requested_period = SlotParser.parse_time_period(user_input)
            specific_time = SlotParser.parse_specific_time(user_input)
            range_override = SlotParser.parse_vague_time(user_input)
            
            variables["target_date_raw"] = target_date.strftime("%Y-%m-%d")
            variables["target_period"] = requested_period
            
            # Determine relative day phrase
            today = datetime.now().date()
            if target_date == today:
                day_rel = "today"
            elif target_date == today + timedelta(days=1):
                day_rel = "tomorrow"
            else:
                day_rel = format_date_full(target_date)
            
            if requested_period:
                variables["requested_day_rel"] = f"{day_rel} {requested_period}"
            else:
                variables["requested_day_rel"] = day_rel
            
            available_slots = manager.find_slots_for_date_and_period(target_date, requested_period, range_override)
            
            if specific_time and specific_time in available_slots:
                variables["confirmed_date"] = f"{format_date_full(target_date)} at {specific_time}"
                variables["confirmed_time_only"] = specific_time
                return {"status": "SUCCESS", "outcome": "available"}
            elif not specific_time and available_slots:
                # If there are slots for this period, suggest them
                if len(available_slots) > 1:
                    variables["matching_period_slots_text"] = " and ".join(available_slots[:2])
                    return {"status": "SUCCESS", "outcome": "suggest_period_choices"}
                else:
                    selected_slot = available_slots[0]
                    variables["confirmed_date"] = f"{format_date_full(target_date)} at {selected_slot}"
                    variables["confirmed_time_only"] = selected_slot
                    return {"status": "SUCCESS", "outcome": "available"}
            
            # If completely unavailable, fetch alternatives
            alternates = manager.get_alternate_suggestions(target_date, requested_period)
            alt_strings = []
            for d, t in alternates:
                day_rel = "tomorrow" if d == datetime.now().date() + timedelta(days=1) else format_date_full(d)
                alt_strings.append(f"{day_rel} at {t}")
            
            variables["alternate_suggestions_text"] = " or ".join(alt_strings) or "next Monday at 09:00 AM"
            variables["alternate_suggestions_raw"] = [(d.strftime("%Y-%m-%d"), t) for d, t in alternates]
            
            return {"status": "SUCCESS", "outcome": "unavailable"}

        return {"status": "SUCCESS", "logs": f"Action {action_type} executed"}

class KnowledgeBaseNodeExecutor(NodeExecutor):
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.acknowledgments = {
            "finance": ["That's a fair point about the interest rates.", "I understand, finance is a key part of the decision.", "I can definitely clarify the EMI details for you."],
            "transparency": ["I appreciate your need for clarity on the costs.", "That's a valid question regarding the fees.", "I'll be very clear about the pricing for you."],
            "general": ["That's a good question.", "I see what you mean.", "Happy to help with that information."]
        }

    def get_ack(self, last_msg: str) -> str:
        if any(word in last_msg for word in ["interest", "rate", "loan", "emi", "finance"]): return random.choice(self.acknowledgments["finance"])
        if any(word in last_msg for word in ["catch", "hidden", "fee", "cost"]): return random.choice(self.acknowledgments["transparency"])
        return random.choice(self.acknowledgments["general"])

    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        variables = context.get("variables", {})
        session_id = context.get("session_id", "unknown")
        user_msgs = [m for m in context.get("history", []) if m.get("role") == "user"]
        last_msg = user_msgs[-1].get("text", "").lower().strip() if user_msgs else ""
        memory = variables.get("memory", {})
        answer = None
        
        # --- PRE-SALES & RECEPTION: Generic Intent Engine ---
        if variables.get("flow_type") in ["pre_sales", "pre_sales_upgrade", "reception"]:
            engine = context.get("intent_engine")
            if engine:
                # P0: Normalize model context (e.g. 'Hyundai Creta' -> 'creta')
                model_ctx = str(variables.get("car_model", "creta") or "creta").lower()
                if "creta" in model_ctx: model_ctx = "creta"
                elif "venue" in model_ctx: model_ctx = "venue"
                elif "verna" in model_ctx: model_ctx = "verna"
                elif "tucson" in model_ctx: model_ctx = "tucson"
                elif "aura" in model_ctx: model_ctx = "aura"

                model_info = engine.kb.get("models", {}).get(model_ctx, {})
                res = engine.handle_query(last_msg, info=model_info, variables=variables)
                
                if res:
                    # Record that a query has been successfully handled in this turn to prevent duplication
                    context["query_handled_this_turn"] = True
                    
                    # Record this intent as acknowledged so that CTAs and nudges can filter it out
                    intent = res.get("intent")
                    if intent:
                        ack_intents = variables.get("acknowledged_intents", [])
                        if intent not in ack_intents:
                            ack_intents.append(intent)
                            variables["acknowledged_intents"] = ack_intents

                    
                    # Direct transfer intent interception for both Sales and Service
                    if res.get("intent") == "transfer":
                        is_reception = variables.get("flow_type") == "reception"
                        is_service_node = "service" in str(context.get("current_node_id") or "").lower() or "svc" in str(context.get("current_node_id") or "").lower()
                        if is_reception and is_service_node:
                            transfer_msg = "Connecting you to our Service Advisor now. Please stay on the line."
                        else:
                            transfer_msg = "Connecting you to our Sales Manager now. They will help you with the best offers and next steps. Please stay on the line."
                        
                        return {
                            "status": "SUCCESS",
                            "outcome": "transferred",
                            "text": transfer_msg,
                            "logs": "KB Intent: Direct Call Transfer Requested"
                        }

                    # P0 FIX: Update vehicle context strictly if engine detects a switch
                    if res.get("model") and res["model"] != model_ctx:
                        variables["car_model"] = res["model"]
                        variables["car"] = res["model"].capitalize()
                        print(f"[CONTEXT SWITCH] Vehicle updated to: {res['model']}")
                    
                    # IntentEngine now handles its own intros/bridges for naturalness
                    final_response = res["text"]
                    
                    # 2. Adaptive Nudges (Sales Bridges)
                    # Deduplication: Avoid double bridges if engine already included one
                    sales_blocked = variables.get("sales_nudge_blocked", False)
                    has_bridge = any(word in final_response.lower() for word in ["connect", "advisor", "manager", "representative", "specialist"])
                    has_question = final_response.strip().endswith("?")
                    
                    # High-fidelity conversational pacing:
                    # Increment query counter and nudge the user to speak with our advisor after every 3 queries
                    # (3rd, 6th, 9th, etc.) to keep the dialogue clean and professional.
                    query_count = int(variables.get("query_count", 0)) + 1
                    variables["query_count"] = query_count
                    
                    if not sales_blocked and not has_bridge and not has_question:
                        if query_count % 3 == 0:
                            final_response += " Would you like to speak to our advisor?"
                    
                    return {
                        "status": "SUCCESS",
                        "outcome": "answered",
                        "text": final_response,
                        "logs": f"Adaptive KB Answered: {final_response[:30]}..."
                    }
                
                # P0 FIX: Silent Listener Recovery fallback in KB Executor
                salutation = variables.get("salutation", "Sir")
                clean_msg = last_msg.strip(".,?! ")
                is_ambiguous = (len(clean_msg.split()) <= 1 and clean_msg in ["hmm", "fine", "understood", "okay", "ok", "haan"])
                if is_ambiguous:
                    probe_count = int(variables.get("ambiguous_counter", 0)) + 1
                    variables["ambiguous_counter"] = probe_count
                    if probe_count <= 2:
                        return {
                            "status": "SUCCESS",
                            "outcome": "answered", # Stay in query loop
                            "text": f"I understand {salutation}. Would you like to know more about the features, pricing, or should I connect you with our advisor?",
                            "is_bridge": True,
                            "logs": "Ambiguous Input: Professional Probe"
                        }
                    else:
                        # Graceful exit after 3 probes for silent listeners
                        return {
                            "status": "SUCCESS",
                            "outcome": "no_match",
                            "text": f"I see you're probably busy right now {salutation}. I'll arrange a callback for later when it's more convenient. Have a great day!",
                            "logs": "KB Passive Recovery: Max Probes reached. Graceful exit."
                        }

                # [RECEPTION HARDENING] Conversational Fallback matching translation rules perfectly
                name_val = str(variables.get("name", "Customer")).strip()
                name = name_val.split()[0] if name_val else "Customer"
                car_name = variables.get("car", "vehicle")
                if variables.get("flow_type") == "reception":
                    is_service_node = "service" in str(context.get("current_node_id") or "").lower() or "svc" in str(context.get("current_node_id") or "").lower()
                    if is_service_node:
                        fallback_text = f"Thank you {name_val}. To proceed, could you please share your vehicle registration number?"
                    else:
                        fallback_text = f"Thank you {name_val}. Which model are you interested in today? I can help with pricing, features, or EMI details."
                else:
                    fallback_text = f"I can certainly clarify that for you {salutation}. Would you like to know more about the features, EMI options, pricing of the {car_name}, or should I connect you with our manager?"
                
                return {
                    "status": "SUCCESS",
                    "outcome": "answered",
                    "text": fallback_text,
                    "is_bridge": True,
                    "logs": "Unmatched query fallback"
                }
        
        elif variables.get("flow_type") in ["insurance", "insurance_start"]:
            # --- INSURANCE: Legacy KB (Fallback) ---
            # Use existing legacy logic for parity
            stage = int(variables.get("stage", 1))
            comparison_offered = variables.get("comparison_offered", False)
            
            is_renewed_stmt = any(word in last_msg for word in ['already renewed', 'done it', 'renewed already', 'got it from elsewhere', 'renewed elsewhere', 'done already'])
            if not is_renewed_stmt:
                answer = InsuranceFlow.handle_query(last_msg, variables, stage=stage, comparison_offered=comparison_offered)
            else:
                answer = None
        
        if answer:
            # PARITY: Track interest during query
            self.db.update_lead_state(session_id, lead_status="WARM_LEAD", lead_score=60, last_action="Inquired about details")

            # If it's a comparison offer, track it in variables
            if "ICICI Lombard" in answer or "partner rates" in answer:
                variables["comparison_offered"] = True

            # Trigger outbound comms flag if user asks for details on WhatsApp/payment link
            # or if the agent suggests sharing them on WhatsApp
            if "whatsapp" in last_msg or "whatsapp" in answer.lower() or "payment link" in last_msg or "secure payment" in answer.lower():
                print(f"[KB OUTBOUND TRIGGER] Setting trigger_outbound_comms to True in session variables")
                variables["trigger_outbound_comms"] = True
                
            # Escalation to Manager Transfer flow
            if "Insurance Manager" in answer:
                return {
                    "status": "SUCCESS",
                    "outcome": "manager_transfer",
                    "text": answer,
                    "logs": "Escalating to Manager Callback"
                }

            return {
                "status": "SUCCESS",
                "outcome": "answered",
                "text": answer,
                "logs": f"KB Answered: {answer[:30]}..."
            }
        
        return {"status": "SUCCESS", "outcome": "no_match"}

class PassThroughExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "SUCCESS", "logs": "Silent pass-through"}

class FlowRuntime:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.executors = {
            "startnode": PassThroughExecutor(),
            "messagenode": MessageNodeExecutor(),
            "conditionnode": ConditionNodeExecutor(db),
            "apinode": ApiNodeExecutor(),
            "contextlogicnode": ContextLogicNodeExecutor(),
            "dashboardbridgenode": DashboardBridgeNodeExecutor(db),
            "actionnode": ActionNodeExecutor(db),
            "knowledgebasenode": KnowledgeBaseNodeExecutor(db),
            "endnode": PassThroughExecutor()
        }

    async def execute_turn(self, flow: Dict[str, Any], session: Dict[str, Any]) -> List[str]:
        responses = []
        
        # 1. Index nodes for Semantic Routing (Manager's dynamic flow request)
        node_map = {n["id"]: n for n in flow["nodes"]}
        capability_map = {}
        for n in flow["nodes"]:
            # Priority: capability tag > label
            cap = n.get("data", {}).get("capability")
            if cap:
                cap_lower = cap.lower()
                if cap_lower == "query":
                    if "sales" in n["id"].lower():
                        capability_map["query_sales"] = n["id"]
                    elif "service" in n["id"].lower():
                        capability_map["query_service"] = n["id"]
                capability_map[cap_lower] = n["id"]
            
            label = n.get("data", {}).get("label")
            if label and label.lower() not in capability_map:
                capability_map[label.lower()] = n["id"]

            # Fallback by Node Type for seamless standard routing
            ntype = n["type"].lower()
            if ntype == "knowledgebasenode":
                if "sales" in n["id"].lower():
                    capability_map["query_sales"] = n["id"]
                elif "service" in n["id"].lower():
                    capability_map["query_service"] = n["id"]
                if "query" not in capability_map:
                    capability_map["query"] = n["id"]
            if ntype == "actionnode":
                if "callback" in n["id"].lower() and "callback" not in capability_map:
                    capability_map["callback"] = n["id"]
                elif "transfer" in n["id"].lower() and "transfer" not in capability_map:
                    capability_map["transfer"] = n["id"]

        print(f"[AGENT ROUTER] Capability Map: {list(capability_map.keys())}")

        # 2. Global Intent Interception (Prajyot's "Agent defines the flow" vision)
        variables = session.get("variables", {})
        user_input = (session.get("user_input") or "").lower().strip()
        is_reception_booking = (variables.get("flow_type") == "reception" and session.get("current_node_id") in [
            "ask_date", "capture_date_service", "collect_mileage", "capture_mileage_service",
            "ask_concerns", "capture_concerns_service", "pick_drop_offer", "pick_drop_check",
            "final_booking_sync", "confirm_valet", "confirm_self"
        ])
        if user_input and variables.get("flow_type") not in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day", "booking"] and not is_reception_booking:
            # Check for high-level jumps (Query, Callback, Transfer)
            # Use IntentEngine for complex detection if available
            engine = getattr(self, "intent_engine", None)
            if not engine:
                # Fallback to simple keyword detection
                engine = IntentEngine({}) # Mock
            
            # Use variables context if available
            variables = session.get("variables", {})
            model_ctx = variables.get("car_model", "creta")
            model_info = {} # We'll fetch this in the node, just checking intent here
            
            if variables.get("flow_type") in ["insurance", "insurance_start"]:
                stage = int(variables.get("stage", 1))
                comparison_offered = variables.get("comparison_offered", False)
                intent_res_text = InsuranceFlow.handle_query(user_input, variables, stage=stage, comparison_offered=comparison_offered)
                intent_res = {"text": intent_res_text, "intent": "query"} if intent_res_text else None
            else:
                intent_res = engine.handle_query(user_input, info=model_info, variables=variables)
            
            # Catch Identity/AI questions (Exclude rejections like "don't call")
            is_identity = any(word in user_input for word in ["who", "name", "ai", "real person", "bot"]) and "don't" not in user_input and "stop" not in user_input
            
            # [RECEPTION HARDENING] Predictive Shortcuts to bypass name prompts if user answers query late
            if variables.get("flow_type") == "reception":
                c_node = session.get("current_node_id")
                
                # Dynamic mid-query loop switching between sales and service loops:
                # If currently in service loop, and user asks a sales-focused question:
                if c_node in ["kb_handler_service", "service_query_loop"]:
                    is_sales_query = any(w in user_input for w in ["buy", "purchase", "car", "model", "price", "emi", "suv", "creta", "venue", "verna", "tucson", "aura", "exter", "grand i10", "i20", "exchange", "deal", "offer", "discount", "down payment", "waiting", "turbo", "cng", "colour", "color", "white", "black", "silver", "test drive", "loan", "dekhni", "kharidni"])
                    if is_sales_query:
                        print(f"[AGENT ROUTER] Mid-query loop switch: service loop -> sales loop")
                        session["current_node_id"] = "sales_query_loop"
                        c_node = "sales_query_loop"
                
                # If currently in sales loop, and user asks a service-focused question:
                elif c_node in ["kb_handler_sales", "sales_query_loop"]:
                    is_service_query = any(w in user_input for w in ["service package", "maintenance", "repair", "appointment", "pickup", "valet", "parts", "spare", "warranty", "servicing", "workshop"])
                    if is_service_query:
                        print(f"[AGENT ROUTER] Mid-query loop switch: sales loop -> service loop")
                        session["current_node_id"] = "service_query_loop"
                        c_node = "service_query_loop"
                
                if any(w in user_input for w in ["new car", "enquiry", "buy", "purchase", "showroom"]) and c_node in ["capture_name_service", "ask_name_service", "intent_check", "start", "service_path", "ask_reg_service", "capture_reg_service", "collect_mileage", "capture_mileage_service", "ask_concerns", "capture_concerns_service", "pick_drop_offer", "pick_drop_check"]:
                    print(f"[AGENT ROUTER] Shortcut to sales path from {c_node}")
                    session["current_node_id"] = "sales_path"
                elif any(w in user_input for w in ["service", "repair", "maintenance", "book a service"]) and c_node in ["capture_name_sales", "ask_name_sales", "intent_check", "start", "sales_path", "ask_model", "sales_query_loop"]:
                    print(f"[AGENT ROUTER] Shortcut to service path from {c_node}")
                    session["current_node_id"] = "service_path"

            
            # Catch Objections that should pivot to Callback
            is_objection = any(word in user_input for word in ["high price", "too expensive", "not now", "busy", "meeting", "discuss with family", "talk to family", "ask family", "ask my family", "consult my family"])
            
            kb_node = capability_map.get("query", "kb_handler")
            if variables.get("flow_type") == "reception":
                c_node = session.get("current_node_id") or ""
                if c_node in ["start", "init_context", "intent_check", "greeting"]:
                    # Analyze input text to route initial queries to the correct KB node
                    from flows.translation_utils import TranslationAdapter
                    normalized_input = TranslationAdapter.normalize_typos(user_input)
                    is_sales = any(w in normalized_input for w in ["buy", "purchase", "car", "model", "price", "emi", "suv", "creta", "venue", "verna", "tucson", "aura", "exchange", "deal", "offer", "discount", "down payment", "waiting", "turbo", "cng", "colour", "test drive", "loan", "dekhni", "kharidni", "nayi", "gadi", "gaadi", "puchtach", "नई", "नयी", "कार", "गाड़ी", "गाड़ी", "पूछताछ"])
                    is_service = any(w in normalized_input for w in ["service", "repair", "book", "appointment", "maintenance", "mileage", "advisor", "pickup", "valet", "parts", "kaam", "booking", "सर्विस", "बुकिंग", "रजिस्ट्रेशन", "नंबर"])
                    if is_service and not is_sales:
                        kb_node = capability_map.get("query_service", kb_node)
                    else:
                        # Default to sales for general queries during greeting
                        kb_node = capability_map.get("query_sales", kb_node)
                else:
                    is_sales_focused = any(x in str(c_node).lower() for x in ["sales", "model", "query_loop"]) and "service" not in str(c_node).lower()
                    if is_sales_focused:
                        kb_node = capability_map.get("query_sales", kb_node)
                    else:
                        kb_node = capability_map.get("query_service", kb_node)
            
            cb_node = capability_map.get("callback", "rejection_pivot")
            
            if is_objection and session.get("current_node_id") != cb_node and variables.get("flow_type") not in ["insurance", "insurance_start"]:
                print(f"[AGENT ROUTER] Objection detected. Pivoting to Callback.")
                session["current_node_id"] = cb_node
            elif (intent_res or is_identity) and session.get("current_node_id") not in [capability_map.get("query_sales"), capability_map.get("query_service"), kb_node]:
                print(f"[AGENT ROUTER] Global query/identity detected. Jumping to Knowledge Base.")
                session["current_node_id"] = kb_node
            elif any(word in user_input for word in ["transfer", "manager", "representative", "specialist"]):
                # P0: Exclude 'reception' from global jump to allow template-based data capture
                if variables.get("flow_type") != "reception":
                    print(f"[AGENT ROUTER] Global transfer request detected. Jumping to Transfer.")
                    session["current_node_id"] = capability_map.get("transfer", "transfer_node")
            # [INSURANCE SHORTCUT] If user explicitly requests quote on WhatsApp/link, jump straight to share_link_consent
            if variables.get("flow_type") in ["insurance", "insurance_start"]:
                stage = int(variables.get("stage", 1))
                comparison_offered = variables.get("comparison_offered", False)
                is_faq_query = InsuranceFlow.handle_query(user_input, variables, stage=stage, comparison_offered=comparison_offered)
                if not is_faq_query:
                    c_node = session.get("current_node_id") or ""
                    # Identity verification responses should not trigger the quote sharing shortcut
                    if c_node not in ["start", "crm_lookup", "verify_identity", "check_verification"]:
                        consent_intent = InsuranceFlow.handle_consent(user_input)
                        if consent_intent in ["INTERESTED", "INTERESTED_QUOTE_SHARED"] or any(word in user_input.lower() for word in ["whatsapp", "bhejo", "send", "share", "link"]):
                            if c_node not in ["final_processing", "collect_feedback", "log_success", "closing", "end"]:
                                print(f"[AGENT ROUTER] Direct WhatsApp/Link request. Jumping straight to share_link_consent.")
                                session["current_node_id"] = "share_link_consent"

        limit = 12
        count = 0
        while count < limit:
            current_node_id = session.get("current_node_id")
            print(f"[DEBUG] Current Node: {current_node_id} | Flow Type: {variables.get('flow_type')}")
            node = node_map.get(current_node_id)
            if not node:
                print(f"[FLOW ERROR] Node {current_node_id} not found")
                break
                
            # Suppress logs for cleaner output as requested
            executor = self.executors.get(node["type"].lower())
            if not executor:
                break
                
            print(f"[RUNTIME] Executing Node: {current_node_id} ({node['type']})")
            res = await executor.execute(node["data"], session)
            outcome = res.get("outcome")
            text = res.get("text")
            print(f"[RUNTIME] Node Result -> Outcome: {outcome}, Text: {text[:30] if text else 'None'}, Status: {session.get('status')}")
            if text: responses.append(text)

            # [NEW] Check for Terminal Status IMMEDIATELY after execution
            if node["type"].lower() == "endnode":
                session["status"] = "COMPLETED"
                break
            if outcome in ["transferred", "mark_dnd", "mark_renewed"]:
                session["status"] = "TRANSFER_REQUIRED" if outcome == "transferred" else "COMPLETED"
                break

            # --- DYNAMIC JUMP (Agent Routing) ---
            suggested_cap = res.get("target_capability")
            if suggested_cap and suggested_cap.lower() in capability_map:
                next_node_id = capability_map[suggested_cap.lower()]
                print(f"[DEBUG] Dynamic Jump detected to capability: {suggested_cap} -> {next_node_id}")
                session["current_node_id"] = next_node_id
                if res.get("is_bridge"): 
                    count += 1
                    continue
                else: break

            # Find edge based on outcome
            next_node_id = None
            default_edge = None
            print(f"[DEBUG] Searching edges for Node: {current_node_id} | Outcome: {outcome}")
            for edge in flow["edges"]:
                if edge["source"] == current_node_id:
                    handle = edge.get("sourceHandle")
                    if outcome and str(handle) == str(outcome):
                        next_node_id = edge["target"]
                        print(f"[DEBUG] Matched edge handle '{outcome}' -> {next_node_id}")
                        break
                    if not handle:
                        default_edge = edge["target"]
            
            if not next_node_id:
                next_node_id = default_edge
                if next_node_id:
                    print(f"[DEBUG] Default edge match -> {next_node_id}")
            
            # --- ORPHAN RECOVERY ---
            if not next_node_id and outcome:
                # Try direct capability match
                if outcome.lower() in capability_map:
                    target_id = capability_map[outcome.lower()]
                    # P0 FIX: Prevent self-referencing infinite loops
                    if target_id == current_node_id:
                        next_node_id = capability_map.get("query", "query_intent_check")
                    else:
                        next_node_id = target_id
                elif node["type"].lower() == "knowledgebasenode":
                    # KB nodes default back to query capability if outcome unhandled
                    next_node_id = capability_map.get("query", "query_intent_check")
                elif outcome == "busy" and "callback" in capability_map:
                    next_node_id = capability_map["callback"]
                elif outcome == "transfer" and "transfer" in capability_map:
                    next_node_id = capability_map["transfer"]

            if next_node_id:
                if next_node_id == current_node_id:
                    print(f"[FLOW ERROR] Infinite loop detected at {current_node_id}. Breaking.")
                    break
                session["current_node_id"] = next_node_id
                # Only continue looping if it's a bridge/passthrough node
                # P0 FIX: Prevent MessageNode auto-bridging (which skips user input), but allow bridging to endNode
                is_bridge = res.get("is_bridge") or node.get("data", {}).get("is_bridge") or node["type"].lower() in ["startnode", "contextlogicnode", "actionnode", "knowledgebasenode", "apinode", "conditionnode"]
                
                if node["type"].lower() == "messagenode":
                    for edge in flow["edges"]:
                        if edge["source"] == current_node_id:
                            target_node = node_map.get(edge["target"])
                            if target_node and target_node["type"].lower() in ["endnode", "actionnode", "contextlogicnode", "apinode"]:
                                is_bridge = True
                                break

                # Conversational turn pacing safety: If current node spoke text, and the next node is a ConditionNode, do NOT bridge.
                if res.get("text") and next_node_id and node_map.get(next_node_id, {}).get("type", "").lower() == "conditionnode":
                    is_bridge = False

                # Pacing safety: Avoid auto-bridging when transitioning to validate_slot_request or check_slot_action or from ask_date
                if next_node_id:
                    next_node = node_map.get(next_node_id, {})
                    next_action = next_node.get("data", {}).get("action_type") or next_node.get("data", {}).get("label")
                    if next_action == "validate_slot_request" or next_node_id == "check_slot_action" or current_node_id == "ask_date":
                        is_bridge = False

                print(f"[DEBUG] Next Node: {next_node_id} | Is Bridge: {is_bridge}")
                
                if is_bridge:
                    count += 1
                    continue
                else:
                    break
            else:
                # [NEW] If no next node and it's an endNode, it's a completion
                if node["type"].lower() == "endnode":
                    session["status"] = "COMPLETED"
                    return responses, session
                else:
                    print(f"[FLOW BREAK] No edge or dynamic target found for {current_node_id}")
                break
                
        # Universal Fallback to prevent Dead Air
        is_terminal = session.get("status") in ["COMPLETED", "TRANSFER_REQUIRED"]
        if not responses and not is_terminal:
            # P0: For reception flow, avoid aggressive fallback to allow logic steps
            if session.get("variables", {}).get("flow_type") == "reception":
                return responses, session
                
            salutation = session.get("variables", {}).get("salutation", "Sir")
            responses.append(f"I understand your point {salutation}. Let me connect you with our specialist who can assist you further with these details.")
            session["current_node_id"] = "transfer_node"
            session["status"] = "TRANSFER_REQUIRED"

        return responses, session

class OrchestrationBridge:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.runtime = FlowRuntime(db)
        self.templates_path = os.path.join(os.path.dirname(__file__), "..", "flow_orchestrator", "server", "templates")
        
        # Load KB for IntentEngine
        kb_path = os.path.join(os.path.dirname(__file__), "data", "kb.json")
        kb_data = {}
        if os.path.exists(kb_path):
            with open(kb_path, "r") as f:
                kb_data = json.load(f)
        self.intent_engine = IntentEngine(kb_data)

    def load_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.templates_path, f"{template_name}.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                return json.load(f)
        return None

    def log_transition(self, call_sid, prev_node, curr_node, reason, raw_input="", intent="", confidence=1.0):
        query = """
            INSERT INTO orchestration_audit 
            (call_sid, previous_node, current_node, trigger_reason, raw_input, resolved_intent, confidence_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        try:
            self.db.execute_query(query, (call_sid, str(prev_node), str(curr_node), str(reason), str(raw_input), str(intent), float(confidence)))
            print(f"[AUDIT] Logged transition for {call_sid}: {prev_node} -> {curr_node}")
        except Exception as e:
            print(f"[AUDIT ERROR] {e}")

    async def process_turn(self, call_sid: str, user_input: Optional[str], template_name: str, context: Dict[str, Any]):
        # Global Turn Entry Log
        self.log_transition(call_sid, context.get("current_node_id"), "ENTRY", "Processing Turn", raw_input=user_input)
        
        # Inject user_input into context for executors
        context["user_input"] = user_input
        
        flow = self.load_template(template_name)
        if not flow: return {"error": "Template not found"}

        history = context.get("history", [])
        if user_input:
            history.append({"role": "user", "text": user_input})

        # --- PARITY: Initial Status Check ---
        variables = context.get("variables", {})
        variables.pop("last_action", None)
        initial_last_action = None
        policy_status = str(variables.get("policy_status", "")).lower()
        if not user_input and policy_status in ["renewed", "already_renewed"]:
            salutation = "Ma'am" if variables.get("gender") == "female" else "Sir"
            car = variables.get("car_model", "vehicle")
            text = f"Hello {salutation}, I'm Supriya from Alcon. I noticed your {car} insurance is already renewed. That's great! Have a wonderful day."
            self.db.update_lead_state(call_sid, last_action="Acknowledge Renewal", lead_status="RENEWED", disposition="ALREADY_RENEWED")
            return {
                "text": text,
                "current_node_id": "end",
                "variables": variables,
                "history": history + [{"role": "ai", "text": text}],
                "status": "COMPLETED"
            }

        session = {
            "session_id": call_sid,
            "user_input": user_input,
            "current_node_id": context.get("current_node_id") or self._find_start_node(flow),
            "variables": variables,
            "history": history,
            "intent_engine": self.intent_engine, # Pass engine to executors
            "audit_logs": []
        }

        # --- SESSION CONTINUITY BYPASS ---
        # If this is a returning session with a known vehicle, skip intro/consent
        is_returning = context.get("is_returning_customer", False) or (variables.get("memory", {}).get("previously_discussed"))
        
        if is_returning and user_input and not context.get("current_node_id"):
            # Force jump to a direct query handling or main menu
            session["current_node_id"] = "intro_options" 
            print(f"[CONTINUITY] Resuming session for {call_sid} at node {session['current_node_id']}")
        
        # Ensure flow_type is in variables for executors
        if "flow_type" not in variables:
            variables["flow_type"] = context.get("flow_type", "pre_sales") # Default to pre_sales for this showcase

        ai_responses, session = await self.runtime.execute_turn(flow, session)
        
        # --- RESPONSE ORCHESTRATION LAYER ---
        seen_sentences = set()
        clean_responses = []
        has_bridge = False
        
        # Priority 1: Check if any response already contains a bridge/CTA
        for resp in ai_responses:
            if any(word in resp.lower() for word in ["connect", "advisor", "manager", "specialist", "call you"]):
                has_bridge = True
                break

        for resp in ai_responses:
            # Sentence-level deduplication
            sentences = re.split(r'\.(?!\d)', resp)
            for sentence in sentences:
                s = sentence.strip()
                if not s: continue
                
                # Deduplication
                if s.lower() in seen_sentences: continue
                
                # Naturalness: Remove generic intros if we are already in a deep query state
                if "let's talk about" in s.lower() and (variables.get("memory", {}).get("previously_discussed") or len(history) > 4):
                    continue
                
                # CTA Limiting: If we already have a bridge, remove generic "What would you prefer?"
                if has_bridge and "what would you prefer" in s.lower(): continue
                
                # Pacing: Limit to top 4 sentences for standard chats, or 6 for detailed feedback/insurance compliance to avoid overload
                is_feedback_or_insurance = (
                    variables.get("flow_type") in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day"] 
                    or str(variables.get("flow_type", "")).startswith("insurance")
                )
                max_sentences = 6 if is_feedback_or_insurance else 4
                if len(clean_responses) >= max_sentences: break

                clean_responses.append(s)
                seen_sentences.add(s.lower())
        
        final_text = ". ".join(clean_responses)
        if final_text and not final_text.endswith((".", "?", "!")):
            final_text += "."
        if final_text:
            history.append({"role": "ai", "text": final_text})

        # --- FEEDBACK FILE PERSISTENCE ---
        if variables.get("flow_type") in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day"] and session.get("current_node_id") == "end":
            try:
                base_dir = os.path.dirname(__file__)
                feedback_path = os.path.join(base_dir, "data", "post_service_feedback.json")
                
                feedback_list = []
                if os.path.exists(feedback_path):
                    with open(feedback_path, "r") as f:
                        try:
                            feedback_list = json.load(f)
                        except:
                            feedback_list = []
                
                if not any(f.get("call_sid") == call_sid for f in feedback_list):
                    entry = {
                        "call_sid": call_sid,
                        "customer_id": variables.get("id"),
                        "name": variables.get("name"),
                        "phone": variables.get("phone"),
                        "car_model": variables.get("car_model"),
                        "flow_type": variables.get("flow_type"),
                        "advisor_rating": variables.get("advisor_rating"),
                        "pickup_rating": variables.get("pickup_rating"),
                        "cleanliness_rating": variables.get("cleanliness_rating"),
                        "overall_rating": variables.get("overall_rating"),
                        "timestamp": datetime.now().isoformat()
                    }
                    feedback_list.append(entry)
                    with open(feedback_path, "w") as f:
                        json.dump(feedback_list, f, indent=4)
                    print(f"[FEEDBACK SYNC] Saved completed feedback to data/post_service_feedback.json: {entry}")
            except Exception as e:
                print(f"[FEEDBACK SYNC ERROR] Failed to save post_service_feedback.json: {e}")

        # --- PERSISTENCE LAYER: Save all stateful variables back to DB ---
        # Resolve a clean, human-readable Last Action based on the flow's current state and outcome
        resolved_action = None
        disp = variables.get("disposition", "")
        status = variables.get("lead_status", "")
        
        # Only treat last_action as a custom high-priority action if it was specifically set/updated during this turn
        custom_action = variables.get("last_action")
        if custom_action != initial_last_action and custom_action and not str(custom_action).startswith("AI Response"):
            resolved_action = custom_action
        else:
            if disp == "DND_REQUESTED" or status in ["NOT_INTERESTED", "DND"]:
                resolved_action = "Added to DND"
            elif disp == "REJECTED" or status == "COLD_LEAD":
                resolved_action = "Lead Declined Offer"
            elif disp in ["BUSY_RETRY", "CALLBACK_SCHEDULED"] or "Callback" in str(custom_action or ""):
                resolved_action = "Scheduled Callback"
            elif disp == "ANSWERED_INTERESTED" or status == "CONVERTED":
                resolved_action = "Accepted Renewal Offer"
            elif disp == "ALREADY_RENEWED" or status == "RENEWED":
                resolved_action = "Already Covered Elsewhere"
            elif disp == "QUERY_COMPARISON" or "Comparison" in str(custom_action or ""):
                resolved_action = "Requested Competitor Quote"
            elif disp == "SERVICE_BOOKED":
                resolved_action = "Service Booked"
            elif disp == "SERVICE_COMPLAINT" or status == "COMPLAINT":
                resolved_action = "Service Complaint Registered"
            elif disp == "POSITIVE_FEEDBACK":
                resolved_action = "Positive Feedback Recorded"
            elif disp == "NEGATIVE_FEEDBACK":
                resolved_action = "Negative Feedback Escalated"
            elif disp == "TRANSFER_REQUESTED" or "Manager" in str(custom_action or ""):
                resolved_action = "Transferred to Agent"
            elif "Transferred" in str(custom_action or ""):
                resolved_action = custom_action

        if not resolved_action:
            resolved_action = f"Discussing Details" if final_text else "AI Response"

        # Sync back to variables so it stays consistent
        variables["last_action"] = resolved_action

        self.db.update_lead_state(call_sid, 
            car=variables.get("car"),
            car_model=variables.get("car_model"),
            memory=variables.get("memory", {}),
            feedback_score=variables.get("overall_rating"),
            feedback_text=f"Advisor: {variables.get('advisor_rating')}, Pickup: {variables.get('pickup_rating')}, Cleanliness: {variables.get('cleanliness_rating')}",
            last_action=resolved_action
        )

        return {
            "text": final_text,
            "current_node_id": session["current_node_id"],
            "variables": session["variables"],
            "history": history,
            "status": session.get("status", "ACTIVE")
        }

    def sync_process_turn(self, *args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.process_turn(*args, **kwargs))
                    return future.result()
        except RuntimeError: pass
        return asyncio.run(self.process_turn(*args, **kwargs))

    def _find_start_node(self, flow: Dict[str, Any]) -> str:
        for node in flow.get("nodes", []):
            if node["type"] == "startNode": return node["id"]
        return flow["nodes"][0]["id"] if flow.get("nodes") else "unknown"
