import asyncio
import aiohttp
import time
import statistics
import random
import os
import json
import argparse
from datetime import datetime

# --- CONFIGURATION ---
BASE_URL = "http://localhost:8000"
REPORT_FILE = "PLATFORM_RESILIENCE_REPORT.md"
SAFE_LATENCY_THRESHOLD_MS = 2000 # 2 seconds

class MasterResilienceHarness:
    def __init__(self):
        self.results = []
        self.metrics_history = []
        self.BASE_URL = "http://localhost:8000"

    async def reset_backend_metrics(self, session):
        """Reset metrics on the server for a clean run."""
        try:
            async with session.post(f"{self.BASE_URL}/telephony/metrics/reset") as resp:
                if resp.status == 200:
                    print("🧹 SERVER METRICS RESET")
        except Exception as e:
            print(f"⚠️ FAILED TO RESET METRICS: {str(e)}")
        self.metrics = {
            "latency": [],
            "logic_ms": [],
            "db_wait_ms": [],
            "errors": 0
        }

    async def scrape_metrics(self):
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    async with session.get(f"{BASE_URL}/metrics") as resp:
                        data = await resp.json()
                        data["timestamp"] = time.time()
                        self.metrics_history.append(data)
                except: pass
                await asyncio.sleep(2) # Faster scraping for discovery

    async def run_test_category(self, name, task_func, count, duration_mins=0, **kwargs):
        print(f"\n🚀 RUNNING: {name} ({count} sessions)")
        start_time = time.time()
        
        # Start background metric scraper
        scraper = asyncio.create_task(self.scrape_metrics())
        
        # PRODUCTION TUNING: force_close=True forces Gunicorn to re-balance every request
        connector = aiohttp.TCPConnector(limit=5000, force_close=True)
        async with aiohttp.ClientSession(connector=connector) as session:
            if duration_mins > 0:
                end_time = start_time + (duration_mins * 60)
                while time.time() < end_time:
                    tasks = [task_func(session, i, sustained=True, **kwargs) for i in range(count)]
                    await asyncio.gather(*tasks)
                    await asyncio.sleep(1)
            else:
                tasks = [task_func(session, i, **kwargs) for i in range(count)]
                await asyncio.gather(*tasks)
            
        scraper.cancel()
        duration = time.time() - start_time
        avg_lat = self.generate_section_report(name, count, duration)
        return avg_lat

    def verify_requirements(self, snapshot):
        """Analyze snapshot against core business requirements."""
        success_rate = ((len(self.metrics['latency']) - self.metrics['errors']) / len(self.metrics['latency']) * 100) if self.metrics['latency'] else 0
        active_cleared = snapshot.get("active_sessions", 0) == 0
        worker_stats = snapshot.get("worker_stats", {})
        
        # Load Balancing check (Variation coefficient)
        if worker_stats:
            counts = list(worker_stats.values())
            avg = sum(counts) / len(counts)
            balanced = all(abs(c - avg) <= (avg * 0.8) for c in counts) # Within 80% of mean
        else:
            balanced = True

        return {
            "Stability (Success >= 98%)": "PASS ✅" if success_rate >= 98 else "FAIL ❌",
            "Accounting (Active == 0)": "PASS ✅" if active_cleared else "FAIL ❌",
            "Distribution (Worker Balance)": "PASS ✅" if balanced else "WARN ⚠️",
            "Persistence (Completed > 0)": "PASS ✅" if snapshot.get("completed_sessions", 0) > 0 else "FAIL ❌"
        }

    def generate_section_report(self, name, count, duration):
        avg_lat = statistics.mean(self.metrics["latency"]) * 1000 if self.metrics["latency"] else 0
        avg_logic = statistics.mean(self.metrics["logic_ms"]) if self.metrics["logic_ms"] else 0
        avg_db = statistics.mean(self.metrics["db_wait_ms"]) if self.metrics["db_wait_ms"] else 0
        success_rate = ((len(self.metrics['latency']) - self.metrics['errors']) / len(self.metrics['latency']) * 100) if self.metrics['latency'] else 0
        
        report = f"""
## {name}
- **Sessions**: {count}
- **Success Rate**: {success_rate:.1f}%
- **Avg Latency**: {avg_lat:.1f}ms
- **Logic / DB / Queue**: {avg_logic:.1f}ms / {avg_db:.1f}ms / {max(0, avg_lat - avg_logic - avg_db):.1f}ms

### Metrics Snapshot (Global Cluster Truth)
| Time | Active | Worker Load (PID:Req) | Completed | Backlog |
| :--- | :--- | :--- | :--- | :--- |
"""
        recent_snaps = [s for s in self.metrics_history if time.time() - s['timestamp'] < duration + 10]
        for snap in recent_snaps[-3:]:
            t_str = datetime.fromtimestamp(snap.get("timestamp", 0)).strftime("%H:%M:%S")
            stats = snap.get("worker_stats", {})
            worker_str = ", ".join([f"{k.split('_')[1]}:{v}" for k, v in sorted(stats.items())])
            report += f"| {t_str} | {snap.get('active_sessions')} | {worker_str} | {snap.get('completed_sessions', 0)} | {snap.get('async_backlog', 0)} |\n"
        
        # [NEW] Requirement Scorecard
        last_snap = self.metrics_history[-1] if self.metrics_history else {}
        scorecard = self.verify_requirements(last_snap)
        report += "\n### Requirement Scorecard\n"
        for req, status in scorecard.items():
            report += f"- **{req}**: {status}\n"
            
        print(report)
        with open(REPORT_FILE, "a") as f: f.write(report)
        self.metrics = {"latency": [], "logic_ms": [], "db_wait_ms": [], "errors": 0}
        return avg_lat

    async def post(self, session, url, data, params=None):
        start = time.time()
        try:
            async with session.post(url, data=data, params=params, timeout=30) as resp:
                lat = time.time() - start
                m_raw = resp.headers.get("X-Internal-Metrics")
                if m_raw:
                    m = json.loads(m_raw)
                    self.metrics["logic_ms"].append(m.get("logic_ms", 0))
                    self.metrics["db_wait_ms"].append(m.get("db_wait_ms", 0))
                self.metrics["latency"].append(lat)
                return await resp.text(), resp.status
        except:
            self.metrics["errors"] += 1
            return None, 500

