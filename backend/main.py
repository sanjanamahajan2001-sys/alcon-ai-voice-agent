import os
import json
import sqlite3
import time
import httpx
from datetime import datetime, date
from typing import Optional
import httpx
from dotenv import load_dotenv
load_dotenv()

from twilio.rest import Client
from typing import Dict, Any, Optional
from flow_manager import FlowManager
from telephony_logger import TelephonyLogger
from metrics_collector import metrics
import os
from sap_bridge import SAPBridge
from fastapi import FastAPI, HTTPException, Body, Request, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from async_utils import run_tracked_task
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from worker import trigger_outbound_call, retry_scheduler_loop
from contextlib import asynccontextmanager
import asyncio

load_dotenv()

load_dotenv()

# Moved initialization below lifespan definition
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the campaign runner background loop for centralized orchestration
    from campaign_runner import CampaignQueueRunner
    campaign_runner = CampaignQueueRunner(db_manager)
    await campaign_runner.start()
    yield
    await campaign_runner.stop()

app = FastAPI(title="Alcon Voice POC Backend", lifespan=lifespan)

# --- Mount Flow Orchestrator Sub-App ---
import sys
import importlib.util

orchestrator_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "flow_orchestrator", "server"))
if orchestrator_dir not in sys.path:
    sys.path.insert(0, orchestrator_dir)

try:
    spec = importlib.util.spec_from_file_location(
        "flow_orchestrator_main",
        os.path.join(orchestrator_dir, "main.py")
    )
    flow_orchestrator_module = importlib.util.module_from_spec(spec)
    sys.modules["flow_orchestrator_main"] = flow_orchestrator_module
    spec.loader.exec_module(flow_orchestrator_module)
    flow_orchestrator_app = flow_orchestrator_module.app
    app.mount("/flow-orchestrator", flow_orchestrator_app)
    print("✅ Flow Orchestrator mounted successfully at /flow-orchestrator")
except Exception as e:
    print(f"⚠️ Failed to mount Flow Orchestrator: {e}")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alcon-voice.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:5173",
        "http://localhost:5174"
    ],
    allow_origin_regex=r"https?://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 

# DB Management
from database import DatabaseManager
db_manager = DatabaseManager()

# Twilio Configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
NGROK_URL = os.getenv("NGROK_URL")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "alcon2024")
MANAGER_PHONE = os.getenv("MANAGER_PHONE", "+18881012767") # Fallback for demo

# Initialize Twilio Client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize Managers
flow_manager = FlowManager()
telephony_logger = TelephonyLogger()
sap_bridge = SAPBridge()

class Customer(BaseModel):
    id: str
    name: str
    phone: str
    car_model: str
    last_service_date: str
    service_due_months: int

def get_customers():
    with open("data/customers.json", "r") as f:
        return json.load(f)

@app.post("/login")
async def login(payload: dict = Body(...)):
    password = payload.get("password")
    if password == DEMO_PASSWORD:
        return {"status": "success"}
    raise HTTPException(status_code=401, detail="Invalid password")

def find_customer_by_phone(phone: str):
    """Search for customer by phone number - returns all matches for disambiguation"""
    phone = phone.replace(" ", "").replace("-", "")
    customers = get_customers()
    matches = []
    for c in customers:
        if c["phone"].replace(" ", "").replace("-", "") == phone:
            matches.append(c)
    return matches

async def send_sms(to_number: str, message: str):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        print("SMS Error: Twilio credentials not configured")
        return
    
    try:
        # client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        # client.messages.create(
        #     body=message,
        #     from_=TWILIO_PHONE_NUMBER,
        #     to=to_number
        # )
        print(f"SMS Simulation: Message to {to_number} -> {message}")
    except Exception as e:
        print(f"SMS Failed: {str(e)}")

async def send_whatsapp_mock(to_number: str, message: str):
    """Mock WhatsApp integration for multi-channel fallback"""
    print(f"WHATSAPP Simulation: Message to {to_number} -> {message}")
    # In production, use Twilio WhatsApp API

@app.get("/customers")
async def list_customers():
    return get_customers()
@app.get("/dms/scan")
async def scan_dms():
    """Identify customers due for service"""
    customers = get_customers()
    due_list = []
    today = date.today()
    for c in customers:
        try:
            last_service = datetime.strptime(c["last_service_date"], "%Y-%m-%d").date()
            delta = (today.year - last_service.year) * 12 + (today.month - last_service.month)
            if delta >= c["service_due_months"]:
                c['due_months'] = delta
                due_list.append(c)
        except:
            continue
    return due_list

@app.get("/dms/scan/sales")
async def scan_sales_potential():
    """Identify customers for upgrade/exchange campaigns based on registration date"""
    with open("data/customers.json", "r") as f:
        customers = json.load(f)
    
    potential_list = []
    today = datetime.now()
    
    for c in customers:
        if "Hyundai" not in c.get("car_model", ""):
            continue
            
        reg_date_str = c.get("registration_date")
        if not reg_date_str:
            continue
            
        reg_date = datetime.strptime(reg_date_str, "%Y-%m-%d")
        age = (today.year - reg_date.year) - ((today.month, today.day) < (reg_date.month, reg_date.day))
        
        # Categorization logic
        if age >= 5:
            campaign = "exchange"
            reason = f"Vehicle Age {age} Years (High Potential)"
        elif age >= 3:
            campaign = "upgrade"
            reason = f"Vehicle Age {age} Years (Upgrade Candidate)"
        else:
            campaign = "emi_benefit"
            reason = f"Newer Vehicle ({age}y) - EMI Benefit"
            
        c['campaign_type'] = campaign
        c['vehicle_age'] = age
        c['reason'] = reason
        c['reason'] = reason
        potential_list.append(c)
            
    return potential_list

