import os
import json
import re
import hashlib
import sqlite3
import threading
import time
import copy
import urllib.parse
from datetime import datetime, date, timedelta
from async_utils import run_tracked_task
from twilio.twiml.voice_response import VoiceResponse, Gather, Redirect
from date_utils import parse_date_phrase, format_date_full
from database import DatabaseManager
from intent_engine import IntentEngine
from flows.intro_flow import IntroFlow
from flows.data_collection_flow import DataCollectionFlow
from flows.followup_manager import FollowupManager
from flows.service_bridge_flow import ServiceBridgeFlow
from flows.fallback_handler import FallbackHandler
from flows.insurance_flow import InsuranceFlow
from metrics_collector import metrics
from orchestration_bridge import OrchestrationBridge

class SessionManager:
    def __init__(self, ttl_seconds=900): # 15 minutes default
        self.sessions = {}
        self.lock = threading.Lock()
        self.ttl = ttl_seconds

    def get_session(self, session_id):
        with self.lock:
            session = self.sessions.get(session_id)
            if not session:
                return None
            
            # Check Expiry
            if time.time() - session.get("last_updated", 0) > self.ttl:
                del self.sessions[session_id]
                return None
            
            # Return deep copy for minimal lock scope processing
            return copy.deepcopy(session)

    def save_session(self, session_id, state):
        with self.lock:
            state["last_updated"] = time.time()
            self.sessions[session_id] = state

    def clear_session(self, session_id):
        with self.lock:
            if session_id in self.sessions:
                del self.sessions[session_id]

    def is_duplicate(self, session_id, step, user_input, session_obj=None):
        # Context-aware hash (step + input)
        input_hash = hashlib.md5(f"{step}:{user_input}".encode()).hexdigest()
        
        with self.lock:
            session = self.sessions.get(session_id)
            if not session: return False, None, 0
            
            if session.get("last_input_hash") == input_hash:
                # Increment duplicate count in memory
                dup_count = session.get("duplicate_count", 0) + 1
                session["duplicate_count"] = dup_count
                if session_obj is not None:
                    session_obj["duplicate_count"] = dup_count # Sync back to working object
                return True, session.get("last_response"), dup_count
            
            # Not a duplicate: Reset count
            session["duplicate_count"] = 0
            if session_obj is not None:
                session_obj["duplicate_count"] = 0
            return False, None, 0

    def update_last_response(self, session_id, step, user_input, response_data):
        input_hash = hashlib.md5(f"{step}:{user_input}".encode()).hexdigest()
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]["last_input_hash"] = input_hash
                self.sessions[session_id]["last_response"] = response_data

