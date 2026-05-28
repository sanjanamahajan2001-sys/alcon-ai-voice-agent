    async def execute(self, node_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        condition = node_data.get("label", "")
        variables = context.get("variables", {})
        session_id = context.get("session_id", context.get("call_sid", "unknown"))
        
        # Use explicit user_input from context, fallback to history
        last_msg = context.get("user_input", "").lower().strip()
        if not last_msg:
            user_msgs = [m for m in context.get("history", []) if m.get("role") == "user"]
            last_msg = user_msgs[-1].get("text", "").lower().strip() if user_msgs else ""
        
        print(f"[DEBUG] Resolved last_msg: '{last_msg}'")

        # 1. Base Intent Detection
        is_busy = any(word in last_msg for word in ['busy', 'meeting', 'later', 'call back', 'not now', 'driving'])
        is_wrong = any(word in last_msg for word in ["wrong number", "not me", "incorrect", "wrong person", "sold", "no longer have", "don't have that car"])
        is_yes = any(word in last_msg for word in ["yes", "yeah", "correct", "yep", "speaking", "sure", "ok", "good", "satisfied", "proceed", "hello", "hi", "send", "share", "whatsapp"])
        is_no = any(word in last_msg for word in ["no", "nope", "dont", "don't", "not now", "stop", "not interested"])
        is_dnd = any(word in last_msg for word in ['stop', 'don\'t call', 'do not call', 'remove', 'dnd', 'annoying', 'not interested'])
        is_transfer = any(word in last_msg for word in ['advisor', 'manager', 'person', 'human', 'specialist', 'connect', 'transfer', 'speak to someone'])
        
        # 2. Priority Branching (Exits & Transfers)
        if is_busy:
            self.db.update_lead_state(session_id, lead_status="WARM_LEAD", disposition="BUSY_RETRY", last_action="Requested Callback")
            self.log_transition(session_id, context.get("current_node_id"), "BUSY_EXIT", "Busy intent detected", raw_input=last_msg)
            return {"status": "SUCCESS", "outcome": "busy", "text": "No problem! I understand you're busy. I'll arrange a callback for you later. Have a great day!"}

        if is_wrong:
            self.db.update_lead_state(session_id, lead_status="NOT_INTERESTED", disposition="WRONG_NUMBER", last_action="Incorrect Person")
            self.log_transition(session_id, context.get("current_node_id"), "WRONG_DATA_EXIT", "Wrong person/sold car intent detected", raw_input=last_msg)
            return {"status": "SUCCESS", "outcome": "wrong_number", "text": "I apologize for the confusion. I'll update our records to ensure you're not contacted again regarding this vehicle. Have a wonderful day!"}

        if is_transfer or "connect" in last_msg or "transfer" in last_msg:
            self.db.update_lead_state(session_id, lead_status="NEGOTIATING", lead_score=85, disposition="TRANSFER_REQUESTED", last_action="Requested Human Expert", escalation_status="IN_PROGRESS", escalation_reason="MANUAL_REQUEST")
            self.log_transition(session_id, context.get("current_node_id"), "TRANSFER_EXIT", "Manual transfer request detected", raw_input=last_msg)
            return {"status": "SUCCESS", "outcome": "transfer", "text": "Sure! I'll connect you to our Sales Manager who can assist you with more specific details. Please stay on the line."}

        if is_dnd:
            self.db.update_lead_state(session_id, lead_status="DND", lead_score=0, disposition="REJECTED", last_action="Explicit Rejection")
            mark_customer_dnd_permanent(variables.get("id"))
            return {"status": "SUCCESS", "outcome": "dnd", "text": "I understand. I've marked your number for exclusion from our lists. Have a great day."}

        # 3. Persona-Aware Query Bridges
        if any(word in last_msg for word in ["catch", "hidden", "fee", "loyalty", "bonus", "years", "price", "cost", "emi", "finance"]):
            bridge = "I understand you have some specific questions about the costs and benefits. Let me address those for you."
            if "loyalty" in last_msg or "years" in last_msg:
                bridge = "It's wonderful to speak with a long-term Hyundai owner! I'd be happy to explain our exclusive loyalty benefits for you."
            elif "catch" in last_msg or "hidden" in last_msg or "fee" in last_msg:
                bridge = "I completely appreciate your need for transparency. Let me clarify the exact costs and current offers."
            
            return {"status": "SUCCESS", "outcome": "direct_query", "text": bridge}

        # 4. Node-Specific Evaluation
        if condition == "Consent/Identity Check":
            engine = context.get("intent_engine")
            if engine:
                trace = engine.explain_decision(last_msg)
                decision = trace["decision"]
                self.log_transition(session_id, context.get("current_node_id"), "ConditionEvaluation", "Intent classification", raw_input=last_msg, intent=decision)

                if decision == "HOT": return {"status": "SUCCESS", "outcome": "true"}
                if decision == "WARM": return {"status": "SUCCESS", "outcome": "busy", "text": "I see. Would it be better if I call you back later when you have more time?"}
                if decision == "EXIT": return {"status": "SUCCESS", "outcome": "wrong_number", "text": "Understood. I'll update our records. Have a nice day!"}
            
            return {"status": "SUCCESS", "outcome": "true" if is_yes else "false" if is_no else "true"}

        if condition == "Query Intent Check":
            if "price" in last_msg or "cost" in last_msg or "how much" in last_msg: return {"status": "SUCCESS", "outcome": "query"}
            return {"status": "SUCCESS", "outcome": "query"} # Default for now

        if condition == "Transfer Consent Check":
            return {"status": "SUCCESS", "outcome": "true" if is_yes else "false"}

        if condition == "Service Bridge Eligibility":
            return {"status": "SUCCESS", "outcome": "is_due" if variables.get("is_due") else "not_due"}

        return {"status": "SUCCESS", "outcome": "true"}
