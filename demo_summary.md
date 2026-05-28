# Alcon Voice Agent: POC Demo Summary

This document provides a comprehensive overview of the **Alcon Voice Agent** setup. This POC (Proof of Concept) demonstrates an automated, voice-enabled service reminder bot designed to handle outbound customer interactions with premium naturalness and calendar intelligence.

## 🚀 The Technology Stack
*   **TTS (Text-to-Speech):** [ElevenLabs](https://elevenlabs.io/) (via FastAPI streaming) for human-like emotional depth.
*   **STT (Speech-to-Text):** Browser-native **Web Speech API** for ultra-fast, zero-cost voice recognition.
*   **Backend:** **FastAPI** (Python 3) for orchestration, logging, and data management.
*   **Frontend:** Vanilla JS/HTML5 with **Glassmorphism** and CSS3 animations.

## 🛠 Features Implemented

### 1. Natural Voice Personality
*   **Professional Persona:** "Supriya," a Virtual Assistant with a friendly, helpful tone.
*   **Voice Cloning:** Readily supports your own cloned voice via the `VOICE_ID` environment variable.

### 2. Voice-to-Voice (Hands-Free) Flow
*   **Auto-Listening:** After Supriya finishes speaking, the microphone activates automatically.
*   **Visual Waveform:** A pulsating blue waveform provides visual feedback to the user when the AI is "listening."

### 3. "Calendar Intelligence" Engine
*   **Dynamic Parsing:** The code converts natural phrases like *"Monday"*, *"Tomorrow"*, or *"18th April"* into real calendar dates.
*   **Specific Assignments:** The agent doesn't just repeat your words—it confirms the full date and day (e.g., *"Perfect, I've booked you for Monday, April 20th"*).
*   **Auto-Timing:** Assigns different logic for weekday vs. weekend appointment slots.

### 4. Robust Intent Matching
*   **Nuanced Handling:** Recognizes different ways of saying "No" (e.g., *"Not right now"*, *"I'm busy"*, *"Cancel"*).
*   **Polite Error Handling:** Specifically handles "Wrong Number" calls with an automatic apology and hang-up.

### 5. Premium Conversational UI
*   **Chat Bubble Interface:** A modern conversation log featuring left/right-aligned bubbles.
*   **Smooth Transitions:** Messages enter with a fade-in animation and automatically scroll to the bottom.

## 📞 The Conversation Journey (The Demo Flow)

1.  **Identity Check:** The bot calls the customer and confirms their identity via voice.
2.  **Health Check:** Accesses backend data to see if the customer's car (e.g., Hyundai Creta) is due for service.
3.  **The Offer:** If due, the bot explains how many months it has been since the last service and offers a booking.
4.  **Booking Interaction:** The user speaks a date/day. The AI calculates the date and assigns a time slot.
5.  **Conclusion:** The bot confirms the pickup details, ends the call, and saves the **full transcript** to `data/history.json`.

---

## 📊 Business Value for Demo
This setup shows how Alcon can automate high-volume service calls while maintaining a premium, "human" feel, reducing operational costs while improving customer engagement through modern AI technology.

**Demo Ready Status:** ✅ 100%
