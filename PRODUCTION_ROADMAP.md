# Alcon AI: Production Roadmap (Hybrid Telephony)

This document outlines the transition from the current **Demo/POC** state to a **Production-Grade** enterprise system for the Insurance Renewal and Service flows.

## 1. Hybrid Switchover (AI ↔ Human)

| Feature | Demo/POC Implementation | Production Implementation |
| :--- | :--- | :--- |
| **Routing** | Hardcoded manager phone number. | **Twilio TaskRouter**: Intelligent skill-based routing (e.g., Insurance Expert vs. Service Advisor). |
| **Availability** | Assumes manager is available. | **Presence Tracking**: AI checks if a human is "Online" in the dashboard before offering a transfer. |
| **Context** | Manager manually opens the dashboard. | **CTI Screen-Pop**: The transcript pops up automatically on the manager's screen as the phone rings. |
| **Reverse Handover** | Manual "Resume AI" button. | **Post-Call Workflow**: AI automatically resumes if the human agent hangs up but the customer is still on the line. |

## 2. Scalability & Infrastructure

| Layer | Demo/POC (Current) | Production (Future) |
| :--- | :--- | :--- |
| **Database** | SQLite (`alcon.db`) - suitable for low concurrency. | **PostgreSQL**: Managed RDS instance for high-concurrency and row-level locking. |
| **State** | In-memory `dict` / `customers.json`. | **Redis**: Distributed session storage for sub-millisecond state recovery. |
| **Worker** | Simple Python background tasks. | **Celery + RabbitMQ**: Distributed task queue for handling thousands of simultaneous calls. |
| **Logs** | Local file system. | **ELK Stack (Elasticsearch)**: Centralized logging for real-time analytics and auditing. |

## 3. Compliance & Security (IRDAI Standards)

*   **DND Integration**: Move from a local mock list to a real-time API integration with the **NCPR (National Customer Preference Register)**.
*   **PII Masking**: Automatically redact sensitive customer data (Credit Card numbers, Policy IDs) from the AI transcripts before they are saved to disk.
*   **Audit Vault**: Move audit logs to an immutable storage (like AWS S3 with Object Lock) to satisfy regulatory requirements for 7-year data retention.

## 4. Enhanced AI Reasoning

*   **Sentiment Trigger**: Automatically escalate to a human if the AI detects **Anger** or **Frustration** score > 0.8, even if the user doesn't ask for a manager.
*   **Multi-Lingual Support**: Expand beyond English to support Hindi and regional languages using multi-lingual LLM models.
*   **Summary Handover**: When resuming, the AI will get a "Short Summary" of the human conversation (transcribed via Twilio Media Streams) so it truly knows what happened.

---
**Status**: Demo Phase Complete. Ready for Production Engineering.
