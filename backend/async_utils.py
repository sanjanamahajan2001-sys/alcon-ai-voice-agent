import json
import redis
import os

# Connect to Redis for Task Queue
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

TASK_QUEUE_KEY = "alcon_task_queue"

def run_tracked_task(func_name, *args, skip_queue_count=False, **kwargs):
    """
    Production-Grade Task Producer:
    Pushes task metadata to Redis to be processed by a dedicated worker.
    """
    from metrics_collector import metrics
    if not skip_queue_count:
        metrics.record_task_queued()
    
    task_data = {
        "func": func_name,
        "args": args,
        "kwargs": kwargs,
        "timestamp": os.getpid() # For tracking
    }
    
    try:
        redis_client.rpush(TASK_QUEUE_KEY, json.dumps(task_data))
    except Exception as e:
        print(f"⚠️ TASK QUEUE ERROR: {str(e)}")
