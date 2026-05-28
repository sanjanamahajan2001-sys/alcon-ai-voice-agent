import asyncio
import aiohttp
import time
import statistics
import random

BASE_URL = "http://localhost:8000"

async def simulate_conversation(session_name, customer_id):
    """Simulates a full 4-turn P&D Workshop Update conversation."""
    async with aiohttp.ClientSession() as session:
        start_time = time.time()
        
        # 1. Start Session
        try:
            async with session.post(f"{BASE_URL}/sessions/start/pd_workshop_update?from_phone=+91988101276{customer_id}") as resp:
                data = await resp.json()
                session_id = data['session_id']
        except Exception as e:
            return None, 0

        latencies = []
        
        # 2. Simulation Steps (Greeting -> ID -> Concern -> Price -> End)
        messages = ["yes", "no", "yes please proceed", "thank you"]
        
        for msg in messages:
            step_start = time.time()
            try:
                async with session.post(f"{BASE_URL}/sessions/{session_id}/message", json={"text": msg}) as resp:
                    await resp.json()
                    latencies.append(time.time() - step_start)
            except Exception:
                return None, 0
            
            # Tiny sleep to simulate human typing delay (optional, but keep small for stress)
            await asyncio.sleep(random.uniform(0.1, 0.3))

        total_duration = time.time() - start_time
        return latencies, total_duration

async def run_stress_test(concurrent_calls=100):
    print(f"\n🚀 STARTING STRESS TEST: {concurrent_calls} Concurrent Conversations")
    print(f"📊 Target: http://localhost:8000")
    print("-" * 50)

    start_time = time.time()
    tasks = []
    for i in range(concurrent_calls):
        tasks.append(simulate_conversation(f"User_{i}", (i % 7) + 1))

    results = await asyncio.gather(*tasks)
    
    # Process Results
    all_latencies = []
    successful_calls = 0
    total_times = []

    for latencies, duration in results:
        if latencies:
            all_latencies.extend(latencies)
            total_times.append(duration)
            successful_calls += 1

    end_time = time.time()
    total_elapsed = end_time - start_time

    # Display Metrics
    print("\n" + "="*50)
    print("📈 PERFORMANCE REPORT")
    print("="*50)
    print(f"✅ Successful Conversations: {successful_calls} / {concurrent_calls}")
    print(f"⏱️ Total Wall Time: {total_elapsed:.2f} seconds")
    
    if all_latencies:
        print(f"⚡ Avg Orchestration Latency: {statistics.mean(all_latencies)*1000:.2f} ms")
        print(f"⚡ P95 Orchestration Latency: {statistics.quantiles(all_latencies, n=20)[18]*1000:.2f} ms")
        print(f"⚡ P99 Orchestration Latency: {statistics.quantiles(all_latencies, n=100)[98]*1000:.2f} ms")
    
    print(f"🔄 Throughput: { (successful_calls * 4) / total_elapsed:.2f} turns/sec")
    print("="*50 + "\n")

if __name__ == "__main__":
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    asyncio.run(run_stress_test(count))
