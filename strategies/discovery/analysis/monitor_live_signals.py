#!/usr/bin/env python3
"""
Live Signal Monitor: Observes the Trio Ensemble using Hyperliquid Live Feed
"""
import time
from datetime import datetime
from quant_engine import TradingEngine

def main():
    print("\n" + "🛰️"*35)
    print("TRIO ENSEMBLE - LIVE SIGNAL MONITOR")
    print("🛰️"*35 + "\n")
    
    # Initialize Engine
    engine = TradingEngine()
    
    print("\n" + "="*70)
    print("📊 MONITORING STARTING...")
    print(f"   Targets WH/MTF: 1.5% TP / 0.8% SL")
    print(f"   💎 GEM TARGETS: 0.3% TP / 0.5% SL")
    print(f"   Model: Trio Ensemble (XGB + LGB + CAT)")
    print("="*70)

    iteration = 0
    try:
        while True:
            iteration += 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[{now}] Check #{iteration}")
            
            # Check models
            print("   🔍 Checking Winner Hunter (1H)...")
            wh_signal, wh_conf = engine.check_winner_hunter()
            
            print("   🔍 Checking MTF Scalper (5M)...")
            mtf_signal, mtf_conf = engine.check_mtf_scalper()
            
            print("   🔍 Checking Gem Sniper (5M)...")
            gem_signal, gem_conf = engine.check_gem_sniper()
            
            # Display Summary
            print(f"\n   📈 LIVE CONFIDENCE:")
            
            # WH Status
            wh_l = engine.wh_elastic.active_threshold_long
            wh_s = engine.wh_elastic.active_threshold_short
            wh_mode = engine.wh_elastic.mode
            wh_status = f"🚨 SIGNAL [{wh_mode}]" if wh_signal else f"🟠 {wh_mode}"
            print(f"      Winner Hunter (1H): L:{wh_l:.1%}, S:{wh_s:.1%} | Conf: {wh_conf:.2%} -> {wh_status}")
            
            # MTF Status
            mtf_l = engine.mtf_elastic.active_threshold_long
            mtf_s = engine.mtf_elastic.active_threshold_short
            mtf_mode = engine.mtf_elastic.mode
            mtf_status = f"🚨 SIGNAL [{mtf_mode}]" if mtf_signal else f"🟠 {mtf_mode}"
            print(f"      MTF Scalper (5M):   L:{mtf_l:.1%}, S:{mtf_s:.1%} | Conf: {mtf_conf:.2%} -> {mtf_status}")
            
            # Gem status
            gem_target = 0.75
            gem_status = "💎 ACTIVE" if gem_signal else "⚪ Waiting"
            print(f"      GEM SNIPER (5M):    Target: {gem_target:.1%} | Conf: {gem_conf:.2%} -> {gem_status}")
            
            if wh_signal:
                print(f"\n🚨 [SIGNAL] WINNER HUNTER 1H {wh_signal['direction']} fired at ${wh_signal['price']:,.2f}!")
            if mtf_signal:
                print(f"\n🚨 [SIGNAL] MTF SCALPER 5M {mtf_signal['direction']} fired at ${mtf_signal['price']:,.2f}!")
            if gem_signal:
                print(f"\n💎 [SIGNAL] GEM SNIPER 5M {gem_signal['direction']} fired at ${gem_signal['price']:,.2f}!")
                print(f"   ✅ Gem Target: ${gem_signal['tp']:,.2f}")
                
            print(f"\n   ⏳ Waiting 60s for next bar update...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitor stopped by user.")

if __name__ == "__main__":
    main()
