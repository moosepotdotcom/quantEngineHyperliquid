
import time
from datetime import datetime
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from rich.text import Text
from rich import box

# Import Strategy
from live_trader import WilliamsStrategy, LEVERAGE, MAX_POSITION_SIZE_USD

# Initialize Consistency
console = Console()

def make_header():
    grid = Table.grid(expand=True)
    grid.add_column(justify="left", ratio=1)
    grid.add_column(justify="center", ratio=1)
    grid.add_column(justify="right", ratio=1)
    
    title = Text(" Williams %R + ML Strategy V1 ", style="bold white on blue")
    grid.add_row(
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        title,
        "SANITY ONE | $53 Seed Plan"
    )
    return Panel(grid, style="white on black")

def make_account_info(positions):
    table = Table(box=box.SIMPLE_HEAD)
    table.add_column("Account Metric", style="cyan")
    table.add_column("Value", style="green")
    
    # Placeholder for real account balance fetching if we expanded execution.py
    # For now, we assume fixed.
    table.add_row("Balance (Est)", "$53.00")
    table.add_row("Leverage", f"{LEVERAGE}x")
    table.add_row("Target Size", f"${MAX_POSITION_SIZE_USD}")
    table.add_row("Active Trades", str(len(positions)))
    
    return Panel(table, title="Account Status", border_style="green")

def make_market_table(status_list):
    table = Table(expand=True, box=box.ROUNDED)
    table.add_column("Coin", style="bold yellow")
    table.add_column("Price", justify="right")
    table.add_column("Williams %R", justify="right")
    table.add_column("ML Conf", justify="right")
    table.add_column("Status", justify="center")
    
    for s in status_list:
        # Williams Color
        wr_val = s['wr']
        if wr_val > -20: wr_style = "bold green" # Overbought/Breakout
        elif wr_val < -80: wr_style = "bold red" # Oversold/Breakdown
        else: wr_style = "white"
        
        # Conf Color
        conf_val = s['conf']
        if conf_val > 0.65: conf_style = "bold green"
        elif conf_val > 0.5: conf_style = "yellow"
        else: conf_style = "dim white"
        
        # Status Icon
        icon = "WAIT"
        style = "dim"
        if s['price'] == 0:
            icon = "DATA ERR"
            style = "red"
        elif s['signal'] == 'LONG':
            icon = "🚀 LONG"
            style = "bold white on green blink"
        elif s['signal'] == 'SHORT':
            icon = "🔻 SHORT"
            style = "bold white on red blink"
        elif conf_val > 0.65:
            icon = "👀 WATCH"
            style = "yellow"
            
        table.add_row(
            s['coin'],
            f"${s['price']:,.2f}",
            Text(f"{wr_val:.1f}", style=wr_style),
            Text(f"{conf_val:.2%}", style=conf_style),
            Text(icon, style=style)
        )
        
    return Panel(table, title="Live Market Scanner (5m)", border_style="blue")

def make_log_panel(logs):
    # Determine the height of the panel based on available space or fixed limit
    # For simplicity, we just join the last N logs.
    log_text = "\n".join(logs[-10:])
    return Panel(log_text, title="Strategy Logs", border_style="white", title_align="left")

def run_dashboard():
    strategy = WilliamsStrategy()
    logs = ["System Initialized."]
    
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="main", ratio=1),
        Layout(name="footer", size=10)
    )
    
    layout["main"].split_row(
        Layout(name="market", ratio=2),
        Layout(name="account", ratio=1)
    )
    
    with Live(layout, refresh_per_second=1, screen=True) as live:
        while True:
            # 1. Update Header
            layout["header"].update(make_header())
            
            # 2. Get Data
            try:
                status = strategy.get_market_status()
                # 3. Update Market Table
                layout["market"].update(make_market_table(status))
                
                # 4. Update Account
                # Need to expose active positions from strategy
                layout["account"].update(make_account_info(strategy.active_positions))
                
                # 5. Logs (Simulated for this refresh)
                # In real app, we'd hook into strategy logs.
                # Here we just log signals if found
                for s in status:
                    if s['signal']:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        msg = f"[{timestamp}] SIGNAL: {s['coin']} {s['signal']} (Conf {s['conf']:.2f})"
                        if msg not in logs:
                            logs.append(msg)
                            
                layout["footer"].update(make_log_panel(logs))
                
            except Exception as e:
                logs.append(f"Error: {e}")
                
            time.sleep(60) # Scan every minute

if __name__ == "__main__":
    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("Dashboard Exited.")
