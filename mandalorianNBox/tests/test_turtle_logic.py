
import unittest
import pandas as pd
import numpy as np
import sys
import os

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_agent import SandboxMLBot

class TestTurtleLogic(unittest.TestCase):
    def setUp(self):
        self.bot = SandboxMLBot()
        self.bot.quantity = 0.1
        
        # Create dummy dataframe with 150 bars (enough for 98 lookback)
        dates = pd.date_range(start='2024-01-01', periods=150, freq='H')
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': 100,
            'high': 100,
            'low': 90,
            'close': 95,
            'volume': 1000
        })
        self.df.set_index('timestamp', inplace=True)
        
    def test_no_breakout(self):
        # Highs are all 100
        # Current price 99 -> No Breakout
        current_price = 99
        latest_atr = 1.0
        timestamp = "12:00:00"
        
        result = self.bot.check_turtle_optimized(self.df, current_price, latest_atr, timestamp)
        self.assertFalse(result)
        self.assertIsNone(self.bot.position)

    def test_breakout(self):
        # Highs are all 100
        # Current price 101 -> Breakout
        current_price = 101.0
        latest_atr = 2.0
        timestamp = "12:00:00"
        
        # Mocking values in DF to ensure calculation works
        # Ensure 'high' column logic relies on previous 98 bars
        # All previous highs are 100.
        
        result = self.bot.check_turtle_optimized(self.df, current_price, latest_atr, timestamp)
        self.assertTrue(result)
        self.assertEqual(self.bot.position, 'LONG')
        
        # Check TP/SL calculations
        # entry = 101
        # atr_mult = 3.7065, atr = 2.0 (fallback) -> deviation = 7.413
        # SL = 101 - 7.413 = 93.587
        # TP_pct = 0.8997% -> 101 * 1.008997 = 101.9087
        
        # TR is 10.0 (100-90) for all bars. ATR(30) of 10.0 is 10.0.
        # calculated_atr = 10.0
        # SL = 101 - (10.0 * 3.7065) = 101 - 37.065 = 63.935
        expected_sl = 101 - (10.0 * 3.7065)
        expected_tp = 101 * (1 + 0.8997 / 100)
        
        self.assertAlmostEqual(self.bot.sl_price, expected_sl, places=4)
        self.assertAlmostEqual(self.bot.tp_price, expected_tp, places=4)

if __name__ == '__main__':
    unittest.main()
