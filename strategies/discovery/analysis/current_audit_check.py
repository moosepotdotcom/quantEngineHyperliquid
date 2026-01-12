from quant_engine import TradingEngine
import os

# Ensure models are available
if not os.path.exists('models'):
    print("❌ Models directory missing")
    exit(1)

engine = TradingEngine()

print("\n💎 Checking Current Confidence Levels...")
gem_signal, gem_conf = engine.check_gem_sniper()
wh_signal, wh_conf = engine.check_winner_hunter()
mtf_signal, mtf_conf = engine.check_mtf_scalper()

print(f"   Gem Sniper Confidence: {gem_conf:.2%}")
print(f"   Winner Hunter Confidence: {wh_conf:.2%}")
print(f"   MTF Scalper Confidence: {mtf_conf:.2%}")

if gem_conf >= 0.75 or wh_conf >= 0.47 or mtf_conf >= 0.90:
    print("\n🚨 ALERT: A signal is currently TRIGGERED!")
else:
    print("\n🟢 No signals triggered (Thresholds not met)")
