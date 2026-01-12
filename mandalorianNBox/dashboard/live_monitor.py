
"""
Live Trading Monitor Dashboard V2

Enhanced with:
- Probability vs Threshold gauges
- News Engine integration
- Market regime indicator
"""

from flask import Flask, render_template, jsonify
import os
import json
import re
from datetime import datetime
import glob

app = Flask(__name__)

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(PROJECT_ROOT, 'PROJECT_DEV_LOG.md')
MODELS_DIR = os.path.join(PROJECT_ROOT, 'models')
NEWS_CACHE = os.path.join(PROJECT_ROOT, 'data', 'news_cache.json')
TRADES_FILE = os.path.join(PROJECT_ROOT, 'data', 'trades.json')

# Shared state (updated by parsing logs)
LIVE_STATE = {
    'long_prob': 0.0,
    'short_prob': 0.0,
    'threshold': 0.50,
    'regime': 'CHOP',
    'whale_bias': 0,
    'funding_bias': 0
}


def parse_ml_probabilities():
    """Parse latest ML probabilities from log output"""
    global LIVE_STATE
    
    # Look for most recent probability line in a status file
    status_file = os.path.join(PROJECT_ROOT, 'data', 'ml_status.json')
    if os.path.exists(status_file):
        try:
            with open(status_file, 'r') as f:
                data = json.load(f)
                LIVE_STATE.update(data)
        except:
            pass
    
    return LIVE_STATE


def parse_recent_logs(max_entries=50):
    """Parse recent log entries from PROJECT_DEV_LOG.md"""
    if not os.path.exists(LOG_FILE):
        return []
    
    try:
        with open(LOG_FILE, 'r') as f:
            content = f.read()
        
        entries = re.findall(r'### (.+?) - (.+?)\n(.*?)(?=\n### |\Z)', content, re.DOTALL)
        
        logs = []
        for emoji_title, timestamp, details in entries[-max_entries:]:
            logs.append({
                'title': emoji_title.strip(),
                'timestamp': timestamp.strip(),
                'details': details.strip()[:200],
                'type': 'trade' if 'Trade' in emoji_title else 'alert' if 'ALERT' in emoji_title else 'news' if 'NEWS' in emoji_title else 'info'
            })
        
        return logs[::-1]
    except Exception as e:
        return [{'title': f'Error: {e}', 'timestamp': '', 'details': '', 'type': 'error'}]


def get_news():
    """Get recent news from news cache and journal"""
    news = []
    
    # First try to parse from journal (most reliable)
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                content = f.read()
            
            # Match both news formats
            news_entries = re.findall(
                r'### (📰|🚨).*?(News|NEWS).*? - (.+?)\n.*?\*\*Headline\*\*: (.+?)\n.*?\*\*Source\*\*: (.+?)\n',
                content, re.DOTALL
            )
            
            for emoji, _, timestamp, headline, source in news_entries[-10:]:
                news.append({
                    'timestamp': timestamp.strip()[:20],
                    'headline': headline.strip()[:80],
                    'source': source.strip(),
                    'is_alert': emoji == '🚨'
                })
        except Exception as e:
            pass
    
    return news[-5:][::-1]  # Last 5, newest first


def get_model_stats():
    """Get ML model statistics"""
    stats = {
        'long_model': os.path.exists(os.path.join(MODELS_DIR, 'scalp_mtf_long.pkl')),
        'short_model': os.path.exists(os.path.join(MODELS_DIR, 'scalp_mtf_short.pkl')),
        'regime_model': os.path.exists(os.path.join(MODELS_DIR, 'regime_classifier.pkl')),
        'adaptive_model': os.path.exists(os.path.join(MODELS_DIR, 'scalp_adaptive.pkl')),
        'adaptive_precision': 'N/A',
        'adaptive_last_train': 'N/A'
    }
    
    metrics_path = os.path.join(MODELS_DIR, 'adaptive_metrics.json')
    if os.path.exists(metrics_path):
        try:
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
                stats['adaptive_precision'] = f"{metrics.get('precision', 0)*100:.1f}%"
                stats['adaptive_last_train'] = metrics.get('last_train', 'N/A')[:16]
        except:
            pass
    
    return stats


