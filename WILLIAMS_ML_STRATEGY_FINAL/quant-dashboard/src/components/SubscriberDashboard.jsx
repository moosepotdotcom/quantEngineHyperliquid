import React, { useState } from 'react';
import axios from 'axios';
import { LogOut, TrendingUp, ShieldCheck, Activity, Save, Key } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API_URL = 'http://localhost:8000';

const SubscriberDashboard = () => {
    const navigate = useNavigate();
    const [config, setConfig] = useState({ wallet_address: '', api_key: '', risk_multiplier: 1.0 });
    const [status, setStatus] = useState('');

    const handleLogout = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('role');
        navigate('/login');
    };

    const handleSaveConfig = async (e) => {
        e.preventDefault();
        const token = localStorage.getItem('token');
        try {
            await axios.post(`${API_URL}/saas/configure`, config, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setStatus('success');
            setTimeout(() => setStatus(''), 3000);
        } catch (err) {
            setStatus('error');
        }
    };

    return (
        <div className="min-h-screen bg-slate-900 text-white font-sans p-6">
            {/* Header */}
            <header className="flex justify-between items-center mb-10 pb-6 border-b border-slate-700">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                        <TrendingUp size={24} className="text-white" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-teal-400">
                            Subscriber Portal
                        </h1>
                        <p className="text-xs text-slate-400">Williams %R Strategy Access</p>
                    </div>
                </div>
                <button
                    onClick={handleLogout}
                    className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg transition-colors border border-slate-700"
                >
                    <LogOut size={16} />
                    <span>Sign Out</span>
                </button>
            </header>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

                {/* Status Card */}
                <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl hover:bg-slate-800 transition-all">
                    <div className="flex justify-between mb-4">
                        <h3 className="text-slate-400 font-medium">Subscription Status</h3>
                        <ShieldCheck className="text-emerald-400" />
                    </div>
                    <div className="text-3xl font-bold text-emerald-400 mb-1">Active</div>
                    <p className="text-sm text-slate-500">Next billing: Feb 21, 2026</p>
                </div>

                {/* Performance Card */}
                <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl hover:bg-slate-800 transition-all">
                    <div className="flex justify-between mb-4">
                        <h3 className="text-slate-400 font-medium">Strategy Performance</h3>
                        <Activity className="text-blue-400" />
                    </div>
                    <div className="text-3xl font-bold text-white mb-1">+79.6%</div>
                    <p className="text-sm text-slate-500">All-time Win Rate</p>
                </div>

                {/* Copy Trading Settings */}
                <div className="bg-gradient-to-br from-indigo-900/40 to-slate-900 border border-indigo-500/30 p-6 rounded-xl relative overflow-hidden">
                    <div className="relative z-10">
                        <h3 className="text-indigo-300 font-bold text-lg mb-4 flex items-center gap-2">
                            <Key size={18} /> Copy Trading Setup
                        </h3>

                        <form onSubmit={handleSaveConfig} className="space-y-4">
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">Hyperliquid API Wallet</label>
                                <input
                                    type="text"
                                    value={config.wallet_address}
                                    onChange={(e) => setConfig({ ...config, wallet_address: e.target.value })}
                                    className="w-full bg-slate-800/50 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none font-mono"
                                    placeholder="0x..."
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">API Private Key (Non-Custodial)</label>
                                <input
                                    type="password"
                                    value={config.api_key}
                                    onChange={(e) => setConfig({ ...config, api_key: e.target.value })}
                                    className="w-full bg-slate-800/50 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none font-mono"
                                    placeholder="0x..."
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-slate-400 mb-1">Risk Multiplier (0.1 - 2.0)</label>
                                <input
                                    type="number" step="0.1" min="0.1" max="2.0"
                                    value={config.risk_multiplier}
                                    onChange={(e) => setConfig({ ...config, risk_multiplier: parseFloat(e.target.value) })}
                                    className="w-full bg-slate-800/50 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:border-indigo-500 outline-none font-mono"
                                />
                            </div>

                            <button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 rounded-lg transition-colors flex justify-center items-center gap-2">
                                <Save size={16} /> Save Configuration
                            </button>

                            {status === 'success' && <p className="text-green-400 text-xs text-center font-bold">Configuration Saved!</p>}
                            {status === 'error' && <p className="text-red-400 text-xs text-center font-bold">Save Failed</p>}
                        </form>
                    </div>
                </div>

            </div>

            <div className="mt-8 text-center text-slate-600 text-sm">
                <p>Quant Engine SaaS v1.0 • Secure Connection</p>
            </div>
        </div>
    );
};

export default SubscriberDashboard;
