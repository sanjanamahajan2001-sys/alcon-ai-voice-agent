# Showcase: The Confused Buyer
**Archetype:** The Confused Buyer
**Goal:** Vague timeline and conflicting needs.

## 🎙️ Conversation Transcript
> **🤖 AI:** Hello Sir, I'm Supriya from Alcon. I see you've been enjoying your Hyundai Creta for 2 years now, and I'm calling because it's currently eligible for an exclusive upgrade to the 2024 model with the same EMI. Is this something you'd like to explore?.
  *(Node: `greeting`)*

> **👤 USER:** Maybe I'll buy after 6 months, or maybe sooner if the deal is good.

> **🤖 AI:** I can definitely help with that! Let me give you the key details.
  *(Node: `intro_options`)*

> **👤 USER:** Wait, do you have the Venue instead?

> **🤖 AI:** Great! To help you better, I can share the latest price, ongoing offers, or schedule a test drive for the Venue. What would you prefer?.
  *(Node: `query_intent_check`)*

> **👤 USER:** How does the Venue price compare to Creta?

> **🤖 AI:** I understand your point Sir. Let me connect you with our specialist who can assist you further with these details. One moment please.
  *(Node: `transfer_node`)*

## 📊 Behavioral Insights
- **Repetition:** NONE
- **Naturalness Score:** 81.0/10
- **Human Readiness:** READY

## 💾 Final Backend State
```json
{
  "call_sid": "showcase_1778819367_The_Confused_Buyer",
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
  "updated_at": "2026-05-15 04:29:27.345089",
  "car": "Venue",
  "car_model": "venue",
  "memory": {}
}
```
