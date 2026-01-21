#!/usr/bin/env python3
"""
SIMPLE ADMIN DASHBOARD
Real-time engine switching + Liquidation heatmap
No complex dependencies
"""

from flask import Flask, render_template_string, jsonify, request, session, redirect
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "admin_dashboard_v8_enhanced"

# Global state
current_engine = "current"  # or "v8_enhanced"
ADMIN_PASSWORD = "admin"

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MandalorianBox - Entry</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        
        body {
            background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 50%, #16213e 100%);
            color: #c0c0c0;
            font-family: 'Orbitron', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        
        /* Animated background */
        body::before {
            content: '';
            position: absolute;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(192,192,192,0.1) 1px, transparent 1px);
            background-size: 50px 50px;
            animation: scroll 20s linear infinite;
            z-index: 0;
        }
        
        @keyframes scroll {
            0% { transform: translate(0, 0); }
            100% { transform: translate(50px, 50px); }
        }
        
        .login-container {
            position: relative;
            z-index: 1;
            background: linear-gradient(135deg, rgba(26,26,46,0.95), rgba(22,33,62,0.95));
            padding: 60px 50px;
            border-radius: 20px;
            box-shadow: 0 0 60px rgba(192,192,192,0.4), inset 0 0 30px rgba(192,192,192,0.1);
            border: 2px solid #c0c0c0;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        .mandalorian-logo {
            font-size: 3em;
            font-weight: 900;
            background: linear-gradient(135deg, #c0c0c0, #ffffff, #c0c0c0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 30px rgba(192,192,192,0.8);
            margin-bottom: 10px;
            letter-spacing: 3px;
        }
        
        .subtitle {
            color: #c0c0c0;
            font-size: 0.9em;
            margin-bottom: 30px;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        
        .motto {
            color: #c0c0c0;
            font-size: 1.1em;
            margin: 20px 0;
            font-style: italic;
            text-shadow: 0 0 10px rgba(192,192,192,0.5);
        }
        
        input {
            padding: 15px 20px;
            margin: 20px 0;
            width: 300px;
            border: 2px solid #c0c0c0;
            background: rgba(0,0,0,0.5);
            color: #c0c0c0;
            font-family: 'Orbitron', sans-serif;
            font-size: 1em;
            border-radius: 10px;
            outline: none;
            transition: all 0.3s;
        }
        
        input:focus {
            box-shadow: 0 0 20px rgba(192,192,192,0.6);
            border-color: #ffffff;
        }
        
        button {
            padding: 15px 40px;
            background: linear-gradient(135deg, #c0c0c0, #ffffff);
            border: none;
            color: #0d0d0d;
            font-weight: 900;
            cursor: pointer;
            font-family: 'Orbitron', sans-serif;
            font-size: 1.1em;
            border-radius: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
            transition: all 0.3s;
            box-shadow: 0 0 20px rgba(192,192,192,0.5);
        }
        
        button:hover {
            transform: scale(1.05);
            box-shadow: 0 0 40px rgba(192,192,192,0.8);
        }
        
        .helmet {
            font-size: 4em;
            margin-bottom: 20px;
            filter: drop-shadow(0 0 20px rgba(192,192,192,0.6));
        }
    </style>
</head>
<body>
    <div class="login-container">
        <div class="helmet">⚔️</div>
        <div class="mandalorian-logo">MANDALORIANBOX</div>
        <div class="subtitle">Beskar Trading System</div>
        <div class="motto">"This is the Way"</div>
        <form method="POST">
            <input type="password" name="password" placeholder="Enter Access Code" required autocomplete="off">
            <br><button type="submit">⚡ ENTER ⚡</button>
        </form>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MandalorianBox - Command Center</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 50%, #16213e 100%);
            color: #c0c0c0;
            font-family: 'Orbitron', sans-serif;
            padding: 20px;
            min-height: 100vh;
        }
        
        /* Animated grid background */
        body::before {
            content: '';
            position: fixed;
            width: 100%;
            height: 100%;
            background: 
                linear-gradient(90deg, rgba(192,192,192,0.03) 1px, transparent 1px),
                linear-gradient(rgba(192,192,192,0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: 0;
            pointer-events: none;
        }
        
        .container { position: relative; z-index: 1; max-width: 1600px; margin: 0 auto; }
        
        .header {
            background: linear-gradient(135deg, rgba(26,26,46,0.95), rgba(22,33,62,0.95));
            padding: 25px 30px;
            border-radius: 15px;
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 2px solid #c0c0c0;
            box-shadow: 0 0 30px rgba(192,192,192,0.3), inset 0 0 20px rgba(192,192,192,0.05);
            backdrop-filter: blur(10px);
        }
        
        .header-left { display: flex; align-items: center; gap: 20px; }
        
        .logo {
            font-size: 2em;
            font-weight: 900;
            background: linear-gradient(135deg, #c0c0c0, #ffffff, #c0c0c0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: 2px;
        }
        
        .motto {
            color: #c0c0c0;
            font-size: 0.9em;
            font-style: italic;
            opacity: 0.8;
        }
        
        .logout-btn {
            background: linear-gradient(135deg, #c0c0c0, #ffffff);
            padding: 12px 25px;
            border: none;
            color: #0d0d0d;
            border-radius: 8px;
            cursor: pointer;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            transition: all 0.3s;
            box-shadow: 0 0 15px rgba(192,192,192,0.4);
        }
        
        .logout-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 0 25px rgba(192,192,192,0.6);
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 25px;
            margin-bottom: 25px;
        }
        
        .panel {
            background: linear-gradient(135deg, rgba(26,26,46,0.95), rgba(22,33,62,0.95));
            padding: 25px;
            border-radius: 15px;
            border: 2px solid #c0c0c0;
            box-shadow: 0 0 30px rgba(192,192,192,0.2), inset 0 0 20px rgba(192,192,192,0.05);
            backdrop-filter: blur(10px);
            transition: all 0.3s;
        }
        
        .panel:hover {
            box-shadow: 0 0 40px rgba(192,192,192,0.4), inset 0 0 30px rgba(192,192,192,0.1);
            transform: translateY(-2px);
        }
        
        .panel h2 {
            color: #ffffff;
            margin-bottom: 20px;
            font-size: 1.3em;
            text-transform: uppercase;
            letter-spacing: 2px;
            border-bottom: 2px solid #c0c0c0;
            padding-bottom: 10px;
            text-shadow: 0 0 10px rgba(192,192,192,0.5);
        }
        
        .engine-selector {
            display: flex;
            gap: 15px;
            margin: 20px 0;
        }
        
        .engine-btn {
            flex: 1;
            padding: 20px;
            border: 2px solid #c0c0c0;
            background: rgba(0,0,0,0.3);
            color: #c0c0c0;
            cursor: pointer;
            border-radius: 10px;
            font-size: 1em;
            font-family: 'Orbitron', sans-serif;
            font-weight: 700;
            text-transform: uppercase;
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }
        
        .engine-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(192,192,192,0.3), transparent);
            transition: left 0.5s;
        }
        
        .engine-btn:hover::before {
            left: 100%;
        }
        
        .engine-btn.active {
            background: linear-gradient(135deg, #c0c0c0, #ffffff);
            color: #0d0d0d;
            font-weight: 900;
            box-shadow: 0 0 30px rgba(192,192,192,0.6), inset 0 0 20px rgba(255,255,255,0.3);
            border-color: #ffffff;
        }
        
        .engine-btn:hover {
            transform: scale(1.02);
            box-shadow: 0 0 20px rgba(192,192,192,0.4);
        }
        
        .active-engine-display {
            margin-top: 20px;
            padding: 20px;
            background: rgba(192,192,192,0.1);
            border-radius: 10px;
            border: 1px solid #c0c0c0;
        }
        
        .active-engine-label {
            font-size: 0.8em;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .active-engine-value {
            font-size: 1.8em;
            color: #ffffff;
            font-weight: 900;
            margin-top: 8px;
            text-shadow: 0 0 15px rgba(192,192,192,0.6);
        }
        
        .stat {
            display: flex;
            justify-content: space-between;
            padding: 15px 0;
            border-bottom: 1px solid rgba(192,192,192,0.2);
            align-items: center;
        }
        
        .stat:last-child { border-bottom: none; }
        
        .stat-label {
            color: #c0c0c0;
            font-size: 0.95em;
        }
        
        .stat-value {
            color: #ffffff;
            font-weight: 700;
            font-size: 1.1em;
            text-shadow: 0 0 10px rgba(192,192,192,0.5);
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 15px;
            background: linear-gradient(135deg, #c0c0c0, #ffffff);
            color: #0d0d0d;
            border-radius: 20px;
            font-weight: 900;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
            animation: pulse 2s infinite;
            box-shadow: 0 0 15px rgba(192,192,192,0.5);
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.8; transform: scale(0.98); }
        }
        
        .features-list {
            font-size: 0.95em;
            line-height: 2;
            color: #c0c0c0;
        }
        
        .features-list div::before {
            content: '⚔️ ';
            margin-right: 8px;
        }
        
        .heatmap-container {
            grid-column: 1 / -1;
        }
        
        iframe {
            width: 100%;
            height: 700px;
            border: 2px solid #c0c0c0;
            border-radius: 10px;
            background: #000;
            box-shadow: 0 0 30px rgba(192,192,192,0.3);
        }
        
        .helmet-icon {
            font-size: 1.5em;
            margin-right: 10px;
            filter: drop-shadow(0 0 10px rgba(192,192,192,0.6));
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <span class="helmet-icon">⚔️</span>
                <div>
                    <div class="logo">MANDALORIANBOX</div>
                    <div class="motto">"This is the Way"</div>
                </div>
            </div>
            <button class="logout-btn" onclick="location.href='/logout'">⚡ EXIT</button>
        </div>
        
        <div class="grid">
            <div class="panel">
                <h2>⚡ Engine Selector</h2>
                <p style="color: #888; margin-bottom: 15px; font-size: 0.9em;">Choose your weapon (switches in real-time):</p>
                <div class="engine-selector">
                    <button class="engine-btn" id="btn-current" onclick="switchEngine('current')">
                        CURRENT<br>ENGINE
                    </button>
                    <button class="engine-btn" id="btn-v8" onclick="switchEngine('v8_enhanced')">
                        V8<br>ENHANCED
                    </button>
                </div>
                <div class="active-engine-display">
                    <div class="active-engine-label">Active Weapon System:</div>
                    <div class="active-engine-value" id="active-engine">Loading...</div>
                </div>
            </div>
            
            <div class="panel">
                <h2>🛡️ V8 Enhanced Status</h2>
                <div class="stat">
                    <span class="stat-label">Base Win Rate</span>
                    <span class="stat-value" id="base-wr">83.82%</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Expected Win Rate</span>
                    <span class="stat-value" id="expected-wr">90%+</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Auto-Optimization</span>
                    <span class="status-badge">ACTIVE</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Liquidation Boost</span>
                    <span class="status-badge">ENABLED</span>
                </div>
            </div>
            
            <div class="panel">
                <h2>🔥 Liquidation Intel</h2>
                <div class="stat">
                    <span class="stat-label">Total Events</span>
                    <span class="stat-value" id="liq-total">Loading...</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Total Volume</span>
                    <span class="stat-value" id="liq-volume">Loading...</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Long Liquidations</span>
                    <span class="stat-value" id="liq-long">Loading...</span>
                </div>
                <div class="stat">
                    <span class="stat-label">Short Liquidations</span>
                    <span class="stat-value" id="liq-short">Loading...</span>
                </div>
            </div>
            
            <div class="panel">
                <h2>⚔️ Beskar Features</h2>
                <div class="features-list">
                    <div>V8 Base Model (83.82% WR)</div>
                    <div>Auto-Optimization (900+ tests)</div>
                    <div>Liquidation Proximity Detection</div>
                    <div>Dynamic Confidence Boost (+20%)</div>
                    <div>24-Hour Re-optimization Cycle</div>
                </div>
            </div>
            
            <div class="panel heatmap-container">
                <h2>📈 Tactical Heatmap</h2>
                <iframe src="/heatmap"></iframe>
            </div>
        </div>
    </div>
    
    <script>
        let currentEngine = 'current';
        
        async function switchEngine(engine) {
            try {
                const response = await fetch('/api/engine/switch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({engine: engine})
                });
                const data = await response.json();
                
                if (data.status === 'ok') {
                    currentEngine = engine;
                    updateUI();
                    showNotification('⚡ Engine switched to: ' + (engine === 'v8_enhanced' ? 'V8 ENHANCED' : 'CURRENT ENGINE'));
                }
            } catch (e) {
                console.error('Failed to switch engine:', e);
            }
        }
        
        function updateUI() {
            document.getElementById('btn-current').classList.toggle('active', currentEngine === 'current');
            document.getElementById('btn-v8').classList.toggle('active', currentEngine === 'v8_enhanced');
            document.getElementById('active-engine').textContent = currentEngine === 'v8_enhanced' ? 'V8 ENHANCED' : 'CURRENT ENGINE';
        }
        
        function showNotification(msg) {
            const notification = document.createElement('div');
            notification.style.cssText = 'position:fixed;top:20px;right:20px;background:linear-gradient(135deg,#c0c0c0,#fff);color:#0d0d0d;padding:20px 30px;border-radius:10px;font-weight:900;z-index:9999;box-shadow:0 0 30px rgba(192,192,192,0.6);';
            notification.textContent = msg;
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 3000);
        }
        
        async function loadData() {
            try {
                const v8Res = await fetch('/api/v8_enhanced_status');
                const v8Data = await v8Res.json();
                document.getElementById('base-wr').textContent = v8Data.base_wr + '%';
                document.getElementById('expected-wr').textContent = v8Data.expected_wr + '%+';
                
                const liqRes = await fetch('/api/liquidation_heatmap_data');
                const liqData = await liqRes.json();
                document.getElementById('liq-total').textContent = liqData.total_liquidations.toLocaleString();
                document.getElementById('liq-volume').textContent = liqData.total_volume.toFixed(2) + ' BTC';
                document.getElementById('liq-long').textContent = liqData.long_liquidations.toLocaleString();
                document.getElementById('liq-short').textContent = liqData.short_liquidations.toLocaleString();
                
                const engineRes = await fetch('/api/engine/current');
                const engineData = await engineRes.json();
                currentEngine = engineData.engine;
                updateUI();
            } catch (e) {
                console.error('Failed to load data:', e);
            }
        }
        
        loadData();
        setInterval(loadData, 30000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%); color: #fff; font-family: Arial; padding: 20px; }
        .header { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { color: #00ff88; }
        .logout-btn { background: #ef4444; padding: 10px 20px; border: none; color: #fff; border-radius: 5px; cursor: pointer; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .panel { background: rgba(255,255,255,0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(0,255,136,0.3); }
        .panel h2 { color: #00ff88; margin-bottom: 15px; font-size: 1.2em; }
        .engine-selector { display: flex; gap: 10px; margin: 15px 0; }
        .engine-btn { padding: 15px 30px; border: 2px solid #00ff88; background: transparent; color: #fff; cursor: pointer; border-radius: 5px; font-size: 1em; transition: all 0.3s; }
        .engine-btn.active { background: #00ff88; color: #0a0e27; font-weight: bold; }
        .engine-btn:hover { transform: scale(1.05); }
        .stat { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .stat-value { color: #00ff88; font-weight: bold; }
        .status-badge { display: inline-block; padding: 5px 15px; background: #00ff88; color: #0a0e27; border-radius: 20px; font-weight: bold; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        iframe { width: 100%; height: 600px; border: 1px solid rgba(0,255,136,0.3); border-radius: 10px; background: #000; }
        .heatmap-container { grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Admin Dashboard - V8 Enhanced</h1>
        <button class="logout-btn" onclick="location.href='/logout'">Logout</button>
    </div>
    
    <div class="grid">
        <div class="panel">
            <h2>⚡ Engine Selector</h2>
            <p style="color: #888; margin-bottom: 10px;">Select active trading engine (switches in real-time):</p>
            <div class="engine-selector">
                <button class="engine-btn" id="btn-current" onclick="switchEngine('current')">Current Engine</button>
                <button class="engine-btn" id="btn-v8" onclick="switchEngine('v8_enhanced')">V8 Enhanced</button>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: rgba(0,255,136,0.1); border-radius: 5px;">
                <div style="font-size: 0.9em; color: #888;">Active Engine:</div>
                <div id="active-engine" style="font-size: 1.5em; color: #00ff88; font-weight: bold; margin-top: 5px;">Loading...</div>
            </div>
        </div>
        
        <div class="panel">
            <h2>📊 V8 Enhanced Status</h2>
            <div class="stat">
                <span>Base Win Rate</span>
                <span class="stat-value" id="base-wr">83.82%</span>
            </div>
            <div class="stat">
                <span>Expected Win Rate</span>
                <span class="stat-value" id="expected-wr">90%+</span>
            </div>
            <div class="stat">
                <span>Auto-Optimization</span>
                <span class="status-badge">ACTIVE</span>
            </div>
            <div class="stat">
                <span>Liquidation Boost</span>
                <span class="status-badge">ENABLED</span>
            </div>
        </div>
        
        <div class="panel">
            <h2>🔥 Liquidation Data</h2>
            <div class="stat">
                <span>Total Events</span>
                <span class="stat-value" id="liq-total">Loading...</span>
            </div>
            <div class="stat">
                <span>Total Volume</span>
                <span class="stat-value" id="liq-volume">Loading...</span>
            </div>
            <div class="stat">
                <span>Long Liquidations</span>
                <span class="stat-value" id="liq-long">Loading...</span>
            </div>
            <div class="stat">
                <span>Short Liquidations</span>
                <span class="stat-value" id="liq-short">Loading...</span>
            </div>
        </div>
        
        <div class="panel">
            <h2>💡 V8 Enhanced Features</h2>
            <div style="font-size: 0.9em; line-height: 1.8;">
                ✓ V8 Base Model (83.82% WR)<br>
                ✓ Auto-Optimization (900+ tests)<br>
                ✓ Liquidation Proximity Detection<br>
                ✓ Dynamic Confidence Boosting (+20%)<br>
                ✓ 24-Hour Re-optimization Cycle
            </div>
        </div>
        
        <div class="panel heatmap-container">
            <h2>📈 Interactive Liquidation Heatmap</h2>
            <iframe src="/heatmap"></iframe>
        </div>
    </div>
    
    <script>
        let currentEngine = 'current';
        
        async function switchEngine(engine) {
            try {
                const response = await fetch('/api/engine/switch', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({engine: engine})
                });
                const data = await response.json();
                
                if (data.status === 'ok') {
                    currentEngine = engine;
                    updateUI();
                    alert('✅ Engine switched to: ' + (engine === 'v8_enhanced' ? 'V8 Enhanced' : 'Current Engine'));
                }
            } catch (e) {
                console.error('Failed to switch engine:', e);
            }
        }
        
        function updateUI() {
            document.getElementById('btn-current').classList.toggle('active', currentEngine === 'current');
            document.getElementById('btn-v8').classList.toggle('active', currentEngine === 'v8_enhanced');
            document.getElementById('active-engine').textContent = currentEngine === 'v8_enhanced' ? 'V8 Enhanced' : 'Current Engine';
        }
        
        async function loadData() {
            try {
                // Load V8 status
                const v8Res = await fetch('/api/v8_enhanced_status');
                const v8Data = await v8Res.json();
                document.getElementById('base-wr').textContent = v8Data.base_wr + '%';
                document.getElementById('expected-wr').textContent = v8Data.expected_wr + '%+';
                
                // Load liquidation data
                const liqRes = await fetch('/api/liquidation_heatmap_data');
                const liqData = await liqRes.json();
                document.getElementById('liq-total').textContent = liqData.total_liquidations.toLocaleString();
                document.getElementById('liq-volume').textContent = liqData.total_volume.toFixed(2) + ' BTC';
                document.getElementById('liq-long').textContent = liqData.long_liquidations.toLocaleString();
                document.getElementById('liq-short').textContent = liqData.short_liquidations.toLocaleString();
                
                // Get current engine
                const engineRes = await fetch('/api/engine/current');
                const engineData = await engineRes.json();
                currentEngine = engineData.engine;
                updateUI();
            } catch (e) {
                console.error('Failed to load data:', e);
            }
        }
        
        // Load data on page load
        loadData();
        
        // Auto-refresh every 30 seconds
        setInterval(loadData, 30000);
    </script>
</body>
</html>

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect('/login')
    return render_template_string(DASHBOARD_HTML)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/')
        return "Incorrect Password", 401
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

@app.route('/api/engine/switch', methods=['POST'])
def switch_engine():
    global current_engine
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    engine = data.get('engine')
    
    if engine in ['current', 'v8_enhanced']:
        current_engine = engine
        print(f"🔄 ENGINE SWITCHED TO: {engine.upper()}")
        return jsonify({'status': 'ok', 'engine': engine})
    
    return jsonify({'error': 'Invalid engine'}), 400

@app.route('/api/engine/current')
def get_current_engine():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify({'engine': current_engine})

@app.route('/api/v8_enhanced_status')
def v8_status():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify({
        'base_wr': 83.82,
        'expected_wr': 90.0,
        'auto_optimization': 'active',
        'liquidation_boost': 'enabled',
        'status': 'ready'
    })

@app.route('/api/liquidation_heatmap_data')
def liquidation_data():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        df = pd.read_csv('V9_LIQUIDATION_EXPERIMENT/liquidation_data/REAL_liquidations_continuous.csv')
        return jsonify({
            'total_liquidations': len(df),
            'total_volume': float(df['size'].sum()),
            'long_liquidations': len(df[df['side'] == 'A']),
            'short_liquidations': len(df[df['side'] == 'B'])
        })
    except:
        return jsonify({'total_liquidations': 0, 'total_volume': 0, 'long_liquidations': 0, 'short_liquidations': 0})

@app.route('/heatmap')
def heatmap():
    if not session.get('logged_in'):
        return redirect('/login')
    
    try:
        with open('V9_LIQUIDATION_EXPERIMENT/liquidation_data/interactive_heatmap.html', 'r') as f:
            return f.read()
    except:
        return "Heatmap not available", 404

if __name__ == '__main__':
    print("🚀 SIMPLE ADMIN DASHBOARD STARTING...")
    print("   URL: http://localhost:9000")
    print("   Password: admin")
    print("   Features: Real-time engine switching + Liquidation heatmap")
    app.run(host='0.0.0.0', port=9000, debug=True)
