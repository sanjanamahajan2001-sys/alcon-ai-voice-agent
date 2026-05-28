import asyncio
import aiohttp
import time
import statistics
import random
import sys

BASE_URL = "http://localhost:8000"

# --- PRODUCTION SETTINGS ---
MAX_CONCURRENT_REQUESTS = 500  # Prevent client-side socket exhaustion
VOICE_CPU_FACTOR = 0.05        # Simulated seconds of extra CPU load for STT/TTS emulation
RAMP_UP_DELAY = 0.01           # Delay between spawning each session (seconds)

class StressTestPro:
    def __init__(self, target_concurrency):
        self.target_concurrency = target_concurrency
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.results = []
        self.errors = 0
        self.flow_types = ["insurance", "booking"]

    async def simulate_call(self, session_idx):
        flow_type = random.choice(self.flow_types)
        call_sid = f"CA_STRESS_{int(time.time())}_{session_idx}"
        customer_id = (session_idx % 7) + 1
        
        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                try:
                    latencies = []
                    
                    # 1. INITIAL WEBHOOK: POST /voice (Twilio Call Answered)
                    turn_start = time.time()
                    params = {"CallSid": call_sid, "From": "+910000000000", "Direction": "outbound-api"}
                    async with session.post(f"{BASE_URL}/voice?customer_id={customer_id}&flow_type={flow_type}", data=params) as resp:
                        if resp.status != 200: raise Exception(f"Voice Init Fail: {resp.status}")
                        latencies.append(time.time() - turn_start)

                    # 2. SEQUENTIAL WEBHOOKS: POST /process (Twilio Gather/Speech Result)
                    steps = ["greeting", "booking_options", "final_confirmation"]
                    for step in steps:
                        await asyncio.sleep(random.uniform(0.1, 0.3) + VOICE_CPU_FACTOR)
                        turn_start = time.time()
                        
                        process_data = {
                            "CallSid": call_sid,
                            "SpeechResult": "yes please",
                            "From": "+910000000000"
                        }
                        process_url = f"{BASE_URL}/process?step={step}&customer_id={customer_id}&flow_type={flow_type}"
                        async with session.post(process_url, data=process_data) as resp:
                            if resp.status != 200: raise Exception(f"Process Fail: {resp.status}")
                            latencies.append(time.time() - turn_start)

                    # 3. COMPLETION WEBHOOK: POST /status-callback (Twilio Call Ended)
                    callback_data = {"CallSid": call_sid, "CallStatus": "completed", "CallDuration": "45"}
                    async with session.post(f"{BASE_URL}/status-callback", data=callback_data) as resp:
                        if resp.status != 200: raise Exception(f"Callback Fail: {resp.status}")

                    total_duration = time.time() - start_time
                    self.results.append((latencies, total_duration))
                except Exception as e:
                    # print(f"DEBUG: {str(e)}")
                    self.errors += 1



    async def run(self):
        print(f"\n" + "🔥" * 25)
        print(f"ALCON PRODUCTION STRESS TEST: {self.target_concurrency} CALLERS")
        print(f"🔥" * 25)
        print(f"Settings: Ramp-up={RAMP_UP_DELAY}s, Voice-Factor={VOICE_CPU_FACTOR}s")
        
        start_time = time.time()
        tasks = []
        for i in range(self.target_concurrency):
            tasks.append(self.simulate_call(i))
            await asyncio.sleep(RAMP_UP_DELAY) # Gradual ramp up
            
        print(f"🚀 All {self.target_concurrency} sessions spawned. Awaiting completion...")
        await asyncio.gather(*tasks)
        
        total_time = time.time() - start_time
        self.print_report(total_time)

    def print_report(self, total_time):
        all_lats = [l for res in self.results for l in res[0]]
        successful = len(self.results)
        
        print("\n" + "█" * 50)
        print("📊 PRODUCTION READINESS REPORT")
        print("█" * 50)
        print(f"🏁 Total Calls Attempted: {self.target_concurrency}")
        print(f"✅ Success Rate: {(successful/self.target_concurrency)*100:.1f}% ({successful} passed)")
        print(f"❌ Failure Rate: {(self.errors/self.target_concurrency)*100:.1f}% ({self.errors} failed)")
        print(f"⏱️ Total Campaign Duration: {total_time:.2f}s")
        
        if all_lats:
            avg = statistics.mean(all_lats) * 1000
            p95 = statistics.quantiles(all_lats, n=20)[18] * 1000
            p99 = statistics.quantiles(all_lats, n=100)[98] * 1000
            
            print(f"\n--- LATENCY (Orchestration Brain) ---")
            print(f"⚡ Average Response: {avg:.1f}ms")
            print(f"⚡ P95 (Stable):     {p95:.1f}ms")
            print(f"⚡ P99 (Worst Case): {p99:.1f}ms")
            
            print(f"\n--- TELEPHONY CAPACITY ESTIMATE ---")
            if p99 < 200:
                print("🟢 STATUS: Voice-Ready (Premium Quality)")
            elif p99 < 500:
                print("🟡 STATUS: Voice-Capable (Minor Latency Risk)")
            else:
                print("🔴 STATUS: Hardware Overload (Jitter Risk)")
        
        print("█" * 50 + "\n")

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    asyncio.run(StressTestPro(count).run())
