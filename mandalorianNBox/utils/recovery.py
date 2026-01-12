import os
import re
from datetime import datetime

LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'PROJECT_DEV_LOG.md'))

class LogRecoverer:
    """
    Parses PROJECT_DEV_LOG.md to recover the last known state of the agent.
    """
    def __init__(self, log_file=LOG_FILE):
        self.log_file = log_file

    def get_latest_state(self):
        if not os.path.exists(self.log_file):
            return None

        with open(self.log_file, 'r') as f:
            lines = f.readlines()

        state = {
            'last_trade': None,
            'last_position': None,
            'last_best_strategy': None,
            'last_action': None
        }

        # Iterate backwards to find latest entries
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i]
            
            # Check for best strategy
            if "New Best Strategy Found!" in line:
                if not state['last_best_strategy']:
                    # Extract strategy details from next few lines
                    try:
                        profit = re.search(r"Profit\*\*: ([\d.-]+)%", lines[i+1]).group(1)
                        sharpe = re.search(r"Sharpe\*\*: ([\d.-]+)", lines[i+2]).group(1)
                        params = re.search(r"Params\*\*: (.*)", lines[i+3]).group(1)
                        state['last_best_strategy'] = {
                            'profit': float(profit),
                            'sharpe': float(sharpe),
                            'params': params
                        }
                    except:
                        pass

            # Check for trade status
            if "### 💓 Sandbox Trade: STATUS CHECK" in line:
                if not state['last_trade']:
                    try:
                        timestamp = re.search(r"- (.*)", line).group(1)
                        price = re.search(r"\*\*Price\*\*: \$([\d.,-]+)", lines[i+3]).group(1)
                        status = re.search(r"\*\*Status\*\*: (.*)", lines[i+5]).group(1)
                        state['last_trade'] = {
                            'timestamp': timestamp,
                            'price': price,
                            'status': status
                        }
                    except:
                        pass

            # Check for last agent action
            if "### 👨‍💻 Agent Action:" in line:
                if not state['last_action']:
                    try:
                        action = re.search(r"Agent Action: (.*) -", line).group(1)
                        state['last_action'] = action
                    except:
                        pass

        return state

if __name__ == "__main__":
    recoverer = LogRecoverer()
    state = recoverer.get_latest_state()
    print("--- RECOVERED STATE ---")
    import json
    print(json.dumps(state, indent=4))
