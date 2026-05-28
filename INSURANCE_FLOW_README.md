# 🧾 Alcon AI Insurance Telephony System – End-to-End Lifecycle (Points 1–9)

This document outlines the complete architecture and lifecycle of the Alcon AI Insurance Renewal platform, covering both **POC implementation** and **production-ready design**.

---

# 🏗️ 1. Data Sourcing & Preparation (Points 1 & 2)

### ✅ POC Implementation
* Customer data stored in `customers.json` (mock DMS)
* Includes:
  * Name, vehicle, insurer
  * Expiry date
  * DND status
* Manual toggles simulate:
  * Already renewed
  * DND / invalid number

### 🚀 Production Design
* Integration with:
  * Dealer Management System (DMS)
  * Vahan / Insurance APIs
* Real-time validation:
  * Policy status check before every call
* Dynamic segmentation:
  * By expiry date
  * By insurer
  * By renewal probability

---

# 📞 2. Calling Schedule Engine (Point 3)

### ✅ POC Implementation
Fixed stage-based calling:

| Stage | Timeline   | Purpose      |
| ----- | ---------- | ------------ |
| T-30  | Awareness  | Intent check |
| T-15  | Follow-up  | Reminder     |
| T-7   | Urgency    | NCB risk     |
| T-1   | Final push | Conversion   |
| T+1   | Recovery   | Break-in     |

### 🚀 Production Design
* **Campaign Orchestrator**
  * Runs daily
  * Calculates `days_to_expiry`
  * **Quiet Hours Enforcement** (9 AM – 8 PM) to ensure compliance and customer experience.
* Automatically schedules next stage
* Only progresses if:
  * Not converted
  * Not DND
  * Policy still active

---

# 🔁 3. Retry & Reachability Engine (Point 5)

### ✅ POC Implementation
* **Configurable retry intervals** (e.g., 1 min → 5 min → 30 min) implemented in `worker.py`.

### 🚀 Production Design
* **Within-stage retry logic**
  * Retry conditions: NO_ANSWER, BUSY
* Max retries → fallback triggered
* **🔄 Multi-Channel Fallback**: WhatsApp / SMS triggered after max retries within a stage are exhausted to ensure 100% reachability.

---

# 🔐 4. Call Safety & Idempotency Layer

### ✅ POC Implementation
* **Unique job_key**: Prevents duplicate scheduling of the same campaign stage.
* **Pre-call validation**:
  * `policy_status` check: Aborts if already renewed.
  * `dnd_status` check: Aborts if customer opted out.

### 🚀 Production Design
* **Distributed locking (Redis)**: Ensures single-instance execution across multiple workers.
* **Idempotent scheduling**: Across globally distributed workers.
* **Time-window enforcement**: Strict quiet hours compliance.

---

# 🗣️ 5. Conversational AI Engine (Point 4)

### ✅ POC Implementation
* Rule-based intent engine (`flows/insurance_flow.py`)
* Handles: Interested, Busy, Rejected, Already renewed

### 🚀 Production Enhancements
* **💰 Pricing & Comparison Engine**: Deterministic quotes and handling "Too expensive" objections.
* **🔄 Transfer Guardrails**: Double confirmation before agent transfer.
* **📈 Escalation Logic**: Manager callbacks for complex negotiations.
* **🎯 Benefit Positioning**: OEM support, Cashless claims, Paperless process.

---

# 🧾 6. Closure & CRM Automation (Point 6)

### ✅ POC Implementation
* **Internal lead state updated in DB** (designed for future CRM sync).
* Lead status: INTERESTED, NOT_INTERESTED, CONVERTED.

### 🚀 Production Design
* **CRM sync (DMS integration)**: Atomic updates to external records.
* Automated actions: Send payment link, Mark DND, Schedule callback.
* Hot leads flagged instantly for human intervention.

---

# 📊 7. KPI Monitoring Engine (Point 7)

### ✅ POC Implementation
Dashboard tracks:
* Total calls, Connected calls, Conversions, Hot leads.

### 🚀 Production Design
* **📈 Dynamic Lead Scoring**: `Score = intent + urgency + recency`.
* **🔥 Hot Lead Detection**: Score ≥ 85 triggers priority manager handling.
* **📊 Advanced Metrics**: Conversion rates per stage, daily trends.

---

# 🔒 8. Quality & Compliance Engine (Point 8)

### ✅ POC Implementation
* Consent captured digitally and logged.
* Audit summary generated per call.

### 🚀 Production-Grade Compliance
* **✅ IRDAI Audit Engine**: Each call generates a status (PASSED/FAILED/REVIEW_REQUIRED).
* **📋 Audit Fields**: consent_taken, dnd_respected, no_misrepresentation, feedback_score.
* **📡 Audit API**: `GET /telephony/leads/{call_sid}/audit` returns full transcript and compliance results.
* **🚫 DND Enforcement**: "Stop calling" triggers permanent central DND marking.

---

# 🔄 9. Review & Continuous Improvement (Point 9)

### ✅ POC Implementation
* Feedback captured (1–5 scale) at the end of the flow.
* Daily reporting API live (`/telephony/dashboard/reports`).

### 🚀 Production Design
* **📊 Feedback Loop**: Used for script improvement and intent tuning.
* **🤖 Continuous AI Training**: Uses transcripts, objections, and feedback data.

---

# 🧠 System Orchestration Architecture

### Core Components
* **Campaign Orchestrator**: Schedules lifecycle events and enforces Quiet Hours.
* **Worker**: Executes calls, handles retries, and triggers multi-channel fallbacks.
* **Flow Manager**: Controls the conversation logic and sentiment analysis.
* **Database**: Central authority for `lead_states`, `call_logs`, and `consent_logs`.

---

# 🚀 Production Deployment Strategy

| Component  | POC          | Production          |
| ---------- | ------------ | ------------------- |
| Database   | SQLite       | PostgreSQL          |
| Queue      | In-memory    | Redis + Celery      |
| Calls      | Simulated    | Twilio              |
| Messaging  | Console logs | WhatsApp / SMS APIs |
| Compliance | Local logs   | Auditable storage   |
