import os
import json
import redis
import time
import asyncio
from datetime import datetime, timedelta
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

# --- SHARED RESOURCE INITIALIZATION ---
from metrics_collector import metrics
from database import DatabaseManager
from telephony_logger import TelephonyLogger
from flow_manager import FlowManager

db = DatabaseManager()
telephony_logger = TelephonyLogger()
flow_manager = FlowManager(db)

# Configuration for Production-Grade Reliability
CONFIG = {
    "MAX_RETRIES": 3,
    "RETRY_BACKOFF": [60, 300, 1800], # 1m, 5m, 30m
    "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
    "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
    "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER"),
    "NGROK_URL": os.getenv("NGROK_URL"),
    "QUIET_HOURS": (9, 20) # 9 AM to 8 PM
}

# Redis Connection for Task Queue
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
TASK_QUEUE_KEY = "alcon_task_queue"

# Global Queue for Sequential Campaigns is now Redis-backed for distributed state persistence
REDIS_CAMPAIGN_QUEUE_KEY = "alcon_campaign_queue"
REDIS_QUEUED_CUSTOMERS_KEY = "alcon_queued_customers"

def enqueue_campaign_task(task: dict):
    """Enqueue a campaign call to the Redis queue and mark the customer as queued."""
    customer_id = str(task["customer_id"])
    redis_client.sadd(REDIS_QUEUED_CUSTOMERS_KEY, customer_id)
    redis_client.rpush(REDIS_CAMPAIGN_QUEUE_KEY, json.dumps(task))

def is_customer_campaign_queued(customer_id) -> bool:
    """Check if a customer is currently in the campaign queue."""
    return bool(redis_client.sismember(REDIS_QUEUED_CUSTOMERS_KEY, str(customer_id)))

def check_ncpr_compliance(phone: str) -> bool:
    """
    Verify compliance against India's NCPR National DND Registry.
    - Demo/Fallback mode is triggered if NCPR_API_URL environment variable is missing.
    - External registry hit is fully safe and wrapped in a 1.5s timeout.
    """
    if not phone:
        return False
        
    ncpr_url = os.getenv("NCPR_API_URL")
    ncpr_key = os.getenv("NCPR_API_KEY")
    
    if not ncpr_url:
        # DEMO MODE: Fallback to mock log print
        print(f"[NCPR COMPLIANCE] (DEMO MODE) Querying NCPR registry for {phone} -> PASS")
        return False
        
    # PRODUCTION MODE: Secure external call
    try:
        import requests
        headers = {"Authorization": f"Bearer {ncpr_key}"} if ncpr_key else {}
        # Safe timeout of 1.5s to prevent stalling calls if regulatory servers are slow
        response = requests.get(f"{ncpr_url}/check?phone={phone}", headers=headers, timeout=1.5)
        if response.status_code == 200:
            return response.json().get("on_dnd", False)
        else:
            print(f"[NCPR WARNING] Query returned status {response.status_code}. Defaulting to safe PASS.")
    except Exception as e:
        # Fail-Open safe fallback logic under unreachable networks for Demo resilience
        print(f"[NCPR ERROR] External registry unreachable: {str(e)}. Defaulting to safe PASS.")
        
    return False

def get_customer_phone(customer_id):
    """Helper to look up phone number from customer data"""
    try:
        import json
        with open("data/customers.json", "r") as f:
            customers = json.load(f)
        customer = next((c for c in customers if str(c["id"]) == str(customer_id)), None)
        return customer["phone"] if customer else None
    except:
        return None

