#!/bin/bash

# WILLIAMS STRATEGY BUNDLE LAUNCHER
# Starts Backend (API+Bot) and Frontend (Dashboard)

echo "🚀 Initializing Williams %R Strategy Bundle..."

# 1. Start Backend
echo "🔌 Starting API Server & Trading Bot..."
# Kill any existing instance on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null

python3 -u api.py > api.log 2>&1 &
API_PID=$!
echo "   ✅ API Started (PID: $API_PID) - Logging to api.log"

# 2. Setup Frontend
echo "💻 Setting up Dashboard..."
cd quant-dashboard

if [ ! -d "node_modules" ]; then
    echo "   📦 Installing dependencies (First run only)..."
    npm install > /dev/null 2>&1
    echo "   ✅ Dependencies installed"
fi

# 3. Start Frontend
echo "   🌐 Starting Vite Server..."
npm run dev > ../dashboard.log 2>&1 &
FRONTEND_PID=$!
echo "   ✅ Dashboard Started (PID: $FRONTEND_PID)"

echo "---------------------------------------------------"
echo "🎉 SYSTEM ONLINE"
echo "👉 Dashboard: http://localhost:5173"
echo "👉 API:       http://localhost:8000"
echo "---------------------------------------------------"
echo "Press [CTRL+C] to stop all services."

# Trap cleanup
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $API_PID
    kill $FRONTEND_PID
    exit
}

trap cleanup SIGINT

# Keep script running
wait
