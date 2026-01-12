# 💸 Transfer Funds to Test Wallet

## 🎯 Goal
Transfer $10-20 from your funded wallet to the test wallet for running the live trade flow test.

## 📋 Wallets

**From (Funded Wallet):**
- Has $52.87 USDC
- You're viewing this in the Hyperliquid UI

**To (Test Wallet):**
- Address: `0xb01713a6fcdc9419f37db065f0274ea172e4689e`
- Currently has $0.00
- Has private key for testing

## 🔄 Transfer Methods

### Option 1: Using Hyperliquid UI (Easiest)

1. **Go to Hyperliquid Portfolio**
   - Visit: https://app.hyperliquid.xyz/portfolio
   - Make sure you're logged in with your funded wallet

2. **Click "Send" or "Withdraw"**
   - Look for the "Send" button in the top right
   - Or go to the Balances tab and click "Send" next to USDC

3. **Enter Transfer Details**
   - **To Address**: `0xb01713a6fcdc9419f37db065f0274ea172e4689e`
   - **Amount**: `15` USDC (enough for testing)
   - **Asset**: USDC (Perps)

4. **Confirm Transaction**
   - Review the details
   - Sign the transaction with your wallet
   - Wait for confirmation (~few seconds)

### Option 2: Using Python Script

If you prefer to do it programmatically:

```python
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from eth_account import Account

# Initialize with your FUNDED wallet's private key
funded_wallet_private_key = "YOUR_FUNDED_WALLET_PRIVATE_KEY"
wallet = Account.from_key(funded_wallet_private_key)

exchange = Exchange(
    wallet,
    "https://api.hyperliquid.xyz"
)

# Transfer USDC
result = exchange.usd_transfer(
    amount=15.0,  # $15 USDC
    destination="0xb01713a6fcdc9419f37db065f0274ea172e4689e"
)

print(f"Transfer result: {result}")
```

## ⚠️ Important Notes

1. **Minimum Transfer**: Transfer at least $10-15 to have enough for the test
2. **Gas Fees**: Hyperliquid has very low fees (~$0.01)
3. **Confirmation**: Transfer should complete in a few seconds
4. **Verify**: Check the test wallet balance before running the test

## ✅ After Transfer

Once the transfer completes, run the test:

```bash
python3 test_live_trade_flow.py
```

The test will:
- ✅ Detect the $15 balance
- ✅ Place a $10 test trade
- ✅ Set SL/TP orders
- ✅ Monitor for 60 seconds
- ✅ Offer to cleanup

## 🔐 Security Reminder

- Keep your private keys secure
- Only transfer what you need for testing
- The test wallet private key is already in `.env.live_trading`
