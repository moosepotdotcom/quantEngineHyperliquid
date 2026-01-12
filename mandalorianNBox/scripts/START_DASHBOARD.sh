#!/bin/bash
# Start the Trading Bot Dashboard

cd "$(dirname "$0")/.."

echo "🚀 Starting Trading Bot Dashboard..."
echo ""

# Activate environment
source algotrader/bin/activate

# Check if dashboard dependencies are installed
echo "📦 Checking dashboard dependencies..."
python -c "import flask, flask_socketio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing dashboard dependencies..."
    pip install -q Flask flask-socketio python-socketio eventlet
fi

# Navigate to dashboard directory
cd dashboard

echo ""
echo "🌐 Starting dashboard server..."
echo "📊 Dashboard will be available at: http://127.0.0.1:5000"
echo ""
echo "💡 Press Ctrl+C to stop the dashboard"
echo ""

# Start the dashboard
python app.py

