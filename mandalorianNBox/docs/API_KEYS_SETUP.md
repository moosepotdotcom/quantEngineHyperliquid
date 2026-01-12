# 🔑 API Keys & Credentials Setup Guide

Complete guide to getting all the API keys and credentials needed to run the trading bots.

---

## 📋 Required Services Overview

The bots use **two different exchanges** depending on which bot you're running:

1. **HyperLiquid** (Primary - Days 10-12 bots) ⭐ **START HERE**
   - Uses **MetaMask wallet private key** (not an API key)
   - Decentralized exchange (DEX)
   - No API key needed!

2. **Phemex** (Optional - Days 4-9 bots)
   - Requires **API Key + Secret**
   - Centralized exchange
   - Only needed for older tutorial bots

---

## 🚀 HyperLiquid Setup (Recommended - Start Here)

HyperLiquid is a **decentralized exchange** that uses your MetaMask wallet. You don't need API keys - just your wallet's private key.

### Step 1: Install MetaMask Wallet

**Download MetaMask:**
- **Chrome/Brave/Edge:** https://chrome.google.com/webstore/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn
- **Firefox:** https://addons.mozilla.org/en-US/firefox/addon/ether-metamask/
- **Mobile:** https://metamask.io/download/

**Installation Steps:**
1. Click the link above for your browser
2. Click "Add to Chrome" (or your browser)
3. Click "Add Extension"
4. Click "Get Started"
5. Choose "Create a Wallet" (or import existing)
6. **IMPORTANT:** Save your seed phrase securely (12 words)
7. Set a password

### Step 2: Add Arbitrum Network to MetaMask

HyperLiquid runs on Arbitrum. You need to add this network:

**Option A: Automatic (Recommended)**
1. Go to: https://app.hyperliquid.xyz
2. Click "Connect Wallet"
3. MetaMask will prompt you to add Arbitrum network - click "Approve"

**Option B: Manual**
1. Open MetaMask
2. Click network dropdown (top left)
3. Click "Add Network"
4. Enter these details:
   - **Network Name:** Arbitrum One
   - **RPC URL:** https://arb1.arbitrum.io/rpc
   - **Chain ID:** 42161
   - **Currency Symbol:** ETH
   - **Block Explorer:** https://arbiscan.io
5. Click "Save"

### Step 3: Get Funds on Arbitrum

You need ETH on Arbitrum to trade. Options:

**Option A: Bridge from Ethereum**
1. Go to: https://bridge.arbitrum.io
2. Connect MetaMask
3. Select Arbitrum One network
4. Enter amount of ETH to bridge
5. Click "Move funds to Arbitrum"

**Option B: Buy on Arbitrum directly**
1. Use a DEX like Uniswap on Arbitrum
2. Or use a centralized exchange that supports Arbitrum withdrawals

**Option C: Use a bridge service**
- **Stargate:** https://stargate.finance/transfer
- **Hop Protocol:** https://app.hop.exchange/

**Minimum:** Start with $50-100 for testing (use small amounts!)

### Step 4: Sign Up for HyperLiquid (Get Fee Discount)

**Sign Up Link:** https://app.hyperliquid.xyz/join/MOONDEV

**Steps:**
1. Click the link above
2. Connect your MetaMask wallet
3. You'll get a fee discount by using this referral link
4. That's it! No account creation needed (it's decentralized)

### Step 5: Export Your MetaMask Private Key

**⚠️ SECURITY WARNING:** Your private key gives full access to your wallet. Keep it secret!

**Steps:**
1. Open MetaMask extension
2. Click the account icon (circle with avatar) in top right
3. Click "Account Details"
4. Click "Export Private Key"
5. Enter your MetaMask password
6. **Copy the private key** (starts with `0x` followed by 64 characters)
7. **Example format:** `0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef`

**⚠️ NEVER:**
- Share your private key with anyone
- Store it in screenshots or unencrypted files
- Commit it to git
- Send it via email/message

### Step 6: Add Private Key to Your Bot

1. Open `dontshare.py` in your project
2. Find this line:
   ```python
   private_key = 'YOUR_HYPERLIQUID_PRIVATE_KEY_HERE'
   ```
3. Replace with your actual key:
   ```python
   private_key = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
   ```
4. Save the file

**✅ HyperLiquid Setup Complete!**

---

## 🔐 Phemex Setup (Optional - For Older Bots)

Only needed if you want to run the Day 4-9 tutorial bots. Skip this if you're starting with HyperLiquid bots.

### Step 1: Sign Up for Phemex

**Sign Up Link:** https://www.phemex.com

**Steps:**
1. Go to https://www.phemex.com
2. Click "Sign Up" (top right)
3. Enter email and password
4. Verify your email
5. Complete KYC (Know Your Customer) verification if required

### Step 2: Get API Keys

