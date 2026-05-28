import sys
import os
import asyncio
import json
import time
from typing import List, Dict, Any
from datetime import datetime

# Add current working directory to path
sys.path.append(os.getcwd())

from flow_manager import FlowManager
from database import DatabaseManager

class ShowcaseRunner:
    def __init__(self):
        self.db = DatabaseManager()
        self.fm = FlowManager()
        self.results = []

    async def simulate_persona_journey(self, persona: Dict[str, Any], scenario_name: str):
        """Simulate a full journey for a specific persona archetypes."""
        call_sid = f"showcase_{int(time.time())}_{scenario_name.replace(' ', '_')}"
        
        print(f"\n🎭 [PERSONA] {persona['archetype']}: {scenario_name}")
        print("="*60)
        
        transcript = []
        
        # 1. AI Greeting
        context = {
            "call_sid": call_sid, "session_id": call_sid, "flow_type": "pre_sales",
            "variables": {
                "name": "Test User", "car_model": "Hyundai Creta", "car": "Creta",
                "campaign_type": "upgrade", "vehicle_age": 2
            },
            "history": [], "current_node_id": "start"
        }
        
        # Initialize DB State
        self.db.update_lead_state(call_sid, lead_status="INITIATED", interest_level="COLD")

        # --- Continuation Logic (Persistence Simulation) ---
        if persona.get("is_continuation"):
            print(f"[PERSISTENCE] Loading previous session context for {persona['archetype']}...")
            self.db.update_lead_state(call_sid, 
                lead_status="WARM_LEAD", 
                car="Venue", 
                car_model="venue",
                memory={"has_loyalty": True, "previously_discussed": "the Venue exchange bonus"}
            )
            context["is_returning_customer"] = True # Force bypass intro
            context["variables"]["car"] = "Venue"
            context["variables"]["car_model"] = "venue"
            context["variables"]["memory"] = {"has_loyalty": True, "previously_discussed": "the Venue exchange bonus"}
        
        res = self.fm.orchestrator.sync_process_turn(call_sid, None, "pre_sales_template", context)
        # Sync to SessionManager
        self.fm.session_manager.save_session(call_sid, {
            "current_node_id": res["current_node_id"],
            "params": res["variables"],
            "history": res["history"],
            "step": "continue"
        })
        ai_msg = res.get("text", "")
        transcript.append({"role": "AI", "text": ai_msg, "node": "greeting"})
        print(f"🤖 AI: {ai_msg}")

        # 2. Sequential Interaction
        for i, user_input in enumerate(persona["inputs"]):
            print(f"👤 USER: {user_input}")
            
            # Sync context for turn
            context["current_node_id"] = res["current_node_id"]
            context["variables"] = res["variables"]
            context["history"] = res["history"]
            
            # Process turn
            res = self.fm.orchestrator.sync_process_turn(call_sid, user_input, "pre_sales_template", context)
            
            # Sync to SessionManager
            self.fm.session_manager.save_session(call_sid, {
                "current_node_id": res["current_node_id"],
                "params": res["variables"],
                "history": res["history"],
                "step": "continue"
            })
            
            ai_msg = res.get("text", "")
            session = self.fm.session_manager.get_session(call_sid)
            curr_node = session.get("current_node_id", "unknown")
            
            transcript.append({"role": "USER", "text": user_input})
            transcript.append({"role": "AI", "text": ai_msg, "node": curr_node})
            
            print(f"🤖 AI: {ai_msg}")
            
            if res.get("status") == "COMPLETED":
                break

        # 3. Behavioral Analysis
        state = self.db.get_lead_state(call_sid)
        quality_report = self.analyze_behavior(transcript, state)
        
        self.results.append({
            "scenario": scenario_name,
            "persona": persona["archetype"],
            "transcript": transcript,
            "final_state": state,
            "quality": quality_report
        })
        
        self.generate_markdown_artifact(scenario_name, persona, transcript, quality_report, state)

    def analyze_behavior(self, history, final_state):
        """Analyze conversational quality and adaptive behavior."""
        if not history: return {"score": 0, "observations": ["No conversation occurred"]}
        
        score = 80 # Base score
        metrics = {"Naturalness": 0, "Repetition": 0, "Escalation Timeliness": 0}
        
        # Compression Metric (avg words per response)
        ai_msgs = [m for m in history if m["role"] == "AI"]
        if ai_msgs:
            avg_words = sum(len(m["text"].split()) for m in ai_msgs) / len(ai_msgs)
            if avg_words < 20: metrics["Naturalness"] += 1.5
            elif avg_words > 40: metrics["Naturalness"] -= 1.0
            
        # Re-eval Empathy loops (Repetition)
        for i in range(len(ai_msgs) - 1):
            if ai_msgs[i]["text"][:20] == ai_msgs[i+1]["text"][:20]:
                metrics["Repetition"] -= 2.0
                
        # Conversion Metric (Transfer timing)
        has_transfer = any("connect" in m["text"].lower() or "transfer" in m["text"].lower() for m in ai_msgs)
        if has_transfer: metrics["Escalation Timeliness"] += 1.0
        
        observations = []
        ai_texts = [m["text"].lower() for m in ai_msgs]
        user_msgs = [m["text"].lower() for m in history if m["role"] == "USER"]
        
        # 1. Repetition & Robotic Pattern Detection
        if len(ai_texts) != len(set(ai_texts)):
            score -= 15
            observations.append("REPETITIVE: Found duplicate AI responses.")
            
        robotic_phrases = ["absolutely thrilled", "deep dive", "representative", "clarify", "transparency"]
        robotic_count = sum(1 for m in ai_texts if any(phrase in m for phrase in robotic_phrases))
        if robotic_count > 3:
            score -= 10
            observations.append("TONE: AI used too many marketing/robotic phrases.")

        # 2. Memory & Continuity Check
        loyalty_mentioned = any("10 years" in m or "loyalty" in m for m in user_msgs)
        loyalty_referenced = any("loyal hyundai owner" in m for m in ai_texts)
        if loyalty_mentioned and not loyalty_referenced:
            score -= 15
            observations.append("MEMORY: AI failed to acknowledge loyalty mention later in call.")
        elif loyalty_mentioned and loyalty_referenced:
            score += 10
            observations.append("MEMORY: AI successfully referenced customer loyalty.")

        # 3. Escalation Smoothness
        escalated = final_state and final_state.get("escalation_status") == "IN_PROGRESS"
        engagement = final_state and int(final_state.get("engagement_depth", 0))
        if escalated and engagement < 2:
            score -= 20
            observations.append("ESCALATION: Escalated too early without enough engagement.")
        elif escalated and engagement >= 3:
            score += 10
            observations.append("ESCALATION: Timely and qualified escalation to manager.")

        # 4. Empathy & Acknowledgment
        acks = ["fair question", "understand", "point", "respect", "makes sense"]
        ack_count = sum(1 for m in ai_texts if any(ack in m for ack in acks))
        if ack_count < 1:
            score -= 10
            observations.append("EMPATHY: AI lacked human-like acknowledgments.")
        
        return {
            "naturalness_score": max(0, min(100, score + sum(metrics.values()))),
            "human_readiness": "READY" if score > 70 else "NEEDS_TUNING",
            "repetition": "DETECTED" if len(ai_texts) != len(set(ai_texts)) else "NONE",
            "observations": observations
        }

    def generate_markdown_artifact(self, name, persona, transcript, quality, state):
        """Generate a formatted showcase report."""
        output = f"# Showcase: {name}\n"
        output += f"**Archetype:** {persona['archetype']}\n"
        output += f"**Goal:** {persona['goal']}\n\n"
        
        output += "## 🎙️ Conversation Transcript\n"
        for t in transcript:
            role_icon = "🤖" if t["role"] == "AI" else "👤"
            output += f"> **{role_icon} {t['role']}:** {t['text']}\n"
            if t.get("node"):
                output += f"  *(Node: `{t['node']}`)*\n\n"
            else:
                output += "\n"
                
        output += "## 📊 Behavioral Insights\n"
        output += f"- **Repetition:** {quality['repetition']}\n"
        output += f"- **Naturalness Score:** {quality['naturalness_score']}/10\n"
        output += f"- **Human Readiness:** {quality['human_readiness']}\n\n"
        
        output += "## 💾 Final Backend State\n"
        output += f"```json\n{json.dumps(state, indent=2, default=str)}\n```\n"
        
        # Save as artifact
        artifact_name = f"showcase_{name.lower().replace(' ', '_')}.md"
        with open(artifact_name, "w") as f:
            f.write(output)
        print(f"✨ Showcase Report Generated: {artifact_name}")