class FlowManager:
    def __init__(self, customers_file="data/customers.json"):
        self.customers_file = customers_file
        # Removed self.customers = self._load_customers() for memory efficiency
        self.slots = self._load_json("data/slots.json", {})
        self.advisors = self._load_json("data/advisors.json", [])
        self.kb = self._load_json("data/kb.json", {})
        self.sales_reps = self._load_json("data/sales_reps.json", [])
        self.static_prompts = self._load_json("data/static_prompts.json", {})
        self.leads_file = "data/leads.json"
        self.service_details_file = "data/service_details.json"
        self.service_details = self._load_json(self.service_details_file, {})
        self.service_status = self._load_json("data/service_status.json", [])
        self._last_db_time = 0 # Fallback for JSON ops
        self.last_rep_index = {"Sales": -1, "Service": -1} 
        self.prompt_cache = {} # Runtime cache for optimization tracking
        self.session_manager = SessionManager()
        self.db = DatabaseManager()
        self.intent_engine = IntentEngine(self.kb)
        self.orchestrator = OrchestrationBridge(self.db)
        
        self.use_insurance_template = os.getenv("USE_INSURANCE_TEMPLATE", "false").lower() == "true"
        self.use_pre_sales_template = os.getenv("USE_PRE_SALES_TEMPLATE", "false").lower() == "true"
        self.use_feedback_template = os.getenv("USE_FEEDBACK_TEMPLATE", "false").lower() == "true"
        self.use_booking_template = os.getenv("USE_BOOKING_TEMPLATE", "false").lower() == "true"
        self.transcript_accumulator = {} # In-memory transcript storage until call ends
        self._init_mappings()

    @property
    def last_db_time(self):
        # Combine last JSON operation time and last SQLite operation time
        return self._last_db_time + (self.db.last_op_time if hasattr(self.db, 'last_op_time') else 0)

    def _run_bg(self, func, *args, background_tasks=None, **kwargs):
        """Helper to run non-blocking tasks with lifecycle tracking."""
        # Convert function object to name for Redis serialization
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        if background_tasks:
            background_tasks.add_task(run_tracked_task, func_name, *args, **kwargs)
        else:
            # Fallback for non-FastAPI contexts (e.g. testing)
            # Since run_tracked_task is a synchronous function that pushes to Redis,
            # we can run it safely in a standard Python background thread.
            import threading
            threading.Thread(target=run_tracked_task, args=(func_name, *args), kwargs=kwargs, daemon=True).start()

    def _accumulate_transcript(self, call_sid, speaker, text, tags=None):
        """Internal helper for auditing."""
        if not text: return
        if call_sid not in self.transcript_accumulator:
            self.transcript_accumulator[call_sid] = []
        
        # Robust deduplication check to prevent duplicate transcript logging
        history = self.transcript_accumulator[call_sid]
        if history:
            last_entry = history[-1]
            if last_entry.get("speaker") == speaker and last_entry.get("text") == text:
                # Merge tags if they exist and are richer in the new call
                if tags:
                    existing_tags = set(last_entry.get("tags") or [])
                    for t in tags:
                        existing_tags.add(t)
                    last_entry["tags"] = list(existing_tags)
                return
                
        self.transcript_accumulator[call_sid].append({
            "speaker": speaker,
            "text": text,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat()
        })

    def calculate_lead_score(self, intent, session):
        """Dynamic scoring: base + urgency + recency"""
        base_scores = {
            "INTERESTED": 90,
            "INTERESTED_QUOTE_SHARED": 95,
            "INTERESTED_NEGOTIATING": 85,
            "CONVERTED": 100,
            "BUSY": 50,
            "REJECTED": 0,
            "ALREADY_RENEWED": 10,
            "UNKNOWN": 30
        }
        
        score = base_scores.get(intent, 0)
        
        # Urgency Bonus (Stage >= 3)
        stage = int(session.get("params", {}).get("stage", 1))
        if stage >= 3:
            score += 15 # More aggressive for demo
            
        # Recency Bonus (If this is a follow-up)
        if int(session.get("params", {}).get("stage", 1)) > 1:
            score += 5
            
        return min(score, 100)

    def _init_mappings(self):
        # UI State Mapping for the "Flow Explainer"
        self.ui_state_map = {
            "greeting": "Initial Greeting",
            "intro": "Service Check",
            "booking": "Selecting Date",
            "booking_mileage": "Vehicle Details",
            "booking_concerns": "Health Check",
            "booking_options": "Pick & Drop Options",
            "confirmed": "Service Confirmed",
            "feedback_consent": "Starting Feedback",
            "feedback_issue": "Performance Review",
            "feedback_advisor": "Rating Advisor",
            "feedback_pickup": "Rating Logistics",
            "feedback_overall": "Overall Experience",
            "reception_auth": "Customer Verification",
            "pre_sales_model": "Consulting on Models",
            "track_service_reg": "Status Tracking",
            "insurance_start": "Insurance Reminder",
            "insurance_consent": "Interest Check",
            "insurance_query": "Detailing Policy",
            "insurance_transfer_confirm": "Transfer Confirmation",
            "insurance_transfer": "Expert Hand-off"
        }
        
        self.VALID_TRANSITIONS = {
            "initiated": ["ringing", "failed", "no-answer"],
            "ringing": ["answered", "no-answer", "busy", "failed"],
            "answered": ["completed"],
            "no-answer": ["initiated", "failed"],
            "completed": ["end"]
        }

    def finalize_call(self, call_sid, transcript=None, session=None):
        """Finalize call and log history."""
        if not transcript and call_sid in self.transcript_accumulator:
            transcript = self.transcript_accumulator[call_sid]
        
        if not session:
            session = self.session_manager.get_session(call_sid)
        
        if transcript:
            # Resolve customer and stage from DB (including business status)
            conn = self.db._get_conn()
            cursor = self.db.get_cursor(conn)
            p = self.db.placeholder
            cursor.execute(f"""
                SELECT c.customer_id, c.stage, l.lead_status as status 
                FROM calls c
                LEFT JOIN lead_states l ON c.call_sid = l.call_sid
                WHERE c.call_sid = {p}
            """, (call_sid,))
            row = cursor.fetchone()
            conn.close()
            
            # PARITY FIX: If row is missing (e.g., race condition with background task), use session data
            if not row and session:
                row = {
                    "customer_id": session.get("customer_id"),
                    "stage": session.get("params", {}).get("stage", 1),
                    "status": session.get("params", {}).get("lead_status", "PENDING")
                }

            if row:
                fallback = any(msg.get("tags") and "ESCALATION" in msg["tags"] for msg in transcript)
                # Mock confidence: higher if no escalations
                confidence = 0.95 if not fallback else 0.75
                
                # --- [NEW] Compliance & Audit Calculation ---
                consent_taken = any(msg.get("tags") and "CONSENT_POSITIVE" in msg["tags"] for msg in transcript)
                dnd_respected = True # Logic: if they were called, we assume we checked DND (POC assumption)
                no_misrepresentation = True # AI guidelines enforced by deterministic logic
                
                # Disposition based compliance
                compliance_status = "PASSED"
                if fallback: 
                    compliance_status = "REVIEW_REQUIRED"
                if row["status"] == "REJECTED" and not dnd_respected:
                    compliance_status = "FAILED"

                feedback_score = session["params"].get("feedback_score", None) if session else None
                feedback_text = session["params"].get("feedback_text", "") if session else ""

                audit_summary = {
                    "consent_taken": consent_taken,
                    "dnd_respected": dnd_respected,
                    "no_misrepresentation": no_misrepresentation,
                    "feedback_score": feedback_score,
                    "feedback_text": feedback_text,
                    "audit_timestamp": datetime.now().isoformat()
                }

                self.db.log_call_history(
                    call_sid, 
                    row["customer_id"], 
                    row["stage"], 
                    transcript, 
                    row["status"],
                    fallback=fallback,
                    confidence=confidence,
                    compliance=compliance_status,
                    audit_summary=audit_summary
                )
            # del self.transcript_accumulator[call_sid]
            # To be safe, we'll keep it for the session TTL but log it now.
            
    def get_resume_greeting(self, session_id):
        """Generate a contextual greeting when AI resumes after a human handover."""
        session = self.session_manager.get_session(session_id)
        if not session:
            return {"text": "I'm back. How can I help you finish?", "next_step": "greeting"}

        customer_id = session.get("customer_id")
        customer = self.get_customer(customer_id)
        salutation = self._get_salutation(customer)
        
        # [NEW] Check for Agent Summary and Structured Data
        agent_summary = session["params"].get("agent_summary")
        pending_data = session["params"].get("pending_data")
        
        # [NEW] Validation & Conflict Detection (Scenario 3 & 5)
        validation = self._validate_handover_data(session_id, pending_data)
        
        # Determine specific resume text based on flow
        flow_type = session.get("flow_type", "booking")
        
        if flow_type == 'insurance_start' or flow_type == 'insurance_renewal':
            text = InsuranceFlow.get_contextual_resume(salutation, agent_summary, pending_data)
            
            # [SAFETY GATE] If sensitive updates were made, the AI MUST wait for Supervisor Sync
            disposition = session.get("disposition") or ""
            if validation["status"] == "REVIEW_REQUIRED" and "STATUS:SYNCED" not in disposition:
                # IMPORTANT: Mark the database so the Dashboard shows the "Approve & Sync" button
                self.db.update_lead_state(session_id, disposition="STATUS:REVIEW_REQUIRED")
                
                updates_ack = []
                if pending_data and isinstance(pending_data, dict):
                    if "premium" in pending_data: updates_ack.append(f"the premium discount")
                    if "nominee" in pending_data: updates_ack.append("the nominee change")
                
                ack_str = " and ".join(updates_ack) if updates_ack else "the discussed updates"
                
                # Update session to hold the AI here
                session["step"] = "insurance_consent" 
                self.session_manager.save_session(session_id, session)
                
                return {
                    "text": f"I've noted {ack_str}. I'll need to double-check the final quotation before we can process the link. One moment please.",
                    "next_step": "insurance_consent"
                }
            elif validation["status"] == "CONFLICT":
                text = "I understand add-on changes were discussed with our manager. Let me confirm the final coverage preferences with you before we proceed."
            elif pending_data and "premium" in pending_data:
                # Only show updated premium IF it's already synced or doesn't require review
                text = text.replace("finalize your renewal", f"finalize your renewal with the updated premium of ₹{pending_data['premium']}")
            
            next_step = "query_handler_2" if self.use_insurance_template else "insurance_consent"
            session["step"] = next_step
            if self.use_insurance_template:
                session["current_node_id"] = next_step
        else:
            text = f"I'm back now, {salutation}. Shall we continue where we left off?"
            if agent_summary:
                text = f"I understand from our manager that {agent_summary.replace('Summary:', '').strip()}. {text}"
            next_step = session.get("step", "greeting")

        # Clear summary after use
        session["params"]["agent_summary"] = None
        self.session_manager.save_session(session_id, session)
        
        return {
            "text": text,
            "next_step": next_step,
            "ui_state": "AI Resumed"
        }

    def _generate_fallback_summary(self, session_id):
        """Analyze the human interaction transcript to generate a natural summary."""
        transcript = self.transcript_accumulator.get(session_id, [])
        human_turns = [t for t in transcript if t.get("tags") and "HUMAN_OVERRIDE" in t["tags"]]
        
        if not human_turns:
            # Absolute fallback based on flow
            session = self.session_manager.get_session(session_id)
            flow_type = session.get("flow_type") if session else "booking"
            if flow_type == "insurance_start" or flow_type == "insurance_renewal":
                return "you were discussing the details of the loyalty quote with our manager"
            return "you were just finishing up the details with our representative"

        # Look for the last manager offer and last user agreement
        last_manager_msg = next((t["text"] for t in reversed(human_turns) if t["speaker"] == "Human"), "")
        last_user_msg = next((t["text"] for t in reversed(human_turns) if t["speaker"] == "Customer"), "")
        
        summary = "you were discussing the details with our manager"
        
        # Rule-based natural language generation
        if "discount" in last_manager_msg.lower() or "price" in last_manager_msg.lower() or "offer" in last_manager_msg.lower():
            if any(word in last_user_msg.lower() for word in ["ok", "works", "fine", "yes", "agree"]):
                summary = "you've agreed to the special discounted rate we discussed"
            else:
                summary = "you were exploring some better pricing options with our manager"
        elif "feature" in last_manager_msg.lower() or "safety" in last_manager_msg.lower():
            summary = "you were going over the specific features of the policy"
        elif last_manager_msg:
            # Fallback to a cleaner snippet
            clean_msg = last_manager_msg.split('.')[-1].strip() or last_manager_msg.split('.')[-2].strip() if '.' in last_manager_msg else last_manager_msg
            summary = f"you were discussing '{clean_msg}'"

        return summary

    def _validate_handover_data(self, session_id, data):
        """Production Safety Engine (Scenarios 3, 5, 8, 13)"""
        if not data:
            return {"status": "OK"}
            
        status = "OK"
        risk_flags = []
        
        # 1. Manual Data Change Check (Policy/Premium)
        if "premium" in data or "nominee" in data or "email" in data:
            print(f"[VALIDATOR] Manual data change detected. Marking for REVIEW.")
            status = "REVIEW_REQUIRED"
            risk_flags.append("MANUAL_UPDATE")
                
        # 2. Conflict Detection (Scenario 5)
        # Check if transcript contains "no" or "don't" regarding a feature the manager added
        transcript = self.transcript_accumulator.get(session_id, [])
        user_no_turns = [t["text"].lower() for t in transcript if t["speaker"] == "Customer" and ("no" in t["text"].lower() or "remove" in t["text"].lower())]
        
        if "add_addons" in data:
            for addon in data["add_addons"]:
                if any(addon.lower() in t for t in user_no_turns):
                    status = "CONFLICT"
                    risk_flags.append("CONTRADICTORY_UPDATE")

        # 3. Sensitive Field Check (Scenario 8)
        sensitive_fields = ["vehicle_owner", "nominee", "email", "phone"]
        if any(f in data for f in sensitive_fields):
            status = "REVIEW_REQUIRED"
            risk_flags.append("SENSITIVE_FIELD_MODIFICATION")

        return {"status": status, "flags": risk_flags}

    def _load_json(self, path, default):
        # Implementation of simple runtime cache to avoid I/O storms
        if not hasattr(self, '_file_cache'):
            self._file_cache = {}
        
        # We only cache 'static' files, not dynamic ones like leads or slots
        is_static = any(x in path for x in ["prompts", "kb", "advisors", "reps"])
        if is_static and path in self._file_cache:
            return self._file_cache[path]

        t_start = time.time()
        try:
            if os.path.exists(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    self._last_db_time = time.time() - t_start
                    if is_static:
                        self._file_cache[path] = data
                    return data
        except Exception as e:
            print(f"DEBUG: Error reading {path}: {e}")
        self._last_db_time = time.time() - t_start
        return default

    def _load_customers(self):
        with open(self.customers_file, "r") as f:
            return json.load(f)

    def get_customer(self, customer_id):
        if customer_id == "Unknown":
            return {"id": "Unknown", "name": "Unknown", "phone": "Unknown", "car_model": "Unknown"}
        if customer_id == "Multiple":
            return {"id": "Multiple", "name": "Valued Customer", "phone": "Unknown", "car_model": "our models"}
        
        # Memory-safe: Load only during search
        try:
            with open(self.customers_file, "r") as f:
                customers = json.load(f)
                return next((c for c in customers if c["id"] == customer_id), None)
        except:
            return None

    def find_customer_by_phone(self, phone: str):
        """Memory-safe phone lookup - returns all matches for disambiguation"""
        phone = phone.replace(" ", "").replace("-", "")
        matches = []
        try:
            with open(self.customers_file, "r") as f:
                customers = json.load(f)
                for c in customers:
                    if c["phone"].replace(" ", "").replace("-", "") == phone:
                        matches.append(c)
        except:
            pass
        return matches

    def find_customer_by_reg_and_phone(self, reg_no: str, phone: str):
        """Strict dual-factor authentication"""
        clean_reg = "".join(filter(str.isalnum, reg_no)).upper()
        clean_phone = "".join(filter(str.isdigit, phone))
        if len(clean_phone) > 10: clean_phone = clean_phone[-10:] # Last 10 digits
        
        try:
            with open(self.customers_file, "r") as f:
                customers = json.load(f)
                for c in customers:
                    target_reg = "".join(filter(str.isalnum, c.get("registration_number", ""))).upper()
                    target_phone = "".join(filter(str.isdigit, c.get("phone", "")))
                    if len(target_phone) > 10: target_phone = target_phone[-10:]
                    
                    # Match registration and phone
                    if (clean_reg in target_reg or target_reg in clean_reg) and clean_phone == target_phone:
                        return c
        except Exception as e:
            print(f"Error in find_customer_by_reg_and_phone: {str(e)}")
        return None

    def _get_salutation(self, customer):
        if not customer:
            return "Sir/Ma'am"
        return "Ma'am" if customer.get("gender") == "female" else "Sir"


    def get_service_status(self, customer):
        svc_status = customer.get("service_status")
        if svc_status in ["booked", "in-progress", "completed"]:
            return False, 0
            
        last_service = datetime.strptime(customer["last_service_date"], "%Y-%m-%d").date()
        today = date.today()
        
        delta = (today.year - last_service.year) * 12 + (today.month - last_service.month)
        is_due = delta >= customer["service_due_months"]
        return is_due, delta

    def _start_gather(self, response, step, customer_id, flow_type, timeout=5, extra_params=None, hints=None, call_sid=None):
        params = {
            "step": step,
            "customer_id": customer_id,
            "flow_type": flow_type
        }
        if extra_params:
            import json
            for k, v in extra_params.items():
                if isinstance(v, (list, dict)):
                    extra_params[k] = json.dumps(v)
            params.update(extra_params)
            
        query_string = urllib.parse.urlencode(params)
        action_url = f"/process?{query_string}"
        
        # Look up session language for speech recognition
        lang = "en-IN"
        if call_sid:
            session = self.session_manager.get_session(call_sid)
            if session:
                lang = session.get("params", {}).get("language", "en-IN")

        # Reduced speechTimeout from 1.2 to 1.0 for snappier responses
        gather = Gather(
            input='speech', 
            action=action_url, 
            method='POST', 
            timeout=timeout, 
            speechTimeout='1.0',
            hints=hints,
            language=lang
        )
        response.append(gather)
        response.redirect(action_url + "&retry=true")

    def _get_slots_for_date(self, target_date):
        date_str = target_date.strftime("%Y-%m-%d")
        slots = self.slots.get(date_str)
        if slots is None: # Not defined for this date
            return self.slots.get("default", [])
        return slots

    def _get_next_available_dates(self, count=2):
        today = date.today()
        found = []
        for i in range(1, 10):
            target = today + timedelta(days=i)
            slots = self._get_slots_for_date(target)
            if slots:
                found.append(target)
                if len(found) >= count: break
        return found

    def _consume_slot(self, target_date, slot_str):
        date_str = target_date.strftime("%Y-%m-%d")
        if date_str in self.slots:
            if slot_str in self.slots[date_str]:
                self.slots[date_str].remove(slot_str)
                def save_slots(data):
                    with open("data/slots.json", "w") as f:
                        json.dump(data, f, indent=4)
                
                self._run_bg(save_slots, self.slots, background_tasks=kwargs.get('background_tasks'))
                return True
        return False

    def _assign_advisor(self, concerns=""):
        specialty = "General Service"
        if any(word in concerns.lower() for word in ["engine", "transmission", "noise", "vibration", "starting"]):
            specialty = "Engine & Transmission"
        elif any(word in concerns.lower() for word in ["dent", "paint", "scratch", "accident"]):
            specialty = "Body & Paint"
            
        # PRODUCTION: Only assign 'available' advisors
        available_advisors = [a for a in self.advisors if a.get('status') == 'available']
        if not available_advisors:
            available_advisors = self.advisors # Fallback if all offline
            
        advisor = next((a for a in available_advisors if a['specialty'] == specialty), available_advisors[0])
        return advisor

    def _save_lead(self, phone, name, intent, model=None):
        try:
            leads = self._load_json(self.leads_file, [])
            new_lead = {
                "timestamp": datetime.now().isoformat(),
                "phone": phone,
                "name": name,
                "intent": intent,
                "model_of_interest": model,
                "status": "Captured"
            }
            leads.append(new_lead)
            def save_leads(data):
                with open(self.leads_file, "w") as f:
                    json.dump(data, f, indent=4)
            
            self._run_bg(save_leads, leads, background_tasks=kwargs.get('background_tasks'))
            print(f"Lead Saved: {name} ({phone}) for {intent}")
        except Exception as e:
            print(f"Error saving lead: {str(e)}")

    def _get_current_model(self, session, customer):
        """Robust model lookup from all sources with prefix cleaning."""
        model = session["params"].get("model") or \
                session["params"].get("car_model") or \
                (customer.get("car_model") if isinstance(customer, dict) else None) or \
                "car"
        
        # Clean prefix
        if "Hyundai " in str(model):
            model = model.replace("Hyundai ", "")
        return model

    def _transfer_call(self, response, department="Sales", call_sid=None, reason="MANUAL_REQUEST"):
        """Production skill-based routing with presence awareness."""
        from twilio.twiml.voice_response import Dial, Number
        
        # Log the reason to Database
        if call_sid:
            self.db.update_lead_state(call_sid, 
                escalation_status="IN_PROGRESS", 
                escalation_reason=reason,
                last_action=f"Transferred to {department}"
            )
        
        # Load available experts
        experts = self._load_json("data/advisors.json", [])
        
        # skill-based mapping
        if department == "Insurance Desk":
            reps = [a for a in self.advisors if a.get("specialty") == "Insurance Desk"]
        elif department == "Sales":
            reps = self.sales_reps
        else:
            reps = self.advisors
            
        if not reps:
            # Fallback to general advisors if specific department is empty
            reps = self.advisors
            
        if not reps:
            # Absolute fallback to supervisor number
            fallback_phone = "+919881012767"
            response.say(f"Our {department} team is currently busy assisting other customers. Let me connect you to our on-call supervisor.")
            response.dial(fallback_phone)
            return

        # [NEW] Presence Tracking: Filter only 'available' reps
        available_reps = [r for r in reps if r.get('status') == 'available']
        
        if not available_reps:
            # Fallback: Check if there's any manager phone number available
            from main import MANAGER_PHONE # circular import risk, but main.py imports this, so be careful
            # Better to use a static fallback or config
            fallback_phone = "+919881012767" 
            response.say(f"Our {department} team is currently busy assisting other customers. Let me connect you to our on-call supervisor.")
            response.dial(fallback_phone)
            return

        # Ensure we have a tracking index for this department
        if department not in self.last_rep_index:
            self.last_rep_index[department] = -1
            
        # Round-Robin Logic on available reps
        self.last_rep_index[department] = (self.last_rep_index[department] + 1) % len(available_reps)
        rep = available_reps[self.last_rep_index[department]]
        
        if rep and rep.get('phone'):
            response.say(f"Please wait while I connect you to {rep['name']} from our {department} team.")
            response.dial(rep['phone'])
        else:
            response.say(f"I'm sorry, I couldn't find an available representative. Someone will call you back shortly.")
            response.hangup()

    def _clean_text(self, text):
        """Final cleanup for a premium voice experience"""
        import re
        if not text: return ""
        # 1. Remove redundant prefix "stutters"
        text = re.sub(r'(starting at\s+)+', 'starting at ', text, flags=re.IGNORECASE)
        text = re.sub(r'(Starting from\s+)+', 'Starting from ', text, flags=re.IGNORECASE)
        text = re.sub(r'starting at\s+Starting from', 'starting from', text, flags=re.IGNORECASE)
        # 2. Fix punctuation (double periods, spaces before periods)
        text = text.replace("..", ".").replace(". .", ".").replace(" .", ".")
        # 3. Ensure single space between sentences
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def handle_query(self, text, model_context=None):
        return self.intent_engine.handle_query(text, model_context)

    def _say(self, response, text, logger=None, call_sid=None, speaker="Supriya", is_static=False):
        """Unified wrapper for saying text with logging and optional caching"""
        is_cached = text in self.prompt_cache
        if not is_cached:
            self.prompt_cache[text] = True
            
        if logger and call_sid:
            prefix = "[STATIC]" if is_static else ("[CACHED]" if is_cached else "")
            log_text = f"{prefix} {text}".strip()
            logger.log_event(call_sid, speaker, log_text, len(text))
            
            # Accumulate transcript for history log
            if call_sid not in self.transcript_accumulator:
                self.transcript_accumulator[call_sid] = []
            
            # Simple tagging for demo
            tags = []
            text_lower = text.lower()
            if "premium" in text_lower or "cost" in text_lower: tags.append("PRICE_INFO")
            if "comparison" in text_lower or "hdfc" in text_lower: tags.append("COMPARISON")
            if "manager" in text_lower or "transfer" in text_lower: tags.append("ESCALATION")
            
            self.transcript_accumulator[call_sid].append({
                "speaker": speaker,
                "text": text,
                "tags": tags,
                "timestamp": datetime.now().isoformat()
            })
        
        response.say(text)

    def log_attempt(self, call_sid, stage, outcome, retry_count=0, background_tasks=None):
        """Production Audit Logging"""
        self._run_bg(self.db.update_lead_state, call_sid, background_tasks=background_tasks, reasoning_trace={
            "attempt": {
                "stage": stage,
                "outcome": outcome,
                "retry_count": retry_count,
                "timestamp": datetime.now().isoformat()
            }
        })
        print(f"[AUDIT] Call {call_sid} | Stage {stage} | Outcome {outcome} | Retry {retry_count}")

    def handle_voice(self, customer_id, call_sid, flow_type="booking", logger=None, from_number="Unknown", background_tasks=None, **kwargs):
        """Twilio Entry Point - Adapter for Voice"""
        # Instrumentation: Record turn in background
        if background_tasks:
            background_tasks.add_task(metrics.record_request, call_sid, os.getpid())
        else:
            metrics.record_request(call_sid, os.getpid())
        # 1. Initialize Session (State ownership moves to backend)
        response = VoiceResponse()
        
        # Determine language
        lang = kwargs.get("language", "en-IN")
        
        session = {
            "step": "start",
            "flow_type": flow_type,
            "customer_id": customer_id,
            "params": {
                "phone": from_number,
                "language": lang
            }
        }
        # Capture any extra campaign info
        for k, v in kwargs.items():
            session["params"][k] = v
            
        self.session_manager.save_session(call_sid, session)

        # Dynamic Monkey-patching of VoiceResponse say method
        original_say = response.say
        def patched_say(text, *args, **kwargs_say):
            if lang == "hi-IN":
                from flows.translation_utils import TranslationAdapter
                translated = TranslationAdapter.translate_to_hindi(text)
                print(f"[MONKEY-PATCH SAY] Translating speech '{text}' -> '{translated}'")
                kwargs_say["language"] = "hi-IN"
                return original_say(translated, *args, **kwargs_say)
            else:
                return original_say(text, *args, **kwargs_say)
        response.say = patched_say
        
        # --- ORCHESTRATION BRIDGE: PRE-SALES & RECEPTION ---
        if self.use_pre_sales_template and flow_type in ["pre_sales", "reception", "pre_sales_upgrade"]:
            customer = self.get_customer(customer_id)
            is_due = False
            if customer and customer_id != "Unknown":
                is_due, _ = self.get_service_status(customer)
            
            name_obj = (customer.get("name") if customer else "Customer") or "Customer"
            name_str = str(name_obj).strip()
            name = name_str.split()[0] if name_str else "Customer"
            gender_val = customer.get("gender") if customer else None
            if gender_val == "female":
                salutation = "Ma'am"
            elif gender_val == "male":
                salutation = "Sir"
            else:
                female_names = ["sanjana", "priya", "anika", "kavita", "deepa", "shikha", "neha", "anjali", "sneha", "pooja", "maahi", "sanya", "ananya", "zoya", "ekta", "juhi", "ritu", "richa", "tanvi", "priti", "meera", "shalini"]
                salutation = "Ma'am" if name.lower() in female_names else "Sir"
            
            template_name = "inbound_receptionist" if flow_type == "reception" else "pre_sales_template"
            
            from date_utils import calculate_age
            reg_date = customer.get("registration_date") if customer else None
            age = calculate_age(reg_date) if reg_date else None
            vehicle_age = kwargs.get("vehicle_age") or age
            campaign_type = kwargs.get("campaign_type")
            if not campaign_type and vehicle_age is not None:
                campaign_type = "exchange" if vehicle_age >= 5 else "upgrade" if vehicle_age >= 3 else "emi_benefit"
            if not campaign_type:
                campaign_type = "upgrade"
            
            context = {
                "flow_type": flow_type,
                "variables": {
                    "id": customer_id,
                    "name": customer.get("name") if customer else "Customer",
                    "car_model": customer.get("car_model") if customer else "vehicle",
                    "car": customer.get("car_model") if customer else "vehicle", # Template uses {{car}}
                    "last_service_date": customer.get("last_service_date"),
                    "campaign_type": campaign_type,
                    "vehicle_age": vehicle_age,
                    "is_due": is_due,
                    "salutation": salutation,
                    **{k: v for k, v in customer.items() if k not in ["id", "name", "car_model", "last_service_date"]}
                }
            }
            res = self.orchestrator.sync_process_turn(call_sid, "", template_name, context)
            
            if res.get("text"):
                response.say(res["text"])
            
            # Persist orchestrator state to session manager
            session["current_node_id"] = res["current_node_id"]
            session["params"].update(res["variables"])
            self.session_manager.save_session(call_sid, session)
            
            log_text = res["text"]
            if lang == "hi-IN" and log_text:
                from flows.translation_utils import TranslationAdapter
                log_text = TranslationAdapter.translate_to_hindi(log_text)

            if logger:
                customer_data = self.get_customer(customer_id)
                c_id = customer_data['id'] if customer_data else "Unknown"
                c_name = customer_data['name'] if customer_data else "Unknown"
                c_phone = customer_data['phone'] if customer_data else from_number
                logger.start_call(call_sid, c_id, c_name, c_phone)
                logger.update_step(call_sid, "Sales Template")
                logger.log_event(call_sid, "Supriya", log_text, len(log_text or ""))
            
            self._accumulate_transcript(call_sid, "Supriya", log_text)
            self._start_gather(response, "continue", customer_id, flow_type, call_sid=call_sid)
            return str(response)

        # --- ORCHESTRATION BRIDGE: FEEDBACK ---
        if self.use_feedback_template and flow_type in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day"]:
            customer = self.get_customer(customer_id)
            name_obj = (customer.get("name") if customer else "Customer") or "Customer"
            name_str = str(name_obj).strip()
            name = name_str.split()[0] if name_str else "Customer"
            gender_val = customer.get("gender") if customer else None
            if gender_val == "female":
                salutation = "Ma'am"
            elif gender_val == "male":
                salutation = "Sir"
            else:
                female_names = ["sanjana", "priya", "anika", "kavita", "deepa", "shikha", "neha", "anjali", "sneha", "pooja", "maahi", "sanya", "ananya", "zoya", "ekta", "juhi", "ritu", "richa", "tanvi", "priti", "meera", "shalini"]
                salutation = "Ma'am" if name.lower() in female_names else "Sir"
            
            template_name = "post_service_feedback_15day" if flow_type == "feedback_15day_v2" else "post_service_feedback"
            service_date = customer.get("last_service_date", "recent date") if customer else "recent date"
            reg_no = customer.get("registration_number") or customer.get("reg_number") or "your vehicle" if customer else "your vehicle"
            
            context = {
                "flow_type": flow_type,
                "variables": {
                    "id": customer_id,
                    "name": name_obj,
                    "car_model": customer.get("car_model") if customer else "vehicle",
                    "car": customer.get("car_model") if customer else "vehicle",
                    "last_service_date": service_date,
                    "reg": reg_no,
                    "salutation": salutation,
                    "customer_care_number": "1800-123-4567",
                    **({k: v for k, v in customer.items() if k not in ["id", "name", "car_model", "last_service_date"]} if customer else {})
                }
            }
            res = self.orchestrator.sync_process_turn(call_sid, "", template_name, context)
            
            if res.get("text"):
                response.say(res["text"])
            
            session["current_node_id"] = res["current_node_id"]
            session["params"].update(res["variables"])
            self.session_manager.save_session(call_sid, session)
            
            log_text = res["text"]
            if lang == "hi-IN" and log_text:
                from flows.translation_utils import TranslationAdapter
                log_text = TranslationAdapter.translate_to_hindi(log_text)

            if logger:
                customer_data = self.get_customer(customer_id)
                c_id = customer_data['id'] if customer_data else "Unknown"
                c_name = customer_data['name'] if customer_data else "Unknown"
                c_phone = customer_data['phone'] if customer_data else from_number
                logger.start_call(call_sid, c_id, c_name, c_phone)
                logger.update_step(call_sid, "Feedback Template")
                logger.log_event(call_sid, "Supriya", log_text, len(log_text or ""))
            
            self._accumulate_transcript(call_sid, "Supriya", log_text)
            self._start_gather(response, "continue", customer_id, flow_type, call_sid=call_sid)
            return str(response)

        # --- ORCHESTRATION BRIDGE: SERVICE BOOKING ---
        if self.use_booking_template and flow_type == "booking":
            customer = self.get_customer(customer_id)
            name_obj = (customer.get("name") if customer else "Customer") or "Customer"
            name_str = str(name_obj).strip()
            name = name_str.split()[0] if name_str else "Customer"
            gender_val = customer.get("gender") if customer else None
            if gender_val == "female":
                salutation = "Ma'am"
            elif gender_val == "male":
                salutation = "Sir"
            else:
                female_names = ["sanjana", "priya", "anika", "kavita", "deepa", "shikha", "neha", "anjali", "sneha", "pooja", "maahi", "sanya", "ananya", "zoya", "ekta", "juhi", "ritu", "richa", "tanvi", "priti", "meera", "shalini"]
                salutation = "Ma'am" if name.lower() in female_names else "Sir"
            
            template_name = "service_booking_prod"
            service_date = customer.get("last_service_date", "recent date") if customer else "recent date"
            reg_no = customer.get("registration_number") or customer.get("reg_number") or "your vehicle" if customer else "your vehicle"
            
            context = {
                "flow_type": flow_type,
                "variables": {
                    "id": customer_id,
                    "name": name_obj,
                    "car_model": customer.get("car_model") if customer else "vehicle",
                    "car": customer.get("car_model") if customer else "vehicle",
                    "last_service_date": service_date,
                    "last_svc_formatted": service_date,
                    "reg": reg_no,
                    "salutation": salutation,
                    **({k: v for k, v in customer.items() if k not in ["id", "name", "car_model", "last_service_date"]} if customer else {})
                }
            }
            res = self.orchestrator.sync_process_turn(call_sid, "", template_name, context)
            
            if res.get("text"):
                response.say(res["text"])
            
            session["current_node_id"] = res["current_node_id"]
            session["params"].update(res["variables"])
            self.session_manager.save_session(call_sid, session)
            
            log_text = res["text"]
            if lang == "hi-IN" and log_text:
                from flows.translation_utils import TranslationAdapter
                log_text = TranslationAdapter.translate_to_hindi(log_text)

            if logger:
                customer_data = self.get_customer(customer_id)
                c_id = customer_data['id'] if customer_data else "Unknown"
                c_name = customer_data['name'] if customer_data else "Unknown"
                c_phone = customer_data['phone'] if customer_data else from_number
                logger.start_call(call_sid, c_id, c_name, c_phone)
                logger.update_step(call_sid, "Service Template")
                logger.log_event(call_sid, "Supriya", log_text, len(log_text or ""))
            
            self._accumulate_transcript(call_sid, "Supriya", log_text)
            self._start_gather(response, "continue", customer_id, flow_type, call_sid=call_sid)
            return str(response)

        # [FIX] Only create if doesn't exist to preserve idempotency_key (QUEUED_ SID)
        if not self.db.get_call_data(call_sid):
            self.db.create_call(call_sid, customer_id, campaign_id=None, idempotency_key=call_sid)

        # 2. Get Next Action
        action = self.get_next_action(call_sid, "", channel="voice", background_tasks=background_tasks)

        # response already initialized at top
        
        log_text = action["text"]
        if lang == "hi-IN" and log_text:
            from flows.translation_utils import TranslationAdapter
            log_text = TranslationAdapter.translate_to_hindi(log_text)

        if logger:
            customer = self.get_customer(customer_id)
            c_id = customer['id'] if customer else "Unknown"
            c_name = customer['name'] if customer else "Unknown"
            c_phone = customer['phone'] if customer else from_number
            logger.start_call(call_sid, c_id, c_name, c_phone)
            logger.update_step(call_sid, action["ui_state"])
            logger.log_event(call_sid, "Supriya", log_text, len(log_text or ""))

        if action.get("text"):
            response.say(action["text"])
        self._accumulate_transcript(call_sid, "Supriya", log_text)
        self._start_gather(response, action["next_step"], customer_id, flow_type, call_sid=call_sid)
        
        return str(response)

    def _get_rating(self, text):
        match = re.search(r'\b(10|[1-9])\b', text)
        if match: return int(match.group(1))
        words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
        for word, val in words.items():
            if word in text.lower(): return val
        return None

    def _is_positive(self, text):
        text = text.lower()
        if any(word in text for word in ['don\'t', 'do not', 'no', 'not', 'stop']):
            if any(text.startswith(no) for no in ['no', 'not']): # Simple "No"
                return False
            # Check for "don't proceed" etc
            if any(neg + " " + pos in text for neg in ['don\'t', 'do not', 'not'] for pos in ['yes', 'yeah', 'sure', 'proceed', 'ok', 'good']):
                return False
        return any(word in text for word in ['yes', 'yeah', 'sure', 'ok', 'proceed', 'correct', 'speaking', 'convenient', 'satisfied', 'satisfied'])

    def _is_negative(self, text):
        text = text.lower()
        if any(word in text for word in ['no', 'not', 'don\'t', 'stop', 'wrong', 'bad']):
            return True
        return False

    def _has_issue(self, text):
        text = text.lower()
        if any(word in text for word in ['not working', 'noise', 'vibration', 'leak', 'broke', 'problem', 'issue', 'bad', 'poor']):
            return True
        if 'not' in text and any(word in text for word in ['fine', 'good', 'ok', 'well', 'perfect']):
            return True
        parts = ['ac', 'air conditioning', 'engine', 'brake', 'steering', 'light', 'tire', 'gear', 'clutch', 'battery', 'oil']
        for part in parts:
            if part in text and not any(pos in text for pos in ['is fine', 'is good', 'working well']):
                return True
        return False

    def get_next_action(self, session_id, user_input, channel="web", is_recursive=False, background_tasks=None):
        # 1. Retrieve session to check language
        session = self.session_manager.get_session(session_id)
        lang = "en-IN"
        if session:
            lang = session.get("params", {}).get("language", "en-IN")

        # 2. Hindi/Hinglish to English translation on input (Robust multi-lingual mapping)
        translated_input = user_input
        if user_input:
            from flows.translation_utils import TranslationAdapter
            translated_input = TranslationAdapter.translate_to_english(user_input)
            if translated_input != user_input:
                print(f"[TRANSLATION] Input '{user_input}' -> '{translated_input}'")

        # 3. Call core internal engine
        response_data = self._get_next_action_internal(
            session_id, 
            translated_input, 
            channel=channel, 
            is_recursive=is_recursive, 
            background_tasks=background_tasks
        )

        # 4. English to Hindi translation on output
        if lang == "hi-IN" and response_data:
            from flows.translation_utils import TranslationAdapter
            original_text = response_data.get("text", "")
            if original_text:
                response_data["text"] = TranslationAdapter.translate_to_hindi(original_text)
                print(f"[TRANSLATION] Output '{original_text}' -> '{response_data['text']}'")
            
            # Also translate any options if they are returned
            if response_data.get("options"):
                translated_options = []
                for opt in response_data["options"]:
                    translated_opt = TranslationAdapter.translate_to_hindi(opt)
                    translated_options.append(translated_opt)
                response_data["options"] = translated_options

        return response_data

    def _get_next_action_internal(self, session_id, user_input, channel="web", is_recursive=False, background_tasks=None):
        """Core decision engine - Stateless Logic, Stateful Persistence"""
        # 1. Initialize / Retrieve Session
        session = self.session_manager.get_session(session_id)
        if not session:
            # Lazy Init (Safety Fix)
            session = {
                "step": "start",
                "flow_type": "booking",
                "customer_id": "Unknown",
                "params": {}
            }
            self.session_manager.save_session(session_id, session)

        current_step = session.get("step")
        flow_type = session.get("flow_type")
        customer_id = session.get("customer_id")
        params = session.get("params", {})
        user_input_lower = user_input.lower() if user_input else ""

        # --- GLOBAL INTENT SWITCHING & EXIT ---
        response_data = {
            "text": "",
            "options": [],
            "next_step": session.get("current_node_id") if self.use_insurance_template and flow_type == "insurance_start" else current_step,
            "ui_state": self.ui_state_map.get(current_step, "Processing")
        }

        # --- [NEW] Template Orchestration Bridge ---
        if self.use_insurance_template and flow_type == "insurance_start":
            customer = self.get_customer(customer_id)
            if current_step == "start" and customer:
                salutation = self._get_salutation(customer)
                if customer.get("policy_status") == "RENEWED":
                    self.db.update_lead_state(session_id, lead_status="NOT_CONVERTED", lead_score=10, disposition="ALREADY_RENEWED", last_action="Already Renewed", next_step="No Action")
                    response_data["text"] = f"Hello {salutation}, I'm Supriya from Alcon. I noticed your {customer['car_model']} insurance is already renewed. That's great! Have a wonderful day."
                    response_data["next_step"] = "end"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                
                if customer.get("dnd_status"):
                    self.db.update_lead_state(session_id, lead_status="DND", lead_score=0, disposition="DND_SKIP", last_action="Skipped due to DND", next_step="No Action")
                    response_data["text"] = "Thank you for your time. Have a nice day."
                    response_data["next_step"] = "end"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    return response_data

            template_name = "insurance_v2_template"
            print(f"[ORCHESTRATOR] Delegating turn to template: {template_name}")
            
            # --- PARITY: Log user input for transcript parity ---
            if user_input:
                self._accumulate_transcript(session_id, "Customer", user_input)

            # Prepare context
            customer = self.get_customer(customer_id)
            salutation = self._get_salutation(customer)
            customer_vars = {**(customer or {})}
            customer_vars["salutation"] = salutation
            
            context = {
                "user_input": user_input,
                "variables": {**params, **customer_vars, "flow_type": flow_type},
                "history": session.get("chat_history", []),
                "current_node_id": session.get("current_node_id")
            }
            
            result = self.orchestrator.sync_process_turn(session_id, user_input, template_name, context)
            
            if "error" not in result:
                # Sync back to session
                session["chat_history"] = result["history"]
                session["current_node_id"] = result["current_node_id"]
                
                # Check for Conversion status transition to trigger SMS/WhatsApp Hook
                prev_status = session.get("params", {}).get("lead_status")
                new_status = result.get("variables", {}).get("lead_status")
                if new_status == "CONVERTED" and prev_status != "CONVERTED":
                    print(f"[OUTBOUND TRIGGER] Lead converted in template. Triggering communication links...")
                    customer = self.get_customer(customer_id)
                    if customer:
                        customer_copy = {**customer}
                        pending_premium = result.get("variables", {}).get("pending_data", {}).get("premium")
                        if not pending_premium:
                            pending_premium = session.get("params", {}).get("pending_data", {}).get("premium")
                        if pending_premium:
                            customer_copy["loyalty_premium"] = f"₹{pending_premium}"
                        self._trigger_outbound_comms(customer_copy, "insurance_renewal_link")

                # Trigger outbound comms flag from template runner if requested/suggested in FAQ
                if result.get("variables", {}).get("trigger_outbound_comms") or session.get("params", {}).get("trigger_outbound_comms"):
                    print(f"[OUTBOUND TRIGGER] Session variable trigger_outbound_comms detected. Triggering dispatch...")
                    customer = self.get_customer(customer_id)
                    if customer:
                        customer_copy = {**customer}
                        pending_premium = result.get("variables", {}).get("pending_data", {}).get("premium")
                        if not pending_premium:
                            pending_premium = session.get("params", {}).get("pending_data", {}).get("premium")
                        if pending_premium:
                            customer_copy["loyalty_premium"] = f"₹{pending_premium}"
                        self._trigger_outbound_comms(customer_copy, "insurance_renewal_link")
                        # Clear flag to prevent repeat sends on subsequent turns
                        if "trigger_outbound_comms" in result.get("variables", {}):
                            result["variables"]["trigger_outbound_comms"] = False
                        if "trigger_outbound_comms" in session.get("params", {}):
                            session["params"]["trigger_outbound_comms"] = False
                
                session["params"].update(result["variables"])
                if result["status"] == "COMPLETED":
                    session["step"] = "end"
                self.session_manager.save_session(session_id, session)
                
                response_text = result["text"]
                
                # --- PARITY: Log AI response for transcript parity ---
                if response_text:
                    tags = []
                    if "transfer" in result.get("status", "") or "TRANSFER" in result.get("status", ""): tags.append("ESCALATION")
                    if result.get("status") == "COMPLETED" and result.get("variables", {}).get("lead_status") == "CONVERTED":
                         tags.append("CONSENT_POSITIVE")
                    self._accumulate_transcript(session_id, "Supriya", response_text, tags=tags)

                response_data["text"] = response_text
                
                if result["status"] == "TRANSFER_REQUIRED":
                    # Let `_transfer_call` handle the dynamic agent announcement and round-robin
                    response_data["text"] = "" 
                    response_data["next_step"] = "transfer_insurance"
                    return response_data

                response_data["next_step"] = "end" if result["status"] == "COMPLETED" else "start"
                return response_data
            else:
                print(f"[ORCHESTRATOR] Template error, falling back to legacy: {result['error']}")

        if user_input_lower:
            # 1. Global Exit Intent
            if any(word in user_input_lower for word in ['exit', 'quit', 'stop', 'bye', 'nothing else', 'that is all', 'no thanks', 'nevermind', 'cancel', 'go back', 'end call']):
                # [FIX] Ensure lead state is updated even on global exit
                if "insurance" in flow_type:
                    self.db.update_lead_state(session_id, lead_status="NOT_INTERESTED", lead_score=0, disposition="GLOBAL_EXIT", last_action="User ended call", next_step="DND")
                
                response_data["text"] = "Understood. Thanks for your time. Have a wonderful day!"
                response_data["next_step"] = "end"
                session["step"] = "end"
                self.session_manager.save_session(session_id, session)
                return response_data

            if channel == "web" or current_step == "end":
                # 3. Global Topic Switching
                detected_flow = None
                is_disambiguating = current_step in ["reception_disambiguation", "track_service_reg"]
                
                if not is_disambiguating:
                    if any(word in user_input_lower for word in ['status', 'track', 'where is my car']):
                        if flow_type != "track_service" or current_step == "end":
                            detected_flow = "track_service"
                    elif any(word in user_input_lower for word in ['service', 'book', 'maintenance', 'repair']):
                        if flow_type != "reception" or current_step == "end":
                            detected_flow = "reception"
                    elif any(m in user_input_lower for m in self.kb.get("models", {}).keys()) or \
                         any(word in user_input_lower for word in ['sales', 'buy', 'new car', 'price', 'model']) or \
                         any(typo in user_input_lower for typo in ['venuw', 'venuee', 'venu', 'creeta', 'crett', 'vernaa', 'verne', 'varna']):
                        if flow_type not in ["pre_sales", "pre_sales_upgrade"] or current_step == "end":
                            detected_flow = "pre_sales"
                
                if detected_flow:
                    session["flow_type"] = detected_flow
                    session["step"] = "start"
                    session["params"] = {} # CLEAR PARAMS ON GLOBAL FLOW SWITCH
                    session["params"]["fallback_count"] = 0 
                    self.session_manager.save_session(session_id, session)
                    return self.get_next_action(session_id, user_input, channel, is_recursive=True)

            # 2. Idempotency & Sentiment Check
            # Analyze Sentiment & Help via IntentEngine
            trace = self.intent_engine.explain_decision(user_input)
            sentiment_score = trace.get("sentiment_score", 0)
            wants_help = trace.get("wants_help", False)
            
            # [NEW] Automatic Sentiment/Help Escalation
            if trace["decision"] == "FRUSTRATION" or sentiment_score > 0.7:
                 response_data["text"] = "I apologize for the frustration. To ensure you get the best assistance, I'll connect you to a live representative immediately. Please stay on the line."
                 response_data["next_step"] = "transfer_insurance" if "insurance" in flow_type else "transfer"
                 response_data["escalation_reason"] = "NEGATIVE_SENTIMENT"
                 session["step"] = "end"
                 self.session_manager.save_session(session_id, session)
                 self.db.update_lead_state(session_id, escalation_status="IN_PROGRESS", escalation_reason="NEGATIVE_SENTIMENT", last_action="Sentiment-based Escalation")
                 return response_data
            
            if trace["decision"] == "HELP_REQUEST" or wants_help:
                 if "insurance" in flow_type:
                     response_data["text"] = "Certainly. To ensure you get the best assistance with these specific policy details, I'll connect you to our insurance desk immediately. Please stay on the line."
                     response_data["next_step"] = "transfer_insurance"
                 elif "sales" in flow_type or flow_type in ["pre_sales", "pre_sales_upgrade"]:
                     response_data["text"] = "Certainly. I'll connect you to our Sales team immediately. Please stay on the line."
                     response_data["next_step"] = "transfer_sales"
                 else:
                     response_data["text"] = "Certainly. I will connect you to our Service Advisor immediately. Please stay on the line."
                     response_data["next_step"] = "transfer"
                 response_data["escalation_reason"] = "HELP_REQUEST"
                 session["step"] = "end"
                 self.session_manager.save_session(session_id, session)
                 self.db.update_lead_state(session_id, escalation_status="IN_PROGRESS", escalation_reason="HELP_REQUEST", last_action="Help-based Escalation")
                 return response_data

            if not is_recursive and user_input:
                tags = []
                user_input_lower = user_input.lower()
                if any(w in user_input_lower for w in ["expensive", "high", "cost", "cheaper"]): tags.append("PRICE_OBJECTION")
                if "why" in user_input_lower: tags.append("QUERY")
                if "yes" in user_input_lower or "sure" in user_input_lower: tags.append("CONSENT_POSITIVE")
                self._accumulate_transcript(session_id, "Customer", user_input, tags=tags)

            is_dup, last_resp, dup_count = self.session_manager.is_duplicate(session_id, current_step, user_input, session_obj=session)
            if is_dup:
                if dup_count >= 2: # 3rd identical message
                    response_data["text"] = "I've noticed the same input multiple times. To better assist you, I'll connect you to a live representative for manual support."
                    response_data["next_step"] = "transfer_sales" if flow_type in ["pre_sales", "pre_sales_upgrade"] else "transfer"
                    response_data["escalation_reason"] = "REPETITIVE_INPUT"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    self.db.update_lead_state(session_id, 
                        escalation_status="IN_PROGRESS", 
                        escalation_reason="REPETITIVE_INPUT",
                        last_action="Repetition-based Escalation"
                    )
                    return response_data
                return last_resp

        # 3. Decision Logic (Refactored from handle_process)
        # (response_data already initialized above)

        customer = self.get_customer(customer_id)
        salutation = self._get_salutation(customer)

        # --- FLOW: START / INITIALIZATION ---
        if current_step == "start":
            # Intent Detection for Web/Chat (already handled by Global Switch above)
            if channel == "web":
                # Ensure we jump to specific starting points for web intents
                if flow_type == "track_service":
                    response_data["text"] = "I can help you track your car's service status in real-time. Please share your vehicle registration number and registered mobile number."
                    response_data["next_step"] = "track_service_reg"
                    response_data["ui_state"] = "Status Tracking"
                    response_data["options"] = ["1234", "5678"]
                    session["step"] = "track_service_reg"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                    
                if flow_type == "reception" and ("book" in user_input_lower or "service" in user_input_lower):
                    if customer_id == "Unknown":
                        response_data["text"] = "I can certainly help with your service booking. To get started, could you please share your vehicle registration number and registered mobile number?"
                        response_data["next_step"] = "reception_auth"
                        session["step"] = "reception_auth"
                        self.session_manager.save_session(session_id, session)
                        return response_data
                
                if flow_type in ["pre_sales", "pre_sales_upgrade"]:
                    # Initialize pre-sales with the query logic immediately
                    session["step"] = "pre_sales_query_or_transfer"
                    self.session_manager.save_session(session_id, session)
                    return self.get_next_action(session_id, user_input, channel, is_recursive=True)
            
            # 2. Unknown User Handling
            if customer_id == "Unknown" and flow_type not in ["reception", "pre_sales", "pre_sales_upgrade"]:
                response_data["text"] = "Hello! I'm Supriya, your Alcon Digital Assistant. To help you with your vehicle service or enquiry, could you please share your registration number and registered mobile number?"
                response_data["next_step"] = "reception_auth"
                session["step"] = "reception_auth"
                self.session_manager.save_session(session_id, session)
                return response_data

            if flow_type == "reception":
                if customer_id != "Unknown":
                    # Optimized: If we already know the customer, skip the generic welcome
                    name = customer["name"] if customer else "Valued Customer"
                    response_data["text"] = f"Welcome back {salutation} {name}! I see you're calling about your {customer['car_model']}. How can I assist you today? Service or Sales enquiry?"
                else:
                    response_data["text"] = "Welcome to Alcon Hyundai! I'm Supriya, your digital assistant. How can I assist you today? Are you calling regarding a car service or a new car enquiry?"
                response_data["next_step"] = "reception_intent"
                response_data["ui_state"] = "Initial Reception"
            elif flow_type in ["pre_sales", "pre_sales_upgrade"]:
                # Check if this is an outbound call (params already populated or known customer)
                campaign_type = session["params"].get("campaign_type", "general")
                if customer_id != "Unknown":
                    # Requirement 3A: Modular Intro
                    campaign_type = session["params"].get("campaign_type", "general")
                    vehicle_age = session["params"].get("vehicle_age")
                    
                    response_data["text"] = IntroFlow.get_greeting(
                        salutation, 
                        customer['name'], 
                        customer['car_model'], 
                        campaign_type,
                        vehicle_age=vehicle_age,
                        location=customer.get("location"),
                        current_emi=customer.get("current_emi")
                    )
                    response_data["next_step"] = "pre_sales_consent"
                    response_data["ui_state"] = "Lead Qualification"
                else:
                    # Inbound or direct enquiry
                    response_data["text"] = "I'm Supriya from Alcon. I can certainly help with your new car enquiry. Which model are you interested in today? I can share details on price, features, and EMI for our latest cars."
                    response_data["next_step"] = "pre_sales_query_or_transfer"
                    response_data["ui_state"] = "Pre-Sales Enquiry"
            elif flow_type in ["feedback_initial", "feedback_3rd_day", "feedback_15day_v2"]:
                name = customer["name"] if customer else "Valued Customer"
                response_data["text"] = f"Hello {salutation}, I'm Supriya from Alcon. Am I speaking with {name}?"
                response_data["next_step"] = "feedback_consent"
                response_data["ui_state"] = "Satisfaction Check"
            elif flow_type in ["pd_pickup_confirmation", "pd_pickup_coordination"]:
                response_data["text"] = f"Hello {salutation} {customer['name']}, I'm Supriya from Alcon. Calling to confirm your scheduled Pick & Drop for tomorrow. Is this still a good time?"
                response_data["next_step"] = "pd_pickup_consent"
                response_data["ui_state"] = "Pickup Coordination"
            elif flow_type == "pd_workshop_update":
                response_data["text"] = f"Hello {salutation}, I'm Supriya from Alcon. Am I speaking with {customer['name']}?"
                response_data["next_step"] = "pd_workshop_consent"
                response_data["ui_state"] = "Workshop Update"
            elif flow_type == "pd_ready":
                response_data["text"] = f"Hello {salutation}, I'm Supriya from Alcon. Am I speaking with {customer['name']}?"
                response_data["next_step"] = "pd_ready_consent"
                response_data["ui_state"] = "Vehicle Ready"
            elif flow_type == "track_service":
                response_data["text"] = "I can help you track your car's service status in real-time. Please share your vehicle registration number and registered mobile number."
                response_data["next_step"] = "track_service_reg"
                response_data["ui_state"] = "Status Tracking"
                response_data["options"] = ["1234", "5678"] # Mock options
            elif flow_type == "insurance_start":
                # [NEW] Pre-call Validation for Insurance
                if customer.get("policy_status") == "RENEWED":
                    self.db.update_lead_state(session_id, lead_status="NOT_CONVERTED", lead_score=10, disposition="ALREADY_RENEWED", last_action="Already Renewed", next_step="No Action")
                    response_data["text"] = f"Hello {salutation}, I'm Supriya from Alcon. I noticed your {customer['car_model']} insurance is already renewed. That's great! Have a wonderful day."
                    response_data["next_step"] = "end"
                    return response_data
                
                if customer.get("dnd_status"):
                    self.db.update_lead_state(session_id, lead_status="DND", lead_score=0, disposition="DND_SKIP", last_action="Skipped due to DND", next_step="No Action")
                    response_data["text"] = "Thank you for your time. Have a nice day."
                    response_data["next_step"] = "end"
                    return response_data

                response_data["text"] = f"Hello, I'm Supriya from Alcon. Am I speaking with {customer['name']} {salutation}?"
                response_data["next_step"] = "insurance_start"
                response_data["ui_state"] = "Identity Verification"
                response_data["options"] = ["Yes", "No"]
            else:
                # Default: Booking / Greeting
                if channel == "web" and customer_id != "Unknown":
                    # For Web Inbound, skip "Am I speaking with X?" and jump to status check
                    session["step"] = "greeting"
                    self.session_manager.save_session(session_id, session)
                    return self.get_next_action(session_id, "yes", channel, is_recursive=True, background_tasks=background_tasks)
                
                response_data["text"] = f"Hello, I'm Supriya from Alcon. Am I speaking with {customer['name']} {salutation}?"
                response_data["next_step"] = "greeting"
                response_data["ui_state"] = "Initial Greeting"
                response_data["options"] = ["Yes", "No"]

        # --- FLOW: INSURANCE RENEWAL ---
        elif current_step == 'insurance_start':
            # [NEW] Pre-emptive Intent Check (User might speak during intro)
            intent = InsuranceFlow.handle_consent(user_input_lower)
            if intent == "BUSY":
                self.db.update_lead_state(session_id, interest_level="WARM", reasoning_trace={"outcome": "busy_retry", "stage": params.get("stage")})
                response_data["text"] = f"No problem {salutation}. I completely understand. I'll schedule a call back at a more convenient time for you. Have a great day!"
                response_data["next_step"] = "end"
                return response_data
            elif intent == "REJECTED":
                self.db.update_lead_state(session_id, interest_level="COLD", reasoning_trace={"outcome": "not_interested", "stage": params.get("stage")})
                if any(word in user_input_lower for word in ['wrong number', 'rong number', 'wrong person', 'rong person', 'not her', 'not him', 'galat number', 'wrong no', 'rong no']):
                    response_data["text"] = f"I'm so sorry! I must have the wrong number. I'll update our records immediately. Have a respectful day."
                else:
                    response_data["text"] = f"I understand {salutation}. I've noted your preference and we won't call you further regarding this renewal. Have a nice day."
                response_data["next_step"] = "end"
                return response_data
            
            # [NEW] Handle early queries (e.g. "what is the premium?" during intro)
            stage = int(params.get("stage", 1))
            query_answer = InsuranceFlow.handle_query(user_input_lower, customer, stage=stage)
            if query_answer:
                intro = InsuranceFlow.get_greeting(salutation, customer['name'], customer['car_model'], customer.get('insurance_provider', 'Partner Insurer'), customer.get('insurance_expiry_date', 'Next Month'), stage=stage)
                response_data["text"] = f"{intro} Regarding your question, {query_answer}"
                response_data["next_step"] = "insurance_consent"
                session["step"] = "insurance_consent"
                self.session_manager.save_session(session_id, session)
                return response_data

            # Proceed with normal greeting if no pre-emptive intent
            stage = int(params.get("stage", 1))
            insurance_text = InsuranceFlow.get_greeting(
                salutation, 
                customer['name'], 
                customer['car_model'], 
                customer.get('insurance_provider', 'Partner Insurer'),
                customer.get('insurance_expiry_date', 'Next Month'),
                stage=stage
            )
            response_data["text"] = insurance_text
            response_data["next_step"] = "insurance_consent"
            response_data["ui_state"] = "Insurance Reminder"
            session["step"] = "insurance_consent"
            self.session_manager.save_session(session_id, session)

        elif current_step == 'insurance_consent':
            stage = int(params.get("stage", 1))
            
            # [NEW] Handle No Response / Silence
            if not user_input_lower:
                retries = session["params"].get("no_speech_count", 0) + 1
                session["params"]["no_speech_count"] = retries
                self.session_manager.save_session(session_id, session)
                
                if retries >= 3:
                    response_data["text"] = f"I'm sorry, I'm unable to hear you clearly. I'll schedule a follow-up call and send the details to your WhatsApp. Have a nice day!"
                    response_data["next_step"] = "end"
                    return response_data
                
                response_data["text"] = f"I'm sorry {salutation}, I didn't quite catch that. Could you please repeat?"
                response_data["next_step"] = "insurance_consent"
                return response_data
            
            # Reset silence counter if we got input
            session["params"]["no_speech_count"] = 0

            # 0. Handle Comparison or Transfer Request (Highest priority)
            last_resp = session.get("last_response", {}).get("text", "").lower()
            is_comp_offer = "comparison" in last_resp or ("insurance desk" in last_resp and "compare" in last_resp)
            is_fix_offer = any(word in last_resp for word in ["insurance desk", "coordinator", "fix this immediately", "manager", "approval rate"])
            

            if InsuranceFlow.is_comparison_requested(user_input_lower) or (is_comp_offer and any(word in user_input_lower for word in ['yes', 'yeah', 'sure', 'ok', 'connect'])):
                session["params"]["comparison_offered"] = True
                self.session_manager.save_session(session_id, session)
                
                # Update status to Negotiating early
                self.db.update_lead_state(session_id, lead_status="NEGOTIATING", lead_score=85, disposition="TRANSFER_REQUESTED", last_action="Requested Comparison", next_step="Manager Transfer")
                
                response_data["text"] = f"I can certainly help you compare. Apart from {customer.get('insurance_provider')}, we have tie-ups with 5 other major insurers. Just to confirm, shall I connect you to our insurance desk to find the best possible rate for you?"
                response_data["next_step"] = "insurance_transfer_confirm"
                session["step"] = "insurance_transfer_confirm"
                self.session_manager.save_session(session_id, session)
                return response_data
            
            if is_fix_offer and any(word in user_input_lower for word in ['yes', 'yeah', 'sure', 'ok', 'connect', 'fix']):
                # Update status to Negotiating early
                self.db.update_lead_state(session_id, lead_status="NEGOTIATING", lead_score=90, disposition="URGENT_FIX_REQUESTED", last_action="Requested Urgent Renewal", next_step="Manager Transfer")
                
                response_data["text"] = f"Understood. Just to confirm, shall I connect you to our insurance desk immediately to resolve the expiry and get your {customer.get('car_model')} covered?"
                response_data["next_step"] = "insurance_transfer_confirm"
                session["step"] = "insurance_transfer_confirm"
                self.session_manager.save_session(session_id, session)
                return response_data

            # 1. Handle Questions
            comp_already = session["params"].get("comparison_offered", False)
            kb_answer = InsuranceFlow.handle_query(user_input_lower, customer, stage=stage, comparison_offered=comp_already)
            if kb_answer:
                # [NEW] Track interest during query
                self.db.update_lead_state(session_id, lead_status="WARM_LEAD", lead_score=60, disposition="QUERY_INTEREST", last_action="Inquired about Premium", next_step="Confirm Interest")
                
                # Trigger outbound comms if user asks for details on WhatsApp/payment link
                # or if the agent suggests sharing them on WhatsApp
                if "whatsapp" in user_input_lower or "whatsapp" in kb_answer.lower() or "payment link" in user_input_lower or "secure payment" in kb_answer.lower():
                    print(f"[OUTBOUND TRIGGER] Dispatching WhatsApp quote as requested/suggested in rule-based query.")
                    customer_copy = {**customer}
                    pending_premium = session.get("params", {}).get("pending_data", {}).get("premium")
                    if pending_premium:
                        customer_copy["loyalty_premium"] = f"₹{pending_premium}"
                    self._trigger_outbound_comms(customer_copy, "insurance_renewal_link")
                
                # [NEW] Track that we've offered comparison to trigger escalation on next "expensive" query
                if "ICICI Lombard" in kb_answer or "partner rates" in kb_answer:
                    session["params"]["comparison_offered"] = True
                    self.session_manager.save_session(session_id, session)

                if "Insurance Manager" in kb_answer:
                    # Escalation path
                    response_data["text"] = kb_answer
                    response_data["next_step"] = "insurance_transfer_confirm"
                    return response_data

                # If already renewed, don't ask for quotation
                if "already covered" in kb_answer or "already renewed" in user_input_lower:
                    self.db.update_lead_state(session_id, interest_level="COLD", reasoning_trace={"outcome": "already_renewed", "stage": params.get("stage")})
                    response_data["text"] = kb_answer
                    response_data["next_step"] = "end"
                    return response_data
                
                # [FIX] Don't append if the answer already contains a follow-up question
                if kb_answer.strip().endswith('?'):
                    response_data["text"] = kb_answer
                else:
                    response_data["text"] = kb_answer + " Should I go ahead and share the digital copy of the quotation with you?"
                
                response_data["next_step"] = "insurance_consent" # Loop back for confirmation
                return response_data
            
            # 2. Handle Comparison Request (Direct trigger)
            if InsuranceFlow.is_comparison_requested(user_input_lower):
                response_data["text"] = f"I can certainly help you compare. Apart from {customer.get('insurance_provider')}, we have tie-ups with 5 other major insurers. Just to confirm, shall I connect you to our insurance desk to find the best possible rate for you?"
                response_data["next_step"] = "insurance_transfer_confirm"
                session["step"] = "insurance_transfer_confirm"
                self.session_manager.save_session(session_id, session)
                return response_data

            # 3. Handle Intent Categorization
            intent = InsuranceFlow.handle_consent(user_input_lower)
            
            if intent in ["INTERESTED", "INTERESTED_QUOTE_SHARED", "INTERESTED_NEGOTIATING"]:
                # [NEW] Mandory Confirmation Step (Avoid aggressive closing)
                if not session.get("insurance_confirmed"):
                     session["insurance_confirmed"] = True
                     self.session_manager.save_session(session_id, session)
                     response_data["text"] = InsuranceFlow.get_confirmation_question()
                     response_data["next_step"] = "insurance_consent"
                     return response_data

                # Refined Business Logic: Scoring & Status Consistency
                score = self.calculate_lead_score(intent, session)
                
                # Standardize: lead_status = business state, disposition = call outcome
                status_mapping = {
                    "INTERESTED": "CONVERTED", # For demo, mark as CONVERTED when they agree to link
                    "INTERESTED_QUOTE_SHARED": "CONVERTED",
                    "INTERESTED_NEGOTIATING": "NEGOTIATING"
                }
                
                lead_status = status_mapping.get(intent, "INTERESTED")
                disposition = "ANSWERED_INTERESTED"
                
                # Recalculate score with finalized intent
                score = self.calculate_lead_score(intent if lead_status != "CONVERTED" else "CONVERTED", session)
                
                last_action = "Accepted Loyalty Offer" if lead_status == "CONVERTED" else "Requested Comparison"
                next_step = "Payment Received" if lead_status == "CONVERTED" else "Manager Callback"

                self.db.update_lead_state(session_id, 
                    lead_status=lead_status, 
                    lead_score=score, 
                    disposition=disposition,
                    last_action=last_action,
                    next_step=next_step,
                    policy_status="PENDING_PAYMENT"
                )
                
                # Compliance: Log to consent_logs Table (IRDAI Audit)
                self.db.log_consent(session_id, customer_id, "digital_quote_delivery", True)
                
                self.log_attempt(session_id, stage, intent, background_tasks=background_tasks)
                
                # [FIX] Transition to feedback instead of end
                summary = InsuranceFlow.get_confirmation_summary(customer)
                # [NEW] Ensure final summary uses the human-discounted premium
                pending_data = session["params"].get("pending_data")
                if pending_data and "premium" in pending_data:
                    original_premium = str(customer.get('loyalty_premium'))
                    summary = summary.replace(original_premium, f"₹{pending_data['premium']}")
                
                response_data["text"] = summary + " By the way, did you find this call helpful today?"
                response_data["next_step"] = "insurance_feedback"
                response_data["tags"] = ["CONSENT_POSITIVE"]
                session["step"] = "insurance_feedback"
                self.session_manager.save_session(session_id, session)
                
                # Trigger SMS/WhatsApp Hook with custom premium if negotiated
                customer_copy = {**customer}
                pending_premium = session.get("params", {}).get("pending_data", {}).get("premium")
                if pending_premium:
                    customer_copy["loyalty_premium"] = f"₹{pending_premium}"
                self._trigger_outbound_comms(customer_copy, "insurance_renewal_link")
            elif intent == "ALREADY_RENEWED":
                self.db.update_lead_state(session_id, 
                    lead_status="NOT_CONVERTED", 
                    lead_score=10, 
                    disposition="ALREADY_RENEWED",
                    last_action="Already Renewed Externally",
                    next_step="No Further Action",
                    policy_status="RENEWED"
                )
                response_data["text"] = f"Oh, I see! That's great that your {customer.get('car_model')} is already covered. I'll update our records. By the way, was this call helpful for you?"
                response_data["next_step"] = "insurance_feedback"
                session["step"] = "insurance_feedback"
                self.session_manager.save_session(session_id, session)
            elif intent == "BUSY":
                self.db.update_lead_state(session_id, 
                    lead_status="WARM_LEAD", 
                    lead_score=55, 
                    disposition="BUSY_RETRY",
                    last_action="Requested Callback",
                    next_step="Retry in 4 Hours"
                )
                response_data["text"] = f"No problem {salutation}. I'll schedule a call back. Just one last thing, did you find this interaction helpful?"
                response_data["next_step"] = "insurance_feedback"
                session["step"] = "insurance_feedback"
                self.session_manager.save_session(session_id, session)
            elif intent == "REJECTED":
                self.db.update_lead_state(session_id, 
                    lead_status="NOT_INTERESTED", 
                    lead_score=0, 
                    disposition="REJECTED",
                    last_action="Explicit Rejection",
                    next_step="Mark DND",
                    policy_status="REJECTED"
                )
                self.mark_customer_dnd(customer_id)
                self.log_attempt(session_id, stage, "REJECTED", background_tasks=background_tasks)
                if any(word in user_input_lower for word in ['wrong number', 'rong number', 'wrong person', 'rong person', 'not her', 'not him', 'galat number', 'wrong no', 'rong no']):
                    response_data["text"] = f"I'm so sorry! I'll update our records. Was this call helpful though?"
                else:
                    response_data["text"] = f"I understand {salutation}. I've noted your preference. One quick question, did you find this call helpful today?"
                
                response_data["next_step"] = "insurance_feedback"
                session["step"] = "insurance_feedback"
                self.session_manager.save_session(session_id, session)
            else:
                # UNKNOWN / Fallback
                # --- [NEW] Check for explicit 'no' or 'not' before fallback increment ---
                if any(word in user_input_lower for word in ['no', 'not', 'don\'t']):
                    self.db.update_lead_state(session_id, lead_status="COLD_LEAD", lead_score=20, disposition="SOFT_REJECTION", last_action="Vague Rejection", next_step="Manual Review")
                    response_data["text"] = f"I understand {salutation}. If you change your mind, you can always reach us at Alcon. Have a nice day."
                    response_data["next_step"] = "end"
                    return response_data

                f_count = params.get("fallback_count", 0) + 1
                session["params"]["fallback_count"] = f_count
                self.session_manager.save_session(session_id, session)
                
                if f_count >= 2:
                    # [NEW] Automatic Escalation State
                    self.db.update_lead_state(session_id, escalation_status="IN_PROGRESS", last_action="AI Transfer - Human Handling")
                    
                    response_data["text"] = f"I'm sorry, I'm having a bit of trouble following. Let me connect you to our insurance desk for better assistance. Please stay on the line."
                    response_data["next_step"] = "transfer_insurance"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                
                response_data["text"] = f"I'm sorry {customer.get('name')} {salutation}, I didn't quite catch that. Would you like to proceed with the renewal or do you have any questions about the quote?"
                response_data["next_step"] = "insurance_consent"
            
            return response_data

        elif current_step == 'insurance_feedback':
            score = InsuranceFlow.handle_feedback(user_input_lower)
            session["params"]["feedback_score"] = score
            session["params"]["feedback_text"] = user_input # Capture raw feedback
            self.session_manager.save_session(session_id, session)
            
            response_data["text"] = "Thank you for your feedback! It helps us improve our service. Have a wonderful day."
            response_data["next_step"] = "end"
            session["step"] = "end"
            self.session_manager.save_session(session_id, session)
            return response_data

        elif current_step == 'insurance_transfer_confirm':
            if any(word in user_input_lower for word in ['yes', 'yeah', 'sure', 'ok', 'connect', 'do it', 'please']):
                # Final confirmation of transfer - set status to Negotiating
                self.db.update_lead_state(session_id, lead_status="NEGOTIATING", lead_score=95, disposition="TRANSFERRED_TO_MANAGER", last_action="Transferred to Desk", next_step="Human Handling", escalation_status="IN_PROGRESS")
                response_data["text"] = f"Understood. Connecting you to our insurance desk now. Please stay on the line."
                response_data["next_step"] = "transfer_insurance"
                session["step"] = "end"
            else:
                response_data["text"] = f"No problem. We can continue our discussion here. What else would you like to know about your renewal?"
                response_data["next_step"] = "insurance_consent"
                session["step"] = "insurance_consent"
            
            self.session_manager.save_session(session_id, session)
            return response_data

        # --- GREETING & BOOKING ---
        elif current_step == 'greeting':
            intent = IntroFlow.handle_identity_intent(user_input_lower)
            
            if intent == "YES":
                session["params"]["fallback_count"] = 0 # RESET
                if customer_id == "Unknown":
                    response_data["text"] = "I'm glad to help. To pull up your records, could you please share your vehicle registration number and registered mobile number?"
                    response_data["next_step"] = "reception_auth"
                    session["step"] = "reception_auth"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                else:
                    is_due, months = self.get_service_status(customer)
                    if is_due:
                        last_svc = datetime.strptime(customer["last_service_date"], "%Y-%m-%d").strftime("%B %d")
                        response_data["text"] = f"Great! I've verified your record {salutation} {customer['name']}. I see your {customer['car_model']} was last serviced on {last_svc}, and your next appointment is now due. Would you like to book it today?"
                        response_data["next_step"] = "intro"
                        response_data["options"] = ["Yes, Book", "No, Later"]
                    else:
                        response_data["text"] = f"I checked, and your car is doing great. No service due yet. Have a nice day {salutation}!"
                        response_data["next_step"] = "end"
            elif intent == "WRONG_NUMBER":
                response_data["text"] = "I'm so sorry! I must have the wrong number. I'll update our records immediately. Have a nice day!"
                response_data["next_step"] = "end"
                self.db.update_lead_state(session_id, disposition="WRONG_NUMBER", last_action="Identity Rejection - Wrong Number")
            elif intent == "BUSY":
                response_data["text"] = f"No problem {salutation}. I completely understand. When would be a more convenient time for me to call you back?"
                response_data["next_step"] = "booking_callback"
                session["step"] = "booking_callback"
                self.db.update_lead_state(session_id, disposition="BUSY_RETRY", last_action="Requested Callback")
            else:
                # FALLBACK LOGIC
                f_count = session["params"].get("fallback_count", 0) + 1
                session["params"]["fallback_count"] = f_count
                self.session_manager.save_session(session_id, session)
                
                if f_count >= 3:
                    # [NEW] Automatic Escalation State for Service
                    self.db.update_lead_state(session_id, escalation_status="IN_PROGRESS", last_action="Service Transfer - Human Handling")
                    
                    response_data["text"] = "I'm having trouble following. Let me connect you to our service team for better assistance. Please stay on the line."
                    response_data["next_step"] = "transfer"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                
                if f_count == 1:
                    response_data["text"] = f"I'm sorry, I didn't quite catch that. Am I speaking with {customer['name']}?"
                else:
                    response_data["text"] = f"My apologies, I'm still having a bit of trouble hearing you. Just to confirm, are you {customer['name']}?"
                
                response_data["next_step"] = "greeting"
                return response_data

        elif current_step == 'booking_callback':
            callback_time = parse_date_phrase(user_input)
            if callback_time:
                # Capture and store
                session["params"]["callback_time"] = str(callback_time)
                response_data["text"] = f"Got it. I've scheduled a reminder to call you back. Have a great day {salutation}!"
                response_data["next_step"] = "end"
                self.db.update_lead_state(session_id, disposition="CALLBACK_SCHEDULED", last_action=f"Scheduled callback for {callback_time}")
            else:
                # If we couldn't catch the time, just acknowledge and end gracefully
                response_data["text"] = f"Understood {salutation}. I'll have our team reach out to you later. Have a wonderful day!"
                response_data["next_step"] = "end"
            
            session["step"] = "end"
            self.session_manager.save_session(session_id, session)
            return response_data

        elif current_step == 'intro':
            if any(word in user_input_lower for word in ['yes', 'yeah', 'sure', 'book', 'please', 'correct']):
                response_data["text"] = "Great. What date would you prefer for the service?"
                response_data["next_step"] = "booking"
                response_data["options"] = ["Tomorrow", "Next Monday"]
            else:
                response_data["text"] = f"Understood {salutation}. Have a great day!"
                response_data["next_step"] = "end"

        elif current_step == 'booking':
            target_date = parse_date_phrase(user_input)
            if target_date:
                available_slots = self._get_slots_for_date(target_date)
                formatted_date = format_date_full(target_date)
                if available_slots:
                    preferred_slot = available_slots[0]
                    response_data["text"] = f"Got it. Available on {formatted_date} at {preferred_slot}. What's the current mileage of your car?"
                    response_data["next_step"] = "booking_mileage"
                    session["params"]["date"] = str(target_date)
                    session["params"]["slot"] = preferred_slot
                else:
                    next_dates = self._get_next_available_dates()
                    response_data["text"] = f"Sorry {salutation}, we're booked then. How about {format_date_full(next_dates[0])}?"
                    response_data["options"] = [format_date_full(d) for d in next_dates]
            else:
                response_data["text"] = "I didn't catch the date. Could you please repeat it?"

        elif current_step == 'booking_mileage':
            mileage = re.findall(r'\d+', user_input)
            session["params"]["mileage"] = mileage[0] if mileage else "unknown"
            response_data["text"] = "Got it. And are there any specific concerns or issues with the car?"
            response_data["next_step"] = "booking_concerns"

        elif current_step == 'booking_concerns':
            session["params"]["concerns"] = user_input
            is_urgent = any(word in user_input for word in ['urgent', 'noise', 'smoke', 'stuck'])
            ack = "I understand this sounds concerning. I've flagged this as a priority. " if is_urgent else "I've noted those points. "
            response_data["text"] = ack + "We offer free Pick and Drop service. Would you like to avail this?"
            response_data["next_step"] = "booking_options"
            response_data["options"] = ["Yes, please", "No, I'll drop it"]

        elif current_step == 'booking_options':
            pick_drop = "Yes" if any(word in user_input_lower for word in ['yes', 'yeah', 'avail']) else "No"
            advisor = self._assign_advisor(session["params"].get("concerns", ""))
            
            # Explain benefits and process (Requirement 1.1)
            benefits = "At Alcon, we provide a 50-point safety check and use only genuine Hyundai parts to ensure your vehicle's peak performance."
            process = f"Your Advisor, {advisor['name']}, will greet you upon arrival and walk you through the repair order details."
            
            summary = f"Wonderful {salutation}. Your service is confirmed. {benefits} {process} You'll receive an SMS shortly."
            
            if channel == "web":
                response_data["text"] = f"{summary} You can track your car's progress anytime using the 'Track Service' button below. Have a great day!"
                response_data["options"] = ["Track My Service", "I'm Done"]
            else:
                response_data["text"] = f"{summary} Have a great day!"
                
            response_data["next_step"] = "end"

        # --- FLOW: RECEPTION (INBOUND) ---
        elif current_step == 'reception_intent':
            if any(word in user_input.lower() for word in ['service', 'repair', 'booking', 'workshop']):
                if customer_id != "Unknown":
                    # Known Caller: Ask for Reg No only
                    response_data["text"] = "Understood. For verification, could you please share your vehicle registration number?"
                    response_data["next_step"] = "reception_auth"
                    response_data["ui_state"] = "Identity Verification"
                    # Pre-fill auth_phone from known customer
                    session["params"]["auth_phone"] = customer["phone"]
                    session["params"]["fallback_count"] = 0 # RESET
                    session["step"] = "reception_auth" # FIX: Update session state
                    self.session_manager.save_session(session_id, session)
                    return response_data
                
                # Unknown Caller / Web: Ask for Both
                response_data["text"] = "Understood. To assist you with your service, could you please share your vehicle registration number and registered mobile number?"
                response_data["next_step"] = "reception_auth"
                response_data["ui_state"] = "Customer Verification"
                session["params"]["fallback_count"] = 0 # RESET
                session["step"] = "reception_auth"
                self.session_manager.save_session(session_id, session)
                return response_data
            elif any(word in user_input.lower() for word in ['sales', 'buy', 'enquiry', 'new car', 'price', 'model', 'interested']):
                if customer_id != "Unknown":
                    name = customer["name"]
                    session["params"]["name"] = name
                    response_data["text"] = f"Great {salutation} {name}! I can certainly help with your new car enquiry. Which model are you interested in today? I can help with pricing, features, or EMI details."
                    response_data["next_step"] = "reception_sales_purpose"
                else:
                    response_data["text"] = "Great! I can certainly help with your new car enquiry. May I know your name please?"
                    response_data["next_step"] = "reception_sales_name"
                session["step"] = response_data["next_step"]
                self.session_manager.save_session(session_id, session)
                return response_data
            else:
                # Handle general FAQ or Transfer
                answer = self.handle_query(user_input)
                if answer:
                    response_data["text"] = answer + " Would you like me to connect you to a representative for more help?"
                    response_data["next_step"] = "reception_intent"
                else:
                    response_data["text"] = "I see. Let me connect you to our front desk for further assistance. Please stay on the line."
                    response_data["next_step"] = "transfer"
                    response_data["ui_state"] = "Transferring"

        elif current_step == 'reception_sales_name':
            # Basic Name Extraction: "I am Maahi" -> "Maahi"
            name = user_input.replace("i am", "").replace("my name is", "").strip().title()
            session["params"]["name"] = name
            response_data["text"] = f"Thank you {name}. Which model are you interested in today? I can help with pricing, features, or EMI details."
            response_data["next_step"] = "reception_sales_purpose"
            response_data["ui_state"] = "Model Inquiry"

        elif current_step == 'reception_sales_purpose':
            user_input_lower = user_input.lower()
            
            # Fuzzy Model Identification (Typo tolerance)
            all_models = self.kb.get("models", {}).keys()
            mentioned_models = [m for m in all_models if m in user_input_lower]
            
            # Simple typo fix for common ones
            if not mentioned_models:
                if "venuw" in user_input_lower or "venu" in user_input_lower: mentioned_models = ["venue"]
                elif "creeta" in user_input_lower or "crett" in user_input_lower: mentioned_models = ["creta"]
                elif "vernaa" in user_input_lower or "varna" in user_input_lower: mentioned_models = ["verna"]
            
            if mentioned_models:
                session["params"]["model"] = mentioned_models[0]
            
            current_model = session["params"].get("model")
            
            # 1. Lead Qualification with Explainable Trace
            trace = self.intent_engine.explain_decision(user_input_lower)
            
            # Proactive Data Update: If location provided, it's at least WARM
            extracted = self.intent_engine.extract_data(user_input_lower)
            if extracted["location"]:
                session["params"]["location"] = extracted["location"]
                if trace["decision"] == "COLD":
                    trace["decision"] = "WARM"
                    trace["matched_warm"].append("location_provided")

            self.db.update_lead_state(
                session_id, 
                interest_level=trace["decision"], 
                reasoning_trace=trace
            )
            
            # Save Lead Update (Legacy support)
            phone = session["params"].get("phone", "Unknown")
            name = session["params"].get("name", "Unknown")
            self._save_lead(phone, name, "Sales Enquiry", current_model)

            # 1. Handle "Yes" based on Context
            if any(word == "yes" for word in user_input_lower.split()):
                last_ai_text = session.get("last_response", {}).get("text", "").lower()
                if "features" in last_ai_text and current_model:
                    user_input_lower = f"tell me about {current_model} features"

            # 2. Check for Test Drive specifically
            if any(word in user_input_lower for word in ["test drive", "drive"]):
                session["params"]["intent"] = "test_drive"
                ans = self.kb["general_faqs"]["test_drive"]
                if current_model:
                    ans = ans.replace("Which model would you like to experience?", f"Would you like to experience the {current_model.capitalize()}?")
                response_data["text"] = ans
                response_data["next_step"] = "reception_sales_purpose"
                session["step"] = "reception_sales_purpose"
                self.session_manager.save_session(session_id, session)
                return response_data
            
            # Handle Model Confirmation for Test Drive
            if session["params"].get("intent") == "test_drive" and mentioned_models:
                session["params"]["intent"] = None 
                response_data["text"] = f"Excellent. I've noted that you'd like a test drive for the {mentioned_models[0].capitalize()}. I'll have our coordinator call you shortly to schedule it. Is there anything else you'd like to know?"
                response_data["next_step"] = "reception_sales_purpose"
                session["step"] = "reception_sales_purpose"
                self.session_manager.save_session(session_id, session)
                return response_data

            # 0. Handle Negative Intent / Ending
            if any(word in user_input_lower.split() for word in ["no", "nothing", "bye", "thanks", "thank"]):
                # Requirement: Bridge to service before ending if pre-sales failed
                response_data["text"] = "I understand. By the way, I noticed your vehicle might be due for periodic maintenance. Since we're already speaking, would you like me to book a service appointment for you instead?"
                response_data["next_step"] = "pre_sales_bridge_to_service"
                session["step"] = "pre_sales_bridge_to_service"
                self.session_manager.save_session(session_id, session)
                return response_data

            # 3. Handle specific KB queries
            query_result = self.intent_engine.handle_query(user_input_lower, model_context=current_model)
            q_count = session["params"].get("query_count", 0) + 1
            session["params"]["query_count"] = q_count
            
            if query_result:
                answer = query_result["text"]
                intent = query_result.get("intent")
                
                # Proactive Prompting: If location is missing, ask for it naturally
                if not session["params"].get("location") and intent != "location":
                    answer += " By the way, to give you the most accurate on-road price, could you let me know which city you are calling from? This helps me check the latest regional offers at your nearest showroom."
                elif not session["params"].get("emi_interest") and intent != "emi":
                     answer += " We also have some great EMI schemes starting as low as 8,999 rupees. Would you like to hear about those as well?"
                
                response_data["text"] = answer
                response_data["next_step"] = "pre_sales_query_or_transfer"

                # Bridge Logic
                if not any(word in answer.lower() for word in ["test drive", "connect", "representative", "specialist"]):
                    variations = [
                        "Should I connect you to our Sales Representative for a personalized offer?",
                        "Would you like to speak with an expert to discuss this further?",
                        "Would you like to visit our showroom for a closer look?",
                        "I can have our representative call you with a detailed quote. Should I arrange that?"
                    ]
                    # Select based on intent if possible
                    bridge = ""
                    if intent == "features": bridge = "Would you like to experience these features in a test drive?"
                    elif intent == "price": bridge = "We have some great ongoing offers as well. Should I connect you to a representative to discuss them?"
                    else: bridge = variations[q_count % len(variations)]
                    
                    response_data["text"] = f"{answer} {bridge}".strip()

                self.session_manager.save_session(session_id, session)
                return response_data
            
            # 3. If no specific answer but model mentioned, give summary only if it's the first time
            if mentioned_models:
                info = self.kb["models"][current_model]
                response_data["text"] = f"The {current_model.capitalize()} is a great choice with {info['features']} and is {info['price']}. Would you like to know more, or should I connect you to our Sales Representative?"
                response_data["next_step"] = "reception_sales_purpose"
                session["step"] = "reception_sales_purpose"
                self.session_manager.save_session(session_id, session)
                return response_data

            if any(word in user_input.lower() for word in ['connect', 'talk', 'yes', 'advisor', 'person', 'representative', 'transfer']):
                response_data["text"] = f"Understood. Connecting you to our Sales Specialist now. Please stay on the line."
                response_data["next_step"] = "transfer_sales"
                response_data["ui_state"] = "Transferring to Sales"
            else:
                response_data["text"] = f"I have details on {current_model.capitalize() if current_model else 'our models'} pricing, offers, and features. What would you like to know? Or should I connect you to a representative?"
                response_data["next_step"] = "reception_sales_purpose"

        elif current_step == 'reception_transfer_check':
            if any(word in user_input.lower() for word in ['yes', 'yeah', 'sure', 'ok', 'connect', 'talk', 'please', 'transfer']):
                response_data["text"] = "Perfect. Connecting you to our Sales Representative now. Please stay on the line."
                response_data["next_step"] = "transfer_sales"
            else:
                response_data["text"] = "No problem. Do you have any other questions about our models, or should I have a representative call you back later?"
                response_data["next_step"] = "reception_intent"

        elif current_step == 'reception_auth' or current_step == 'track_service_reg':
            # 0. Increment Fallback Counter for this turn (will be reset on success)
            f_count = session["params"].get("fallback_count", 0) + 1
            session["params"]["fallback_count"] = f_count

            # 1. Extraction Logic (Detect Reg No and Phone)
            phone_match = re.search(r'\d{9,12}', user_input)
            new_phone = phone_match.group(0) if phone_match else None
            
            reg_candidates = re.findall(r'[A-Z0-9]{4,12}', user_input.upper())
            new_reg = None
            blacklist = [
                "PHONE", "MOBILE", "NUMBER", "REGISTRATION", "VEHICLE", "DETAILS", 
                "ALCON", "HYUNDAI", "BOOK", "SERVICE", "WANT", "PLEASE", "BOOKING",
                "I DON", "KNOW", "STILL", "WHAT", "HELLO", "THIS", "THAT", "THEIR",
                "THERE", "THEY", "YOUR", "YOURS", "HELP", "ASSIST", "QUERY", "ENQUIRY",
                "DONT", "DO NOT", "CANT", "PLEASE", "THANK", "THANKS", "OKAY",
                "I DONT", "STILL DONT", "DONT KNOW", "DO NOT KNOW", "GIBBERISH", "RANDOM"
            ]
            for cand in reg_candidates:
                clean_cand = "".join(filter(str.isalnum, cand))
                # Indian Reg No Pattern (approx): 2 letters, 2 digits, 1-2 letters, 4 digits
                # Or at least shouldn't be all digits if long, or all letters if common words
                is_valid_format = bool(re.search(r'[A-Z].*\d|\d.*[A-Z]', clean_cand)) # Mix of letters and digits is good
                
                if clean_cand != new_phone and clean_cand not in blacklist and len(clean_cand) >= 4 and is_valid_format:
                    new_reg = cand.strip()
                    break
            
            # Update Session State
            if new_reg: session["params"]["reg_no"] = new_reg
            if new_phone: session["params"]["auth_phone"] = new_phone
            
            reg_no = session["params"].get("reg_no")
            phone = session["params"].get("auth_phone")
            
            # 2. Check for Repeated Confusion (Global Safety Net)
            if f_count >= 3:
                response_data["text"] = "I'm having trouble identifying your record. Let me connect you to our front desk for manual assistance. Please stay on the line."
                response_data["next_step"] = "transfer"
                session["step"] = "end"
                self.session_manager.save_session(session_id, session)
                return response_data

            # 3. Decision Logic (shared for auth and tracking)
            if reg_no and phone:
                customer = self.find_customer_by_reg_and_phone(reg_no, phone)
                if customer:
                    session["params"]["fallback_count"] = 0 # SUCCESS: RESET
                    session["customer_id"] = customer["id"]
                    
                    if current_step == 'track_service_reg':
                        # Track Service Flow Execution (Flexible lookup)
                        clean_input_reg = "".join(filter(str.isalnum, reg_no)).upper()
                        
                        info = None
                        for s in self.service_status:
                            target_reg = "".join(filter(str.isalnum, s.get("reg_no", ""))).upper()
                            # Match if one is a suffix of the other
                            if clean_input_reg and (clean_input_reg in target_reg or target_reg in clean_input_reg):
                                info = s
                                break
                        
                        if info:
                            response_data["text"] = f"I found your record, {salutation} {customer['name']}. Your {info['model']} is currently in the **{info['stage']}** stage. \n\nStatus: *{info['status']}* \nEst. Completion: **{info['est_completion']}** \nLast Update: {info['last_update']}."
                            response_data["next_step"] = "end"
                            response_data["ui_state"] = "Status Delivered"
                            session["step"] = "end"
                            self.session_manager.save_session(session_id, session)
                            return response_data
                        else:
                            response_data["text"] = f"I authenticated your record, but I couldn't find a live service session for '{reg_no}'. Please contact our service desk."
                            response_data["next_step"] = "end"
                            session["step"] = "end"
                            self.session_manager.save_session(session_id, session)
                            return response_data
                    
                    # Normal Auth Flow Execution
                    session["step"] = "greeting"
                    self.session_manager.save_session(session_id, session)
                    return self.get_next_action(session_id, "yes", channel, is_recursive=True)
                else:
                    # AUTH FAILURE FALLBACK
                    f_count = session["params"].get("fallback_count", 0) + 1
                    session["params"]["fallback_count"] = f_count
                    self.session_manager.save_session(session_id, session)
                    
                if f_count >= 3:
                    response_data["text"] = "I'm sorry, I'm unable to verify those details. Let me connect you to our front desk for manual assistance."
                    response_data["next_step"] = "transfer"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                
                response_data["text"] = f"I'm sorry, I couldn't find a record for registration '{reg_no}' and mobile '{phone}'. Please check the details and try again."
                # Clear state for retry
                session["params"].pop("reg_no", None)
                session["params"].pop("auth_phone", None)
                self.session_manager.save_session(session_id, session)
                return response_data
            elif reg_no:
                # Only "Got it" if it's the first time or looks really like a reg no
                if f_count == 1:
                    response_data["text"] = f"I've noted the registration number {reg_no}. And could you also provide your registered mobile number for verification?"
                else:
                    response_data["text"] = f"Thank you. I also need your registered mobile number to proceed. Could you please share it?"
                response_data["next_step"] = current_step
                self.session_manager.save_session(session_id, session)
                return response_data
            elif phone:
                response_data["text"] = f"Thank you for the mobile number. And what is your vehicle registration number?"
                response_data["next_step"] = current_step
                self.session_manager.save_session(session_id, session)
                return response_data
            else:
                # NO EXTRACTION FALLBACK
                f_count = session["params"].get("fallback_count", 0) + 1
                session["params"]["fallback_count"] = f_count
                self.session_manager.save_session(session_id, session)
                
                if f_count >= 3:
                    response_data["text"] = "I'm having trouble identifying your record. Let me connect you to an agent for help."
                    response_data["next_step"] = "transfer"
                    session["step"] = "end"
                    self.session_manager.save_session(session_id, session)
                    return response_data
                
                prompt = "registration number and mobile number"
                if current_step == 'track_service_reg':
                    response_data["text"] = f"I didn't catch that. To track your service, please provide your {prompt}."
                else:
                    response_data["text"] = f"I'm sorry, I didn't get that. Could you please share your {prompt}?"
                return response_data

        elif current_step == 'reception_disambiguation':
            matches = session["params"].get("matches", [])
            selected_customer = None
            user_input_lower = user_input.lower()
            for m in matches:
                # Flexible matching: "Creta" or "Hyundai Creta"
                model_name = m["car_model"].lower()
                # Remove "hyundai" for comparison if user just said "creta"
                short_model = model_name.replace("hyundai", "").strip()
                if short_model in user_input_lower or model_name in user_input_lower:
                    selected_customer = m
                    break
            
            if selected_customer:
                session["customer_id"] = selected_customer["id"]
                session["step"] = "greeting"
                self.session_manager.save_session(session_id, session)
                return self.get_next_action(session_id, "yes", channel, is_recursive=True)
            else:
                model_names = [m["car_model"] for m in matches]
                response_data["text"] = f"I'm sorry, I didn't catch that. Was it the {model_names[0]} or the {model_names[1]}?"
                response_data["next_step"] = "reception_disambiguation"

        # --- FLOW: SERVICE STATUS TRACKER ---
        elif current_step == 'track_service_reg':
            # 1. Extraction Logic
            reg_match = re.search(r'[A-Z0-9]{4,}', user_input.upper())
            phone_match = re.search(r'\d{10}', user_input)
            
            new_reg = reg_match.group(0) if reg_match else None
            new_phone = phone_match.group(0) if phone_match else None
            
            if new_reg: session["params"]["reg_no"] = new_reg
            if new_phone: session["params"]["auth_phone"] = new_phone
            
            reg_no = session["params"].get("reg_no")
            phone = session["params"].get("auth_phone")
            
            # 2. Authentication Logic
            if reg_no and phone:
                customer = self.find_customer_by_reg_and_phone(reg_no, phone)
                if customer:
                    matches = [s for s in self.service_status if s["reg_no"] == reg_no]
                    if matches:
                        info = matches[0]
                        response_data["text"] = f"I found your record for the {info['model']}. Your car is currently in the **{info['stage']}** stage. \n\nStatus: *{info['status']}* \nEst. Completion: **{info['est_completion']}** \nLast Update: {info['last_update']}."
                        response_data["next_step"] = "end"
                        response_data["ui_state"] = "Status Delivered"
                        session["step"] = "end"
                        self.session_manager.save_session(session_id, session)
                        return response_data
                    else:
                        response_data["text"] = f"I authenticated your record, but I couldn't find a live service session for '{reg_no}'. Please contact our service desk for more details."
                        response_data["next_step"] = "end"
                        session["step"] = "end"
                        self.session_manager.save_session(session_id, session)
                        return response_data
                else:
                    response_data["text"] = f"I couldn't verify the details for registration '{reg_no}' and mobile '{phone}'. Please try again."
                    response_data["next_step"] = "track_service_reg"
                    session["params"].pop("reg_no", None)
                    session["params"].pop("auth_phone", None)
                    self.session_manager.save_session(session_id, session)
                    return response_data
            elif reg_no:
                response_data["text"] = f"I've noted the registration number {reg_no}. Could you also provide your registered mobile number?"
                response_data["next_step"] = "track_service_reg"
                self.session_manager.save_session(session_id, session)
                return response_data
            elif phone:
                response_data["text"] = "Thank you. And what is the vehicle registration number?"
                response_data["next_step"] = "track_service_reg"
                self.session_manager.save_session(session_id, session)
                return response_data
            else:
                response_data["text"] = "To track your service, please provide your vehicle registration number and registered mobile number."
                response_data["next_step"] = "track_service_reg"
                return response_data

        # --- FLOW: UNIFIED FEEDBACK (Initial, 3rd Day, 15th Day) ---
        elif current_step == 'feedback_consent':
            if any(word in user_input_lower for word in ['yes', 'yeah', 'sure', 'speaking', 'correct']):
                response_data["text"] = f"Thank you {salutation}. Were all requested jobs done to your complete satisfaction?"
                response_data["next_step"] = "feedback_satisfaction"
                response_data["ui_state"] = "Satisfaction Check"
            elif any(word in user_input_lower for word in ['noise', 'vibration', 'leak', 'broke', 'problem', 'issue', 'bad', 'poor', 'not working', 'facing']):
                response_data["text"] = f"I'm sorry to hear that you're facing issues {salutation}. I am escalating this to our senior service team immediately. May I still ask for your ratings for other areas?"
                response_data["next_step"] = "feedback_unsatisfied_continue"
                response_data["ui_state"] = "Issue Escalation"
            else:
                response_data["text"] = f"I understand {salutation}. Could you please let me know a suitable date or time when I should call you back for this feedback?"
                response_data["next_step"] = "feedback_reschedule"
                response_data["ui_state"] = "Rescheduling"

        elif current_step == 'feedback_reschedule':
            session["params"]["callback_time"] = user_input
            print(f"DEBUG: Callback scheduled for {customer_id} at {user_input}")
            response_data["text"] = f"Got it. I've scheduled a callback for {user_input}. Thank you, and have a nice day!"
            response_data["next_step"] = "end"

        elif current_step == 'feedback_satisfaction':
            if any(word in user_input for word in ['yes', 'yeah', 'sure', 'ok']) or ('satisfied' in user_input and 'not' not in user_input and 'no' not in user_input):
                response_data["text"] = f"That's great to hear. Now, on a scale of one to ten, how would you rate the service advisor’s explanation of work and charges?"
                response_data["next_step"] = "feedback_q1"
                response_data["ui_state"] = "Advisor Rating"
            else:
                response_data["text"] = f"I'm sorry to hear that {salutation}. I am escalating this to our senior service team immediately. They will contact you to resolve this. May I still ask for your ratings for other areas?"
                response_data["next_step"] = "feedback_unsatisfied_continue"

        elif current_step == 'feedback_unsatisfied_continue':
            if any(word in user_input for word in ['yes', 'yeah', 'sure', 'ok']):
                response_data["text"] = "Thank you. On a scale of one to ten, how would you rate the advisor’s explanation?"
                response_data["next_step"] = "feedback_q1"
            else:
                response_data["text"] = "Understood. Our team will contact you shortly. Have a nice day."
                response_data["next_step"] = "end"

        elif current_step == 'feedback_q1':
            rating = self._get_rating(user_input)
            session["params"]["q1_rating"] = rating
            if rating and rating <= 9:
                response_data["text"] = f"I've noted the rating of {rating}. May I know the reason for this rating, so we can improve our service?"
                response_data["next_step"] = "feedback_q1_reason"
                response_data["ui_state"] = "Capturing Reason"
            else:
                response_data["text"] = "Thank you. Next, how would you rate the pickup process after servicing?"
                response_data["next_step"] = "feedback_q2"
                response_data["ui_state"] = "Pickup Rating"

        elif current_step == 'feedback_q1_reason':
            session["params"]["q1_reason"] = user_input
            response_data["text"] = "Thank you for sharing that. Next, how would you rate the pickup process after servicing?"
            response_data["next_step"] = "feedback_q2"
            response_data["ui_state"] = "Pickup Rating"

        elif current_step == 'feedback_q2':
            rating = self._get_rating(user_input)
            session["params"]["q2_rating"] = rating
            if rating and rating <= 9:
                response_data["text"] = f"Understood. Could you share the reason for the {rating} rating for the pickup process?"
                response_data["next_step"] = "feedback_q2_reason"
                response_data["ui_state"] = "Capturing Reason"
            else:
                response_data["text"] = "Noted. And how would you rate the cleanliness and condition of the car?"
                response_data["next_step"] = "feedback_q3"
                response_data["ui_state"] = "Cleanliness Rating"

        elif current_step == 'feedback_q2_reason':
            session["params"]["q2_reason"] = user_input
            response_data["text"] = "Got it. And how would you rate the cleanliness and condition of the car?"
            response_data["next_step"] = "feedback_q3"
            response_data["ui_state"] = "Cleanliness Rating"

        elif current_step == 'feedback_q3':
            rating = self._get_rating(user_input)
            session["params"]["q3_rating"] = rating
            if rating and rating <= 9:
                response_data["text"] = f"Thank you. Could you please tell me why you gave a {rating} for cleanliness?"
                response_data["next_step"] = "feedback_q3_reason"
                response_data["ui_state"] = "Capturing Reason"
            else:
                response_data["text"] = "Finally, how would you rate your overall workshop experience?"
                response_data["next_step"] = "feedback_q4"
                response_data["ui_state"] = "Overall Experience"

        elif current_step == 'feedback_q3_reason':
            session["params"]["q3_reason"] = user_input
            response_data["text"] = "Thank you. Finally, how would you rate your overall workshop experience?"
            response_data["next_step"] = "feedback_q4"
            response_data["ui_state"] = "Overall Experience"

        elif current_step == 'feedback_q4':
            rating = self._get_rating(user_input)
            session["params"]["q4_rating"] = rating
            if rating and rating <= 9:
                response_data["text"] = f"I've noted your rating of {rating}. Any suggestions on how we can make your overall experience better?"
                response_data["next_step"] = "feedback_q4_reason"
                response_data["ui_state"] = "Capturing Reason"
            else:
                response_data["text"] = "Thank you for your valuable feedback! We appreciate your time. Have a great day!"
                response_data["next_step"] = "end"

        elif current_step == 'feedback_q4_reason':
            session["params"]["q4_reason"] = user_input
            # Check for dissatisfied customers (1-8) for CRM callback flag
            low_ratings = [session["params"].get(f"q{i}_rating", 10) for i in range(1, 5)]
            if any(r <= 8 for r in low_ratings if r is not None):
                print(f"DEBUG: CRM Callback Flagged for Customer {customer_id} due to low ratings.")
                session["params"]["crm_callback"] = True
            
            response_data["text"] = "Thank you for your valuable feedback! We've noted your suggestions and will work on them. Have a great day!"
            response_data["next_step"] = "end"

        # --- FLOW: PICK & DROP ---
        elif current_step == 'pd_pickup_consent':
            user_input_lower = user_input.lower() if user_input else ""
            is_driver_query = (any(word in user_input_lower for word in ['driver', 'rajesh', 'ड्राइवर', 'ड्रायवर', 'राजेश']) and any(word in user_input_lower for word in ['safe', 'license', 'trust', 'verify', 'police', 'experience', 'credentials', 'who is', 'kaun', 'amit', 'सुरक्षित', 'लाइसेंस', 'पुलिस', 'सत्यापित', 'भरोसा', 'अनुभवी', 'सेफ', 'ड्राइवर', 'ड्रायवर'])) or any(word in user_input_lower for word in ['driver safe', 'driver license', 'driver trusted', 'driver verified', 'police verified', 'license hai', 'लाइसेंस है', 'लाइसेंस ड्राइवर'])
            
            if is_driver_query:
                response_data["text"] = "Yes, all our drivers, including Rajesh, are fully licensed, police-verified, and highly experienced professionals with clean safety records. You can be fully assured of your car's safety. Is this still a good time for the pickup?"
                response_data["next_step"] = "pd_pickup_consent"
                response_data["ui_state"] = "Pickup Coordination"
            elif any(word in user_input for word in ['yes', 'yeah', 'speaking', 'correct']):
                # Clarifying driver info (Requirement 1.2)
                response_data["text"] = "Great. Our driver Rajesh is assigned for the pickup. What time should he arrive at your location?"
                response_data["next_step"] = "pd_pickup_slot"
                response_data["ui_state"] = "Slot Confirmation"
            else:
                response_data["text"] = "No problem. I will have our coordinator call you to reschedule the pickup. Have a nice day!"
                response_data["next_step"] = "end"

        elif current_step == 'pd_pickup_slot':
            user_input_lower = user_input.lower() if user_input else ""
            is_driver_query = (any(word in user_input_lower for word in ['driver', 'rajesh', 'ड्राइवर', 'ड्रायवर', 'राजेश']) and any(word in user_input_lower for word in ['safe', 'license', 'trust', 'verify', 'police', 'experience', 'credentials', 'who is', 'kaun', 'amit', 'सुरक्षित', 'लाइसेंस', 'पुलिस', 'सत्यापित', 'भरोसा', 'अनुभवी', 'सेफ', 'ड्राइवर', 'ड्रायवर'])) or any(word in user_input_lower for word in ['driver safe', 'driver license', 'driver trusted', 'driver verified', 'police verified', 'license hai', 'लाइसेंस है', 'लाइसेंस ड्राइवर'])
            
            if is_driver_query:
                response_data["text"] = "Yes, all our drivers, including Rajesh, are fully licensed, police-verified, and highly experienced professionals with clean safety records. You can be fully assured of your car's safety. What time should he arrive at your location?"
                response_data["next_step"] = "pd_pickup_slot"
                response_data["ui_state"] = "Slot Confirmation"
            else:
                from slot_manager import SlotParser
                parsed_time = SlotParser.parse_specific_time(user_input)
                pickup_time = parsed_time if parsed_time else user_input
                response_data["text"] = f"Perfect. Rajesh will see you tomorrow at {pickup_time}. You'll receive driver contact details via SMS shortly. Thanks!"
                response_data["next_step"] = "end"

        elif current_step == 'pd_workshop_consent':
            if any(word in user_input for word in ['yes', 'yeah', 'speaking', 'correct']):
                svc = self.service_details.get(customer_id, {})
                concerns = svc.get("reported_concerns", "periodic maintenance")
                response_data["text"] = f"Great. I'm calling from the workshop to confirm the reported issues for your {customer['car_model']}. We have noted: {concerns}. Do you have any additional concerns we should address?"
                response_data["next_step"] = "pd_workshop_concerns"
                response_data["ui_state"] = "Additional Concerns"
            else:
                response_data["text"] = "Understood. I'll call back at a more convenient time. Have a great day!"
                response_data["next_step"] = "end"

        elif current_step == 'pd_workshop_concerns':
            svc = self.service_details.get(customer_id, {})
            ack = "Excellent. " if any(word in user_input for word in ['no', 'none', 'nothing else']) else f"I've noted down: {user_input}. "
            cost = svc.get("estimated_cost", "four thousand five hundred rupees")
            time_est = svc.get("estimated_time", "by evening")
            response_data["text"] = ack + f"Based on our inspection, the estimated cost is approximately {cost}, and we expect to have it ready {time_est}. Should we proceed?"
            response_data["next_step"] = "pd_workshop_estimate"
            response_data["ui_state"] = "Cost Estimate"

        elif current_step == 'pd_workshop_estimate':
            user_input_lower = user_input.lower() if user_input else ""
            if any(word in user_input_lower for word in ['why', 'expensive', 'cost', 'charges', 'high', 'mehenga', 'mehnga', 'mhenga', 'jyada', 'zyada', 'daam', 'kharch', 'kharcha', 'price', 'paisa', 'paise', 'महंगा', 'मंहगा', 'ज्यादा', 'ज़्यादा', 'दाम', 'खर्च', 'चार्ज']):
                response_data["text"] = f"I understand. The estimate includes authorized parts for your {customer['car_model']}, professional labor, and a service warranty. Would you like to proceed, or should I have the Service Advisor call you?"
                response_data["next_step"] = "pd_workshop_estimate"
                response_data["ui_state"] = "Price Explanation"
            elif any(word in user_input_lower for word in ['advisor', 'talk', 'speak', 'person', 'representative', 'connect', 'transfer', 'बात', 'सलाहकार', 'मैनेजर', 'जोड़', 'कनेक्ट', 'ट्रांसफर']):
                response_data["text"] = "Understood. Connecting you to our Service Advisor now. Please stay on the line."
                response_data["next_step"] = "transfer"
                response_data["ui_state"] = "Transferring"
            elif any(word in user_input_lower for word in ['yes', 'yeah', 'proceed', 'ok']):
                response_data["text"] = "Excellent! We are proceeding with the service now. You'll get a detailed breakdown via SMS. Thank you!"
                response_data["next_step"] = "end"
            else:
                response_data["text"] = "Understood. I will have your Service Advisor call you immediately to discuss the details. Thank you!"
                response_data["next_step"] = "end"

        # --- FLOW: PICK & DROP READY ---
        elif current_step == 'pd_ready_consent':
            if any(word in user_input for word in ['yes', 'yeah', 'speaking', 'correct']):
                svc = self.service_details.get(customer_id, {})
                summary = svc.get("service_summary", "the scheduled service")
                response_data["text"] = f"Wonderful news {salutation} {customer['name']}! Your car is ready for delivery. We've completed {summary}. Would you like us to drop it back to your location, or will you be coming to pick it up?"
                response_data["next_step"] = "pd_ready_options"
                response_data["ui_state"] = "Delivery Options"
                response_data["options"] = ["Drop it", "I'll pick up"]
            else:
                response_data["text"] = "No problem. I'll call you back later. Have a nice day!"
                response_data["next_step"] = "end"

        elif current_step == 'pd_ready_options':
            if any(word in user_input for word in ['drop', 'send', 'delivery', 'ड्रॉप', 'भेज', 'डिलीवरी']):
                response_data["text"] = "Perfect. I've scheduled the drop-off for you. Our driver will contact you shortly. Thank you!"
                response_data["next_step"] = "end"
            else:
                response_data["text"] = "Got it. Your car is parked at our service entrance. See you soon!"
                response_data["next_step"] = "end"

        # --- FLOW: PRE-SALES ---
        elif current_step == 'pre_sales_consent':
            # 1. Check for implicit consent via a query (e.g. "what is the price?")
            model_ctx = self._get_current_model(session, customer)
            query_result = self.handle_query(user_input, model_context=model_ctx)
            
            if query_result or IntroFlow.handle_consent(user_input_lower):
                session["params"]["fallback_count"] = 0
                response_data["text"] = f"Great! To help you better, I can share the latest price, ongoing offers, or schedule a test drive for the {model_ctx.capitalize()}. What would you prefer?"
                response_data["next_step"] = "pre_sales_query_or_transfer"
                response_data["ui_state"] = "Proactive Qualification"
                
                # If they already asked something, jump straight to answering it
                if query_result:
                    session["step"] = "pre_sales_query_or_transfer"
                    self.session_manager.save_session(session_id, session)
                    return self.get_next_action(session_id, user_input, channel, is_recursive=True)
            else:
                # 2. Rejection or Busy: Detect actual interest level
                trace = self.intent_engine.explain_decision(user_input)
                interest_level = trace["decision"]
                
                print(f"\033[94m[ENGINE] Classified as {interest_level} (Trace: {trace['matched_hot'] or trace['matched_warm']})\033[0m")

                if interest_level == "EXIT":
                    response_data["text"] = f"I sincerely apologize {salutation}. I must have the wrong number. I'll remove this contact immediately. Have a respectful day."
                    response_data["next_step"] = "end"
                    return response_data
                
                if trace.get("is_dnd"):
                    response_data["text"] = f"I sincerely apologize {salutation}. I've marked your number for no further contact. Have a respectful day."
                    response_data["next_step"] = "end"
                    return response_data

                # Requirement 4: Check if they are just busy or WARM
                if FollowupManager.should_schedule_callback(user_input_lower, interest_level):
                    msg = FollowupManager.get_callback_prompt()
                    if trace.get("is_whatsapp"):
                        session["params"]["requested_whatsapp"] = True
                        msg = f"I'll send the brochure and details to your WhatsApp right away! {msg}"
                        print("\033[92m[ACTION] WhatsApp Triggered\033[0m")
                    
                    response_data["text"] = msg
                    response_data["next_step"] = "pre_sales_schedule_callback"
                    response_data["ui_state"] = "Scheduling Callback"
                else:
                    # Respectful Exit: If they say 'no' twice, don't be pushy or schedule follow-ups
                    session["params"]["rejection_count"] = session["params"].get("rejection_count", 0) + 1
                    if session["params"]["rejection_count"] >= 2:
                        response_data["text"] = f"I understand {salutation}. Have a wonderful day!"
                        response_data["next_step"] = "end"
                        # Explicitly cancel any pre-scheduled follow-up
                        self.db.cancel_followup(customer_id)
                        self.db.update_lead_state(session_id, interest_level="COLD")
                    else:
                        # Requirement 3F: SERVICE BRIDGE
                        is_due, _ = self.get_service_status(customer)
                    if is_due:
                        response_data["text"] = ServiceBridgeFlow.get_bridge_prompt(salutation, model_ctx)
                        response_data["next_step"] = "pre_sales_bridge_to_service"
                    else:
                        response_data["text"] = f"Understood {salutation}. Should I have a representative call you back later, or would you like to visit our showroom?"
                        response_data["next_step"] = "end"

        elif current_step == 'pre_sales_bridge_to_service':
            if any(word in user_input.lower() for word in ['yes', 'yeah', 'sure', 'ok', 'book']):
                # Transition to Service Booking Flow
                session["flow_type"] = "booking"
                session["step"] = "intro"
                self.session_manager.save_session(session_id, session)
                return self.get_next_action(session_id, "yes", channel, is_recursive=True, background_tasks=background_tasks)
            else:
                # Requirement 4: Check if they are busy when rejecting service
                if FollowupManager.should_schedule_callback(user_input_lower, "WARM"):
                    response_data["text"] = FollowupManager.get_callback_prompt()
                    response_data["next_step"] = "pre_sales_schedule_callback"
                    response_data["ui_state"] = "Scheduling Callback"
                else:
                    response_data["text"] = f"No problem at all. Have a wonderful day {salutation}!"
                    response_data["next_step"] = "end"

        elif current_step == 'pre_sales_query_or_transfer':
            # 1. Capture model if mentioned
            mentioned_models = [m for m in self.kb.get("models", {}).keys() if m in user_input_lower]
            if mentioned_models:
                session["params"]["model"] = mentioned_models[0]
            
            # Unify model context (Campaign data vs Conversation data)
            model_ctx = self._get_current_model(session, customer)

            # 2. Handle Query with Context
            query_result = self.handle_query(user_input, model_context=model_ctx)
            
            # Lead Qualification Update for Outbound
            trace = self.intent_engine.explain_decision(user_input)
            interest_level = trace["decision"]
            
            print(f"\033[94m[ENGINE] Classified as {interest_level} (Trace: {trace['matched_hot'] or trace['matched_warm']})\033[0m")
            
            if trace.get("is_dnd"):
                response_data["text"] = f"I apologize {salutation}. I've marked your number for no further contact. Have a respectful day."
                response_data["next_step"] = "end"
                return response_data

            self.db.update_lead_state(
                session_id, 
                interest_level=interest_level, 
                reasoning_trace=trace
            )

            # Lock model context into session memory if detected by query
            if query_result and query_result.get("model"):
                session["params"]["model"] = query_result["model"]
            
            # Increment Query Count
            q_count = session["params"].get("query_count", 0) + 1
            session["params"]["query_count"] = q_count
            
            if query_result:
                final_text = query_result["text"]
                intent = query_result.get("intent")
                response_data["text"] = final_text
                response_data["next_step"] = "pre_sales_query_or_transfer"
                response_data["ui_state"] = "Query Handling"

                # Requirement 4: Global Busy/Callback Check (HIGHEST PRIORITY)
                if FollowupManager.should_schedule_callback(user_input_lower, interest_level):
                    msg = FollowupManager.get_callback_prompt()
                    if trace.get("is_whatsapp"):
                         session["params"]["requested_whatsapp"] = True
                         msg = f"I'll send that to your WhatsApp right away! {msg}"
                    
                    response_data["text"] = f"{final_text} {msg}"
                    response_data["next_step"] = "pre_sales_schedule_callback"
                    response_data["ui_state"] = "Query + Scheduling"
                    return response_data

                # Nudge only if no escalation offered and not finance turn
                # q_count == 1: Info only (Silence)
                # q_count == 2: Offer Test Drive
                # q_count >= 3: Offer Transfer
                if q_count == 2:
                    response_data["text"] += " Would you like to schedule a doorstep test drive to experience the new Creta?"
                elif q_count >= 3:
                    response_data["text"] += " I have more details on this, or I can connect you to our representative for a deep dive. What would you prefer?"

                session["step"] = response_data["next_step"]
                session["params"]["fallback_count"] = 0 # Reset on valid query
                self.session_manager.save_session(session_id, session)
                return response_data
            
            # 3. If no specific answer but model mentioned, give summary
            if mentioned_models:
                target_model = mentioned_models[0]
                info = self.kb["models"][target_model]
                response_data["text"] = f"The {target_model.capitalize()} is a great choice with {info['features']} and is {info['price']}. Would you like to know more, or should I connect you to our Sales Representative?"
                response_data["next_step"] = "pre_sales_query_or_transfer"
                session["step"] = "pre_sales_query_or_transfer"
                session["params"]["fallback_count"] = 0 # Reset on valid model mention
                self.session_manager.save_session(session_id, session)
                return response_data
            
            # 4. Fallback for Gibberish/Unknown in Sales
            f_count = session["params"].get("fallback_count", 0) + 1
            session["params"]["fallback_count"] = f_count
            if f_count >= 3:
                response_data["text"] = "I'm having trouble understanding your request. Let me connect you to our Sales Specialist who can assist you better. Please stay on the line."
                response_data["next_step"] = "transfer_sales"
                session["step"] = "end"
                self.session_manager.save_session(session_id, session)
                return response_data

            if any(word in user_input.lower() for word in ['connect', 'talk', 'yes', 'advisor', 'person', 'representative', 'transfer']):
                response_data["text"] = "Perfect. Connecting you to our Sales Specialist now. Please stay on the line."
                response_data["next_step"] = "transfer_sales"
                response_data["ui_state"] = "Transferring to Sales"
            elif any(word in user_input.lower() for word in ['no', 'stop', 'nothing', 'bye']):
                # User says "no" to more info - pivot to service bridge
                is_due, _ = self.get_service_status(customer)
                if is_due:
                    response_data["text"] = ServiceBridgeFlow.get_bridge_prompt(salutation, customer['car_model'])
                    response_data["next_step"] = "pre_sales_bridge_to_service"
                else:
                    response_data["text"] = f"Understood {salutation}. Have a wonderful day!"
                    response_data["next_step"] = "end"
            else:
                target_model = self._get_current_model(session, customer)
                prompt_model = f"the {target_model.capitalize()}" if target_model != "car" else "our models"
                
                # Requirement 3D: Acknowledge data capture if it just happened
                ack = ""
                if "location" in user_input_lower and any(city in user_input_lower for city in ["nashik", "pune", "mumbai", "maharashtra"]):
                    ack = f"Got it, {user_input.split(',')[0].strip()}. "
                
                msg = f"{ack}I have details on {prompt_model} pricing, offers, and features. What would you like to know? Or should I connect you to a representative?"
                
                # Double Check for WARM interest here as well (Fix for "maybe next month")
                if interest_level == "WARM":
                    callback_msg = FollowupManager.get_callback_prompt()
                    if trace.get("is_whatsapp"):
                        callback_msg = f"I'll send details to your WhatsApp! {callback_msg}"
                    msg = f"{ack}I understand. {callback_msg}"
                    response_data["next_step"] = "pre_sales_schedule_callback"
                else:
                    response_data["next_step"] = "pre_sales_query_or_transfer"

                response_data["text"] = msg

        elif current_step == "pre_sales_transfer_check":
            if any(word in user_input.lower() for word in ['yes', 'yeah', 'sure', 'ok', 'connect', 'talk', 'please', 'transfer']):
                response_data["text"] = "Perfect. Connecting you to our Sales Representative now. Please stay on the line."
                response_data["next_step"] = "transfer_sales"
                response_data["ui_state"] = "Transferring to Sales"
            else:
                response_data["text"] = f"Understood {salutation}. Have a wonderful day!"
                response_data["next_step"] = "end"

        elif current_step == "pre_sales_schedule_callback":
            # 1. Check if they asked a NEW question instead of giving a time
            query_result = self.handle_query(user_input_lower)
            if query_result:
                response_data["text"] = f"{query_result['text']} What time would be convenient for that callback?"
                response_data["next_step"] = "pre_sales_schedule_callback"
                return response_data

            if any(word in user_input_lower for word in ['no', 'never', 'don\'t call']):
                response_data["text"] = f"No problem at all. Have a wonderful day {salutation}!"
                response_data["next_step"] = "end"
            else:
                FollowupManager.record_callback(self.db, session_id, user_input, customer_id=customer_id)
                is_whatsapp = session["params"].get("requested_whatsapp", False)
                response_data["text"] = FollowupManager.get_confirmation_message(user_input, is_whatsapp=is_whatsapp)
                response_data["next_step"] = "end"
            session["step"] = "end"
            self.session_manager.save_session(session_id, session)
            return response_data

        # 4. Finalize State Update (Minimal Lock Scope)
        session["step"] = response_data["next_step"]
        self.session_manager.save_session(session_id, session)
        self.session_manager.update_last_response(session_id, current_step, user_input, response_data)

        # 5. Channel Awareness (Platform Fix)
        if channel == "voice":
            # For voice, we might want to strip complex punctuation or add SSML
            response_data["text"] = response_data["text"].replace("\n", " ")
        
        return response_data

    def handle_process(self, customer_id, step, speech_result, call_sid, flow_type="booking", logger=None, background_tasks=None, **kwargs):
        """Twilio Processing Endpoint - Fully refactored to use stateful engine"""
        # Instrumentation: Record turn in background
        if background_tasks:
            background_tasks.add_task(metrics.record_request, call_sid, os.getpid())
        else:
            metrics.record_request(call_sid, os.getpid())
        if logger and speech_result:
            logger.log_event(call_sid, "Customer", speech_result)

        # Sync flow_type if session just started
        session = self.session_manager.get_session(call_sid)
        if session and session["step"] == "start":
             session["flow_type"] = flow_type
             session["customer_id"] = customer_id
             # Capture any extra campaign info
             for k, v in kwargs.items():
                 session["params"][k] = v
             self.session_manager.save_session(call_sid, session)
             self.db.update_call_status(call_sid, "answered")
        
        # Override step for testing/force-transitions if provided
        if step and step != "greeting" and session:
            session["step"] = step
            self.session_manager.save_session(call_sid, session)

        # Input Translation for hi-IN session language (e.g. templates)
        lang = "en-IN"
        if session:
            lang = session.get("params", {}).get("language", "en-IN")
        if lang == "hi-IN" and speech_result:
            from flows.translation_utils import TranslationAdapter
            translated_speech = TranslationAdapter.translate_to_english(speech_result)
            print(f"[TRANSLATION INPUT] Translating input '{speech_result}' -> '{translated_speech}'")
            speech_result = translated_speech

        # Conversational Language Lock detection
        if speech_result and session:
            user_input_lower = speech_result.lower()
            if "hindi" in user_input_lower or "speak in hindi" in user_input_lower:
                session["params"]["language"] = "hi-IN"
                self.session_manager.save_session(call_sid, session)
                lang = "hi-IN"
                print(f"[LANGUAGE LOCK] Session locked to Hindi (hi-IN) based on: '{speech_result}'")

        # Repeat Request Handler
        if speech_result and speech_result.lower().strip() == "repeat" and session:
            history = session.get("history", [])
            last_ai = [m for m in history if m.get("role") == "ai"]
            if last_ai:
                repeat_text = last_ai[-1].get("text", "")
                print(f"[REPEAT HANDLER] Repeating last AI response: '{repeat_text}'")
                
                # Format TwiML Response
                response = VoiceResponse()
                
                # Monkey-patching of VoiceResponse say method for Hindi translation support
                original_say = response.say
                def patched_say(text, *args, **kwargs_say):
                    if lang == "hi-IN":
                        from flows.translation_utils import TranslationAdapter
                        translated = TranslationAdapter.translate_to_hindi(text)
                        return original_say(translated, language="hi-IN", *args, **kwargs_say)
                    return original_say(text, language="en-IN", *args, **kwargs_say)
                response.say = patched_say
                
                response.say(repeat_text)
                
                action_url = f"/process?customer_id={customer_id}&step={step}&flow_type={flow_type}"
                gather = Gather(input="speech", action=action_url, timeout=5, speechTimeout="auto")
                response.append(gather)
                response.redirect(action_url)
                
                return str(response)

        # --- ORCHESTRATION BRIDGE: PRE-SALES & RECEPTION ---
        if self.use_pre_sales_template and flow_type in ["pre_sales", "reception", "pre_sales_upgrade"]:
            template_name = "inbound_receptionist" if flow_type == "reception" else "pre_sales_template"
            context = {
                "user_input": speech_result,
                "call_sid": call_sid,
                "session_id": call_sid,
                "flow_type": flow_type,
                "current_node_id": session.get("current_node_id"),
                "variables": session.get("params", {}),
                "history": session.get("history", [])
            }
            res = self.orchestrator.sync_process_turn(call_sid, speech_result, template_name, context)
            
            # Sync back
            session["current_node_id"] = res["current_node_id"]
            session["params"] = res["variables"]
            session["history"] = res["history"]
            session["step"] = "end" if res["status"] == "COMPLETED" else session["step"]
            self.session_manager.save_session(call_sid, session)
            
            # Determine terminal status
            final_status = res.get("status", "ACTIVE")
            
            is_service_transfer = final_status == "TRANSFER_REQUIRED" and flow_type == "reception" and "service" in str(session.get("current_node_id", "")).lower()
            action = {
                "text": res["text"],
                "next_step": "end" if final_status == "COMPLETED" else ("transfer" if is_service_transfer else ("transfer_sales" if final_status == "TRANSFER_REQUIRED" else "continue")),
                "ui_state": "Sales Template"
            }
            # Requirement: If next_step is transfer, ensure ui_state reflects it
            if action["next_step"] == "transfer_sales":
                action["ui_state"] = "Transferring to Sales"
            elif action["next_step"] == "transfer":
                action["ui_state"] = "Transferring to Service"
            
            # P0: Log debugging for status interpretation
            print(f"[ORCHESTRATION SYNC] Status: {res['status']} | Next Step: {action['next_step']}")
        elif self.use_feedback_template and flow_type in ["feedback_15day_v2", "feedback_initial", "feedback_3rd_day"]:
            template_name = "post_service_feedback_15day" if flow_type == "feedback_15day_v2" else "post_service_feedback"
            context = {
                "user_input": speech_result,
                "call_sid": call_sid,
                "session_id": call_sid,
                "flow_type": flow_type,
                "current_node_id": session.get("current_node_id"),
                "variables": session.get("params", {}),
                "history": session.get("history", [])
            }
            res = self.orchestrator.sync_process_turn(call_sid, speech_result, template_name, context)
            
            # Sync back
            session["current_node_id"] = res["current_node_id"]
            session["params"] = res["variables"]
            session["history"] = res["history"]
            session["step"] = "end" if res["status"] == "COMPLETED" else session["step"]
            self.session_manager.save_session(call_sid, session)
            
            final_status = res.get("status", "ACTIVE")
            
            action = {
                "text": res["text"],
                "next_step": "end" if final_status == "COMPLETED" else "continue",
                "ui_state": "Feedback Template"
            }
            print(f"[ORCHESTRATION FEEDBACK] Status: {res['status']} | Next Step: {action['next_step']}")
        elif self.use_booking_template and flow_type == "booking":
            template_name = "service_booking_prod"
            context = {
                "user_input": speech_result,
                "call_sid": call_sid,
                "session_id": call_sid,
                "flow_type": flow_type,
                "current_node_id": session.get("current_node_id"),
                "variables": session.get("params", {}),
                "history": session.get("history", [])
            }
            res = self.orchestrator.sync_process_turn(call_sid, speech_result, template_name, context)
            
            # Sync back
            session["current_node_id"] = res["current_node_id"]
            session["params"] = res["variables"]
            session["history"] = res["history"]
            session["step"] = "end" if res["status"] == "COMPLETED" else session["step"]
            self.session_manager.save_session(call_sid, session)
            
            final_status = res.get("status", "ACTIVE")
            
            action = {
                "text": res["text"],
                "next_step": "end" if final_status == "COMPLETED" else "continue",
                "ui_state": "Service Booking Template"
            }
            print(f"[ORCHESTRATION SERVICE] Status: {res['status']} | Next Step: {action['next_step']}")
        else:
            # 1. Get Next Action from stateful engine (Legacy)
            action = self.get_next_action(call_sid, speech_result, channel="voice", background_tasks=background_tasks)

        # 2. Format TwiML Response
        response = VoiceResponse()
        
        # Look up session language for TTS translation
        lang = "en-IN"
        session_obj = self.session_manager.get_session(call_sid)
        if session_obj:
            lang = session_obj.get("params", {}).get("language", "en-IN")
            
        # Dynamic Monkey-patching of VoiceResponse say method
        original_say = response.say
        def patched_say(text, *args, **kwargs_say):
            if lang == "hi-IN":
                from flows.translation_utils import TranslationAdapter
                translated = TranslationAdapter.translate_to_hindi(text)
                print(f"[MONKEY-PATCH SAY] Translating speech '{text}' -> '{translated}'")
                kwargs_say["language"] = "hi-IN"
                return original_say(translated, *args, **kwargs_say)
            else:
                return original_say(text, *args, **kwargs_say)
        response.say = patched_say
        
        log_text = action["text"]
        if lang == "hi-IN" and log_text:
            from flows.translation_utils import TranslationAdapter
            log_text = TranslationAdapter.translate_to_hindi(log_text)

        if logger:
            logger.update_step(call_sid, action["ui_state"])
            logger.log_event(call_sid, "Supriya", log_text, len(log_text or ""))

        if action.get("text"):
            response.say(action["text"])
        self._accumulate_transcript(call_sid, "Supriya", log_text, tags=action.get("tags", []))

        if action["next_step"] == "end":
            self.db.update_call_status(call_sid, "completed")
            response.hangup()
        elif action["next_step"] == "transfer":
            self._transfer_call(response, "Service Advisor", call_sid=call_sid, reason=action.get("escalation_reason", "MANUAL_REQUEST"))
        elif action["next_step"] == "transfer_sales":
            self._transfer_call(response, "Sales", call_sid=call_sid, reason=action.get("escalation_reason", "MANUAL_REQUEST"))
        elif action["next_step"] == "transfer_insurance":
            self._transfer_call(response, "Insurance Desk", call_sid=call_sid, reason=action.get("escalation_reason", "HELP_REQUEST"))
        else:
            self._start_gather(response, action["next_step"], customer_id, flow_type, call_sid=call_sid)
            
        return str(response)

    def _trigger_outbound_comms(self, customer, template):
        """Mock/Production trigger for SMS/WhatsApp multi-channel quote delivery"""
        phone = customer.get("phone", "")
        name = customer.get("name", "Valued Customer")
        car = customer.get("car_model", "vehicle")
        loyalty_premium = customer.get("loyalty_premium", "TBD")
        
        # Payment link from demo config
        payment_link = f"https://gloss-playlist-grass.ngrok-free.dev/pay?phone={phone}"
        
        # Format the actual quote messages
        whatsapp_message = (
            f"Dear {name},\n\n"
            f"Here is your customized loyalty renewal quote for your {car}:\n"
            f"- Approved Special Premium: {loyalty_premium}\n"
            f"- Coverage Includes: Zero Depreciation, Engine Protection & Roadside Assistance\n\n"
            f"Click here to instantly renew and complete payment: {payment_link}\n\n"
            f"Thank you for choosing Alcon Hyundai!"
        )
        
        sms_backup_message = (
            f"Alcon Hyundai: Dear {name}, your {car} insurance renewal link is ready: "
            f"{payment_link} - Premium: {loyalty_premium} (incl Zero-Dep)."
        )
        
        # Production Hook: We log the payload and simulate full delivery channel pipeline
        print(f"\n\033[92m[OUTBOUND HOOK] Initiating multi-channel dispatch via {template} for {name} ({phone})\033[0m")
        print(f"\033[92m[WHATSAPP DISPATCH] Send payload:\n{whatsapp_message}\033[0m")
        print(f"\033[92m[SMS DISPATCH] Send payload:\n{sms_backup_message}\033[0m")
        
        # Attempt production Twilio WhatsApp / SMS if client is configured
        try:
            import os
            from twilio.rest import Client
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")
            from_phone = os.getenv("TWILIO_PHONE_NUMBER")
            
            if account_sid and auth_token:
                client = Client(account_sid, auth_token)
                
                # SMS Dispatch
                if from_phone:
                    sms_msg = client.messages.create(
                        body=sms_backup_message,
                        from_=from_phone,
                        to=phone
                    )
                    print(f"\033[92m[TWILIO SMS] Dispatched SMS. SID: {sms_msg.sid}\033[0m")
                
                # WhatsApp Dispatch (Twilio Sandbox or Production WhatsApp sender)
                # Production format: 'whatsapp:<phone_number>'
                try:
                    # If sandbox is configured, from_ is 'whatsapp:+14155238886'
                    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
                    whatsapp_msg = client.messages.create(
                        body=whatsapp_message,
                        from_=whatsapp_from,
                        to=f"whatsapp:{phone}"
                    )
                    print(f"\033[92m[TWILIO WHATSAPP] Dispatched WhatsApp. SID: {whatsapp_msg.sid}\033[0m")
                except Exception as wa_err:
                    print(f"\033[93m[TWILIO WHATSAPP WARNING] Could not send via WhatsApp: {wa_err}. Sandboxed environment requires opt-in.\033[0m")
        except Exception as e:
            print(f"\033[91m[TWILIO DISPATCH ERROR] Production Twilio dispatch skipped/failed: {e}\033[0m")
        print()

    def mark_customer_dnd(self, customer_id):
        """Permanently mark a customer as DND in customers.json."""
        customers_path = "data/customers.json"
        if not os.path.exists(customers_path):
            return
        
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
            print(f"[ERROR] Failed to update DND for {customer_id}: {e}")