# --- SCENARIOS ---

async def test_sustained_lifecycle(session, idx, sustained=False, **kwargs):
    call_sid = f"LIFE_{int(time.time())}_{idx}"
    customer_id = (idx % 7) + 1
    try:
        # turn 1
        await harness.post(session, f"{BASE_URL}/voice", {"CallSid": call_sid}, {"customer_id": str(customer_id)})
        await asyncio.sleep(random.uniform(0.1, 0.5))
        # turn 2
        await harness.post(session, f"{BASE_URL}/process", {"CallSid": call_sid, "SpeechResult": "book"}, {"step": "greeting", "customer_id": str(customer_id)})
    finally:
        # LIFECYCLE FIX: Explicitly signal completion to metrics
        async with session.get(f"{BASE_URL}/metrics/complete?call_sid={call_sid}") as _: pass

async def run_discovery():
    print("🔎 STARTING CONCURRENCY SATURATION DISCOVERY...")
    levels = [1, 5, 10, 20, 50, 100]
    safe_limit = 0
    for count in levels:
        avg_lat = await harness.run_test_category(f"Saturation Test @ {count}", test_sustained_lifecycle, count)
        if avg_lat < SAFE_LATENCY_THRESHOLD_MS:
            safe_limit = count
        else:
            print(f"⚠️ Saturation reached at {count} calls.")
            break
    print(f"\n🏆 PROOF OF CAPACITY: Server safely handles **{safe_limit}** concurrent parallel calls.")

# --- MAIN ---
harness = MasterResilienceHarness()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["full", "discovery"], default="full")
    parser.add_argument("--sessions", type=int, default=50)
    args = parser.parse_args()

    if os.path.exists(REPORT_FILE): os.remove(REPORT_FILE)
    header = f"# ALCON PLATFORM RESILIENCE REPORT\n---\n"
    with open(REPORT_FILE, "w") as f: f.write(header)

    # --- PRE-RUN RESET ---
    async with aiohttp.ClientSession() as session:
        await harness.reset_backend_metrics(session)

    if args.mode == "discovery":
        await run_discovery()
    else:
        await harness.run_test_category("Sustained Active Sessions", test_sustained_lifecycle, args.sessions, duration_mins=1)

    # --- [NEW] PERSISTENCE VALIDATION ---
    print("\n🔍 RUNNING FINAL PERSISTENCE VALIDATION...")
    await asyncio.sleep(5) # Wait for final async tasks to settle
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/metrics") as resp:
            final_snap = await resp.json()
            reqs = final_snap.get("total_requests", 0)
            tasks_q = final_snap.get("tasks_queued", 0)
            tasks_f = final_snap.get("tasks_finished", 0)
            backlog = final_snap.get("async_backlog", 0)
            
            print(f"📊 Final Results: {reqs} Requests | {tasks_q} Tasks Queued | {tasks_f} Tasks Finished")
            if backlog == 0 and tasks_f >= reqs:
                print("✅ PERSISTENCE VALIDATION: All tasks processed successfully.")
            else:
                print(f"⚠️ PERSISTENCE WARNING: {backlog} tasks still in queue or missing.")

if __name__ == "__main__":
    asyncio.run(main())
