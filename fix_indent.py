
path = '/Users/alifiyaa/Downloads/quantEngineHyperliquid/quant_engine.py'
with open(path, 'r') as f:
    text = f.read()

# The specific messy block I saw in view_file
old_block = """            signal_str = self.v2_scalper.check_signal(df_5m, df_15m, df_30m)
            if signal_str and signal_str != 'NEUTRAL':
                    # Convert to standard signal dict
                    price = float(df_5m['close'].iloc[-1])
                    return {
                        'model': 'MLScalper V2 (Enhanced)',
                        'timestamp': datetime.now(),
                        'price': price,
                        'direction': signal_str,
                        'confidence': self.v2_scalper.last_probs[0] if signal_str == 'LONG' else self.v2_scalper.last_probs[1],
                        'rsi': 50, # Placeholder or actual if available
                        'macd': 0,
                        'atr_pct': 0
                    }, self.v2_scalper.last_probs[0] if signal_str == 'LONG' else self.v2_scalper.last_probs[1]
            return None, 0.0"""

new_block = """            signal_str = self.v2_scalper.check_signal(df_5m, df_15m, df_30m)
            if signal_str and signal_str != 'NEUTRAL':
                # Convert to standard signal dict
                price = float(df_5m['close'].iloc[-1])
                return {
                    'model': 'MLScalper V2 (Enhanced)',
                    'timestamp': datetime.now(),
                    'price': price,
                    'direction': signal_str,
                    'confidence': self.v2_scalper.last_probs[0] if signal_str == 'LONG' else self.v2_scalper.last_probs[1],
                    'rsi': 50, # Placeholder or actual if available
                    'macd': 0,
                    'atr_pct': 0
                }, self.v2_scalper.last_probs[0] if signal_str == 'LONG' else self.v2_scalper.last_probs[1]
            return None, 0.0"""

if old_block in text:
    fixed_text = text.replace(old_block, new_block)
    with open(path, 'w') as f:
        f.write(fixed_text)
    print("✅ Fixed indentation successfully")
else:
    # Try a slightly different variation if spaces were slightly off
    print("❌ Could not find exact old_block. Trying line-by-line fallback.")
    lines = text.splitlines()
    with open(path, 'w') as f:
        for i, line in enumerate(lines):
            # Line 660-672 (0-indexed 659-671)
            if 660 <= (i + 1) <= 672:
                 stripped = line.strip()
                 if stripped.startswith('if signal_str'):
                     f.write('            ' + stripped + '\n')
                 elif stripped.startswith('return None') or stripped.startswith('return None'):
                     f.write('            ' + stripped + '\n')
                 elif stripped.startswith('}, self.v2_scalper'):
                     f.write('                ' + stripped + '\n')
                 elif stripped.startswith('},'):
                      f.write('                ' + stripped + '\n')
                 elif stripped == '{':
                      f.write('                {\n')
                 elif i+1 == 668: # confidence line
                      f.write('                    ' + stripped + '\n')
                 else:
                     f.write('                ' + stripped + '\n')
            else:
                f.write(line + '\n')
    print("✅ Fixed indentation via fallback")
