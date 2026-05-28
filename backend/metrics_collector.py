import os
import time
import json
import threading
from collections import Counter

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class MetricsCollector:
    def __init__(self, redis_host="localhost", redis_port=6379):
        self.start_time = time.time()
        self.local_stats = Counter()
        self.REDIS_KEY = "alcon_metrics"
        self.redis = None
        
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
                self.redis.ping()
                # Ensure the metrics hash exists
                if not self.redis.exists(self.REDIS_KEY):
                    self.redis.hset(self.REDIS_KEY, "tasks_finished", 0)
                print(f"✅ MetricsCollector: Connected to REDIS ({self.REDIS_KEY})")
            except Exception as e:
                print(f"❌ Metrics Connection Failed: {e}")
                self.redis = None

    def _increment(self, field, amount=1):
        if self.redis:
            self.redis.hincrby(self.REDIS_KEY, field, amount)
        else:
            self.local_stats[field] += amount

    def record_request(self, call_sid, worker_pid):
        self._increment("total_requests")
        self._increment(f"worker_{worker_pid}_req")
        if self.redis:
            self.redis.sadd(f"{self.REDIS_KEY}_active", call_sid)
            # Store last activity timestamp
            self.redis.hset(f"{self.REDIS_KEY}_last_activity", call_sid, time.time())
        else:
            self.local_stats["active_count"] += 1

    def record_completion(self, call_sid):
        self._increment("completed_sessions")
        if self.redis:
            self.redis.srem(f"{self.REDIS_KEY}_active", call_sid)
            self.redis.hdel(f"{self.REDIS_KEY}_last_activity", call_sid)

    def record_failure(self, call_sid):
        self._increment("failed_sessions")
        if self.redis:
            self.redis.srem(f"{self.REDIS_KEY}_active", call_sid)
            self.redis.hdel(f"{self.REDIS_KEY}_last_activity", call_sid)

    def record_task_queued(self):
        self._increment("tasks_queued")
        self._increment("async_backlog")

    def record_task_finished(self):
        # ATOMIC SYNC: Ensure tasks_finished is incremented in Redis
        self._increment("tasks_finished")
        # Decrement backlog gauge
        if self.redis:
            self.redis.hincrby(self.REDIS_KEY, "async_backlog", -1)
        else:
            self.local_stats["async_backlog"] -= 1

    def record_retry(self):
        self._increment("retry_count")

    def reset_all(self):
        """Clean all metrics for a fresh test run."""
        if self.redis:
            self.redis.delete(f"{self.REDIS_KEY}_active")
            self.redis.delete(f"{self.REDIS_KEY}_last_activity")
            self.redis.delete(self.REDIS_KEY)
            print("🗑️ Metrics: All keys cleared.")

    def _cleanup_zombies(self):
        """Mock cleanup for active sessions list"""
        pass

    def get_snapshot(self):
        self._cleanup_zombies()
        if self.redis:
            data = self.redis.hgetall(self.REDIS_KEY)
            active_count = self.redis.scard(f"{self.REDIS_KEY}_active")
            
            # Convert all numeric fields to integers
            snapshot = {}
            for k, v in data.items():
                try:
                    snapshot[k] = int(v)
                except:
                    snapshot[k] = v
            
            snapshot["active_sessions"] = active_count
            snapshot["uptime"] = time.time() - self.start_time
            
            # Ensure critical fields exist
            for field in ["total_requests", "completed_sessions", "failed_sessions", "tasks_queued", "tasks_finished", "async_backlog"]:
                if field not in snapshot:
                    snapshot[field] = 0
            
            worker_stats = {k: v for k, v in snapshot.items() if k.startswith("worker_")}
            snapshot["worker_stats"] = worker_stats
            
            # Calculate Drain Rate (Estimated TPS)
            now = time.time()
            uptime = max(1, now - self.start_time)
            snapshot["drain_rate_tps"] = round(snapshot.get("tasks_finished", 0) / uptime, 2)
            snapshot["enqueue_rate_tps"] = round(snapshot.get("tasks_queued", 0) / uptime, 2)
            
            # Safety: Clamp backlog
            if snapshot["async_backlog"] < 0: snapshot["async_backlog"] = 0
            
            return snapshot
        else:
            return {
                "active_sessions": self.local_stats["active_count"],
                "completed_sessions": self.local_stats["completed_sessions"],
                "failed_sessions": self.local_stats["failed_sessions"],
                "total_requests": self.local_stats["total_requests"],
                "tasks_queued": self.local_stats["tasks_queued"],
                "tasks_finished": self.local_stats["tasks_finished"],
                "local_mode": True
            }

metrics = MetricsCollector()
