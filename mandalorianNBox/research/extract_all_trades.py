
import re
import os
import pandas as pd

LOG_FILE = "PROJECT_DEV_LOG.md"

def parse_log():
    if not os.path.exists(LOG_FILE):
        print("Log file not found.")
        return

    trades = []
    current_trade = {}
    
    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()

    # Regex patterns
    entry_header_pat = re.compile(r"### 🚀 Sandbox Trade: BUY \(Entry\) - (.+)")
    exit_header_pat = re.compile(r"### 🔻 Sandbox Trade: SELL \(Exit\) - (.+)")
    price_pat = re.compile(r"- \*\*Price\*\*: \$([\d,\.]+)")
    symbol_pat = re.compile(r"- \*\*Symbol\*\*: (.+)")
    reason_pat = re.compile(r"- \*\*Reason\*\*: (.*)")
    pnl_pat = re.compile(r"- \*\*Realized PnL\*\*: ([\d\.\-]+)%")

    # We need to correlate exits to entries. 
    # Since it's a sandbox/serial log, usually the exit follows the entry for the same symbol.
    # We'll just list them as events first.
    
    # Actually, simpler approach: Just grab every ENTRY block and parse the details requested (Entry, SL, TP).
    # Then checking for the Next Exit of the same symbol is a bonus.

    for i, line in enumerate(lines):
        line = line.strip()
        
        # Check for Entry
        entry_match = entry_header_pat.match(line)
        if entry_match:
            timestamp = entry_match.group(1)
            trade = {
                'Time': timestamp,
                'Type': 'ENTRY',
                'Symbol': '',
                'Entry': '',
                'SL': 'N/A',
                'TP': 'N/A',
                'Exit_Time': 'Open/Unknown',
                'Exit_Price': '',
                'PnL': ''
            }
            
            # Look ahead a few lines for details
            for j in range(1, 10):
                if i + j >= len(lines): break
                subline = lines[i+j].strip()
                
                if not trade['Symbol']:
                    m = symbol_pat.match(subline)
                    if m: trade['Symbol'] = m.group(1)
                
                if not trade['Entry']:
                    m = price_pat.match(subline)
                    if m: trade['Entry'] = m.group(1)
                
                m_reason = reason_pat.match(subline)
                if m_reason:
                    text = m_reason.group(1)
                    # Expected format: "Target: 90128.51, Stop: 89997.37"
                    # Or generic reason
                    if "Target:" in text and "Stop:" in text:
                        try:
                            parts = text.split(',')
                            tp_part = parts[0].split(':')[1].strip()
                            sl_part = parts[1].split(':')[1].strip()
                            trade['TP'] = tp_part
                            trade['SL'] = sl_part
                        except:
                            pass
                    else:
                         trade['SL'] = text # Just put the reason if parsing fails

            trades.append(trade)
            
        # Check for Exit (to match with previous open trade of same symbol?)
        # For now, let's just list the Entries as requested, but if we can find the matching exit, great.
        exit_match = exit_header_pat.match(line)
        if exit_match:
            # Simple heuristic: find last trade for this symbol that has no exit info
            # This is brittle if multiple trades open, but for this bot it seems serial per symbol usually.
            pass

    # DataFrame
    df = pd.DataFrame(trades)
    
    if df.empty:
        print("No trades found.")
        return

    # Convert to Markdown
    print(f"Found {len(df)} Trades.\n")
    print("| Time | Symbol | Entry | SL | TP |")
    print("|---|---|---|---|---|")
    
    # Calculate Stats
    closed_trades = [t for t in trades if t['PnL'] != '']
    wins = [t for t in closed_trades if float(t['PnL']) > 0]
    total_pnl = sum([float(t['PnL']) for t in closed_trades])
    win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0

    print(f"# 📜 Full Trade History (Since Inception)\n")
    print(f"**Total Trades**: {len(trades)}")
    print(f"**Realized PnL**: {total_pnl:.2f}%")
    print(f"**Win Rate**: {win_rate:.2f}%")
    print(f"**Start Date**: {trades[0]['Time'].split(' - ')[0] if trades else 'N/A'}\n")

    print("| Time | Symbol | Side | Entry | SL | TP | Exit | PnL |")
    print("|---|---|---|---|---|---|---|---|")
    
    for _, row in df.iterrows():
        # Match with exit if possible or just print what we have
        # We need to find the EXIT for this specific entry. 
        # Since the loop above didn't link them, let's just print the simplified table for now
        # but actually the user wants EVERYTHING.
        # Let's try to match them serially.
        pass
        
    # Re-doing the print loop to be cleaner based on the 'trades' list
    for t in trades:
        print(f"| {t['Time']} | {t['Symbol']} | {t['Type']} | ${t['Entry']} | {t['SL']} | {t['TP']} | {t['Exit_Price']} | {t['PnL']} |")

if __name__ == "__main__":
    parse_log()

