
def calculate_growth():
    start_balance = 52.0
    target_daily_pnl = 20.0
    
    # Scenarios based on Backtests
    scenarios = [
        {"name": "Bear/Chop (Jan)", "daily_roi": 0.013}, # 1.3% daily
        {"name": "Volatile (Dec)", "daily_roi": 0.040},  # 4.0% daily
        {"name": "Bull Run (Nov)", "daily_roi": 0.140}   # 14.0% daily !!
    ]

    print("="*60)
    print("💰 ROAD TO $20/DAY (Starting: $52)")
    print("="*60)

    for s in scenarios:
        balance = start_balance
        days = 0
        roi = s['daily_roi']
        
        while True:
            daily_profit = balance * roi
            if daily_profit >= target_daily_pnl:
                break
            
            balance += daily_profit
            days += 1
            
            if days > 365: break # Cap at 1 year
            
        print(f"\nScenario: {s['name']} ({roi*100:.1f}% Daily ROI)")
        print(f" -> Days to reach goal: {days} Days")
        print(f" -> Balance needed: ${balance:.2f}")

if __name__ == "__main__":
    calculate_growth()