**Steps:**
1. Log in to Phemex
2. Click your profile icon (top right)
3. Go to **"Account"** → **"API Management"**
4. Click **"Create API Key"**
5. Enter a name (e.g., "Trading Bot")
6. **IMPORTANT:** Enable these permissions:
   - ✅ **Read** (to check balances)
   - ✅ **Trade** (to place orders)
   - ❌ **Withdraw** (NOT recommended for security)
7. Enter your password
8. Complete 2FA if enabled
9. Click "Create"

### Step 3: Copy API Credentials

After creation, you'll see:
- **API Key:** A long string (e.g., `abc123def456...`)
- **Secret Key:** Another long string (e.g., `xyz789uvw456...`)

**⚠️ IMPORTANT:** Copy these immediately - the Secret Key is only shown once!

### Step 4: Add API Keys to Your Bot

1. Open `key_file.py` in your project
2. Replace the placeholders:
   ```python
   xP_KEY = 'YOUR_PHEMEX_API_KEY_HERE'
   xP_SECRET = 'YOUR_PHEMEX_API_SECRET_HERE'
   ```
3. With your actual keys:
   ```python
   xP_KEY = 'abc123def456ghi789'
   xP_SECRET = 'xyz789uvw456rst123'
   ```
4. Save the file

**✅ Phemex Setup Complete!**

---

## 🧪 Testing Your Setup

### Test HyperLiquid Connection

1. **Activate your environment:**
   ```bash
   source activate_env.sh
   ```

2. **Run the test script:**
   ```bash
   python test_setup.py
   ```

3. **Expected output:**
   ```
   ✅ All required packages are installed!
   ✅ dontshare.py - Configured
   ✅ HyperLiquid API - Connected
   ✅ All tests passed! You're ready to run bots.
   ```

### Manual Connection Test

You can also test manually:

```bash
source activate_env.sh
python
```

Then in Python:
```python
import dontshare as d
from eth_account.signers.local import LocalAccount
import eth_account
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Test private key loading
account = eth_account.Account.from_key(d.private_key)
print(f"✅ Wallet address: {account.address}")

# Test HyperLiquid connection
info = Info(constants.MAINNET_API_URL, skip_ws=True)
meta = info.meta()
print(f"✅ HyperLiquid connected! Available coins: {len(meta['universe'])}")
```

---

## 📝 Quick Reference

### HyperLiquid (Primary)
- **What you need:** MetaMask wallet + Private key
- **Sign up:** https://app.hyperliquid.xyz/join/MOONDEV
- **Network:** Arbitrum One
- **Config file:** `dontshare.py`
- **Cost:** Just gas fees (very low on Arbitrum)

### Phemex (Optional)
- **What you need:** API Key + Secret
- **Sign up:** https://www.phemex.com
- **Config file:** `key_file.py`
- **Cost:** Trading fees (maker/taker)

---

## ⚠️ Security Best Practices

1. **Never share your private keys or API secrets**
2. **Use separate wallets** for trading bots (don't use your main wallet)
3. **Start with small amounts** to test
4. **Enable 2FA** on exchanges when possible
5. **Don't enable withdraw permissions** on API keys
6. **Keep config files local** - never commit to git
7. **Use a dedicated trading wallet** - not your main wallet

---

## 🚀 Next Steps

Once your API keys are configured:

1. **Test your setup:**
   ```bash
   python test_setup.py
   ```

2. **Configure your bot settings:**
   - Edit `10_day10_bots/day10_hyperliquid/10_bollinger_bot.py`
   - Set symbol, size, target, max_loss

3. **Run your first bot:**
   ```bash
   python 10_day10_bots/day10_hyperliquid/10_bollinger_bot.py
   ```

4. **Monitor closely** - watch the terminal output and your account

---

## 🆘 Troubleshooting

### "Invalid private key" error
- Make sure your private key starts with `0x`
- Check for extra spaces or quotes
- Verify you copied the entire key (64 hex characters after `0x`)

### "Insufficient funds" error
- Make sure you have ETH on Arbitrum network
- Check your wallet balance on HyperLiquid
- You need ETH for gas fees

### "Network error" or connection issues
- Check your internet connection
- Verify MetaMask is connected to Arbitrum network
- Try refreshing the connection

### API key errors (Phemex)
- Verify API key and secret are correct
- Check that trading permissions are enabled
- Make sure you're not using a testnet API key

---

## 📚 Additional Resources

- **HyperLiquid Docs:** https://hyperliquid.gitbook.io/hyperliquid-docs
- **MetaMask Support:** https://support.metamask.io
- **Arbitrum Bridge:** https://bridge.arbitrum.io
- **Phemex API Docs:** https://phemex.com/user-guides/api-overview

---

**Ready to trade?** Once your keys are configured, run `python test_setup.py` to verify everything works!