def get_recent_trades(max_entries=50):
    """Get recent trades from JSON log"""
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE, 'r') as f:
                trades = json.load(f)
        except:
            pass
    return trades[-max_entries:][::-1]  # Newest first


def get_whale_activity(max_entries=50):
    """Get persistent whale activity from JSON"""
    whale_file = os.path.join(PROJECT_ROOT, 'data', 'whale_activity.json')
    whales = []
    if os.path.exists(whale_file):
        try:
            with open(whale_file, 'r') as f:
                whales = json.load(f)
        except:
            pass
            
    # Normalize keys if needed or just return raw
    # Our JSON has: timestamp, name, coin, action, change, size, price
    # We want newest first
    return whales[-max_entries:][::-1]


def get_engine_summary():
    """Get engine status summary"""
    is_cloud = os.environ.get('PORT') is not None
    darwin_status = 'DISABLED (CLOUD)' if is_cloud else 'WAIT'
    
    return {
        'engines': [
            {'name': 'Day Trader', 'status': 'NEUTRAL', 'type': 'turtle'},
            {'name': 'Swing Trader', 'status': 'NEUTRAL', 'type': 'consolidation'},
            {'name': 'Investor', 'status': 'SHORT', 'type': 'sma'},
            {'name': 'Darwin Evo', 'status': darwin_status, 'type': 'genetic'},
            {'name': 'AI Scalper V1', 'status': 'WAIT', 'type': 'ml'},
            {'name': 'AI Scalper V2', 'status': 'WAIT', 'type': 'ml_enhanced'},
        ],
        'last_update': datetime.now().strftime('%H:%M:%S')
    }


@app.route('/')
def index():
    return render_template('live_monitor.html')


@app.route('/api/status')
def api_status():
    ml_state = parse_ml_probabilities()
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'logs': parse_recent_logs(20),
        'models': get_model_stats(),
        'engines': get_engine_summary(),
        'ml': ml_state,
        'ml': ml_state,
        'news': get_news(),
        'trades': get_recent_trades(),
        'whales': get_whale_activity()
    })


