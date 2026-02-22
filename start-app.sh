#!/bin/bash

# startup.sh - One-click start for LLM WebApp

# Trap SIGINT (Ctrl+C) to kill all background processes
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

echo "🚀 Starting LLM WebApp..."

# 1. Start Backend
echo "🔹 Launching Backend (FastAPI)..."
cd backend
# Check for venv and activate if it exists
# Check for venv and activate if it exists
if [ -d ".venv" ]; then
    echo "   Running in virtual environment..."
    source .venv/bin/activate
fi
export PYTORCH_ALLOC_CONF=expandable_segments:True
export PYTORCH_ENABLE_MPS_FALLBACK=1
export HF_HOME=$(pwd)/models
python3 main.py &
BACKEND_PID=$!
cd ..

# 2. Start Frontend
echo "🔹 Launching Frontend (Next.js)..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ Systems are running!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   (Press Ctrl+C to stop)"

# Wait for both processes
wait