async def main():
    showcase = ShowcaseRunner()
    
    personas = [
        {
            "archetype": "The Skeptic",
            "goal": "Verify all hidden costs before even considering a transfer.",
            "inputs": [
                "What's the catch? Why are you calling now?",
                "Is this a loan? What are the interest rates?",
                "Okay, is there any hidden processing fee?",
                "Fine, you can connect me to your manager to explain this."
            ]
        },
        {
            "archetype": "The Emotional Brand-Loyal",
            "goal": "Wants to be recognized as a long-term customer.",
            "inputs": [
                "I've been with Hyundai for 10 years, do I get a loyalty bonus?",
                "The new Creta looks good, but my current one is perfect.",
                "If the manager can give me a special loyalty discount, then I'll talk."
            ]
        },
        {
            "archetype": "The Busy Professional",
            "goal": "High value but extremely short on time.",
            "inputs": [
                "I'm in a meeting. Be quick.",
                "EMI offers? Just email them to me.",
                "No, wait, did you say 20,000 exchange bonus? Tell me more.",
                "Actually, call me back at 5 PM today."
            ]
        },
        {
            "archetype": "The Test Drive Enthusiast",
            "goal": "Wants to experience the car immediately.",
            "inputs": [
                "I want a test drive of the new Creta.",
                "Yes, connect me to the manager to book it."
            ]
        },
        {
            "archetype": "The Confused Buyer",
            "goal": "Vague timeline and conflicting needs.",
            "inputs": [
                "Maybe I'll buy after 6 months, or maybe sooner if the deal is good.",
                "Wait, do you have the Venue instead?",
                "How does the Venue price compare to Creta?",
                "Actually, just tell me the EMI for the Creta again."
            ]
        },
        {
            "archetype": "The Angry Service Customer",
            "goal": "Frustrated with past dealership experience.",
            "inputs": [
                "Why are you calling for a new car? Your service center never calls back!",
                "I had a terrible experience last time my car went for repairs.",
                "If I buy a new one, will the service be better?",
                "Okay, explain the exchange bonus then."
            ]
        },
        {
            "archetype": "The Distrustful Customer",
            "goal": "Privacy concerned and skeptical of the call origin.",
            "inputs": [
                "How did you get my number? Is this a scam?",
                "I don't remember giving consent for marketing calls.",
                "Fine, if you are from Alcon, what color is my current car?",
                "Okay, what's the loyalty benefit you mentioned?"
            ]
        },
        {
            "archetype": "The Bargain Hunter",
            "goal": "Aggressively negotiating for the lowest price.",
            "inputs": [
                "The other showroom is giving me a better discount. Can you match it?",
                "Your EMI is too high. Give me a better interest rate.",
                "Okay, what is the final on-road price if I book today?",
                "Fine, connect me to the manager for the final discount."
            ]
        },
        {
            "archetype": "The Silent Listener",
            "goal": "Gives minimal feedback, needs proactive probing.",
            "inputs": [
                "Hmm.",
                "Okay.",
                "Haan.",
                "Tell me more."
            ]
        },
        {
            "archetype": "The Family Decision Maker",
            "goal": "Needs to consult spouse before deciding.",
            "inputs": [
                "The car looks good, but I need to ask my wife first.",
                "She will decide on the color and the model.",
                "Can you call me back after I discuss this with her?",
                "Yes, evening would be better."
            ]
        },
        {
            "archetype": "The Competitor Buyer",
            "goal": "Compares Hyundai unfavorably to Kia or Tata.",
            "inputs": [
                "I was looking at the Kia Seltos, it feels more modern.",
                "Tata cars are much safer, right? How is Hyundai safety?",
                "Does the Creta have better mileage than the MG Astor?",
                "Okay, if the manager can prove Creta is better, I'll talk."
            ]
        },
        {
            "archetype": "The Callback Continuation",
            "goal": "Resuming a previous conversation about the Venue.",
            "is_continuation": True,
            "inputs": [
                "Yes, you called me yesterday about the Venue offers.",
                "I wanted to know if the exchange bonus is still active?",
                "Okay, and what about the test drive we discussed?",
                "Great, connect me to book it now."
            ]
        },
        {
            "archetype": "The Fast Closer",
            "goal": "Wants immediate price information and quick resolution.",
            "inputs": [
                "Just give me the final price for the top model.",
                "That's too high. Can you connect me to someone for the best deal?"
            ]
        },
        {
            "archetype": "The Technical Questioner",
            "goal": "Focuses on vehicle specifications and performance metrics.",
            "inputs": [
                "What's the engine specs? Does it have the turbo variant?",
                "What about the mileage? Is it better than the Seltos?"
            ]
        },
        {
            "archetype": "The Callback Only User",
            "goal": "Deflects interaction to a later time.",
            "inputs": [
                "I'm in a meeting right now, please call me in the evening.",
            ]
        },
        {
            "archetype": "The Rapid Multi-Question User",
            "goal": "Asks several questions in one go.",
            "inputs": [
                "What's the price, mileage, and waiting period for the Creta?",
            ]
        }
    ]
    
    print("="*60)
    print("ALCON CONVERSATION SHOWCASE GENERATOR")
    print("="*60)
    
    for persona in personas:
        await showcase.simulate_persona_journey(persona, persona["archetype"])

if __name__ == "__main__":
    asyncio.run(main())