@app.get("/dms/scan/insurance")
async def scan_insurance_renewals():
    """Identify customers for insurance renewal based on expiry date (within 30 days)"""
    with open("data/customers.json", "r") as f:
        customers = json.load(f)
    
    today = datetime.now()
    renewal_list = []
    
    for c in customers:
        expiry_str = c.get("insurance_expiry_date")
        if not expiry_str:
            continue
            
        expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
        days_to_expiry = (expiry_date - today).days
        
        # 30-day window requirement
        if -3 <= days_to_expiry <= 30:
            # Determine stage based on timeline
            if days_to_expiry > 20: stage = 1
            elif days_to_expiry > 10: stage = 2
            elif days_to_expiry > 3: stage = 3
            elif days_to_expiry >= 0: stage = 4
            else: stage = 5 # Post-expiry
            
            c['campaign_type'] = "insurance"
            c['days_to_expiry'] = days_to_expiry
            c['stage'] = stage
            c['priority'] = 100 - days_to_expiry # Simple prioritization
            renewal_list.append(c)
            
    return sorted(renewal_list, key=lambda x: x['priority'], reverse=True)

@app.post("/dms/campaign/start")
async def start_campaign(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    """Add customers to the sequential campaign queue"""
    customer_ids = payload.get("customer_ids", [])
    campaign_id = payload.get("campaign_id", f"camp_{int(time.time())}")
    
    print(f"Adding {len(customer_ids)} customers to automated campaign '{campaign_id}'")
    
    from date_utils import calculate_age
    from worker import enqueue_campaign_task, is_customer_campaign_queued
    customers_data = get_customers()
    
    for c_id in customer_ids:
        customer = next((c for c in customers_data if str(c["id"]) == str(c_id)), None)
        if customer:
            if payload.get("campaign_type") == "insurance":
                campaign_type = "insurance"
                stage = payload.get("stage", 1)
                extra = {"stage": stage, "insurance_provider": customer.get("insurance_provider")}
            else:
                age = calculate_age(customer["registration_date"])
                campaign_type = "exchange" if age >= 5 else "upgrade" if age >= 3 else "emi_benefit"
                extra = {"campaign_type": campaign_type, "vehicle_age": age, "car_model": customer["car_model"]}
            
            request_id = f"QUEUED_{int(time.time())}_{c_id}"
            task = {
                "customer_id": c_id,
                "flow_type": "insurance_start" if campaign_type == "insurance" else "pre_sales",
                "to_number": customer["phone"],
                "campaign_id": campaign_id,
                "request_id": request_id,
                "extra": {**extra, "campaign_type": campaign_type}
            }
            print(f"[CAMPAIGN] Queuing {task['flow_type']} call for {c_id}")
            
            # [NEW] Distributed Idempotency Check
            if is_customer_campaign_queued(c_id):
                print(f"[CAMPAIGN] Skipping {c_id} - already in queue.")
                continue
                
            enqueue_campaign_task(task)
            
    return {"status": "queued", "campaign_id": campaign_id, "queue_size": len(customer_ids)}

@app.get("/customer/{customer_id}/status")
async def get_customer_status(customer_id: str):
    customers = get_customers()
    customer = next((c for c in customers if c["id"] == customer_id), None)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    last_service = datetime.strptime(customer["last_service_date"], "%Y-%m-%d").date()
    today = date.today()
    
    delta = (today.year - last_service.year) * 12 + (today.month - last_service.month)
    is_due = delta >= customer["service_due_months"]
    
    return {
        "customer": customer,
        "is_due": is_due,
        "months_since_last": delta
    }

@app.post("/chat")
async def chat(payload: dict = Body(...)):
    """Web Bot Adapter - No Twilio costs"""
    session_id = payload.get("session_id")
    message = payload.get("message", "")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
        
    # Core Engine Reuse (Plug & Play)
    response_data = flow_manager.get_next_action(session_id, message, channel="web")
    return response_data

@app.post("/tts")
async def text_to_speech(text: str = Body(..., embed=True)):
    if not ELEVENLABS_API_KEY:
        print("ERROR: ELEVENLABS_API_KEY is missing from .env")
        raise HTTPException(status_code=500, detail="ElevenLabs API Key not configured")
    
    print(f"Generating TTS for: {text[:20]}...")
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2", 
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    async def generate():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=data, headers=headers, timeout=30.0) as response:
                    if response.status_code != 200:
                        detail = await response.aread()
                        print(f"ElevenLabs Error ({response.status_code}): {detail.decode()}")
                        raise HTTPException(status_code=response.status_code, detail=detail.decode())
                    
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as e:
                print(f"Streaming Error: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(generate(), media_type="audio/mpeg")

# --- Twilio Telephony Endpoints ---

@app.api_route("/voice/language", methods=["GET", "POST"])
async def voice_language(request: Request, customer_id: Optional[str] = None, flow_type: str = "booking"):
    from twilio.twiml.voice_response import VoiceResponse, Gather
    response = VoiceResponse()
    
    # Store query params for redirection
    params = dict(request.query_params)
    if customer_id:
        params["customer_id"] = customer_id
    if flow_type:
        params["flow_type"] = flow_type
        
    import urllib.parse
    query_string = urllib.parse.urlencode(params)
    action_url = f"/voice/language-callback?{query_string}"
    
    gather = Gather(numDigits=1, action=action_url, method="POST", timeout=5)
    # Bilingual greeting
    gather.say("Welcome to Alcon Hyundai. For English, press 1. Hindi ke liye, do dabayein.")
    response.append(gather)
    response.redirect(action_url)
    
    return Response(content=str(response), media_type="application/xml")

@app.api_route("/voice/language-callback", methods=["GET", "POST"])
async def voice_language_callback(request: Request, customer_id: Optional[str] = None, flow_type: str = "booking"):
    form_data = await request.form()
    digit = form_data.get("Digits", "")
    
    # Press 1 for English, Press 2 for Hindi
    if digit == "2":
        lang = "hi-IN"
    else:
        lang = "en-IN" # Default to English
        
    import urllib.parse
    params = dict(request.query_params)
    if customer_id:
        params["customer_id"] = customer_id
    if flow_type:
        params["flow_type"] = flow_type
    params["language"] = lang
    query_string = urllib.parse.urlencode(params)
    
    from twilio.twiml.voice_response import VoiceResponse
    response = VoiceResponse()
    response.redirect(f"/voice?{query_string}")
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/voice")
async def voice(request: Request, background_tasks: BackgroundTasks, customer_id: Optional[str] = None, flow_type: str = "booking"):
    """Entry point for Twilio calls"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    from_number = form_data.get("From", "")
    
    # Check if language is specified in query params
    language = request.query_params.get("language")
    if not language:
        # Redirect to language selection IVR
        import urllib.parse
        params = dict(request.query_params)
        if customer_id:
            params["customer_id"] = customer_id
        if flow_type:
            params["flow_type"] = flow_type
        query_string = urllib.parse.urlencode(params)
        from twilio.twiml.voice_response import VoiceResponse
        response = VoiceResponse()
        response.redirect(f"/voice/language?{query_string}")
        return Response(content=str(response), media_type="application/xml")
    
    # Inbound Authentication Logic
    if not customer_id and from_number:
        # Default to reception for new calls if not specified
        if flow_type == "booking" and not request.query_params.get("flow_type"):
            flow_type = "reception" 
            
        matches = find_customer_by_phone(from_number)
        if len(matches) >= 1:
            customer_id = matches[0]["id"]
        else:
            customer_id = "Unknown"
    
    # Final fallback only if we truly have no ID and no From number
    customer_id = customer_id or "Unknown" 
    
    # [NEW] STRESS TEST BYPASS: Ensure ID '1' always exists for testing
    if customer_id == "1":
        customer_id = "1" # Force valid state
    
    # Capture any extra query params and remove overlapping ones
    params = dict(request.query_params)
    for key in ['customer_id', 'flow_type']:
        params.pop(key, None)
    
    print(f"Incoming {flow_type} call for customer: {customer_id}, CallSid: {call_sid}")
    
    # Update DB Status & Record metrics (Eagerly increment to avoid reporting lag)
    stage_val = params.get('stage')
    metrics.record_request(call_sid, os.getpid())
    metrics.record_task_queued()
    
    background_tasks.add_task(run_tracked_task, "update_call_status", call_sid, "in-progress", customer_id=customer_id, stage=stage_val, skip_queue_count=True)
    
    # Finalize logic with fail-safe guard
    try:
        twiml = flow_manager.handle_voice(customer_id, call_sid, flow_type, telephony_logger, from_number=from_number, background_tasks=background_tasks, **params)
    except Exception as e:
        print(f"⚠️ FAIL-SAFE TRIGGERED: {e}")
        from twilio.twiml.voice_response import VoiceResponse
        twiml_obj = VoiceResponse()
        twiml_obj.say("System update in progress. Please hold.")
        twiml_obj.hangup()
        twiml = str(twiml_obj)
    
    if "Hangup" in str(twiml) or "Reject" in str(twiml):
        background_tasks.add_task(run_tracked_task, "record_completion", call_sid)
    
    return Response(content=str(twiml), media_type="application/xml")

@app.post("/process")
async def process(request: Request, background_tasks: BackgroundTasks, step: str = "greeting", customer_id: str = "1", flow_type: str = "booking"):
    """Handle speech results from Twilio Gather"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    from_number = form_data.get("From", "")
    speech_result = form_data.get("SpeechResult", "")
    
    # Eager Metrics (Avoid reporting lag)
    metrics.record_request(call_sid, os.getpid())
    metrics.record_task_queued()
    
    # --- INSTRUMENTATION START ---
    t_start = time.time()
    
    # 1. Capture any extra query params and remove overlapping ones
    params = dict(request.query_params)
    for key in ['step', 'customer_id', 'flow_type']:
        params.pop(key, None)
        
    t_pre_logic = time.time()
    twiml = flow_manager.handle_process(customer_id, step, speech_result, call_sid, flow_type, telephony_logger, background_tasks=background_tasks, **params)
    t_post_logic = time.time()
    
    # Calculate Metrics
    logic_time = (t_post_logic - t_pre_logic) * 1000
    total_time = (time.time() - t_start) * 1000
    
    # Add metrics to response headers
    headers = {
        "X-Internal-Metrics": json.dumps({
            "logic_ms": round(logic_time, 2),
            "total_ms": round(total_time, 2),
            "db_wait_ms": round(flow_manager.last_db_time * 1000, 2) if hasattr(flow_manager, 'last_db_time') else 0
        })
    }
    # --- INSTRUMENTATION END ---

    # Trigger Professional SMS if booking is confirmed
    if step == 'booking_options' and 'confirmed' in twiml.lower():
        customer = flow_manager.get_customer(customer_id)
        if customer:
            date_str = params.get('date', 'Upcoming')
            slot_str = params.get('slot', 'TBD')
            # Extract advisor name from the TwiML response if possible, or just re-assign for SMS
            concerns = params.get('concerns', '')
            advisor = flow_manager._assign_advisor(concerns)
            
            sms_msg = (
                f"Booking Confirmed! \n\n"
                f"Dear {customer['name']}, your {customer['car_model']} service is scheduled for {date_str} at {slot_str}. \n"
                f"Service Advisor: {advisor['name']} ({advisor['specialty']})\n"
                f"Location: Alcon Hyundai Service Center.\n\n"
                f"Add to Calendar: https://alcon.ai/cal/bk-{call_sid[:6]}\n\n"
                f"Thank you for choosing Alcon!"
            )
            async def background_notifications():
                await send_sms(customer['phone'], sms_msg)
                # SAP INTEGRATION: Trigger Automated Invoicing Mock
                try:
                    invoice_id = sap_bridge.generate_service_invoice_mock(customer, params)
                    print(f"SAP Integration Active: Generated Invoice {invoice_id}")
                except Exception as e:
                    print(f"SAP Bridge Error: {str(e)}")
            
            asyncio.create_task(background_notifications())

    # SAP INTEGRATION: Trigger Lead Sync for new callers
    if step == 'reception_name' and speech_result:
        async def background_lead_sync():
            try:
                lead_data = {
                    "name": speech_result.title(),
                    "phone": from_number or "Unknown",
                    "intent": params.get('intent', 'sales'),
                    "timestamp": datetime.now().isoformat()
                }
                sap_bridge.generate_lead_record(lead_data)
            except Exception as e:
                print(f"SAP Lead Sync Error: {str(e)}")
        
        asyncio.create_task(background_lead_sync())

    return Response(content=twiml, media_type="application/xml", headers=headers)

@app.post("/status-callback")
async def status_callback(request: Request, background_tasks: BackgroundTasks):
    """Callback when call status changes to update SQLite state machine"""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    status = form_data.get("CallStatus") # initiated, ringing, answered, completed, failed, busy, no-answer
    duration = form_data.get("CallDuration", 0)
    recording_url = form_data.get("RecordingUrl")
    
    print(f"[CALLBACK] Call {call_sid} status changed to: {status}")
    
    # 1. Update State Machine in background
    background_tasks.add_task(run_tracked_task, "update_call_status", call_sid, status)
    
    # 2. Legacy Logging support
    if status in ['completed', 'failed', 'busy', 'no-answer']:
        background_tasks.add_task(run_tracked_task, "end_call", call_sid, duration)
        if recording_url:
            background_tasks.add_task(run_tracked_task, "update_recording", call_sid, recording_url)
        
        # [NEW] Finalize business logic and log history in background
        transcript = flow_manager.transcript_accumulator.get(call_sid)
        session = flow_manager.session_manager.get_session(call_sid)
        background_tasks.add_task(run_tracked_task, "finalize_call", call_sid, transcript=transcript, session=session)
    
    return {"status": "updated"}

@app.get("/telephony/history")
async def get_all_history(limit: int = 50):
    """Get summarized history of all calls"""
    return telephony_logger.get_history(limit=limit)

@app.get("/telephony/logs/{call_id}")
async def get_call_logs(call_id: str):
    """Get detailed logs for a specific call with metadata for the UI"""
    from database import DatabaseManager
    db = DatabaseManager()
    
    # 1. Try to find the call metadata in DB first
    # This helps us get the customer name and status even if logs aren't ready
    call_info = None
    
    # Instrumentation: Record active session and worker PID
    metrics.record_request(call_id, os.getpid())
    
    idempotency_key = call_id
    # Check if this is a repeat/retry
    if idempotency_key and db_manager.get_sid_by_idempotency_key(idempotency_key):
        metrics.record_retry()
    conn = db._get_conn()
    cursor = db_manager.get_cursor(conn)
    p = db_manager.placeholder
    cursor.execute(f'''
        SELECT * FROM calls 
        WHERE call_sid = {p} OR idempotency_key = {p}
    ''', (call_id, call_id))
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        rows_dict = [dict(r) for r in rows]
        # Prioritize the row where idempotency_key matches the call_id (meaning it has the resolved Twilio call_sid)
        resolved_row = next((r for r in rows_dict if r.get('idempotency_key') == call_id), None)
        call_info = resolved_row if resolved_row else rows_dict[0]
    
    target_sid = call_info['call_sid'] if call_info else call_id
    
    # 2. Get high-fidelity logs from the logger
    # Try with resolved SID first, then fallback to raw call_id
    session_data = telephony_logger.get_call_log(target_sid)
    if not session_data and target_sid != call_id:
        session_data = telephony_logger.get_call_log(call_id)
    
    # 3. Resolve Customer Name and Metrics
    customer_name = "Unknown Customer"
    duration = 0
    chars = 0
    cost = 0.0
    
    if session_data:
        customer_name = session_data.get("customer_name", "Unknown")
        # Calculate live duration if call is in progress
        if session_data.get("status") != "completed" and "start_time" in session_data:
            try:
                start_time = datetime.fromisoformat(session_data["start_time"])
                duration = int((datetime.now() - start_time).total_seconds())
            except:
                duration = session_data.get("duration_seconds", 0)
        else:
            duration = session_data.get("duration_seconds", 0)
        chars = session_data.get("total_characters", 0)
        if session_data.get("status") != "completed":
            char_cost = (chars / 100) * 0.08
            minute_cost = (duration / 60) * 0.013
            cost = round(char_cost + minute_cost, 4)
        else:
            cost = session_data.get("estimated_cost", 0.0)
    elif call_info:
        customers = get_customers()
        customer = next((c for c in customers if str(c["id"]) == str(call_info["customer_id"])), None)
        if customer:
            customer_name = customer["name"]
            
    # 4. Construct the structured response the UI expects
    status_raw = call_info['status'] if call_info else (session_data['status'] if session_data else "QUEUED")
    
    # Extract transcript
    raw_transcript = session_data.get("transcript", []) if session_data else []
    
    # If no logs yet, provide a synthetic 'Pending' entry
    if not raw_transcript:
        transcript = [{
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "speaker": "System",
            "role": "system",
            "text": "Call is queued or initializing... Please wait.",
            "message": "Call is queued or initializing... Please wait."
        }]
    else:
        # Ensure each log entry has both formats for UI compatibility
        transcript = []
        for entry in raw_transcript:
            transcript.append({
                "timestamp": entry.get("timestamp", ""),
                "speaker": entry.get("speaker", entry.get("role", "Unknown")),
                "role": entry.get("role", entry.get("speaker", "unknown")),
                "text": entry.get("text", entry.get("message", "")),
                "message": entry.get("message", entry.get("text", ""))
            })
    
    return {
        "call_sid": target_sid,
        "status": status_raw.upper(),
        "customer_name": customer_name,
        "current_step": session_data.get("current_step", "Active") if session_data else "Initializing",
        "duration_seconds": duration,
        "total_characters": chars,
        "estimated_cost": cost,
        "transcript": transcript
    }

@app.post("/make-call/{customer_id}")
async def trigger_call(customer_id: str, background_tasks: BackgroundTasks, payload: dict = Body(default={})):
    """Queue an outbound call using the async worker-pattern"""
    customers = get_customers()
    customer = next((c for c in customers if str(c["id"]) == customer_id), None)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    to_number = payload.get("to_number", customer["phone"])
    flow_type = payload.get("flow_type", "pre_sales")
    
    # Capture any campaign context from payload (excluding system keys)
    extra_params = {k: v for k, v in payload.items() if k not in ["to_number", "flow_type", "override"]}
    
    request_id = f"QUEUED_{int(time.time())}"
    
    # Add to async background queue
    background_tasks.add_task(
        run_tracked_task,
        "trigger_outbound_call", 
        customer_id=customer_id, 
        flow_type=flow_type, 
        to_number=to_number,
        request_id=request_id,
        override=payload.get("override", False),
        **extra_params
    )
    
    return {"status": "queued", "call_sid": request_id, "message": f"Call to {customer_id} added to execution queue."}

@app.post("/book")
async def book_appointment(customer_id: str = Body(..., embed=True), time: str = Body(..., embed=True)):
    return {"status": "success", "message": f"Appointment booked for {time}"}

@app.get("/telephony/dashboard/kpis")
async def get_dashboard_kpis():
    """Aggregated KPIs for the dashboard."""
    conn = db_manager._get_conn()
    cursor = db_manager.get_cursor(conn)
    
    # 1. Total Calls Today
    today = date.today().isoformat()
    p = db_manager.placeholder
    
    cursor.execute(f"SELECT COUNT(*) FROM calls WHERE created_at >= {p}", (today,))
    total_calls = cursor.fetchone()[0] if db_manager.engine == "sqlite" else cursor.fetchone()['count']
    
    # 2. Connected Calls
    cursor.execute(f"SELECT COUNT(*) FROM calls WHERE status = 'completed' AND created_at >= {p}", (today,))
    connected_calls = cursor.fetchone()[0] if db_manager.engine == "sqlite" else cursor.fetchone()['count']
    
    # 3. Conversions
    cursor.execute("SELECT COUNT(*) FROM lead_states WHERE lead_status = 'CONVERTED'")
    conversions = cursor.fetchone()[0] if db_manager.engine == "sqlite" else cursor.fetchone()['count']
    
    # 4. Hot Leads
    cursor.execute(f"SELECT COUNT(*) FROM lead_states WHERE lead_score >= 85")
    hot_leads = cursor.fetchone()[0] if db_manager.engine == "sqlite" else cursor.fetchone()['count']
    
    # 5. Stage Distribution
    cursor.execute("SELECT stage, COUNT(*) as count FROM calls GROUP BY stage")
    rows = cursor.fetchall()
    stages = {f"stage_{row['stage']}": row['count'] for row in rows if row['stage']}
    
    # 6. Conversion Rate
    cursor.execute("SELECT COUNT(*) FROM calls")
    total_calls_all = cursor.fetchone()[0] if db_manager.engine == "sqlite" else cursor.fetchone()['count']
    conversion_rate = round((conversions / total_calls_all * 100), 1) if total_calls_all > 0 else 0

    conn.close()
    return {
        "total_calls": total_calls,
        "connected_calls": connected_calls,
        "conversions": conversions,
        "hot_leads": hot_leads,
        "conversion_rate": conversion_rate,
        "stages": stages
    }

@app.get("/telephony/dashboard/leads")
async def get_dashboard_leads():
    """Detailed lead management data."""
    conn = db_manager._get_conn()
    if db_manager.engine == "postgres":
        from psycopg2.extras import RealDictCursor
        cursor = conn.cursor(cursor_factory=RealDictCursor)
    else:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
    
    # Simplified query to show active leads
    cursor.execute(f'''
        SELECT l.*, c.customer_id, c.stage, c.last_contacted_at, l.escalation_status
        FROM lead_states l
        JOIN calls c ON l.call_sid = c.call_sid
        ORDER BY c.created_at DESC
        LIMIT 50
    ''')
    rows = cursor.fetchall()
    
    leads = []
    customers = get_customers()
    
    for row in rows:
        lead = dict(row)
        customer = next((c for c in customers if str(c["id"]) == str(lead["customer_id"])), None)
        if customer:
            lead["customer_name"] = customer["name"]
            lead["vehicle"] = customer["car_model"]
        leads.append(lead)
        
    conn.close()
    return leads

@app.get("/telephony/leads/{call_sid}/conversation")
async def get_lead_conversation(call_sid: str):
    """Fetch specific transcript for a lead."""
    conn = db_manager._get_conn()
    cursor = db_manager.get_cursor(conn)
    p = db_manager.placeholder
    
    cursor.execute(f"SELECT transcript FROM call_logs WHERE call_sid = {p}", (call_sid,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "transcript": json.loads(row["transcript"]),
            "status": "FINALIZED"
        }
    
    # Fallback to memory accumulator if not finalized yet
    if call_sid in flow_manager.transcript_accumulator:
        return {
            "transcript": flow_manager.transcript_accumulator[call_sid],
            "compliance": "PENDING",
            "audit": None
        }
        
    return {"transcript": [], "compliance": "NOT_FOUND"}

@app.get("/telephony/leads/{call_sid}/audit")
async def get_lead_audit(call_sid: str):
    """Fetch combined audit trace for a lead (IRDAI Compliance)."""
    conn = db_manager._get_conn()
    cursor = db_manager.get_cursor(conn)
    p = db_manager.placeholder
    
    cursor.execute(f"""
        SELECT transcript, compliance_status, audit_summary, outcome, stage 
        FROM call_logs 
        WHERE call_sid = {p}
    """, (call_sid,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Audit log not found")
        
    return {
        "call_sid": call_sid,
        "transcript": json.loads(row["transcript"]),
        "compliance": row["compliance_status"],
        "audit_summary": json.loads(row["audit_summary"]) if row["audit_summary"] else None,
        "outcome": row["outcome"],
        "stage": row["stage"]
    }

@app.get("/telephony/dashboard/reports")
async def get_dashboard_reports():
    """Fetch historical trends for the last 7 days."""
    conn = db_manager._get_conn()
    cursor = db_manager.get_cursor(conn)
    
    # Simple daily breakdown
    cursor.execute("""
        SELECT date(created_at) as call_date, 
               COUNT(*) as total,
               SUM(CASE WHEN outcome = 'CONVERTED' THEN 1 ELSE 0 END) as conversions
        FROM call_logs
        GROUP BY call_date
        ORDER BY call_date DESC
        LIMIT 7
    """)
    rows = cursor.fetchall()
    conn.close()
    
    reports = []
    for r in rows:
        reports.append({
            "date": r[0],
            "total_calls": r[1],
            "conversions": r[2],
            "conv_rate": round((r[2]/r[1])*100, 1) if r[1] > 0 else 0
        })
        
    return reports

@app.post("/telephony/leads/{call_sid}/send-quote")
async def send_lead_quote(call_sid: str):
    """Manually trigger quote sending and update lead state."""
    db_manager.update_lead_state(call_sid, 
        lead_status="QUOTE_SENT", 
        last_action="Manual Quote Sent",
        next_step="Await Payment Confirmation"
    )
    print(f"[MOCK] Manual Quote sent via WhatsApp for {call_sid}")
    return {"status": "success", "message": "Quote sent successfully"}

@app.post("/telephony/escalate/{call_sid}")
async def escalate_to_human(call_sid: str):
    """Manually trigger a transfer to a human manager via Twilio Redirect."""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio client not initialized")
    
    # 0. Handle Simulation Mode (Fake SIDs)
    if call_sid.startswith("SIM_"):
        db_manager.update_lead_state(call_sid, 
            escalation_status="IN_PROGRESS", 
            last_action="Human Takeover (Simulation)",
            next_step="Human Handling"
        )
        print(f"[MOCK ESCALATION] Simulation takeover successful for {call_sid}")
        return {"status": "success", "message": "Simulation transfer successful"}

    try:
        # 1. Update Database Status
        db_manager.update_lead_state(call_sid, 
            escalation_status="IN_PROGRESS", 
            last_action="Human Takeover Initiated",
            next_step="Human Handling"
        )

        # 2. Construct TwiML for Transfer
        # We redirect the live call to a new TwiML that dials the manager
        redirect_url = f"{NGROK_URL}/telephony/transfer-twiml?target={MANAGER_PHONE}&call_sid={call_sid}"
        
        # 3. Use Twilio REST API to redirect the active call
        twilio_client.calls(call_sid).update(url=redirect_url)
        
        print(f"[ESCALATION] Call {call_sid} redirected to {MANAGER_PHONE}")
        return {"status": "success", "message": "Call transfer initiated"}
    except Exception as e:
        print(f"[ESCALATION] Failed to redirect {call_sid}: {str(e)}")
        # Revert status if failed
        db_manager.update_lead_state(call_sid, escalation_status="REQUIRED")
        raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")

@app.api_route("/telephony/transfer-twiml", methods=["GET", "POST"])
async def get_transfer_twiml(target: str, call_sid: str = None, CallSid: str = None):
    """Helper endpoint to provide TwiML for the redirect."""
    from twilio.twiml.voice_response import VoiceResponse
    
    sid = call_sid or CallSid
    lang = "en-IN"
    if sid:
        session = flow_manager.session_manager.get_session(sid)
        if session:
            lang = session.get("params", {}).get("language", "en-IN")
            
    resp = VoiceResponse()
    
    english_text = "Please stay on the line. I am connecting you to our insurance manager now."
    if lang == "hi-IN":
        from flows.translation_utils import TranslationAdapter
        translated_text = TranslationAdapter.translate_to_hindi(english_text)
        resp.say(translated_text, language="hi-IN")
    else:
        resp.say(english_text, language="en-IN")
        
    resp.dial(target)
    return Response(content=str(resp), media_type="application/xml")

@app.post("/telephony/resume-ai/{call_sid}")
async def resume_ai_control(call_sid: str, payload: dict = Body(default={})):
    """Manually hand the call back to the AI from a human agent."""
    try:
        # 1. Update Database Status
        db_manager.update_lead_state(call_sid, 
            escalation_status="NONE", 
            last_action="AI Resumed Control",
            next_step="Processing"
        )
        
        # [NEW] Store agent summary and structured updates in session params
        summary = payload.get("summary")
        data_updates = payload.get("data_updates") # e.g. {"premium": 10500, "discount_applied": "10%"}
        
        session = flow_manager.session_manager.get_session(call_sid)
        if session:
            session["params"]["agent_summary"] = summary
            if data_updates:
                session["params"]["pending_data"] = data_updates
            flow_manager.session_manager.save_session(call_sid, session)

        # [NEW] Stage updates in Database for Dashboard visibility
        if data_updates:
            # Run validation to determine status
            validation = flow_manager._validate_handover_data(call_sid, data_updates)
            db_manager.update_lead_state(call_sid, 
                pending_updates=data_updates,
                disposition=f"STATUS:{validation['status']}|FLAGS:{','.join(validation['flags'])}"
            )
            print(f"[STAGING] Data updates staged for {call_sid} with status {validation['status']}")

        # 2. Mock Handling for Simulation
        if call_sid.startswith("SIM_"):
            print(f"[MOCK RESUME] AI resumed for simulation {call_sid}")
            return {"status": "success", "message": "Simulation AI resumption successful"}

        # 3. Use Twilio REST API to redirect back to AI root
        redirect_url = f"{NGROK_URL}/telephony/resume-twiml?call_sid={call_sid}"
        twilio_client.calls(call_sid).update(url=redirect_url)
        
        print(f"[RESUME] Call {call_sid} handed back to AI")
        return {"status": "success", "message": "AI Resumption initiated"}
    except Exception as e:
        print(f"[RESUME] Failed to resume {call_sid}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Resumption failed: {str(e)}")

@app.api_route("/telephony/resume-twiml", methods=["GET", "POST"])
async def get_resume_twiml(call_sid: str):
    """Provides TwiML for when the AI takes control back."""
    from twilio.twiml.voice_response import VoiceResponse
    
    # Get the "Welcome Back" message from FlowManager
    resume_data = flow_manager.get_resume_greeting(call_sid)
    
    # Check session language
    session = flow_manager.session_manager.get_session(call_sid)
    lang = "en-IN"
    if session:
        lang = session.get("params", {}).get("language", "en-IN")
        
    resp = VoiceResponse()
    
    original_text = resume_data["text"]
    if lang == "hi-IN":
        from flows.translation_utils import TranslationAdapter
        translated_text = TranslationAdapter.translate_to_hindi(original_text)
        resp.say(translated_text, language="hi-IN")
    else:
        resp.say(original_text, language="en-IN")
    
    # Re-attach the gather loop
    customer_id = session.get("customer_id", "Unknown") if session else "Unknown"
    flow_type = session.get("flow_type", "booking") if session else "booking"
    
    params = {
        "step": resume_data["next_step"],
        "customer_id": customer_id,
        "flow_type": flow_type
    }
    import urllib.parse
    query_string = urllib.parse.urlencode(params)
    action_url = f"/process?{query_string}"
    
    from twilio.twiml.voice_response import Gather
    gather = Gather(input='speech', action=action_url, method='POST', timeout=5, speechTimeout='1.0', language=lang)
    resp.append(gather)
    resp.redirect(action_url + "&retry=true")
    
    return Response(content=str(resp), media_type="application/xml")

@app.post("/telephony/log-human/{call_sid}")
async def log_human_interaction(call_sid: str, payload: dict = Body(...)):
    """Log a turn of human-user conversation during a handover."""
    speaker = payload.get("speaker", "Human")
    text = payload.get("text", "")
    
    # Inject into FlowManager's transcript accumulator
    if call_sid in flow_manager.transcript_accumulator:
        flow_manager.transcript_accumulator[call_sid].append({
            "speaker": speaker,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "tags": ["HUMAN_OVERRIDE"]
        })
    
    return {"status": "success"}

@app.get("/telephony/leads/{call_sid}")
async def get_single_lead(call_sid: str):
    """Fetch details for a specific lead for supervisor review."""
    db = DatabaseManager()
    lead = db.get_lead_state(call_sid)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    # Ensure pending_updates is a dict for UI
    if lead.get("pending_updates") and isinstance(lead["pending_updates"], str):
        try:
            lead["pending_updates"] = json.loads(lead["pending_updates"])
        except:
            pass
            
    return lead

@app.post("/telephony/approve-updates/{call_sid}")
async def approve_pending_updates(call_sid: str):
    """Scenario 12: Simulate Syncing approved changes to external DMS."""
    db = DatabaseManager()
    try:
        lead_data = db.get_lead_state(call_sid)
        if not lead_data or not lead_data.get("pending_updates"):
            print(f"[SYNC ERROR] No pending updates found for {call_sid}")
            raise HTTPException(status_code=404, detail="No pending updates found")
            
        # 1. Simulate DMS Sync
        print(f"\n\033[94m[DMS SYNC] Pushing updates to production systems: {lead_data['pending_updates']}\033[0m")
        
        # 2. Clear Staging & Mark as SYNCED
        db.update_lead_state(call_sid, 
            pending_updates=None,
            last_action="DMS Sync Successful",
            disposition="STATUS:SYNCED"
        )
        
        return {"status": "success", "message": "Changes committed to production DMS"}
    except Exception as e:
        print(f"[SYNC CRITICAL] {str(e)}")
        raise HTTPException(status_code=500, detail=f"DMS Sync failed: {str(e)}")

@app.post("/logs")
async def save_logs(log_data: dict = Body(...)):
    history_path = "data/history.json"
    history = []
    
    if os.path.exists(history_path):
        with open(history_path, "r") as f:
            try:
                history = json.load(f)
            except:
                history = []
                
    log_data["timestamp"] = datetime.now().isoformat()
    history.append(log_data)
    
    with open(history_path, "w") as f:
        json.dump(history, f, indent=4)
        
    return {"status": "success"}

@app.get("/metrics")
async def get_metrics():
    """Exposes real-time orchestration metrics for stress-test reporting."""
    return metrics.get_snapshot()

@app.get("/metrics/complete")
async def signal_completion(call_sid: str):
    """Lifecycle Hook: Allows stress harness to signal session completion."""
    metrics.record_completion(call_sid)
    return {"status": "cleared"}

@app.post("/telephony/metrics/reset")
async def reset_metrics():
    """Administrative reset for benchmarking."""
    metrics.reset_all()
    return {"status": "reset"}

@app.post("/telephony/reset-locks")
async def reset_locks():
    """Reset call locks for all sessions by marking active/processing calls as completed."""
    try:
        # Mark all active/non-completed calls as completed to clear concurrency locks
        db_manager.execute_query("UPDATE calls SET status = 'completed'")
        # Also clear campaign queue just in case
        db_manager.execute_query("DELETE FROM campaign_queue")
        return {"status": "success", "message": "All call locks have been successfully cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset locks: {str(e)}")

@app.post("/telephony/leads/{call_sid}/send-quote")
async def send_quote(call_sid: str):
    """Parity: Trigger outbound quotation via WhatsApp."""
    # Mock logic: Update lead state and 'send' message
    db_manager.update_lead_state(call_sid, last_action="WhatsApp Quote Sent", disposition="QUOTE_SHARED")
    print(f"[OUTBOUND] WhatsApp Quote Sent for session {call_sid}")
    return {"status": "success", "message": "Quotation sent"}

# --- NEW CAMPAIGN ENDPOINTS ---
from trigger_engine import TriggerEngine
from dms_adapter import LocalJSONDMSAdapter
from campaign_runner import CAMPAIGN_CONSOLE_LOGS, add_console_log

@app.get("/campaign/scan")
async def scan_campaigns():
    """Scan all customers in mock DMS against 9 flow rules and return staging counts."""
    dms = LocalJSONDMSAdapter()
    customers = dms.fetch_customers()
    engine = TriggerEngine()
    results = engine.scan_all_customers(customers)
    return results

@app.post("/campaign/trigger")
async def trigger_campaigns(payload: dict = Body(...)):
    """Enqueue selected staged customers into background sequential execution queue."""
    queued_count = 0
    # Payload format: { "flow_type": [ {customer_object}, ... ], ... }
    for flow_type, customer_list in payload.items():
        if not customer_list:
            continue
        for customer in customer_list:
            customer_id = str(customer.get("id"))
            customer_name = customer.get("name", "Unknown Customer")
            car_model = customer.get("car_model", "Unknown Car")
            
            success = db_manager.enqueue_campaign_job(
                customer_id=customer_id,
                customer_name=customer_name,
                car_model=car_model,
                flow_type=flow_type
            )
            if success:
                queued_count += 1
                
    add_console_log(f"Queued {queued_count} campaign tasks across selected segments.", "system")
    return {"status": "success", "queued_count": queued_count}

@app.get("/campaign/queue")
async def get_campaign_queue():
    """Retrieve active campaign queue and live simulated dialogue terminal logs."""
    queue = db_manager.get_queued_jobs()
    return {
        "queue": queue,
        "logs": list(CAMPAIGN_CONSOLE_LOGS)
    }

@app.post("/campaign/queue/clear")
async def clear_campaign_queue():
    """Flush all queued and processed campaign tasks and reset terminal logs."""
    db_manager.clear_campaign_queue()
    CAMPAIGN_CONSOLE_LOGS.clear()
    add_console_log("Campaign queue and logs cleared by administrative request.", "system")
    return {"status": "success"}

class RetriggerPayload(BaseModel):
    job_id: int

@app.post("/campaign/queue/retrigger")
async def retrigger_campaign_job(payload: RetriggerPayload):
    """Reset a completed or failed job's status to 'queued' to rerun it."""
    success = db_manager.retrigger_campaign_job(payload.job_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to retrigger campaign job.")
    add_console_log(f"Campaign Job ID {payload.job_id} re-enqueued for execution.", "system")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
