#!/bin/bash

# ATC Bootcamp Trading Bots - Quick Setup Script
# This script helps you set up the environment and install dependencies

echo "🚀 ATC Bootcamp Trading Bots - Setup Script"
echo "=============================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Ask user which setup method they prefer
echo "Choose your setup method:"
echo "1) Anaconda/Conda (Recommended)"
echo "2) Regular Python venv"
read -p "Enter choice (1 or 2): " choice

if [ "$choice" == "1" ]; then
    # Conda setup
    if ! command -v conda &> /dev/null; then
        echo "❌ Conda is not installed. Please install Anaconda first."
        exit 1
    fi
    
    echo ""
    echo "📦 Creating conda environment 'algotrader'..."
    conda create --name algotrader python=3.8.5 -y
    
    echo ""
    echo "✅ Environment created! Activate it with:"
    echo "   conda activate algotrader"
    echo ""
    echo "Then run: pip install -r requirements.txt"
    
elif [ "$choice" == "2" ]; then
    # Venv setup
    echo ""
    echo "📦 Creating virtual environment..."
    python3 -m venv algotrader
    
    echo ""
    echo "✅ Virtual environment created! Activate it with:"
    echo "   source algotrader/bin/activate"
    echo ""
    echo "Then run: pip install -r requirements.txt"
else
    echo "❌ Invalid choice"
    exit 1
fi

echo ""
echo "📝 Next steps:"
echo "1. Activate your environment (see above)"
echo "2. Run: pip install -r requirements.txt"
echo "3. Configure your API keys in dontshare.py and/or key_file.py"
echo "4. Read SETUP_GUIDE.md for detailed instructions"
echo ""
echo "⚠️  Remember to configure your API keys before running bots!"
echo ""



