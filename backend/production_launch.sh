#!/bin/bash

# ALCON PRODUCTION LAUNCH SCRIPT
# Target: 1,500 Parallel Sessions on AWS 2vCPU / 2GB RAM

echo "🚀 HARDENING BACKEND FOR PRODUCTION..."

# 1. Activate Virtual Environment if it exists
if [ -d "venv" ]; then
    echo "🐍 ACTIVATING VIRTUAL ENVIRONMENT..."
    source venv/bin/activate
fi

# 2. Set Production Environment Variables
export ENV=production
export LOG_LEVEL=info

# 3. Calculate worker count (Optimal for 2vCPU / 2GB RAM)
WORKER_COUNT=3

echo "📦 SPAWNING $WORKER_COUNT WORKER PROCESSES..."

# 4. Launch using Gunicorn with Uvicorn workers
# --backlog 2048: Crucial for handling massive burst connection queues
# --keep-alive 1: Reducing keep-alive prevents worker 'hogging' (Connection Affinity)
# --access-logfile /dev/null: Disable access logging during stress tests for max performance
gunicorn main:app \
    --workers $WORKER_COUNT \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --backlog 2048 \
    --timeout 120 \
    --keep-alive 1 \
    --access-logfile /dev/null \
    --error-logfile data/error.log &

# 5. Launch Background Workers (Role-Based Scaling)
echo "🧠 STARTING 1 CRON WORKER..."
python worker.py --mode cron &

echo "💪 STARTING 3 PERSISTENCE WORKERS..."
for i in {1..3}
do
   python worker.py --mode tasks &
done

echo "✅ SERVER IS LIVE ON PORT 8000"
