#!/usr/bin/env python3
"""
MANDALORIANBOX - Command Center
V8 Enhanced + Liquidation Heatmap
"This is the Way"
"""

from flask import Flask, render_template_string, jsonify, request, session, redirect
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "mandalorianbox_beskar_key"

# Global state
current_engine = "current"
ADMIN_PASSWORD = "admin"

# HTML Templates
LOGIN_HTML = open('templates/mandalorian_login.html', 'r').read() if os.path.exists('templates/mandalorian_login.html') else """
<!DOCTYPE html>
<html><head><title>MandalorianBox</title></head>
<body style="background:#0d0d0d;color:#c0c0c0;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
<div style="background:rgba(26,26,46,0.95);padding:60px;border-radius:20px;border:2px solid #c0c0c0;text-align:center;">
<h1 style="color:#c0c0c0;">⚔️ MANDALORIANBOX ⚔️</h1>
<p style="font-style:italic;">"This is the Way"</p>
<form method="POST">
<input type="password" name="password" placeholder="Access Code" required style="padding:15px;margin:20px 0;width:300px;border:2px solid #c0c0c0;background:rgba(0,0,0,0.5);color:#c0c0c0;border-radius:10px;">
<br><button type="submit" style="padding:15px 40px;background:linear-gradient(135deg,#c0c0c0,#fff);border:none;color:#0d0d0d;font-weight:900;cursor:pointer;border-radius:10px;">⚡ ENTER ⚡</button>
</form></div></body></html>
"""

