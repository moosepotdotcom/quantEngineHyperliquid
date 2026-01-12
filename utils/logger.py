
import datetime
import os

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'PROJECT_DEV_LOG.md'))

def log_to_journal(title, details, emoji="📝"):
    """
    Appends a formatted entry to PROJECT_DEV_LOG.md.
    Format:
    ### {emoji} {title} - {Day, Date Time}
    {details}
    """
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%a %b %d, %Y - %I:%M:%S %p")
    
    entry = f"\n### {emoji} {title} - {timestamp_str}\n"
    entry += f"{details}\n"
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(entry)
        print(f"✅ Logged to Journal: {title}")
    except Exception as e:
        print(f"⚠️ Failed to log to journal: {e}")

TRADES_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'trades.json'))

def log_to_json(trade_data):
    """
    Appends a trade record to data/trades.json
    """
    import json
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)
    
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r') as f:
                trades = json.load(f)
        except:
            trades = []
    
    # Add new trade (keep last 100)
    trades.append(trade_data)
    if len(trades) > 100:
        trades = trades[-100:]
        
    try:
        with open(TRADES_FILE, 'w') as f:
            json.dump(trades, f, indent=2)
    except Exception as e:
        print(f"⚠️ Failed to log trade to JSON: {e}")

def log_trade(symbol, action, price, size=0.0, reason="", pnl=None, status="", sl=None, tp=None, engine=None):
    # 1. Log to Markdown Journal (Human Readable)
    details = f"- **Action**: {action}\n- **Symbol**: {symbol}\n- **Price**: ${price:.2f}\n- **SIZE**: **{size} units**"
    if reason:
        details += f"\n- **Reason**: {reason}"
    if sl:
        details += f"\n- **SL**: ${sl:.2f}"
    if tp:
        details += f"\n- **TP**: ${tp:.2f}"
    if pnl is not None:
        details += f"\n- **Realized PnL**: {pnl:.2f}%"
    if status:
        details += f"\n- **Status**: {status}"
    
    emoji = "🚀" if "BUY" in action else "🔻" if "SELL" in action else "💓"
    log_to_journal(f"Sandbox Trade: {action}", details, emoji)
    
    # 2. Log to JSON (Dashboard Readable)
    trade_record = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'symbol': symbol,
        'action': action,
        'price': price,
        'size': size,
        'sl': sl,
        'tp': tp,
        'pnl': pnl,
        'reason': reason,
        'engine': engine or "Unknown"
    }
    log_to_json(trade_record)

def log_agent_action(action, description):
    """
    Logs an action performed by the Agent (AI Developer).
    """
    emoji = "👨‍💻"
    log_to_journal(f"Agent Action: {action}", description, emoji)

def log_instruction(instruction):
    """
    Logs a User Instruction.
    """
    emoji = "🗣️"
    log_to_journal(f"User Instruction", instruction, emoji)

def log_agent_response(response):
    """
    Logs the Agent's conversational response/report.
    """
    emoji = "🤖"
    log_to_journal(f"Agent Response", response, emoji)

def log_optimization(best_result):
    details = f"**New Best Strategy Found!**\n"
    details += f"- **Profit**: {best_result['profit']:.2f}%\n"
    details += f"- **Sharpe**: {best_result['sharpe']:.2f}\n"
    details += f"- **Params**: {best_result['params']}"
    
    log_to_journal("Optimization Result", details, "🤖")

def log_artifact_snapshot(artifact_name, content):
    """
    Logs a snapshot of an artifact (like task.md or walkthrough.md) to the journal.
    """
    emoji = "📚"
    title = f"Artifact Snapshot: {artifact_name}"
    
    formatted_content = f"```markdown\n{content}\n```"
    log_to_journal(title, formatted_content, emoji)

def log_liquidation(symbol, side, usd_size, price):
    """
    Log a major liquidation event.
    """
    emoji = "🌊"
    title = "LIQUIDATION ALERT"
    
    if usd_size > 500000:
        emoji = "🐋"
        title = "WHALE LIQUIDATION ALERT"
    elif usd_size > 100000:
        emoji = "🚨"
        title = "HIGH PRIORITY REKT"
        
    formatted_size = f"${usd_size:,.0f}"
    details = f"- **Symbol**: {symbol}\n- **Side**: {side} REKT\n- **Amount**: {formatted_size}\n- **Price**: ${price:.2f}"
    
    log_to_journal(title, details, emoji)