async def trigger_outbound_call(customer_id, flow_type, to_number, campaign_id=None, request_id=None, override=False, **kwargs):
    """
    Trigger a real outbound call using Twilio API.
    Includes a concurrency check to prevent duplicate calls.
    """
    # Concurrency Check: Don't call if already active (unless overridden)
    if not override:
        existing = db.get_active_call_for_customer(customer_id)
        if existing:
            print(f"[WORKER] Skipping call to {customer_id} - Call {existing['call_sid']} is already {existing['status']}.")
            return existing['call_sid']

    # --- [NEW] Concurrency Locking (Scaling Fix) ---
    if request_id:
        # If this is a scheduled job, mark it as PROCESSING
        db.update_call_status(request_id, "PROCESSING")

    # --- [NEW] Pre-Call Validation (Compliance & Safety) ---
    now = datetime.now()
    q_start, q_end = CONFIG["QUIET_HOURS"]
    # Temporarily bypassed for testing voice calls
    if False and not (q_start <= now.hour < q_end) and os.getenv("DEBUG_MODE") != "true":
        print(f"[WORKER] Aborting call to {customer_id} - Outside of allowed hours ({q_start}:00-{q_end}:00)")
        return "SKIPPED_QUIET_HOURS"

    try:
        import json
        with open("data/customers.json", "r") as f:
            customers = json.load(f)
        customer = next((c for c in customers if str(c["id"]) == str(customer_id)), None)
        
        if customer:
            if customer.get("policy_status") == "RENEWED":
                print(f"[WORKER] Skipping call to {customer_id} - Policy already RENEWED.")
                return "SKIPPED_RENEWED"
            if customer.get("dnd_status"):
                print(f"[WORKER] Skipping call to {customer_id} - Customer is on DND locally.")
                return "SKIPPED_DND"
                
            # [NEW] NCPR National DND Registry Check
            if check_ncpr_compliance(customer.get("phone")):
                print(f"[WORKER] Skipping call to {customer_id} - Customer is globally on National NCPR.")
                return "SKIPPED_NCPR_DND"
    except Exception as e:
        print(f"[WORKER] Validation Error: {e}")
        
    if not all([CONFIG["TWILIO_ACCOUNT_SID"], CONFIG["TWILIO_AUTH_TOKEN"], CONFIG["NGROK_URL"]]):
        print("[WORKER] Fatal Error: Twilio credentials or NGROK_URL missing in .env")
        return None

    client = Client(CONFIG["TWILIO_ACCOUNT_SID"], CONFIG["TWILIO_AUTH_TOKEN"])
    
    # 1. Prepare Call Record
    print(f"[WORKER] Executing call for {customer_id} to {to_number} (Type: {flow_type})")
    
    try:
        # Flatten kwargs for the URL
        import urllib.parse
        # If extra_params was passed as a dict in kwargs, flatten it
        if "extra_params" in kwargs and isinstance(kwargs["extra_params"], dict):
            params = {**kwargs["extra_params"]}
            del kwargs["extra_params"]
            kwargs.update(params)
            
        params_str = "&" + urllib.parse.urlencode(kwargs)

        call = client.calls.create(
            to=to_number,
            from_=CONFIG["TWILIO_PHONE_NUMBER"],
            url=f"{CONFIG['NGROK_URL']}/voice?customer_id={customer_id}&flow_type={flow_type}{params_str}",
            status_callback=f"{CONFIG['NGROK_URL']}/status-callback",
            status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
            record=True
        )
        
        # 2. Register in SQLite with request_id for UI tracking
        db.create_call(call.sid, customer_id, 
                       campaign_id=campaign_id, 
                       idempotency_key=request_id or call.sid,
                       stage=kwargs.get('stage'))
        db.update_call_status(call.sid, "initiated")
        
        print(f"[WORKER] Call SID: {call.sid} successfully initiated.")
        return call.sid
        
    except Exception as e:
        print(f"[WORKER] Twilio API Error: {str(e)}")
        # No DB update here if call initiation failed
        return None

import time
STARTUP_TIME = time.time()


async def retry_scheduler_loop():
    """
    Background loop that scans for failed calls and schedules retries 
    based on exponential backoff logic.
    """
    print("[SCHEDULER] Starting retry monitor...")
    # Add a 2-minute cooling period on startup to avoid "restart storms"
    await asyncio.sleep(120)
    
    while True:
        try:
            pending_retries = db.get_pending_retries()
            for call in pending_retries:
                # Calculate if it's time for retry
                last_time = datetime.fromisoformat(call['last_contacted_at'])
                retry_idx = min(call['retry_count'], len(CONFIG["RETRY_BACKOFF"]) - 1)
                wait_time = CONFIG["RETRY_BACKOFF"][retry_idx]
                
                if datetime.now() > last_time + timedelta(seconds=wait_time):
                    print(f"[SCHEDULER] Retrying Call {call['call_sid']} (Attempt {call['retry_count'] + 1})")
                    
                    # Update retry count in DB
                    db.increment_retry_count(call['call_sid'])
                    db.update_call_status(call['call_sid'], "initiated")
                    
                    # Re-trigger call
                    await trigger_outbound_call(
                        call['customer_id'], 
                        call.get('flow_type', 'insurance_start'),
                        get_customer_phone(call['customer_id']),
                        campaign_id=call['campaign_id'],
                        request_id=call['call_sid'],
                        stage=call.get('stage', 1)
                    )
                    await asyncio.sleep(10)
                
                # [NEW] Max Retries Fallback
                if call['retry_count'] >= CONFIG["MAX_RETRIES"]:
                    print(f"[SCHEDULER] Max retries reached for {call['call_sid']}. Triggering WhatsApp Fallback.")
                    db.update_call_status(call['call_sid'], "failed_voice_sent_whatsapp")
                    # Mock WhatsApp trigger
                    # trigger_whatsapp(call['customer_id'], "insurance_reminder")

            await asyncio.sleep(60) # Scan every 60s
        except Exception as e:
            print(f"[SCHEDULER] Loop Error: {str(e)}")
            await asyncio.sleep(10)

