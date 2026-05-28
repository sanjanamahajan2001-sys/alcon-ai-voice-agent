import asyncio
import os
import json
import random
from datetime import datetime
from database import DatabaseManager
from dms_adapter import LocalJSONDMSAdapter

# Global thread-safe list to store dashboard console logs
CAMPAIGN_CONSOLE_LOGS = []

def add_console_log(message, category="system"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = f"[{timestamp}] "
    if category == "system":
        log_line = f"{prefix}[SYSTEM] {message}"
    elif category == "ai":
        log_line = f"{prefix}[AI Agent] {message}"
    elif category == "customer":
        log_line = f"{prefix}[Customer] {message}"
    elif category == "outcome":
        log_line = f"{prefix}Outcome: {message}"
    else:
        log_line = f"{prefix}{message}"
    
    CAMPAIGN_CONSOLE_LOGS.append(log_line)
    print(log_line)  # Also print to stdout for debugging

# Mapping of flow types to their corresponding template JSON file names
TEMPLATE_MAP = {
    "booking": "service_booking_prod.json",
    "pd_pickup_coordination": "pd_pickup_coordination.json",
    "pd_workshop_update": "pd_workshop_update.json",
    "pd_ready": "pd_ready_delivery.json",
    "insurance_start": "insurance_v2_template.json",
    "feedback_3rd_day": "post_service_feedback.json",
    "feedback_15day_v2": "post_service_feedback_15day.json",
    "pre_sales": "pre_sales_template.json",
    "reception": "inbound_receptionist.json"
}

class TelephonySimulator:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.dms = LocalJSONDMSAdapter()
        
        # Load templates directory path relative to current file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(base_dir, "..", "flow_orchestrator", "server", "templates")
        if not os.path.exists(self.templates_dir):
            # Try workspace absolute path
            self.templates_dir = "/home/sanjana/Alcon/poc/flow_orchestrator/server/templates"

    def load_flow_template(self, flow_type):
        filename = TEMPLATE_MAP.get(flow_type)
        if not filename:
            return None
        filepath = os.path.join(self.templates_dir, filename)
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                print(f"[SIMULATOR] Template file not found: {filepath}")
        except Exception as e:
            print(f"[SIMULATOR ERROR] Failed to load template {filename}: {e}")
        return None

    def get_mock_customer_responses(self, node_id, flow_type):
        """Generates contextual customer responses based on the current step and flow type."""
        # Common responses for greeting or initial confirmation
        if "greet" in node_id or node_id == "greeting":
            return [
                "Yes, this is Sanjana. Go ahead.",
                "Hello! Yes, speaking. How can I help you?",
                "Yes, I can talk right now. Please tell me.",
                "Speaking. What is this regarding?"
            ]
        
        if "check_id" in node_id or "verify" in node_id:
            return [
                "Yes, that's my vehicle. You have the right details.",
                "Correct. That is my car.",
                "Yes, I am the owner. Please proceed."
            ]

        # Flow-specific responses
        if flow_type == "booking":
            if "ask" in node_id or "due" in node_id or "slot" in node_id:
                return [
                    "Sure, please book a slot for tomorrow morning at 10 AM.",
                    "Yes, I need my service scheduled. Can we do Saturday at 2 PM?",
                    "Actually, my car runs fine but I'll book it anyway. Any slots on Friday?",
                    "Can you pick up my car around 9:00 AM on Monday?"
                ]
        elif flow_type == "pd_pickup_coordination":
            if "pickup_ask" in node_id:
                return [
                    "Please have Rajesh come tomorrow morning around 9:30 AM.",
                    "Is 11 AM okay? I'll be at home then.",
                    "Tell Rajesh to reach by 10 AM, I have to leave for office after that."
                ]
        elif flow_type == "pd_workshop_update":
            if "estimate" in node_id or "update" in node_id or "diag" in node_id:
                return [
                    "Okay, go ahead with the brake pad replacement and wheel alignment.",
                    "Please proceed with the standard service. Let me know once done.",
                    "Sure, the estimated cost looks reasonable. Go ahead."
                ]
        elif flow_type == "pd_ready":
            if "ready" in node_id or "delivery" in node_id:
                return [
                    "Please drop it off at my residence at 6 PM this evening.",
                    "Awesome, I will pick it up myself from the workshop.",
                    "Can the driver drop it tomorrow morning at 9 AM?"
                ]
        elif flow_type == "insurance_start":
            if "stage" in node_id or "renew" in node_id or "offer" in node_id or "quote" in node_id:
                return [
                    "Yes, I'm looking to renew my insurance policy. What are the best quotes?",
                    "Please send me the quote comparison over WhatsApp.",
                    "I want comprehensive coverage with zero depreciation. What is the premium?"
                ]
        elif "feedback" in flow_type:
            if "ask" in node_id or "rate" in node_id:
                return [
                    "I would rate the service a solid 9 out of 10. The car feels amazing!",
                    "Everything was great, but the wash could have been cleaner. I'd give it an 8.",
                    "I am very happy with the experience. 10/10!"
                ]
        elif flow_type == "pre_sales":
            if "offer" in node_id or "exchange" in node_id or "upgrade" in node_id:
                return [
                    "I am actually interested in exchanging my old car for the new Creta. Tell me more.",
                    "What is the maximum exchange bonus you are offering?",
                    "Can you send details of the low EMI scheme for the upgrade?"
                ]
        
        # Generic fallbacks
        return [
            "Yes, that sounds perfect.",
            "Okay, please do that.",
            "Could you send me the details on WhatsApp?",
            "Sure, thank you for the information."
        ]

    async def simulate_call(self, job):
        job_id = job["id"]
        customer_id = job["customer_id"]
        customer_name = job["customer_name"]
        car_model = job["car_model"]
        flow_type = job["flow_type"]
        
        add_console_log(f"Initiating simulated outbound call for {customer_name} ({car_model}) -> Flow: {flow_type}", "system")
        self.db.update_campaign_job_status(job_id, "processing", progress_percent=10, active_node="Call Initiated")
        await asyncio.sleep(1.5)
        
        # Generate a unique dummy call SID for integration logging
        call_sid = f"SIM_{flow_type}_{job_id}_{random.randint(1000, 9999)}"
        self.db.update_call_status(call_sid, "initiated", customer_id=customer_id, stage=1)
        
        template = self.load_flow_template(flow_type)
        transcript = []
        outcome = DatabaseManager.OUTCOME_WARM_NURTURE
        
        if not template:
            # Fallback static simulation if template json is missing
            add_console_log(f"Template for '{flow_type}' not found. Running static mock pipeline...", "system")
            steps = ["Greeting", "Verification", "Offer Pitch", "Closing"]
            for i, step in enumerate(steps):
                percent = int(10 + (i + 1) * 20)
                self.db.update_campaign_job_status(job_id, "processing", progress_percent=percent, active_node=step)
                
                ai_speech = f"Hello {customer_name}, this is Alcon regarding your {flow_type} task. Is this a good time to talk?" if i == 0 else f"Running step: {step} details."
                add_console_log(ai_speech, "ai")
                transcript.append({"role": "assistant", "content": ai_speech})
                await asyncio.sleep(1.5)
                
                cust_response = random.choice(self.get_mock_customer_responses(step.lower(), flow_type))
                add_console_log(cust_response, "customer")
                transcript.append({"role": "user", "content": cust_response})
                await asyncio.sleep(1.5)
            
            outcome = DatabaseManager.OUTCOME_HOT_TRANSFERRED if flow_type == "reception" else DatabaseManager.OUTCOME_WARM_NURTURE
        else:
            # Dynamic template-driven simulation
            nodes = template.get("nodes", [])
            edges = template.get("edges", [])
            
            # Map node IDs to node configurations for quick lookup
            node_map = {node["id"]: node for node in nodes}
            
            # Find start node
            current_node = None
            for node in nodes:
                if node.get("type") == "startNode" or "start" in node.get("id", "").lower():
                    current_node = node
                    break
            if not current_node and nodes:
                current_node = nodes[0]
            
            step_count = 0
            visited = set()
            
            # Simple traversal engine
            while current_node and current_node["id"] not in visited:
                node_id = current_node["id"]
                node_type = current_node.get("type", "")
                node_label = current_node.get("data", {}).get("label", "")
                visited.add(node_id)
                
                step_count += 1
                percent = min(90, int(10 + (step_count * 10)))
                self.db.update_campaign_job_status(job_id, "processing", progress_percent=percent, active_node=node_id)
                
                # Format node_label with customer metadata variables
                formatted_label = node_label.replace("{{name}}", customer_name).replace("{{car_model}}", car_model)
                formatted_label = formatted_label.replace("{{salutation}}", "Mr." if random.random() > 0.5 else "Ms.")
                formatted_label = formatted_label.replace("{{pickup_time}}", "10:30 AM")
                
                if node_type == "messageNode" or node_type == "greetingNode":
                    add_console_log(formatted_label, "ai")
                    transcript.append({"role": "assistant", "content": formatted_label})
                    await asyncio.sleep(1.5)
                    
                    # Generate randomized user response
                    cust_response = random.choice(self.get_mock_customer_responses(node_id, flow_type))
                    add_console_log(cust_response, "customer")
                    transcript.append({"role": "user", "content": cust_response})
                    await asyncio.sleep(1.5)
                
                elif node_type == "apiNode":
                    add_console_log(f"Running automated API node: {formatted_label}", "system")
                    await asyncio.sleep(1.0)
                
                elif node_type == "conditionNode":
                    add_console_log(f"Evaluating conditional logic: {formatted_label}", "system")
                    await asyncio.sleep(1.0)
                
                elif node_type == "endNode":
                    add_console_log(f"Reached final flow branch: {formatted_label}", "system")
                    break
                
                # Determine next node by edges
                next_node_id = None
                out_edges = [edge for edge in edges if edge["source"] == node_id]
                
                if out_edges:
                    # If it's a conditional node, decide a branch (true/false) randomly or based on a condition
                    if node_type == "conditionNode":
                        # Prefer true handle for positive demo flow pathing
                        chosen_edge = next((e for e in out_edges if e.get("sourceHandle") == "true"), out_edges[0])
                        # Occasionally take the false handle
                        if random.random() < 0.15:
                            chosen_edge = next((e for e in out_edges if e.get("sourceHandle") == "false"), out_edges[0])
                    else:
                        chosen_edge = out_edges[0]
                    
                    next_node_id = chosen_edge["target"]
                
                current_node = node_map.get(next_node_id) if next_node_id else None
            
            # Map flows to realistic business outcomes
            if flow_type in ["booking", "pd_pickup_coordination", "pd_ready"]:
                outcome = DatabaseManager.OUTCOME_SERVICE_REDIRECTED if random.random() > 0.3 else DatabaseManager.OUTCOME_HOT_CALLBACK
            elif flow_type == "insurance_start":
                outcome = DatabaseManager.OUTCOME_HOT_CALLBACK if random.random() > 0.4 else DatabaseManager.OUTCOME_WARM_NURTURE
            elif flow_type == "pre_sales":
                outcome = DatabaseManager.OUTCOME_HOT_TRANSFERRED if random.random() > 0.5 else DatabaseManager.OUTCOME_WARM_NURTURE
            elif flow_type == "reception":
                outcome = DatabaseManager.OUTCOME_HOT_TRANSFERRED
            else:
                outcome = DatabaseManager.OUTCOME_WARM_NURTURE

        # Update both local DB call logs & updates back to the JSON DMS mock!
        self.db.log_call_history(
            call_sid=call_sid,
            customer_id=customer_id,
            stage=1,
            transcript=transcript,
            outcome=outcome
        )
        self.db.update_call_status(call_sid, "completed", customer_id=customer_id)
        
        # Sync outcome details directly back to the Local DMS JSON adapter!
        self.dms.update_customer_state(customer_id, {
            "campaign_triggered_at": datetime.now().isoformat(),
            "campaign_last_outcome": outcome,
            "campaign_status": "synced"
        })
        
        add_console_log(f"Campaign session concluded successfully for {customer_name}.", "system")
        add_console_log(f"Final Call Outcome: {outcome}", "outcome")
        
        self.db.update_campaign_job_status(
            job_id, 
            "completed", 
            progress_percent=100, 
            active_node="Session Completed",
            log_text=f"Outcome: {outcome}"
        )

class CampaignQueueRunner:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.simulator = TelephonySimulator(db_manager)
        # Production Concurrency Protection: supports up to 100 concurrent simulated active calls
        self.semaphore = asyncio.Semaphore(100)
        self._running = False
        self.active_jobs = set()  # Track job IDs currently active in memory to prevent double fetching

    async def start(self):
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._loop())
        add_console_log("Central Campaign Campaign Queue Runner started successfully.", "system")

    async def stop(self):
        self._running = False
        add_console_log("Central Campaign Campaign Queue Runner stopped.", "system")

    async def _process_job(self, job):
        job_id = job["id"]
        async with self.semaphore:
            try:
                await self.simulator.simulate_call(job)
            except Exception as e:
                print(f"[QUEUE RUNNER ERROR] Failed processing job {job_id}: {e}")
                self.db.update_campaign_job_status(job_id, "failed", active_node="Error", log_text=str(e))
                add_console_log(f"Job ID {job_id} failed: {e}", "system")
            finally:
                # Remove from in-flight tracker upon completion
                self.active_jobs.discard(job_id)

    async def _loop(self):
        while self._running:
            try:
                # 1. Poll active jobs from the campaign queue
                all_jobs = self.db.get_queued_jobs()
                # Exclude jobs that are already in-flight in memory
                queued_jobs = [j for j in all_jobs if j["status"] == "queued" and j["id"] not in self.active_jobs]
                
                if queued_jobs:
                    # 2. Interleaved Round-Robin Scheduler (by flow_type)
                    jobs_by_flow = {}
                    for job in queued_jobs:
                        ft = job["flow_type"]
                        jobs_by_flow.setdefault(ft, []).append(job)
                    
                    interleaved_jobs = []
                    max_len = max(len(lst) for lst in jobs_by_flow.values()) if jobs_by_flow else 0
                    for i in range(max_len):
                        for ft in sorted(jobs_by_flow.keys()):
                            if i < len(jobs_by_flow[ft]):
                                interleaved_jobs.append(jobs_by_flow[ft][i])
                    
                    # 3. Calculate dynamic live agent transfer pacing (Gap 1 Fix)
                    # Load advisors status to dynamically restrict concurrency based on live agent availability
                    advisors_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "advisors.json")
                    available_agents = 0
                    if os.path.exists(advisors_path):
                        try:
                            with open(advisors_path, "r", encoding="utf-8") as f:
                                advisors = json.load(f)
                                available_agents = sum(1 for a in advisors if a.get("status") == "available")
                        except Exception as e:
                            print(f"[QUEUE RUNNER ERROR] Failed to read advisors.json for pacing: {e}")
                    
                    # Concurrency ceiling is max(2, available_agents * 3) to prevent starving live queues
                    dynamic_ceiling = max(2, available_agents * 3)
                    
                    current_active = len(self.active_jobs)
                    available_slots = min(100 - current_active, dynamic_ceiling - current_active)
                    available_slots = max(0, available_slots)
                    
                    if available_slots <= 0:
                        await asyncio.sleep(1.0)
                        continue
                        
                    batch = interleaved_jobs[:available_slots]
                    if not batch:
                        await asyncio.sleep(1.0)
                        continue
                        
                    add_console_log(
                        f"Queue manager dispatching a batch of {len(batch)} interleaved campaign jobs. "
                        f"In-flight: {current_active}, Live Agents: {available_agents}, Pacing Ceiling: {dynamic_ceiling}", 
                        "system"
                    )
                    
                    # 4. Spool calls asynchronously with Twilio-safe pacing (0.2s delay = 5 calls/sec)
                    for job in batch:
                        job_id = job["id"]
                        self.active_jobs.add(job_id)
                        
                        # Instantly mark as processing in the DB to avoid double-processing on next poll
                        self.db.update_campaign_job_status(job_id, "processing", progress_percent=5, active_node="Queueing")
                        
                        # Launch task in the background
                        asyncio.create_task(self._process_job(job))
                        
                        # 0.2s pacing delay (5 CPS spool rate)
                        await asyncio.sleep(0.2)
                        
                    add_console_log(f"Batch dispatch completed. Running concurrent spools.", "system")
                else:
                    await asyncio.sleep(1.0)
            except Exception as e:
                print(f"[QUEUE RUNNER LOOP ERROR]: {e}")
                await asyncio.sleep(2.0)
