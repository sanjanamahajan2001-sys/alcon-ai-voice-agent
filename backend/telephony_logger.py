import json
import os
import asyncio
import threading
import time
from datetime import datetime
import redis

# Redis Configuration with Fallback
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
    print("[LOGGER] Redis connected successfully for shared telephony cache.")
except Exception as e:
    redis_client = None
    REDIS_AVAILABLE = False
    print(f"[LOGGER] Redis connection failed, falling back to process-safe local files: {e}")

class FileLock:
    """Atomic cross-process file lock using os.open with O_CREAT and O_EXCL."""
    def __init__(self, lock_file_path, timeout=10):
        self.lock_file_path = lock_file_path
        self.timeout = timeout
        self.is_locked = False

    def __enter__(self):
        start_time = time.time()
        while True:
            try:
                fd = os.open(self.lock_file_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                self.is_locked = True
                break
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    # Break the lock if expired
                    try:
                        os.remove(self.lock_file_path)
                    except:
                        pass
                time.sleep(0.05)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_locked:
            try:
                os.remove(self.lock_file_path)
            except:
                pass
            self.is_locked = False

class TelephonyLogger:
    def __init__(self, history_file="data/telephony_history.json"):
        self.history_file = history_file
        self.lock_file = history_file + ".lock"
        self.COST_PER_MINUTE = 0.013
        self.COST_PER_100_CHARACTERS = 0.08
        
        # Local cache fallback and single-process thread safety lock
        self._cache = {}
        self._lock = threading.Lock()
        
        if not os.path.exists("data"):
            os.makedirs("data")
            
        # Perform initial merge from disk
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()

    def _load_and_merge(self):
        """Loads from disk and merges with current memory cache, retaining most up-to-date info."""
        if not os.path.exists(self.history_file):
            return
            
        try:
            with open(self.history_file, "r") as f:
                disk_data = json.load(f)
        except Exception as e:
            print(f"[LOGGER] Failed to read history file: {e}")
            return

        for call_sid, disk_call in disk_data.items():
            if call_sid not in self._cache:
                self._cache[call_sid] = disk_call
            else:
                mem_call = self._cache[call_sid]
                
                # Take the most up-to-date metrics/status
                disk_transcript = disk_call.get("transcript", [])
                mem_transcript = mem_call.get("transcript", [])
                
                if len(disk_transcript) > len(mem_transcript):
                    mem_call["transcript"] = disk_transcript
                    
                if disk_call.get("status") == "completed":
                    mem_call["status"] = "completed"
                    mem_call["current_step"] = "Finished"
                    
                mem_call["duration_seconds"] = max(mem_call.get("duration_seconds", 0), disk_call.get("duration_seconds", 0))
                mem_call["total_characters"] = max(mem_call.get("total_characters", 0), disk_call.get("total_characters", 0))
                mem_call["estimated_cost"] = max(mem_call.get("estimated_cost", 0.0), disk_call.get("estimated_cost", 0.0))
                
                if "recording_url" in disk_call and disk_call["recording_url"]:
                    mem_call["recording_url"] = disk_call["recording_url"]
                if "end_time" in disk_call and disk_call["end_time"]:
                    mem_call["end_time"] = disk_call["end_time"]

    def _write_to_disk(self):
        """Write current cache to disk safely. Must be called under lock."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self._cache, f, indent=4)
        except Exception as e:
            print(f"[LOGGER ERROR] Failed to write history: {e}")

    def start_call(self, call_sid, customer_id, customer_name, to_number):
        call_data = {
            "call_sid": call_sid,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "to_number": to_number,
            "start_time": datetime.now().isoformat(),
            "status": "in-progress",
            "current_step": "Initializing",
            "duration_seconds": 0,
            "total_characters": 0,
            "estimated_cost": 0.0,
            "transcript": []
        }

        # 1. Update in Redis
        if REDIS_AVAILABLE:
            try:
                redis_client.set(f"alcon:call:{call_sid}", json.dumps(call_data))
                redis_client.sadd("alcon:active_calls", call_sid)
            except Exception as e:
                print(f"[LOGGER] Redis error in start_call: {e}")

        # 2. Update persistently on disk
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
                if call_sid not in self._cache:
                    self._cache[call_sid] = call_data
                    self._write_to_disk()

        print(f"[LOGGER] Starting log for {call_sid} (Customer: {customer_name})")

    def update_step(self, call_sid, step_name):
        # 1. Update in Redis
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(f"alcon:call:{call_sid}")
                if data:
                    call_data = json.loads(data)
                    call_data["current_step"] = step_name
                    redis_client.set(f"alcon:call:{call_sid}", json.dumps(call_data))
            except Exception as e:
                print(f"[LOGGER] Redis error in update_step: {e}")

        # 2. Update persistently on disk
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
                if call_sid in self._cache:
                    self._cache[call_sid]["current_step"] = step_name
                    self._write_to_disk()

    def log_event(self, call_sid, speaker, text, characters=0):
        # 1. Update in Redis
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(f"alcon:call:{call_sid}")
                if data:
                    call_data = json.loads(data)
                    transcript = call_data.get("transcript", [])
                    if not transcript or transcript[-1]["speaker"] != speaker or transcript[-1]["text"] != text:
                        call_data["transcript"].append({
                            "timestamp": datetime.now().isoformat(),
                            "speaker": speaker,
                            "text": text
                        })
                    if characters > 0:
                        call_data["total_characters"] += characters
                        char_cost = (call_data["total_characters"] / 100) * self.COST_PER_100_CHARACTERS
                        minute_cost = (call_data["duration_seconds"] / 60) * self.COST_PER_MINUTE
                        call_data["estimated_cost"] = round(char_cost + minute_cost, 4)
                    redis_client.set(f"alcon:call:{call_sid}", json.dumps(call_data))
            except Exception as e:
                print(f"[LOGGER] Redis error in log_event: {e}")

        # 2. Update persistently on disk
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
                if call_sid in self._cache:
                    transcript = self._cache[call_sid]["transcript"]
                    if not transcript or transcript[-1]["speaker"] != speaker or transcript[-1]["text"] != text:
                        self._cache[call_sid]["transcript"].append({
                            "timestamp": datetime.now().isoformat(),
                            "speaker": speaker,
                            "text": text
                        })
                    if characters > 0:
                        self._cache[call_sid]["total_characters"] += characters
                        char_cost = (self._cache[call_sid]["total_characters"] / 100) * self.COST_PER_100_CHARACTERS
                        minute_cost = (self._cache[call_sid]["duration_seconds"] / 60) * self.COST_PER_MINUTE
                        self._cache[call_sid]["estimated_cost"] = round(char_cost + minute_cost, 4)
                    self._write_to_disk()

    def end_call(self, call_sid, duration_seconds):
        call_data = None

        # 1. Update in Redis
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(f"alcon:call:{call_sid}")
                if data:
                    call_data = json.loads(data)
                    call_data["status"] = "completed"
                    call_data["current_step"] = "Finished"
                    call_data["duration_seconds"] = int(duration_seconds)
                    call_data["end_time"] = datetime.now().isoformat()
                    
                    char_cost = (call_data["total_characters"] / 100) * self.COST_PER_100_CHARACTERS
                    minute_cost = (int(duration_seconds) / 60) * self.COST_PER_MINUTE
                    call_data["estimated_cost"] = round(char_cost + minute_cost, 4)
                    
                    redis_client.srem("alcon:active_calls", call_sid)
                    # Cache in Redis with 1 hour expiration
                    redis_client.setex(f"alcon:call:{call_sid}", 3600, json.dumps(call_data))
            except Exception as e:
                print(f"[LOGGER] Redis error in end_call: {e}")

        # 2. Update persistently on disk
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
                if call_sid in self._cache:
                    mem_call = self._cache[call_sid]
                    mem_call["status"] = "completed"
                    mem_call["current_step"] = "Finished"
                    mem_call["duration_seconds"] = int(duration_seconds)
                    mem_call["end_time"] = datetime.now().isoformat()
                    
                    # Update local using whatever metrics are newer
                    if call_data:
                        mem_call["total_characters"] = max(mem_call.get("total_characters", 0), call_data.get("total_characters", 0))
                        mem_call["transcript"] = call_data.get("transcript", mem_call.get("transcript", []))
                    
                    char_cost = (mem_call["total_characters"] / 100) * self.COST_PER_100_CHARACTERS
                    minute_cost = (int(duration_seconds) / 60) * self.COST_PER_MINUTE
                    mem_call["estimated_cost"] = round(char_cost + minute_cost, 4)
                    
                    self._write_to_disk()
                elif call_data:
                    self._cache[call_sid] = call_data
                    self._write_to_disk()

    def update_recording(self, call_sid, recording_url):
        # 1. Update in Redis
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(f"alcon:call:{call_sid}")
                if data:
                    call_data = json.loads(data)
                    call_data["recording_url"] = recording_url
                    if call_data.get("status") == "completed":
                        redis_client.setex(f"alcon:call:{call_sid}", 3600, json.dumps(call_data))
                    else:
                        redis_client.set(f"alcon:call:{call_sid}", json.dumps(call_data))
            except Exception as e:
                print(f"[LOGGER] Redis error in update_recording: {e}")

        # 2. Update persistently on disk
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
                if call_sid in self._cache:
                    self._cache[call_sid]["recording_url"] = recording_url
                    self._write_to_disk()

    def get_history(self, limit=50):
        """Return all summarized call sessions sorted by start time."""
        # 1. Sync from disk first
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
                
        # 2. Build local snapshot and overlay active calls from Redis
        history_dict = dict(self._cache)
        if REDIS_AVAILABLE:
            try:
                active_sids = redis_client.smembers("alcon:active_calls")
                for sid in active_sids:
                    data = redis_client.get(f"alcon:call:{sid}")
                    if data:
                        history_dict[sid] = json.loads(data)
            except Exception as e:
                print(f"[LOGGER] Redis error in get_history: {e}")

        # 3. Sort by start_time descending
        sorted_history = sorted(
            history_dict.values(),
            key=lambda x: x.get("start_time", ""),
            reverse=True
        )
        return sorted_history[:limit]

    def get_call_log(self, call_sid):
        """Return detailed logs for a specific call."""
        # 1. Try Redis first for hot/active session
        if REDIS_AVAILABLE:
            try:
                data = redis_client.get(f"alcon:call:{call_sid}")
                if data:
                    return json.loads(data)
            except Exception as e:
                print(f"[LOGGER] Redis error in get_call_log: {e}")

        # 2. Fallback to Disk sync
        with self._lock:
            with FileLock(self.lock_file):
                self._load_and_merge()
            return self._cache.get(call_sid)
