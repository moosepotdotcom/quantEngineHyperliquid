#!/bin/bash
# Plug & Play Dashboard Starter

cd "$(dirname "$0")/.."

echo "🎛️  Starting Trading Bot Dashboard..."
echo ""

# Activate environment
source algotrader/bin/activate

# Check if dashboard dependencies are installed
echo "📦 Checking dependencies..."
python -c "import flask, flask_socketio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Installing dashboard dependencies..."
    pip install Flask flask-socketio python-socketio eventlet
    echo "✅ Dependencies installed!"
fi

echo ""
echo "🚀 Starting dashboard server..."
echo "📊 Dashboard URL: http://127.0.0.1:5000"
echo ""
echo "💡 Open the URL above in your browser"
echo "🛑 Press Ctrl+C to stop"
echo ""
echo "=" * 60
echo ""

# Start dashboard
cd dashboard
python app.py

