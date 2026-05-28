from abc import ABC, abstractmethod
from typing import Dict, Any, List
import sys
import os
import json
import re
import requests
from datetime import datetime

# Add backend to path for date_utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend")))
from date_utils import parse_date_phrase, format_date_full
from data import MOCK_CRM

def extract_number(text):

    # More robust regex for numbers 1-10 in sentences
    # Matches "i give it an 8", "it was 10", "i'd say 7", etc.
    match = re.search(r'\b(10|[1-9])\b', text)
    if match:
        return int(match.group(1))
    
    # Simple word map
    word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
    for word, val in word_map.items():
        if word in text.lower():
            return val
    return None

class NodeExecutor(ABC):
    @abstractmethod
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        pass

class MessageNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        text = node_data.get("label", "")
        variables = context.get("variables", {})
        
        # Auto-infer salutation if gender is present
        if "gender" in variables:
            salutation = "Ma'am" if variables["gender"] == "female" else "Sir"
            text = text.replace("{{salutation}}", salutation)
        elif "{{salutation}}" in text:
            text = text.replace("{{salutation}}", "Sir/Ma'am")
            
        # Resolve all other variables
        for key, value in variables.items():

            pattern = re.compile(re.escape("{{" + key + "}}"), re.IGNORECASE)
            text = pattern.sub(str(value), text)
        
        return {
            "status": "SUCCESS",
            "action": "speak",
            "logs": f"Spoke: {text}"
        }

class ApiNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        url = node_data.get("label", "")
        variables = context.get("variables", {})
        for key, value in variables.items():
            url = url.replace("{{" + key + "}}", str(value))
        
        print(f"  [API_EXEC] Final URL: {url}")
            
        if "/mock/crm/" in url:

            phone = url.split("/")[-1].replace(" ", "+") 
            result = MOCK_CRM.get(phone, MOCK_CRM["default"])
            
            if "last_service_date" in result:
                try:
                    dt = datetime.strptime(result["last_service_date"], "%Y-%m-%d")
                    result["last_svc_formatted"] = dt.strftime("%B %d")
                except:
                    result["last_svc_formatted"] = result["last_service_date"]
            
            context["variables"].update(result)
            return {
                "status": "SUCCESS",
                "action": "api_call",
                "logs": f"CRM Lookup ({phone}): {result}",
                "result": result
            }
        
        if "/mock/service_details/" in url:
            customer_id = str(context.get("variables", {}).get("id", "default"))
            path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "data", "service_details.json"))
            try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        data = json.load(f)
                        result = data.get(customer_id, {})
                        context["variables"].update(result)
                        return {
                            "status": "SUCCESS",
                            "action": "api_call",
                            "outcome": "success",
                            "logs": f"Service Details Lookup (ID: {customer_id}): {result}",
                            "result": result
                        }
            except Exception as e:
                print(f"DEBUG: Error reading service details: {e}")
                return {"status": "SUCCESS", "outcome": "error", "logs": f"Local API Failure: {str(e)}"}
            
            return {"status": "SUCCESS", "outcome": "success", "action": "api_call", "logs": "Service Details not found", "result": {}}

        # REAL API CALL (For production integration)
        import httpx
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)

                if response.status_code == 200:
                    result = response.json()
                    context["variables"].update(result)
                    return {"status": "SUCCESS", "outcome": "success", "logs": f"API Success: {url}", "result": result}
                else:
                    return {"status": "SUCCESS", "outcome": "error", "logs": f"API Error {response.status_code}: {url}"}
        except Exception as e:
            return {"status": "SUCCESS", "outcome": "error", "logs": f"API Exception: {str(e)}"}



class ConditionNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        condition = node_data.get("label", "")
        variables = context.get("variables", {})
        user_msgs = [m for m in context.get("history", []) if m.get("role") == "user"]
        last_msg = user_msgs[-1].get("text", "").lower().strip() if user_msgs else ""
        
        print(f"\n[ENGINE] Evaluating Condition: '{condition}'")
        print(f"[ENGINE] Last User Message: '{last_msg}'")

        # 1. Numeric Extraction for Ratings
        if any(op in condition for op in ["<", ">", "=="]):
            val = extract_number(last_msg)
            if val is not None:
                # Use the first word as the variable name
                var_name = condition.split()[0]
                context["variables"][var_name] = val
                print(f"[DATA_CAPTURE] Set {var_name} = {val}")

        # 2. Date Extraction for Callbacks
        parsed_dt = parse_date_phrase(last_msg)
        if not parsed_dt and any(x in last_msg for x in ['later', 'busy', 'meeting', 'not now']):
            from datetime import timedelta
            parsed_dt = datetime.now().date() + timedelta(days=1)

        if parsed_dt:
            # 1. Check for specific times (e.g., 10 AM, 1:30 PM, 4pm)
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', last_msg)
            if time_match:
                hh = int(time_match.group(1))
                mm = time_match.group(2) or "00"
                period = time_match.group(3).upper()
                time_suffix = f"{hh:02d}:{mm} {period}"
            # 2. Check for "after X hours"
            elif re.search(r'(?:after|in)\s+(\d+)\s+(?:hour|hr)', last_msg):
                hrs_match = re.search(r'(?:after|in)\s+(\d+)\s+(?:hour|hr)', last_msg)
                hrs = int(hrs_match.group(1))
                time_suffix = (datetime.now() + timedelta(hours=hrs)).strftime("%I:%M %p")
            # 3. Keyword slots
            elif "evening" in last_msg: time_suffix = "06:00 PM"
            elif "afternoon" in last_msg or "after noon" in last_msg: time_suffix = "02:00 PM"
            elif "morning" in last_msg: time_suffix = "10:00 AM"
            else: time_suffix = "09:00 AM"

            formatted = f"{format_date_full(parsed_dt)} at {time_suffix}"
            variables["confirmed_date"] = formatted

            variables["pickup_time"] = formatted # Support P&D templates
            variables["callback_time"] = formatted
            variables["callback_confirmation"] = f"I've scheduled a reminder to call you back at {formatted}"
            print(f"[DATA_CAPTURE] Extracted Date: {formatted}")
        else:
            if "callback_confirmation" not in variables:
                variables["callback_confirmation"] = "I'll check back later"


        # 3. Intent Detection
        condition_norm = condition.lower().strip()
        is_busy = any(word in last_msg for word in ['busy', 'meeting', 'later', 'call back', 'not now', 'driving'])
        if is_busy:
            return {"status": "SUCCESS", "outcome": "busy", "logs": "User intent: BUSY"}

        is_wrong = any(word in last_msg for word in ["wrong number", "not me", "incorrect"])
        if is_wrong:
            return {"status": "SUCCESS", "outcome": "wrong_number", "logs": "User intent: WRONG_NUMBER"}

        # DISSATISFACTION / COMPLAINT (For Feedback Flow)
        complaint_words = ["no", "not satisfied", "issue", "noise", "problem", "unhappy", "bad", "worst"]
        is_complaint = any(word in last_msg for word in complaint_words)
        
        # If the condition specifically asks about satisfaction
        if "satisfaction" in condition_norm or "satisfactory" in condition_norm:
            if is_complaint:
                variables["satisfaction_check"] = False
                return {"status": "SUCCESS", "outcome": "false", "logs": "User intent: NOT SATISFIED (Escalating)"}
            else:
                variables["satisfaction_check"] = True
                # Continue to normal evaluation for "Yes/Positive"

        # 4. P&D Specific Intents
        is_drop = any(word in last_msg for word in ['drop', 'send', 'delivery', 'deliver'])
        is_pickup = any(word in last_msg for word in ['pickup', 'pick up', 'self pick'])
        
        if "delivery_option" in condition_norm:
            if is_drop: return {"status": "SUCCESS", "outcome": "drop", "logs": "User intent: DROP/DELIVERY"}
            if is_pickup: return {"status": "SUCCESS", "outcome": "pickup", "logs": "User intent: PICKUP"}

        # 5. Additional Concerns Ack
        if "concerns" in condition_norm:
            if any(word in last_msg for word in ['no', 'none', 'nothing else', 'not really']):
                variables["additional_concerns_ack"] = ""
            else:
                variables["additional_concerns_ack"] = "I've noted that down. "

        # 6. Transfer Intent
        # Use regex to avoid false positives with "speaking" during ID checks
        transfer_keywords = ['advisor', 'manager', 'person', 'representative', 'human', 'specialist']
        is_transfer = any(word in last_msg for word in transfer_keywords) or \
                      re.search(r'\b(talk|speak)\s+(to|with|a person)\b', last_msg) or \
                      re.search(r'\b(connect|transfer)\b', last_msg)
        
        if is_transfer:
            return {"status": "SUCCESS", "outcome": "transfer", "logs": "User intent: TRANSFER"}


        # 7. Dynamic Evaluation


        try:
            # Handle direct string outcomes from frontend if they happen
            if condition_norm == "true": return {"status": "SUCCESS", "outcome": "true"}
            if condition_norm == "false": return {"status": "SUCCESS", "outcome": "false"}
            
            result = eval(condition, {"__builtins__": None}, context["variables"])
            print(f"[ENGINE] Evaluating: '{condition}' -> {result}")
            print(f"[ENGINE] Current Variables State: {context['variables']}")
            return {"status": "SUCCESS", "outcome": "true" if result else "false"}
        except:
            # Fallback to simple keyword matching for "Yes/No"
            is_yes = any(word in last_msg for word in ["yes", "yeah", "correct", "yep", "speaking", "sure", "ok", "good", "satisfied", "proceed"])
            print(f"[ENGINE] Keyword Match: {'YES' if is_yes else 'NO'}")
            return {"status": "SUCCESS", "outcome": "true" if is_yes else "false"}


class PassThroughExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "SUCCESS", "logs": f"Executed {node_data.get('type')}"}

class TransferNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        agent = node_data.get("agent_name", "a specialist")
        reason = node_data.get("reason", "further assistance")
        return {
            "status": "SUCCESS",
            "action": "transfer",
            "logs": f"Spoke: I'm transferring your call to our {agent} for a {reason}. Please stay on the line.\n[SYSTEM] TRANSFER to {agent}"
        }


class EndNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "status": "COMPLETED",
            "action": "hangup",
            "logs": "Conversation Ended"
        }

from database import DatabaseManager
db_manager = DatabaseManager()

class ActionNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        action_type = node_data.get("action_type", "")
        variables = context.get("variables", {})
        call_sid = context.get("session_id", "unknown")
        customer_id = variables.get("id", "Unknown")
        
        print(f"  [ACTION_EXEC] Running action: {action_type}")
        
        if action_type == "log_consent":
            # IRDAI Compliance
            granted = variables.get("consent_granted", True)
            db_manager.log_consent(call_sid, customer_id, "renewal", granted)
            return {"status": "SUCCESS", "logs": f"Action: Logged consent for {customer_id}"}
            
        if action_type == "mark_dnd":
            # Opt-out compliance
            db_manager.update_lead_state(call_sid, lead_status="DND", last_action="Customer requested DND")
            return {"status": "SUCCESS", "logs": f"Action: Marked {customer_id} as DND"}

        if action_type == "cancel_followup":
            db_manager.cancel_followup(customer_id)
            return {"status": "SUCCESS", "logs": f"Action: Cancelled followups for {customer_id}"}

        if action_type == "schedule_callback":
            user_msgs = [m for m in context.get("history", []) if m.get("role") == "user"]
            last_msg = user_msgs[-1].get("text", "").lower().strip() if user_msgs else ""
            
            # Parse callback date/time from user's input
            from datetime import timedelta
            parsed_dt = parse_date_phrase(last_msg)
            if not parsed_dt:
                # Default to tomorrow if not explicitly understood
                parsed_dt = datetime.now().date() + timedelta(days=1)
                
            # Time slot detection
            if "evening" in last_msg:
                time_suffix = "06:00 PM"
            elif "afternoon" in last_msg or "after noon" in last_msg:
                time_suffix = "02:00 PM"
            elif "morning" in last_msg:
                time_suffix = "10:00 AM"
            else:
                time_suffix = "11:00 AM" # Professional default
                # Try specific time match
                time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', last_msg)
                if time_match:
                    hh = int(time_match.group(1))
                    mm = time_match.group(2) or "00"
                    period = time_match.group(3).upper()
                    time_suffix = f"{hh:02d}:{mm} {period}"
            
            formatted = f"{format_date_full(parsed_dt)} at {time_suffix}"
            variables["callback_time"] = formatted
            variables["confirmed_date"] = formatted
            print(f"[DATA_CAPTURE] ActionNode schedule_callback: parsed '{last_msg}' into '{formatted}'")
            
            db_manager.schedule_followup(customer_id, call_sid, formatted)
            db_manager.update_lead_state(call_sid, lead_status="WARM_LEAD", disposition="BUSY_RETRY", last_action=f"Scheduled Callback for {formatted}")
            
            return {"status": "SUCCESS", "logs": f"Action: Scheduled callback for {customer_id} at {formatted}"}

        return {"status": "SUCCESS", "logs": f"Executed action {action_type}"}

class ContextLogicNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Specialized logic for calculating stage-based content
        variables = context.get("variables", {})
        expiry_date_str = variables.get("policy_expiry_date")
        
        if not expiry_date_str:
            return {"status": "SUCCESS", "logs": "No expiry date found for stage logic"}
            
        try:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            today = datetime.now().date()
            days_until = (expiry_date - today).days
            
            # Determine Stage (T-30, T-15, T-7, T-1, T+1)
            if days_until > 20: stage = 1 # T-30
            elif days_until > 10: stage = 2 # T-15
            elif days_until > 3: stage = 3 # T-7
            elif days_until >= 0: stage = 4 # T-1
            else: stage = 5 # T+1 (Expired)
            
            variables["stage"] = stage
            variables["days_until_expiry"] = days_until
            
            # Dynamic Greeting Calculation (Parity with backend)
            if stage == 1: msg = "calling regarding your policy renewal which is due in about a month."
            elif stage == 2: msg = "following up on your insurance renewal due in the next two weeks."
            elif stage == 3: msg = "sharing a final reminder for your policy which expires in a few days."
            elif stage == 4: msg = "calling urgently as your insurance expires tomorrow. We should renew it today."
            else: msg = "calling regarding your recently expired policy. We can still help you with a break-in renewal."
            
            variables["greeting_context"] = msg
            return {"status": "SUCCESS", "logs": f"Calculated Stage {stage} ({days_until} days left)"}
        except Exception as e:
            return {"status": "SUCCESS", "logs": f"Context logic error: {e}"}

class DashboardBridgeNodeExecutor(NodeExecutor):
    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        # Sync orchestrator state to the production dashboard tables
        variables = context.get("variables", {})
        call_sid = context.get("session_id", "unknown")
        
        lead_status = variables.get("lead_status", "INTERESTED")
        lead_score = int(variables.get("lead_score", 50))
        disposition = variables.get("disposition", "ACTIVE_FLOW")
        
        print(f"  [DASHBOARD_SYNC] Updating call_sid {call_sid} (Score: {lead_score})")
        
        db_manager.update_lead_state(call_sid, 
            lead_status=lead_status,
            lead_score=lead_score,
            disposition=disposition,
            last_action=node_data.get("label", "Flow Step Update")
        )
        
        return {"status": "SUCCESS", "logs": "Dashboard Sync Complete"}

class NodeRegistry:
    def __init__(self):
        self.executors = {
            "startnode": PassThroughExecutor(), # Silent start
            "messagenode": MessageNodeExecutor(),
            "apinode": ApiNodeExecutor(),
            "conditionnode": ConditionNodeExecutor(),
            "transfernode": TransferNodeExecutor(),
            "actionnode": ActionNodeExecutor(),
            "contextlogicnode": ContextLogicNodeExecutor(),
            "dashboardbridgenode": DashboardBridgeNodeExecutor(),
            "endnode": EndNodeExecutor()
        }
    
    def get_executor(self, node_type: str) -> NodeExecutor:
        return self.executors.get(node_type.lower())
