
import os
import time
from utils.logger import log_to_journal

class RiskManager:
    def __init__(self, max_daily_loss_pct=5.0, use_ai_override=False):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.use_ai_override = use_ai_override
        self.start_balance = 0
        self.current_balance = 0
        self.daily_high = 0
        self.triggered = False
        
    def update_pnl(self, current_balance):
        """Called every loop to update checks"""
        if self.start_balance == 0:
            self.start_balance = current_balance
            self.daily_high = current_balance
            return False

        self.current_balance = current_balance
        self.daily_high = max(self.daily_high, current_balance)
        
        # Calculate Drawdown from Start
        total_pnl_pct = ((current_balance - self.start_balance) / self.start_balance) * 100
        
        # Check Hard Limit
        if total_pnl_pct <= -self.max_daily_loss_pct:
            if not self.triggered:
                return self._trigger_risk_event(total_pnl_pct)
        
        return False

    def _trigger_risk_event(self, pnl_pct):
        """Handle the breach"""
        print(f"\n🛑 RISK EVENT: Daily Loss Limit Hit ({pnl_pct:.2f}%)")
        
        decision = "CLOSE_ALL"
        reason = "Hard Limit Breached"
        
        if self.use_ai_override:
            # Placeholder for the AI Call from MoonDev repo
            # In a real scenario, this would call OpenAI/Anthropic
            print("🤖 AI Risk Judge: Analyzing market structure for Override...")
            # For Sandbox, we simulate a "Strict" AI that rarely overrides
            # To enable real AI, we would need the API Keys from the user
            decision = "CLOSE_ALL" 
            reason = "AI Judge confirms: Downward Momentum is Strong. No Override."
            
        self.triggered = True
        
        log_to_journal(
            "RISK MANAGER ALERT", 
            f"- **Event**: Max Loss Hit ({pnl_pct:.2f}%)\n- **Action**: {decision}\n- **Reason**: {reason}",
            "👮‍♂️"
        )
        
        return decision == "CLOSE_ALL"