DASHBOARD_HTML = open('templates/mandalorian_dashboard.html', 'r').read() if os.path.exists('templates/mandalorian_dashboard.html') else """
<!DOCTYPE html>
<html><head><title>MandalorianBox - Command Center</title>
<style>
body{background:linear-gradient(135deg,#0d0d0d,#1a1a2e,#16213e);color:#c0c0c0;font-family:Arial;padding:20px;min-height:100vh;}
.header{background:rgba(26,26,46,0.95);padding:25px;border-radius:15px;margin-bottom:25px;display:flex;justify-content:space-between;align-items:center;border:2px solid #c0c0c0;}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:25px;margin-bottom:25px;}
.panel{background:rgba(26,26,46,0.95);padding:25px;border-radius:15px;border:2px solid #c0c0c0;}
.panel h2{color:#fff;margin-bottom:20px;border-bottom:2px solid #c0c0c0;padding-bottom:10px;}
.engine-btn{flex:1;padding:20px;border:2px solid #c0c0c0;background:rgba(0,0,0,0.3);color:#c0c0c0;cursor:pointer;border-radius:10px;font-weight:700;}
.engine-btn.active{background:linear-gradient(135deg,#c0c0c0,#fff);color:#0d0d0d;font-weight:900;}
.stat{display:flex;justify-content:space-between;padding:15px 0;border-bottom:1px solid rgba(192,192,192,0.2);}
.stat-value{color:#fff;font-weight:700;}
.status-badge{padding:6px 15px;background:linear-gradient(135deg,#c0c0c0,#fff);color:#0d0d0d;border-radius:20px;font-weight:900;}
iframe{width:100%;height:700px;border:2px solid #c0c0c0;border-radius:10px;background:#000;}
.heatmap-container{grid-column:1/-1;}
</style></head>
<body>
<div class="header">
<div><h1 style="color:#c0c0c0;">⚔️ MANDALORIANBOX</h1><p style="font-style:italic;opacity:0.8;">"This is the Way"</p></div>
<button onclick="location.href='/logout'" style="background:linear-gradient(135deg,#c0c0c0,#fff);padding:12px 25px;border:none;color:#0d0d0d;border-radius:8px;cursor:pointer;font-weight:700;">⚡ EXIT</button>
</div>
<div class="grid">
<div class="panel">
<h2>⚡ ENGINE SELECTOR</h2>
<p style="color:#888;margin-bottom:15px;">Choose your weapon (real-time switch):</p>
<div style="display:flex;gap:15px;margin:20px 0;">
<button class="engine-btn" id="btn-current" onclick="switchEngine('current')">CURRENT<br>ENGINE</button>
<button class="engine-btn" id="btn-v8" onclick="switchEngine('v8_enhanced')">V8<br>ENHANCED</button>
</div>
<div style="margin-top:20px;padding:20px;background:rgba(192,192,192,0.1);border-radius:10px;">
<div style="font-size:0.8em;color:#888;">Active Weapon System:</div>
<div id="active-engine" style="font-size:1.8em;color:#fff;font-weight:900;margin-top:8px;">Loading...</div>
</div>
</div>
<div class="panel">
<h2>🛡️ V8 ENHANCED STATUS</h2>
<div class="stat"><span>Base Win Rate</span><span class="stat-value" id="base-wr">83.82%</span></div>
<div class="stat"><span>Expected Win Rate</span><span class="stat-value" id="expected-wr">90%+</span></div>
<div class="stat"><span>Auto-Optimization</span><span class="status-badge">ACTIVE</span></div>
<div class="stat"><span>Liquidation Boost</span><span class="status-badge">ENABLED</span></div>
</div>
<div class="panel">
<h2>🔥 LIQUIDATION INTEL</h2>
<div class="stat"><span>Total Events</span><span class="stat-value" id="liq-total">Loading...</span></div>
<div class="stat"><span>Total Volume</span><span class="stat-value" id="liq-volume">Loading...</span></div>
<div class="stat"><span>Long Liquidations</span><span class="stat-value" id="liq-long">Loading...</span></div>
<div class="stat"><span>Short Liquidations</span><span class="stat-value" id="liq-short">Loading...</span></div>
</div>
<div class="panel">
<h2>⚔️ BESKAR FEATURES</h2>
<div style="line-height:2;">
⚔️ V8 Base Model (83.82% WR)<br>
⚔️ Auto-Optimization (900+ tests)<br>
⚔️ Liquidation Proximity Detection<br>
⚔️ Dynamic Confidence Boost (+20%)<br>
⚔️ 24-Hour Re-optimization Cycle
</div>
</div>
<div class="panel heatmap-container">
<h2>📈 TACTICAL HEATMAP</h2>
<iframe src="/heatmap"></iframe>
</div>
</div>
<script>
let currentEngine='current';
async function switchEngine(engine){
try{
const res=await fetch('/api/engine/switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({engine})});
const data=await res.json();
if(data.status==='ok'){currentEngine=engine;updateUI();alert('⚡ Switched to: '+(engine==='v8_enhanced'?'V8 ENHANCED':'CURRENT ENGINE'));}
}catch(e){console.error(e);}
}
function updateUI(){
document.getElementById('btn-current').classList.toggle('active',currentEngine==='current');
document.getElementById('btn-v8').classList.toggle('active',currentEngine==='v8_enhanced');
document.getElementById('active-engine').textContent=currentEngine==='v8_enhanced'?'V8 ENHANCED':'CURRENT ENGINE';
}
async function loadData(){
try{
const v8=await(await fetch('/api/v8_enhanced_status')).json();
document.getElementById('base-wr').textContent=v8.base_wr+'%';
document.getElementById('expected-wr').textContent=v8.expected_wr+'%+';
const liq=await(await fetch('/api/liquidation_heatmap_data')).json();
document.getElementById('liq-total').textContent=liq.total_liquidations.toLocaleString();
document.getElementById('liq-volume').textContent=liq.total_volume.toFixed(2)+' BTC';
document.getElementById('liq-long').textContent=liq.long_liquidations.toLocaleString();
document.getElementById('liq-short').textContent=liq.short_liquidations.toLocaleString();
const eng=await(await fetch('/api/engine/current')).json();
currentEngine=eng.engine;updateUI();
}catch(e){console.error(e);}
}
loadData();setInterval(loadData,30000);
</script>
</body></html>
"""

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
    print("⚔️ MANDALORIANBOX STARTING...")
    print("   URL: http://localhost:9000")
    print("   Password: admin")
    print("   'This is the Way'")
    app.run(host='0.0.0.0', port=9000, debug=False)
