# Alcon Voice Agent: Telephony Demo Summary (Phase 2)

This document details the transition from a Web-based POC to a **Real Phone Demo** using the Twilio Telephony layer. This upgrade allows the Alcon Voice Agent (Supriya) to engage with customers directly via cellular networks.

## 📱 Telephony Architecture
*   **Carrier Gateway:** **Twilio** handles the cellular call connection and media streaming.
*   **Webhook Tunnel:** **Ngrok** provides a secure tunnel (`https://grinning-linked-rebuilt.ngrok-free.dev`) exposing our local FastAPI server to the global internet.
*   **Voice Engine:** We use Twilio's **`<Say>`** (TwiML) for high-reliability Text-to-Speech and **`<Gather>`** for real-time Speech-to-Text (telephony-native).
*   **Flow Logic:** Ported from the original Frontend JS to a backend **`FlowManager`**, ensuring logic parity between the Web and Phone demos.

---

## 🔐 Token & Credential Management
We handle sensitive credentials using a strictly controlled environment variable system:

### 1. The Secrets Store (`.env`)
All API keys and platform tokens are stored in the `backend/.env` file. These are **never** hardcoded into the logic.
*   `TWILIO_ACCOUNT_SID`: Your Twilio platform identifier.
*   `TWILIO_AUTH_TOKEN`: The secure key for API requests.
*   `TWILIO_PHONE_NUMBER`: The dedicated Alcon demo number (`+1 978 355 1769`).

### 2. Live Orchestration
*   **FastAPI Integration:** Upon startup, the backend loads these tokens into memory using `python-dotenv`.
*   **Stateless Webhooks:** Every time a call interaction happens, our server verifies the incoming request and generates signed **TwiML** responses securely.

---

## 🛠 Features Ported to Telephony

| Feature | Legacy (Web) | Current (Telephony) |
| :--- | :--- | :--- |
| **Voice** | ElevenLabs (Streaming) | Twilio Native TTS (Optimized for phone) |
| **STT** | Web Speech API | Twilio `<Gather>` Speech-to-Text |
| **Flow** | Frontend State Machine | Backend `FlowManager` (Stateless) |
| **Dates** | JS `parseDatePhrase` | Python `date_utils.py` (NLP Date Parsing) |
| **Audit** | `data/history.json` | Twilio Debugger + Terminal Logs |
| **Leads** | None | `data/leads.json` (New Lead Capture) |

---

## 🏎 Section 2: Pre-Sales & Digital Receptionist (New)

We have expanded the agent's capabilities to handle the front-office and sales-enquiry functions of the dealership.

### 1. Digital Receptionist (Inbound)
*   **Authentication:** Automatically identifies existing customers by phone number.
*   **Intent Routing:** AI asks if the caller needs **Sales** or **Service**.
*   **Lead Capture:** If the caller is unknown, the AI captures their name and persists it to the `leads.json` database before transferring.
*   **Multilingual:** Features a bilingual (Hindi/English) welcome for a premium local experience.

### 2. Pre-Sales Lead Qualification (Outbound/Inbound)
*   **Objective:** Qualify leads by answering FAQs before involving a human Sales Representative.
*   **KB Integration:** AI answers questions about Price, Mileage, Features, and Colors using `data/kb.json`.
*   **Proactive Upselling:** Automatically suggests EMI options and Exchange bonuses when price is discussed.
*   **Dynamic Transfer:** If the lead is qualified (interested in a test drive or representative), the AI performs a **Round-Robin** transfer to the next available Sales Rep (e.g., Vikram or Ananya).

---

## 🧪 Exact Testing Procedure (How to Run the Demo)

### Step 1: Prepare the Environment
Ensure your local server is authenticated and ready:
```bash
cd ~/Alcon/poc/backend
# Activate your venv if not done
source ../venv/bin/activate 

# Add missing dependency
pip install python-dotenv
```

### Step 2: Launch the Backend
Start the FastAPI server which will listen for Twilio's webhooks:
```bash
python main.py
```
*   **Note:** Your server must be running on **Port 8000**.

### Step 3: Verify the Tunnel (Ngrok)
Ensure ngrok is active and pointing to the correct URL we configured in Twilio:
```bash
ngrok http 8000
```
*   **Target URL:** `https://grinning-linked-rebuilt.ngrok-free.dev`

### Step 4: Trigger the Outbound Call
Since Alcon initiates the call to the customer, run this script in a **new terminal**:
```bash
cd ~/Alcon/poc/backend
# Call Customer 1 (Aditya) at 9881012767
python make_call.py 1 9881012767
```

### Step 5: The Conversation
1.  **Pick up the phone.**
2.  **Greeting:** AI asks "Hello, am I speaking with Aditya?".
3.  **Confirm:** Say "Yes, speaking."
4.  **Date Booking:** AI mentions service is due. Say "Book it for tomorrow morning."
5.  **Confirmation:** AI confirms "Tomorrow morning at 9:30 AM" and hangs up.

---

## 📊 Monitoring & Logs
*   **Local:** Watch the FastAPI console for `User said: [...]` and `Returning TwiML` logs.
*   **Twilio Console:** Visit the [Twilio Call Logs](https://console.twilio.com/us1/monitor/logs/calls) to see call duration, cost, and raw speech-to-text accuracy.