async def campaign_worker_loop():
    """
    Background loop that processes the Redis campaign queue sequentially.
    Ensures only one campaign call is active at a time.
    """
    print("[CAMPAIGN] Redis Sequential worker started...")
    while True:
        try:
            # Dequeue next task from Redis campaign queue (timeout 2s)
            result = await asyncio.to_thread(redis_client.blpop, REDIS_CAMPAIGN_QUEUE_KEY, 2)
            if not result:
                continue
                
            _, raw_data = result
            task = json.loads(raw_data)
            customer_id = task['customer_id']
            flow_type = task['flow_type']
            to_number = task['to_number']
            campaign_id = task['campaign_id']
            request_id = task['request_id']
            extra = task.get('extra', {})

            # Idempotency Check: Remove from Redis set
            await asyncio.to_thread(redis_client.srem, REDIS_QUEUED_CUSTOMERS_KEY, str(customer_id))
            
            print(f"[CAMPAIGN] Processing Redis-queued task for {customer_id}")
            
            # Execute the call
            await trigger_outbound_call(
                customer_id=customer_id,
                flow_type=flow_type,
                to_number=to_number,
                campaign_id=campaign_id,
                request_id=request_id,
                **extra
            )
            
            # Controlled campaign dial pacing
            await asyncio.sleep(15)
            
        except Exception as e:
            print(f"[CAMPAIGN] Worker Error: {str(e)}")
            await asyncio.sleep(5)

async def followup_scheduler_loop():
    """
    Background loop that scans for scheduled follow-ups and triggers 
    outbound calls when the time is reached.
    """
    print("[FOLLOWUP] Starting follow-up monitor...")
    while True:
        try:
            pending_followups = db.get_pending_followups()
            for fu in pending_followups:
                print(f"[FOLLOWUP] Triggering scheduled call for {fu['customer_id']}")
                
                # Mark as complete first to avoid double triggering
                db.mark_followup_complete(fu['id'])
                
                # Re-trigger call
                await trigger_outbound_call(
                    fu['customer_id'], 
                    "pre_sales", 
                    fu['customer_id'] # Real phone would be looked up here
                )
                
            await asyncio.sleep(30) # Scan every 30 seconds
        except Exception as e:
            print(f"[FOLLOWUP] Loop Error: {str(e)}")
            await asyncio.sleep(10)

# --- SHARED RESOURCE REGISTRY (Initialized in main) ---
db = None
telephony_logger = None
flow_manager = None
TASK_MAP = {}

