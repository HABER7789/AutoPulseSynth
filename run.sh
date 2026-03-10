#!/usr/bin/env bash
set -e

echo "╔══════════════════════════════════════════════╗"
echo "║        AutoPulseSynth — Local Launcher       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# 1. Python backend setup
if [ ! -d ".venv" ]; then
  echo "→ Creating Python virtual environment..."
  python3 -m venv .venv
fi

echo "→ Installing Python dependencies..."
.venv/bin/pip install -q -r requirements-api.txt

# 2. Frontend setup
if [ ! -d "frontend/node_modules" ]; then
  echo "→ Installing frontend dependencies..."
  (cd frontend && npm install --silent)
fi

# 3. Launch both servers
echo ""
echo "→ Starting backend on http://localhost:8000"
echo "→ Starting frontend on http://localhost:3000"
echo ""

.venv/bin/uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

# Open browser after a short delay
sleep 3
if command -v open &> /dev/null; then
  open http://localhost:3000
elif command -v xdg-open &> /dev/null; then
  xdg-open http://localhost:3000
fi

echo ""
echo "AutoPulseSynth is running. Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
