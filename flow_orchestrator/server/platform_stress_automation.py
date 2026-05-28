import asyncio
import aiohttp
import time
import statistics
import random
import sys
import os
import json
try:
    import psutil
except ImportError:
    psutil = None
from datetime import datetime

# --- CONFIGURATION ---
BASE_URL = "http://localhost:8000"
MAX_CLIENT_CONCURRENCY = 1000
REPORT_FILE = "STRESS_REPORT.md"
SAFE_LATENCY_THRESHOLD_MS = 2000 # 2 seconds is the "Safe" limit for Voice AI

class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process(os.getpid()) if psutil else None
        self.start_time = time.time()
        self.cpu_samples = []
        self.ram_samples = []
        self.loop_lag_samples = []

    async def sample(self):
        if not psutil: return
        while True:
            try:
                self.cpu_samples.append(psutil.cpu_percent())
                self.ram_samples.append(self.process.memory_info().rss / (1024 * 1024))
            except: pass
            loop_start = time.time()
            await asyncio.sleep(0.01)
            lag = (time.time() - loop_start) - 0.01
            self.loop_lag_samples.append(lag * 1000)
            await asyncio.sleep(1)

    def get_metrics(self):
        if not self.cpu_samples: return {}
        return {
            "cpu_avg": statistics.mean(self.cpu_samples),
            "cpu_max": max(self.cpu_samples),
            "ram_avg": statistics.mean(self.ram_samples),
            "ram_max": max(self.ram_samples),
            "lag_p95": statistics.quantiles(self.loop_lag_samples, n=20)[18] if len(self.loop_lag_samples) > 1 else 0
        }

class StressHarness:
    def __init__(self, name="StressTest"):
        self.name = name
        self.results = []
        self.errors = 0
        self.monitor = ResourceMonitor()
        self.session_count = 0
        self.start_time = None
        self.semaphore = asyncio.Semaphore(MAX_CLIENT_CONCURRENCY)
        self.logic_times = []
        self.db_wait_times = []

    async def start(self):
        self.start_time = time.time()
        self.monitor_task = asyncio.create_task(self.monitor.sample())

    async def stop(self):
        self.monitor_task.cancel()
        self.end_time = time.time()

    async def post_form(self, session, url, data=None, params=None):
        async with self.semaphore:
            start = time.time()
            try:
                async with session.post(url, data=data, params=params) as resp:
                    latency = (time.time() - start)
                    metrics_raw = resp.headers.get("X-Internal-Metrics")
                    if metrics_raw:
                        metrics = json.loads(metrics_raw)
                        self.logic_times.append(metrics.get("logic_ms", 0))
                        self.db_wait_times.append(metrics.get("db_wait_ms", 0))
                    if resp.status >= 400: self.errors += 1
                    return await resp.text(), latency
            except Exception:
                self.errors += 1
                return None, (time.time() - start)

    def generate_report(self):
        duration = self.end_time - self.start_time
        latencies = [r['latency'] for r in self.results if r['latency'] is not None]
        metrics = self.monitor.get_metrics()
        avg_lat = statistics.mean(latencies) * 1000 if latencies else 0
        p95 = statistics.quantiles(latencies, n=20)[18] * 1000 if len(latencies) > 1 else 0
        avg_logic = statistics.mean(self.logic_times) if self.logic_times else 0
        avg_db = statistics.mean(self.db_wait_times) if self.db_wait_times else 0
        avg_other = avg_lat - avg_logic
        
        status = "SAFE ✅" if avg_lat < SAFE_LATENCY_THRESHOLD_MS else "SATURATED ❌"
        
        report = f"""
### {self.name} Report - {status}
- **Concurrency**: {self.session_count} Calls
- **Success Rate**: {((len(self.results) - self.errors) / len(self.results) * 100) if self.results else 0:.1f}%
- **Avg Latency**: {avg_lat:.1f}ms
- **P95 Latency**: {p95:.1f}ms
- **Logic / DB / Queue**: {avg_logic:.1f}ms / {avg_db:.1f}ms / {max(0, avg_other):.1f}ms
---
        """
        print(report)
        with open(REPORT_FILE, "a") as f: f.write(report)
        return avg_lat

async def simulate_backend_call(harness, session, idx, flow_type="booking", heavy_db=False):
    call_sid = f"CA_STRESS_{int(time.time())}_{idx}"
    customer_id = (idx % 7) + 1
    
    # Optional heavy DB injection
    params = {"customer_id": str(customer_id), "flow_type": flow_type}
    if heavy_db:
        params["heavy_load"] = "true"

    res, lat = await harness.post_form(session, f"{BASE_URL}/voice", params=params, data={"CallSid": call_sid})
    harness.results.append({"latency": lat, "status": "ok" if res else "error"})
    
    if not res: return
    
    # 2nd step simulation
    res, lat = await harness.post_form(session, f"{BASE_URL}/process", params={"step": "greeting", "customer_id": str(customer_id), "flow_type": flow_type}, data={"CallSid": call_sid, "SpeechResult": "yes"})
    harness.results.append({"latency": lat, "status": "ok" if res else "error"})

async def run_test(category, count):
    print(f"🚀 RUNNING {category.upper()} STRESS TEST: {count} Sessions...")
    harness = StressHarness(f"{category.upper()} Load Test")
    await harness.start()
    harness.session_count = count
    
    heavy_db = (category == "db" or category == "all")
    
    async with aiohttp.ClientSession() as session:
        tasks = [simulate_backend_call(harness, session, i, heavy_db=heavy_db) for i in range(count)]
        await asyncio.gather(*tasks)
        
    await harness.stop()
    harness.generate_report()

async def run_discovery_mode():
    print("🔎 STARTING CONCURRENCY SATURATION DISCOVERY...")
    levels = [1, 5, 10, 20, 50, 100]
    safe_limit = 0
    
    for count in levels:
        harness = StressHarness(f"Capacity Test ({count} calls)")
        await harness.start()
        harness.session_count = count
        async with aiohttp.ClientSession() as session:
            tasks = [simulate_backend_call(harness, session, i) for i in range(count)]
            await asyncio.gather(*tasks)
        await harness.stop()
        avg_lat = harness.generate_report()
        
        if avg_lat < SAFE_LATENCY_THRESHOLD_MS:
            safe_limit = count
        else:
            print(f"⚠️ Saturation reached at {count} calls.")
            break
            
    print(f"\n🏆 PROOF OF CAPACITY: This server safely handles **{safe_limit}** concurrent parallel calls.")
    with open(REPORT_FILE, "a") as f:
        f.write(f"\n## FINAL PROOF\n**Maximum Safe Parallel Capacity: {safe_limit} Sessions**\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", choices=["concurrency", "db", "webhook", "api", "discovery", "all"], default="discovery")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    
    if os.path.exists(REPORT_FILE): os.remove(REPORT_FILE)
    
    with open(REPORT_FILE, "w") as f:
        f.write(f"# Alcon Platform Automation Report\n- **Timestamp**: {datetime.now().isoformat()}\n- **Environment**: WSL Production Cluster\n\n")

    if args.category == "discovery":
        asyncio.run(run_discovery_mode())
    elif args.category == "all":
        # Run sequential suite
        asyncio.run(run_test("concurrency", 50))
        asyncio.run(run_test("db", 50))
        asyncio.run(run_test("api", 50))
    else:
        asyncio.run(run_test(args.category, args.count))