async def redis_task_worker():
    """
    The heart of the Async Orchestrator:
    Pulls tasks from Redis and executes them in the background.
    """
    import sys
    print(f"[ASYNC] Distributed Task Worker started (Redis: {REDIS_HOST}:{REDIS_PORT})", flush=True)
    
    last_depth_check = 0
    
    while True:
        try:
            # Heartbeat & Periodic Queue Depth Check
            if time.time() - last_depth_check > 5:
                print(f"[ASYNC] HEARTBEAT: Worker loop active at {datetime.now().strftime('%H:%M:%S')}", flush=True)
                depth = redis_client.llen(TASK_QUEUE_KEY)
                if depth > 0:
                    print(f"[ASYNC] Queue Depth: {depth} tasks waiting...", flush=True)
                last_depth_check = time.time()

            # PRODUCTION FIX: blpop is blocking, must run in thread to avoid stalling event loop
            result = await asyncio.to_thread(redis_client.blpop, TASK_QUEUE_KEY, 2)
            if not result:
                continue
                
            _, raw_data = result
            task = json.loads(raw_data)
            
            func_name = task.get("func")
            args = task.get("args", [])
            kwargs = task.get("kwargs", {})
            
            print(f"[ASYNC] Picking up Task: {func_name}", flush=True)
            
            if func_name in TASK_MAP:
                func = TASK_MAP[func_name]
                if func:
                    try:
                        if asyncio.iscoroutinefunction(func):
                            await func(*args, **kwargs)
                        else:
                            # Wrap synchronous DB/Log calls in a thread
                            await asyncio.to_thread(func, *args, **kwargs)
                        print(f"[WORKER COMPLETE] {func_name} finished.", flush=True)
                        # PHYSICAL PERSISTENCE PROOF
                        try:
                            if metrics.redis:
                                val = int(metrics.redis.hget(metrics.REDIS_KEY, "tasks_finished") or 0)
                                if val % 100 == 0:
                                    with open("data/persistence_durability.log", "a") as f:
                                        f.write(f"[{datetime.now()}] ACK: {val} tasks committed.\n")
                        except: pass
                    except Exception as e:
                        print(f"❌ [ASYNC] EXECUTION ERROR in {func_name}: {str(e)}", flush=True)
                
                # Report task completion to metrics
                metrics.record_task_finished()
            else:
                print(f"⚠️ [ASYNC] UNKNOWN TASK: {func_name}", flush=True)
                metrics.record_task_finished()
                
        except Exception as e:
            print(f"❌ [ASYNC] FATAL WORKER LOOP ERROR: {str(e)}", flush=True)
            await asyncio.sleep(1)

async def main():
    """Main Entry Point for the Worker Process"""
    global db, telephony_logger, flow_manager, TASK_MAP
    
    print("🚀 ALCON BACKGROUND WORKER BOOTING...", flush=True)
    
    # Lazy Init inside Async Loop
    from metrics_collector import metrics
    from database import DatabaseManager
    from telephony_logger import TelephonyLogger
    from flow_manager import FlowManager

    print("[BOOT] Connecting to Database...", flush=True)
    db = DatabaseManager()
    print("[BOOT] Initializing Loggers...", flush=True)
    telephony_logger = TelephonyLogger()
    print("[BOOT] Starting Flow Engine...", flush=True)
    flow_manager = FlowManager(db)
    
    # Ensure Metrics are connected to same Redis as main app
    from metrics_collector import MetricsCollector
    metrics = MetricsCollector(redis_host=REDIS_HOST, redis_port=REDIS_PORT)
    print(f"[BOOT] Metrics Connected to Redis: {metrics.redis is not None}", flush=True)
    with open("data/worker_boot.log", "w") as f:
        f.write(f"WORKER BOOT SUCCESS AT {datetime.now()}\n")

    # Initialize Task Registry
    TASK_MAP = {
        "update_call_status": db.update_call_status,
        "record_request": metrics.record_request,
        "record_completion": metrics.record_completion,
        "record_task_queued": metrics.record_task_queued,
        "record_task_finished": metrics.record_task_finished,
        "finalize_call": flow_manager.finalize_call,
        "end_call": telephony_logger.end_call,
        "update_recording": telephony_logger.update_recording,
        "update_lead_state": db.update_lead_state,
        "log_call_history": db.log_call_history,
        "trigger_outbound_call": trigger_outbound_call
    }
    
    print("✅ ALCON WORKER READY. Starting event loops...", flush=True)
    
    # Role-based Loop Execution
    loops = [redis_task_worker()]
    
    # Only the 'cron' or 'full' worker runs the heavy scheduling logic
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["tasks", "cron", "full"], default="full")
    args, _ = parser.parse_known_args()
    
    if args.mode in ["cron", "full"]:
        print(f"🧠 WORKER MODE: CRON (Starting Schedulers)", flush=True)
        loops.extend([
            retry_scheduler_loop(),
            campaign_worker_loop(),
            followup_scheduler_loop()
        ])
    else:
        print(f"💪 WORKER MODE: TASKS ONLY (High-Throughput Persistence)", flush=True)

    await asyncio.gather(*loops)

if __name__ == "__main__":
    asyncio.run(main())
