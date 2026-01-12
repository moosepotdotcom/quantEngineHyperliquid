
import sys
import subprocess

def install_package(package):
    print(f"📦 Installing {package} into {sys.executable}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully!")
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}. Please try 'pip install {package}' manually.")

if __name__ == "__main__":
    print(f"🔧 Fixing Environment: {sys.prefix}")
    
    requirements = [
        "scikit-learn",
        "pandas",
        "yfinance",
        "ta",
        "ccxt",
        "numpy",
        "websockets",
        "termcolor",
        "feedparser"
    ]
    
    for req in requirements:
        install_package(req)
        
    print("\n🎉 All dependencies installed! You can now run:")
    print("python3 run_paper_trading.py")
