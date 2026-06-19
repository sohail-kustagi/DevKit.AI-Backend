#!/bin/bash

echo "🚀 Booting up DevKit.AI Stack..."

# Trap Ctrl+C (SIGINT) to elegantly kill all background processes
trap 'echo -e "\n🛑 Stopping all services..."; kill $LLM_PID $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' SIGINT

# Get the directory where this script is located
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Helper function to find the correct folder name
find_dir() {
  for name in "$1" "DevKit.AI-$1" "DevKit.AI-$1-main" "$1-main"; do
    if [ -d "$BASE_DIR/$name" ]; then
      echo "$BASE_DIR/$name"
      return 0
    fi
  done
  echo ""
}

LLM_DIR=$(find_dir "LLM")
BACKEND_DIR=$(find_dir "Backend")
FRONTEND_DIR=$(find_dir "Frontend")

if [ -z "$LLM_DIR" ] || [ -z "$BACKEND_DIR" ] || [ -z "$FRONTEND_DIR" ]; then
  echo "❌ Error: Could not find all 3 folders (LLM, Backend, Frontend)."
  echo "Please place this script in the same folder as the downloaded repositories."
  exit 1
fi

# 1. Start LLM Engine
echo "➡️  Starting LLM Engine (gRPC Port 50051)..."
cd "$LLM_DIR"
source .venv/bin/activate 2>/dev/null || echo "⚠️ Warning: No .venv found in LLM"
python -m agents.grpc_server &
LLM_PID=$!

# 2. Start Backend Gateway
echo "➡️  Starting FastAPI Backend (REST/WS Port 8000)..."
cd "$BACKEND_DIR"
source .venv/bin/activate 2>/dev/null || echo "⚠️ Warning: No .venv found in Backend"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 3. Start Frontend UI
echo "➡️  Starting Frontend React UI (Port 5173)..."
cd "$FRONTEND_DIR"
npm run dev -- --port 5173 &
FRONTEND_PID=$!

echo "======================================================="
echo "✅ Stack is fully online!"
echo "   🌍 UI Dashboard:    http://localhost:5173"
echo "   🔌 API Gateway:     http://localhost:8000"
echo "   🤖 LLM Engine:      localhost:50051"
echo "======================================================="
echo "Press Ctrl+C to gracefully stop all services."

# Wait indefinitely until script is interrupted
wait