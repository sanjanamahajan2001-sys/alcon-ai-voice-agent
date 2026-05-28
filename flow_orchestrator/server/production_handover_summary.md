# Alcon Orchestrator: Template Management & Production Safety

This document summarizes the new production-ready features for the AI Telephony Orchestration engine, specifically focusing on the **Draft-to-Master** workflow and live call stability.

## 1. The Workflow: Draft vs. Master

To ensure operational safety, we have implemented a multi-stage update process:

1.  **Stage 1: Save (Draft Creation)**
    *   When a manager edits a flow in the UI and clicks **Save Configuration**, the system creates a **Draft**.
    *   This draft is versioned (e.g., `_draft_v2`) and does **not** affect production calls.
    *   Managers can test this draft in the **Simulator** safely.

2.  **Stage 2: Publish (Promotion to Master)**
    *   Once a draft is vetted, clicking **Publish to Master** promotes it to the global template.
    *   The system automatically performs a "Deep Clean," stripping all developer/draft suffixes to ensure a professional production ID.

## 2. Production Safety & Live Call Stability

### **How it behaves during Live Calls**
A common concern is whether updating a template "breaks" calls that are currently in progress. 

*   **Version Pinning**: In production, when a call starts, the session is "pinned" to the version of the template that was active at that exact second.
*   **Atomic Updates**: When a new template is published, only **new** calls pick up the update. **Live calls continue uninterrupted** on their original logic until they hang up.
*   **Session Persistence**: Unlike the development environment (which uses in-memory storage for speed), production uses a persistent database (PostgreSQL/Redis). This ensures that even if a server restarts, the call context is never lost.

### **Why did the Simulator go "Blank" during the demo?**
During development, we use a tool called `uvicorn --reload`. This tool is designed to restart the server every time a file is edited to save developer time. In a **Production Environment**, this reloader is turned off. The system remains 100% online while templates are being updated in the background.

## 3. Disaster Recovery: Version History

The system now features an **Automatic Audit Trail**:
*   **Instant Backups**: Before any Master Template is overwritten, the system copies the current version to `server/templates/history/`.
*   **Timestamped Records**: Every backup is named with a precise timestamp (e.g., `post_service_feedback_20260511_1340.json`).
*   **Rollback Capability**: If a mistake is made, a manager can revert to a previous "Gold Version" in seconds by simply restoring the file from the history folder.

## 4. Business Value
*   **Agility**: Conversational scripts can be updated by the business team in real-time without waiting for a developer release cycle.
*   **Compliance**: Full history of every script change ever made is preserved for auditing purposes.
*   **Safety**: Zero risk of breaking live telephony traffic during script updates.