# Enhanced Template with Threshold Gauge and News
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🤖 AI Trading Monitor</title>
    <style>
        :root {
            --bg-dark: #0a0a0f;
            --bg-card: #12121a;
            --border: #1e1e2e;
            --text: #e0e0e0;
            --text-muted: #888;
            --accent-green: #00ff88;
            --accent-red: #ff4757;
            --accent-blue: #5f9fff;
            --accent-yellow: #ffa502;
            --accent-purple: #a855f7;
            --accent-pink: #ec4899;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'SF Mono', 'Fira Code', monospace;
            background: var(--bg-dark);
            color: var(--text);
            min-height: 100vh;
            padding: 20px;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid var(--border);
        }
        
        .header h1 { font-size: 24px; color: var(--accent-blue); }
        
        .status-dot {
            width: 12px; height: 12px; border-radius: 50%;
            display: inline-block; margin-right: 8px;
            animation: pulse 2s infinite;
        }
        .status-dot.live { background: var(--accent-green); }
        
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
        }
        
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 15px;
        }
        
        .card h2 {
            font-size: 12px; color: var(--text-muted);
            margin-bottom: 12px; text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Threshold Gauge */
        .gauge-container { display: flex; flex-direction: column; gap: 15px; }
        
        .gauge {
            background: rgba(255,255,255,0.05);
            border-radius: 8px; padding: 12px;
        }
        
        .gauge-label {
            display: flex; justify-content: space-between;
            font-size: 11px; margin-bottom: 8px;
        }
        
        .gauge-bar {
            height: 24px; background: #1a1a2e;
            border-radius: 12px; position: relative;
            overflow: hidden;
        }
        
        .gauge-fill {
            height: 100%; border-radius: 12px;
            transition: width 0.5s ease;
        }
        
        .gauge-fill.long { background: linear-gradient(90deg, #004d26, var(--accent-green)); }
        .gauge-fill.short { background: linear-gradient(90deg, #4d0000, var(--accent-red)); }
        
        .gauge-threshold {
            position: absolute; top: 0; bottom: 0;
            width: 3px; background: white;
            box-shadow: 0 0 8px rgba(255,255,255,0.5);
        }
        
        .gauge-value {
            position: absolute; right: 10px; top: 50%;
            transform: translateY(-50%); font-size: 12px;
            font-weight: bold;
        }
        
        /* Regime Indicator */
        .regime-box {
            text-align: center; padding: 20px;
            border-radius: 8px; margin-top: 10px;
        }
        .regime-box.BULL { background: rgba(0,255,136,0.15); color: var(--accent-green); }
        .regime-box.BEAR { background: rgba(255,71,87,0.15); color: var(--accent-red); }
        .regime-box.CHOP { background: rgba(255,165,2,0.15); color: var(--accent-yellow); }
        
        .regime-label { font-size: 10px; opacity: 0.7; }
        .regime-value { font-size: 28px; font-weight: bold; }
        
        /* News Panel */
        .news-list { display: flex; flex-direction: column; gap: 8px; }
        
        .news-item {
            background: rgba(168,85,247,0.1);
            border-left: 3px solid var(--accent-purple);
            padding: 10px; border-radius: 0 8px 8px 0;
            font-size: 11px;
        }
        
        .news-time { color: var(--text-muted); font-size: 9px; }
        
        /* Engine Grid */
        .engine-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        
        .engine-item {
            background: rgba(255,255,255,0.03);
            padding: 10px; border-radius: 8px;
        }
        
        .engine-name { font-size: 10px; color: var(--text-muted); }
        .engine-status { font-size: 14px; font-weight: bold; }
        .engine-status.LONG { color: var(--accent-green); }
        .engine-status.SHORT { color: var(--accent-red); }
        .engine-status.NEUTRAL, .engine-status.WAIT { color: var(--text-muted); }
        
        /* Log List */
        .log-list { max-height: 300px; overflow-y: auto; }
        
        .log-item {
            padding: 8px; border-bottom: 1px solid var(--border);
            font-size: 11px;
        }
        .log-item:last-child { border-bottom: none; }
        .log-title { font-weight: bold; }
        .log-item.trade .log-title { color: var(--accent-green); }
        .log-item.alert .log-title { color: var(--accent-yellow); }
        .log-item.news .log-title { color: var(--accent-purple); }
        .log-time { color: var(--text-muted); font-size: 9px; }
        
        /* Whale List */
        .whale-list { display: flex; flex-direction: column; gap: 8px; }
        .whale-item {
            background: rgba(236, 72, 153, 0.1);
            border-left: 3px solid var(--accent-pink);
            padding: 10px; border-radius: 0 8px 8px 0;
            font-size: 11px;
        }
        .whale-header { display: flex; justify-content: space-between; font-weight: bold; color: var(--accent-pink); margin-bottom: 4px; }
        .whale-detail { font-size: 10px; color: var(--text); }
        .whale-change { font-weight: bold; }
        .whale-change.pos { color: var(--accent-green); }
        .whale-change.neg { color: var(--accent-red); }

        /* Model List */
        .model-list { display: flex; flex-direction: column; gap: 6px; }
        .model-item { display: flex; justify-content: space-between; padding: 6px 0; }
        .model-status { color: var(--accent-green); }
        .model-status.offline { color: var(--accent-red); }
        
        .full-width { grid-column: 1 / -1; }
        .refresh-indicator { font-size: 11px; color: var(--text-muted); }

        /* Trade Log */
        .trade-table { width: 100%; border-collapse: collapse; font-size: 11px; }
        .trade-table th { text-align: left; color: var(--text-muted); padding: 5px; border-bottom: 1px solid var(--border); }
        .trade-table td { padding: 5px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .trade-profit { color: var(--accent-green); }
        .trade-loss { color: var(--accent-red); }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI Trading Monitor</h1>
        <div>
            <span class="status-dot live"></span>
            <span class="refresh-indicator">Refresh: <span id="countdown">3</span>s</span>
            <button id="notify-btn" onclick="toggleNotifications()" style="background:none; border:none; font-size:16px; cursor:pointer; margin-left:10px; opacity:0.5">🔔</button>
        </div>
    </div>
    
    <div class="grid">
        <!-- Probability Gauges -->
        <div class="card">
            <h2>📊 Signal Probability vs Threshold</h2>
            <div class="gauge-container">
                <div class="gauge">
                    <div class="gauge-label">
                        <span>🟢 LONG</span>
                        <span id="long-prob-text">0.00%</span>
                    </div>
                    <div class="gauge-bar">
                        <div class="gauge-fill long" id="long-gauge" style="width: 0%"></div>
                        <div class="gauge-threshold" id="threshold-line" style="left: 50%"></div>
                    </div>
                </div>
                <div class="gauge">
                    <div class="gauge-label">
                        <span>🔴 SHORT</span>
                        <span id="short-prob-text">0.00%</span>
                    </div>
                    <div class="gauge-bar">
                        <div class="gauge-fill short" id="short-gauge" style="width: 0%"></div>
                        <div class="gauge-threshold" style="left: 50%"></div>
                    </div>
                </div>
                <div style="text-align: center; color: var(--text-muted); font-size: 10px; margin-top: 5px;">
                    Threshold: <span id="threshold-val">50%</span> ← Trade triggers when bar crosses
                </div>
            </div>
        </div>
        
        <!-- Regime Indicator -->
        <div class="card">
            <h2>🌐 Market Regime</h2>
            <div class="regime-box CHOP" id="regime-box">
                <div class="regime-label">Current Regime</div>
                <div class="regime-value" id="regime-value">CHOP</div>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 15px; font-size: 10px;">
                <div>🐋 Whale: <span id="whale-bias">0</span></div>
                <div>💰 Funding: <span id="funding-bias">0</span></div>
            </div>
        </div>
        
        <!-- Whale Tracker (New!) -->
        <div class="card">
            <h2>🐋 HyperLiquid Tracker</h2>
            <div class="whale-list" id="whale-list">
                <div class="whale-item">Scanning for whales...</div>
            </div>
        </div>

        <!-- News -->
        <div class="card">
            <h2>📰 Latest News</h2>
            <div class="news-list" id="news-list">
                <div class="news-item">Loading news...</div>
            </div>
        </div>
        
        <!-- Engines -->
        <div class="card">
            <h2>🚀 Active Engines</h2>
            <div class="engine-grid" id="engines">
                <div class="engine-item"><span class="engine-name">Loading...</span></div>
            </div>
        </div>
        
        <!-- ML Models -->
        <div class="card">
            <h2>🧠 ML Models</h2>
            <div class="model-list" id="models">
                <div class="model-item"><span>Loading...</span></div>
            </div>
        </div>
        
        <!-- Daily Whale Activity -->
        <div class="card" style="grid-column: 1 / -1;">
            <h2>🐋 Daily Whale Activity</h2>
            <div class="table-container">
                <table class="trade-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Whale</th>
                            <th>Coin</th>
                            <th>Action</th>
                            <th>Change</th>
                            <th>New Size</th>
                            <th>Avg Price</th>
                        </tr>
                    </thead>
                    <tbody id="whale-activity-list">
                        <!-- Whale Data -->
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Trade Log -->
        <div class="card" style="grid-column: 1 / -1;">
            <h2>Recent Trades</h2>
            <div style="max-height: 200px; overflow-y: auto;">
                <table class="trade-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Symbol</th>
                            <th>Side</th>
                            <th>Size</th>
                            <th>Entry</th>
                            <th>SL</th>
                            <th>TP</th>
                            <th>Result</th>
                        </tr>
                    </thead>
                    <tbody id="trade-list">
                        <tr><td colspan="8">Loading trades...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Activity Log -->
        <div class="card full-width">
            <h2>📋 Recent Activity</h2>
            <div class="log-list" id="logs">
                <div class="log-item"><div class="log-title">Loading...</div></div>
            </div>
        </div>
    </div>
    
    <script>
        let countdown = 3;
        let lastWhaleTime = null;
        
        // Notification Logic (Mobile Safe)
        let notificationsEnabled = false;
        
        function toggleNotifications() {
            if (!("Notification" in window)) {
                alert("This browser does not support desktop notifications");
                return;
            }
            
            if (Notification.permission === "granted") {
                notificationsEnabled = !notificationsEnabled;
                updateNotifyIcon();
            } else if (Notification.permission !== "denied") {
                Notification.requestPermission().then((permission) => {
                    if (permission === "granted") {
                        notificationsEnabled = true;
                        updateNotifyIcon();
                    }
                });
            } else {
                alert("Notifications denied. Please enable them in browser settings.");
            }
        }
        
        function updateNotifyIcon() {
            const btn = document.getElementById('notify-btn');
            btn.style.opacity = notificationsEnabled ? '1' : '0.5';
            btn.textContent = notificationsEnabled ? '🔕' : '🔔';
        }

        async function fetchStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                
                // Update gauges
                const longPct = (data.ml.long_prob * 100).toFixed(1);
                const shortPct = (data.ml.short_prob * 100).toFixed(1);
                const threshold = data.ml.threshold * 100;
                
                document.getElementById('long-gauge').style.width = longPct + '%';
                document.getElementById('short-gauge').style.width = shortPct + '%';
                document.getElementById('long-prob-text').textContent = longPct + '%';
                document.getElementById('short-prob-text').textContent = shortPct + '%';
                document.getElementById('threshold-val').textContent = threshold + '%';
                
                // Set threshold line position
                document.querySelectorAll('.gauge-threshold').forEach(el => {
                    el.style.left = threshold + '%';
                });
                
                // Update regime
                const regime = data.ml.regime || 'CHOP';
                const regimeBox = document.getElementById('regime-box');
                regimeBox.className = 'regime-box ' + regime;
                document.getElementById('regime-value').textContent = regime;
                document.getElementById('whale-bias').textContent = data.ml.whale_bias > 0 ? '+' + data.ml.whale_bias : data.ml.whale_bias;
                document.getElementById('funding-bias').textContent = data.ml.funding_bias > 0 ? '+' + data.ml.funding_bias : data.ml.funding_bias;
                
                // Update whales
                const whalesHtml = data.whales.length ? data.whales.map(w => {
                    const changeVal = parseFloat(w.change);
                    const changeClass = changeVal > 0 ? 'pos' : (changeVal < 0 ? 'neg' : '');
                    const changeText = changeVal > 0 ? '+' + w.change : w.change;
                    
                    return `
                    <div class="whale-item">
                        <div class="whale-header">
                            <span>${w.name}</span>
                            <span>${w.action}</span>
                        </div>
                        <div class="whale-detail">
                            ${w.coin} | Change: <span class="whale-change ${changeClass}">${changeText}</span> @ $${parseFloat(w.size).toFixed(2)}
                        </div>
                        <div class="news-time">${new Date(w.timestamp * 1000).toLocaleString()}</div>
                    </div>`;
                }).join('') : '<div class="whale-item">No recent whale activity</div>';
                document.getElementById('whale-list').innerHTML = whalesHtml;

                // Whale Notification Logic
                if (data.whales.length > 0) {
                    const latest = data.whales[0];
                    if (lastWhaleTime && latest.timestamp !== lastWhaleTime) {
                        // New whale event!
                        if (notificationsEnabled && Notification.permission === 'granted') {
                            try {
                                new Notification(`🐋 Whale Alert: ${latest.name}`, {
                        if (notificationsEnabled && Notification.permission === 'granted') {
                            try {
                                new Notification(`🐋 Whale Alert: ${latest.name}`, {
                                    body: `${latest.action} ${latest.coin} (${latest.change})`,
                                    icon: 'https://cdn-icons-png.flaticon.com/512/3069/3069172.png'
                                });
                            } catch (e) {
                                console.log("Notification failed:", e);
                            }
                        }
                    }
                    lastWhaleTime = latest.timestamp;
                }

                // Update news
                const newsHtml = data.news.length ? data.news.map(n => `
                    <div class="news-item">
                        <div>${n.headline || n.title || 'News update'}</div>
                        <div class="news-time">${n.timestamp || ''}</div>
                    </div>
                `).join('') : '<div class="news-item">No recent news</div>';
                document.getElementById('news-list').innerHTML = newsHtml;
                
                // Update engines
                const enginesHtml = data.engines.engines.map(e => `
                    <div class="engine-item">
                        <span class="engine-name">${e.name}</span>
                        <span class="engine-status ${e.status}">${e.status}</span>
                    </div>
                `).join('');
                document.getElementById('engines').innerHTML = enginesHtml;
                
                // Update models
                const modelsHtml = `
                    <div class="model-item"><span>LONG</span><span class="model-status">${data.models.long_model ? '✅' : '❌'}</span></div>
                    <div class="model-item"><span>SHORT</span><span class="model-status">${data.models.short_model ? '✅' : '❌'}</span></div>
                    <div class="model-item"><span>Regime</span><span class="model-status">${data.models.regime_model ? '✅' : '❌'}</span></div>
                    <div class="model-item"><span>Adaptive</span><span class="model-status">${data.models.adaptive_precision}</span></div>
                `;
                document.getElementById('models').innerHTML = modelsHtml;

                // Update trade log
                const tradesHtml = data.trades.length ? data.trades.map(t => {
                    const pnlClass = (t.pnl || 0) >= 0 ? 'trade-profit' : 'trade-loss';
                    const pnlText = t.pnl != null ? t.pnl.toFixed(2) + '%' : '-';
                    const slText = t.sl ? '$' + t.sl.toFixed(2) : '-';
                    const tpText = t.tp ? '$' + t.tp.toFixed(2) : '-';
                    const sideClass = t.action.includes('BUY') ? 'trade-profit' : 'trade-loss';
                    
                    return `
                        <tr>
                            <td>${t.timestamp.slice(5, 19)}</td>
                            <td>${t.symbol}</td>
                            <td class="${sideClass}">${t.action.replace('ENGINE SIGNAL', '').replace('(', '').replace(')', '').trim()}</td>
                            <td>${t.size}</td>
                            <td>$${t.price.toFixed(2)}</td>
                            <td>${slText}</td>
                            <td>${tpText}</td>
                            <td class="${pnlClass}">${pnlText}</td>
                        </tr>
                    `;
                }).join('') : '<tr><td colspan="8">No recent trades</td></tr>';
                document.getElementById('trade-list').innerHTML = tradesHtml;
                
                // Update Whale Log
                const whalesHtml = data.whales.length ? data.whales.map(w => {
                    const actionClass = w.action.includes('ACCUMULATING') || w.action.includes('COVERING') ? 'trade-profit' : 'trade-loss';
                    const date = new Date(w.timestamp * 1000);
                    const timeStr = date.toLocaleTimeString();
                    
                    return `
                        <tr>
                            <td>${timeStr}</td>
                            <td>${w.name}</td>
                            <td>${w.coin}</td>
                            <td class="${actionClass}">${w.action}</td>
                            <td>${w.change > 0 ? '+' : ''}${w.change}</td>
                            <td>${w.size}</td>
                            <td>$${w.price}</td>
                        </tr>
                    `;
                }).join('') : '<tr><td colspan="7">No whale activity yet... 🌊</td></tr>';
                document.getElementById('whale-activity-list').innerHTML = whalesHtml;
                
                
                // Update logs
                const logsHtml = data.logs.map(l => `
                    <div class="log-item ${l.type}">
                        <div class="log-title">${l.title}</div>
                        <div class="log-time">${l.timestamp}</div>
                    </div>
                `).join('') || '<div class="log-item">No recent activity</div>';
                document.getElementById('logs').innerHTML = logsHtml;
                
            } catch (err) {
                console.error('Fetch error:', err);
            }
        }
        
        function tick() {
            countdown--;
            document.getElementById('countdown').textContent = countdown;
            if (countdown <= 0) {
                countdown = 3;
                fetchStatus();
            }
        }
        
        fetchStatus();
        setInterval(tick, 1000);
    </script>
</body>
</html>
'''


def setup_templates():
    """Create template file"""
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    template_path = os.path.join(templates_dir, 'live_monitor.html')
    with open(template_path, 'w') as f:
        f.write(TEMPLATE)


    port = int(os.environ.get('PORT', 5001))
    print(f"🖥️  Starting Live Trading Monitor V2 on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
