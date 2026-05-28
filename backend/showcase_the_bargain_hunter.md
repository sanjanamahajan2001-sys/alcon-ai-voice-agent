# Showcase: The Bargain Hunter
**Archetype:** The Bargain Hunter
**Goal:** Aggressively negotiating for the lowest price.

## 🎙️ Conversation Transcript
> **🤖 AI:** Hello Sir, I'm Supriya from Alcon. I see you've been enjoying your Hyundai Creta for 2 years now, and I'm calling because it's currently eligible for an exclusive upgrade to the 2024 model with the same EMI. Is this something you'd like to explore?.
  *(Node: `greeting`)*

> **👤 USER:** The other showroom is giving me a better discount. Can you match it?

> **🤖 AI:** Sure thing. The Hyundai creta focuses on ride comfort and a massive service network compared to competitors. Would you like to know more about the EMI options, or should I arrange a callback? I can connect you with our advisor for the best possible deal. Would that work?.
  *(Node: `inc_query_count`)*

> **👤 USER:** Your EMI is too high. Give me a better interest rate.

> **🤖 AI:** I understand your point Sir. Let me connect you with our specialist who can assist you further with these details. One moment please.
  *(Node: `transfer_node`)*

## 📊 Behavioral Insights
- **Repetition:** NONE
- **Naturalness Score:** 81.0/10
- **Human Readiness:** READY

## 💾 Final Backend State
```json
{
  "call_sid": "showcase_1778819367_The_Bargain_Hunter",
  "lead_status": "INITIATED",
  "lead_score": 0,
  "disposition": null,
  "last_action": "AI Response: I understand your point Sir. Let me connect you wi...",
  "next_step": null,
  "interest_level": "COLD",
  "follow_up_time": null,
  "service_linked": false,
  "whatsapp_sent_at": null,
  "reasoning_trace": null,
  "policy_status": null,
  "priority_score": 0,
  "escalation_status": "NONE",
  "human_agent_id": null,
  "pending_updates": null,
  "escalation_reason": null,
  "updated_at": "2026-05-15 04:29:27.728352",
  "car": "Hyundai Creta",
  "car_model": "Hyundai Creta",
  "memory": {
    "finance_focused": true
  }
}
```
