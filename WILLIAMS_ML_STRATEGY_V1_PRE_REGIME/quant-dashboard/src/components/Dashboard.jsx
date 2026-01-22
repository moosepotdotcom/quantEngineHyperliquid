import { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, TrendingUp, TrendingDown, DollarSign, Wallet, ShieldCheck, Zap, RefreshCw, XCircle, Power, Settings } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import ConfirmationModal from './ConfirmationModal';

const API_URL = 'http://127.0.0.1:8000';

export default function Dashboard() {
    const [marketStatus, setMarketStatus] = useState([]);
    const [positions, setPositions] = useState({});
    const [account, setAccount] = useState({ mode: 'Loading...', leverage: 3, balance: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Modal State
    const [modal, setModal] = useState({ isOpen: false, title: '', message: '', onConfirm: () => { }, isDanger: false });
    const closeModal = () => setModal(prev => ({ ...prev, isOpen: false }));

    const fetchData = async () => {
        try {
            const statusRes = await axios.get(`${API_URL}/status`);
            const posRes = await axios.get(`${API_URL}/positions`);

            // New format: { "market": [...], "account": {...} }
            if (statusRes.data.account) {
                setMarketStatus(statusRes.data.market);
                setAccount(statusRes.data.account);
            } else {
                // Fallback for old format if API hasn't restarted yet
                setMarketStatus(statusRes.data);
            }

            setPositions(posRes.data);
            setError(null);
        } catch (err) {
            console.error("Fetch Error:", err);
            setError("API Offline - Is api.py running?");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 2000);
        return () => clearInterval(interval);
    }, []);

    // --- Actions ---

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        return { headers: { Authorization: `Bearer ${token}` } };
    };

    const toggleMode = () => {
        const newMode = account.mode === 'LIVE' ? 'PAPER' : 'LIVE';
        setModal({
            isOpen: true,
            title: `Switch to ${newMode} Mode?`,
            message: `This will reset the local strategy state. ${newMode === 'LIVE' ? 'Real trades will be executed.' : 'Trading will be simulated.'}`,
            isDanger: newMode === 'LIVE',
            onConfirm: async () => {
                try {
                    await axios.post(`${API_URL}/settings/mode`, { mode: newMode }, getAuthHeaders());
                    fetchData();
                } catch (e) {
                    if (e.response?.status === 401) alert("Unauthorized: Please Login Again");
                    else alert("Failed to switch mode");
                }
            }
        });
    };

    const changeLeverage = async (e) => {
        const lev = parseInt(e.target.value);
        try {
            await axios.post(`${API_URL}/settings/leverage`, { leverage: lev }, getAuthHeaders());
            setAccount(prev => ({ ...prev, leverage: lev }));
        } catch (e) {
            if (e.response?.status === 401) alert("Unauthorized: Please Login Again");
            else alert("Failed to set leverage");
        }
    };

    // Helper for manual close actions
    const closePosition = (coin) => {
        setModal({
            isOpen: true,
            title: `Close ${coin}?`,
            message: "Are you sure you want to manually close this position?",
            isDanger: true,
            onConfirm: async () => {
                try {
                    await axios.post(`${API_URL}/trade/close/${coin}`, {}, getAuthHeaders());
                    fetchData();
                } catch (e) {
                    if (e.response?.status === 401) alert("Unauthorized: Please Login Again");
                    else alert("Close failed");
                }
            }
        });
    };

    // Helper for panic close
    const closeAll = () => {
        setModal({
            isOpen: true,
            title: "PANIC CLOSE ALL?",
            message: "This will immediately market close ALL open positions. Use only in emergencies.",
            isDanger: true,
            onConfirm: async () => {
                try {
                    await axios.post(`${API_URL}/trade/close-all`, {}, getAuthHeaders());
                    fetchData();
                } catch (e) {
                    if (e.response?.status === 401) alert("Unauthorized: Please Login Again");
                    else alert("Close All failed");
                }
            }
        });
    };

    // --- UI Logic ---
    const [activeTab, setActiveTab] = useState('control');
    const [subscribers, setSubscribers] = useState([]);

    const fetchSubscribers = async () => {
        try {
            const res = await axios.get(`${API_URL}/saas/subscribers`, getAuthHeaders());
            setSubscribers(res.data);
        } catch (e) { console.error("Failed to fetch subs"); }
    };

    // Auto-fetch subs when entering users tab
    useEffect(() => {
        if (activeTab === 'users') fetchSubscribers();
    }, [activeTab]);

    const removeSubscriber = (userId) => {
        setModal({
            isOpen: true,
            title: `Kick User ${userId}?`,
            message: "They will immediately stop copying new trades. Existing trades may remain open.",
            isDanger: true,
            onConfirm: async () => {
                try {
                    await axios.delete(`${API_URL}/saas/subscriber/${userId}`, getAuthHeaders());
                    fetchSubscribers();
                } catch (e) { alert("Failed to remove user"); }
            }
        });
    };

    // --- History Logic ---
    const [history, setHistory] = useState({ data: [], total: 0, page: 1, pages: 1 });
    const [historyPage, setHistoryPage] = useState(1);

    const fetchHistory = async (page = 1) => {
        try {
            const res = await axios.get(`${API_URL}/history?page=${page}&limit=10`);
            setHistory(res.data);
            setHistoryPage(page);
        } catch (e) { console.error("Failed to fetch history"); }
    };

    useEffect(() => {
        if (activeTab === 'history') fetchHistory(historyPage);
    }, [activeTab, historyPage]);

    return (
        <div className="min-h-screen bg-slate-900 text-white p-6 font-sans">
            {/* Header */}
            <header className="mb-6 flex flex-col md:flex-row justify-between items-center bg-slate-800 p-4 rounded-xl border border-slate-700 shadow-lg gap-4">
                <div>
                    <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent flex items-center gap-2">
                        <Activity className="text-blue-400" /> Quant Engine V1
                    </h1>
                    {/* Tab Nav */}
                    <div className="flex gap-4 mt-2">
                        <button
                            onClick={() => setActiveTab('control')}
                            className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded transition-colors ${activeTab === 'control' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
                        >
                            Command Center
                        </button>
                        <button
                            onClick={() => setActiveTab('users')}
                            className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded transition-colors ${activeTab === 'users' ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-white'}`}
                        >
                            User Management
                        </button>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* Mode Toggle */}
                    <div className="flex items-center gap-2 bg-slate-900 p-1.5 rounded-lg border border-slate-700">
                        <span className={`text-xs font-bold px-3 py-1 rounded-md transition-colors ${account.mode === 'PAPER' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-500'}`}>PAPER</span>
                        <button
                            onClick={toggleMode}
                            className={`w-12 h-6 rounded-full p-1 transition-colors ${account.mode === 'LIVE' ? 'bg-red-500' : 'bg-blue-500'}`}
                        >
                            <div className={`w-4 h-4 bg-white rounded-full shadow-sm transition-transform ${account.mode === 'LIVE' ? 'translate-x-6' : 'translate-x-0'}`} />
                        </button>
                        <span className={`text-xs font-bold px-3 py-1 rounded-md transition-colors ${account.mode === 'LIVE' ? 'bg-red-500/20 text-red-500 animate-pulse' : 'text-slate-500'}`}>LIVE</span>
                    </div>

                    <StatusBadge status={error ? 'offline' : 'online'} />
                </div>
            </header>

            {activeTab === 'control' ? (
                <>
                    {/* Control Deck */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                        <StatCard title="Balance" value={`$${account.balance?.toLocaleString()}`} icon={<DollarSign className="text-green-400" />} subtext={account.mode === 'PAPER' ? 'Simulated Funds' : 'Real Capital'} />

                        {/* Interactive Leverage Card */}
                        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 relative group">
                            <div className="flex justify-between items-start mb-2">
                                <div className="text-slate-400 text-sm font-medium">Leverage</div>
                                <Zap className="text-yellow-400 w-5 h-5" />
                            </div>
                            <div className="text-2xl font-bold text-white mb-1 flex items-center gap-2">
                                {account.leverage}x
                                <span className="text-xs font-normal text-slate-500 bg-slate-900 px-2 py-0.5 rounded">Risk: {account.leverage * 2}%</span>
                            </div>
                            <input
                                type="range" min="1" max="50" value={account.leverage}
                                onChange={changeLeverage}
                                className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-yellow-400 mt-2"
                            />
                        </div>

                        <StatCard title="Active Trades" value={Object.keys(positions).length.toString()} icon={<Activity className="text-blue-400" />} subtext="Auto-Execution" />

                        {/* Panic Button Area */}
                        <div className="bg-slate-800 p-5 rounded-xl border border-red-900/30 flex flex-col justify-center items-center gap-2 hover:bg-red-900/10 transition-colors cursor-pointer" onClick={closeAll}>
                            <Power className="text-red-500 w-8 h-8" />
                            <span className="text-red-400 font-bold text-sm tracking-wider">PANIC CLOSE ALL</span>
                        </div>
                    </div>

                    {/* Main Content */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                        {/* Market Scanner */}
                        <div className="lg:col-span-2 bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-lg">
                            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                <Activity className="w-5 h-5 text-blue-400" /> Live Market Scanner (5m)
                            </h2>

                            {loading ? (
                                <div className="text-center py-10 text-slate-500 animate-pulse">Connecting to Neural Core...</div>
                            ) : error ? (
                                <div className="text-center py-10 text-red-400 font-mono bg-red-900/10 rounded-lg border border-red-900/20">{error}</div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead>
                                            <tr className="text-slate-400 border-b border-slate-700 text-xs uppercase tracking-wider">
                                                <th className="pb-3 px-4">Coin</th>
                                                <th className="pb-3 px-4 text-right">Price</th>
                                                <th className="pb-3 px-4 text-right">Williams %R</th>
                                                <th className="pb-3 px-4 text-right">ML Conf</th>
                                                <th className="pb-3 px-4 text-center">Status</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-slate-700">
                                            {marketStatus.map((coin) => (
                                                <MarketRow key={coin.coin} data={coin} />
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>

                        {/* Active Positions */}
                        <div className="space-y-6">
                            <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-lg h-full flex flex-col">
                                <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                                    <Wallet className="w-5 h-5 text-green-400" /> Active Positions
                                </h2>
                                {Object.keys(positions).length === 0 ? (
                                    <div className="text-center py-12 text-slate-500 flex-1 flex flex-col items-center justify-center gap-2">
                                        <RefreshCw className="w-8 h-8 opacity-20" />
                                        <span>No active trades. Scanning...</span>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {Object.entries(positions).map(([coin, pos]) => (
                                            <PositionCard key={coin} coin={coin} pos={pos} onClose={() => closePosition(coin)} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </>
            ) : (
                <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 shadow-lg">
                    <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        <ShieldCheck className="w-5 h-5 text-emerald-400" /> Active Subscribers ({subscribers.length})
                    </h2>

                    <div className="overflow-x-auto">
                        <table className="w-full text-left text-sm">
                            <thead>
                                <tr className="text-slate-400 border-b border-slate-700 uppercase tracking-wider text-xs">
                                    <th className="pb-3 px-4">User ID</th>
                                    <th className="pb-3 px-4">Wallet</th>
                                    <th className="pb-3 px-4 text-right">Risk</th>
                                    <th className="pb-3 px-4 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-700">
                                {subscribers.map(sub => (
                                    <tr key={sub.user_id} className="hover:bg-slate-700/30">
                                        <td className="py-4 px-4 font-mono text-white">{sub.user_id}</td>
                                        <td className="py-4 px-4 font-mono text-slate-400">{sub.wallet}</td>
                                        <td className="py-4 px-4 font-mono text-right text-blue-400">{sub.risk}x</td>
                                        <td className="py-4 px-4 text-right">
                                            <button
                                                onClick={() => removeSubscriber(sub.user_id)}
                                                className="text-red-400 hover:text-red-300 font-bold text-xs bg-red-500/10 hover:bg-red-500/20 px-3 py-1.5 rounded transition-colors"
                                            >
                                                KICK
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        {subscribers.length === 0 && (
                            <div className="text-center py-10 text-slate-500">No active subscribers found.</div>
                        )}
                    </div>
                </div>
            )}

            <ConfirmationModal
                isOpen={modal.isOpen}
                onClose={closeModal}
                onConfirm={modal.onConfirm}
                title={modal.title}
                message={modal.message}
                isDanger={modal.isDanger}
            />
        </div>
    );
}

// --- Sub Components ---

function StatCard({ title, value, icon, subtext }) {
    return (
        <div className="bg-slate-800 p-5 rounded-xl border border-slate-700 hover:border-slate-600 transition-all hover:translate-y-[-2px] hover:shadow-xl">
            <div className="flex justify-between items-start mb-2">
                <div className="text-slate-400 text-sm font-medium uppercase tracking-wide">{title}</div>
                {icon}
            </div>
            <div className="text-2xl font-bold text-white mb-1">{value}</div>
            <div className="text-xs text-slate-500">{subtext}</div>
        </div>
    );
}

function MarketRow({ data }) {
    const isLong = data.signal === 'LONG';
    const isShort = data.signal === 'SHORT';
    const isSignal = isLong || isShort;

    let wrClass = "text-slate-400";
    if (data.wr > -20) wrClass = "text-green-400 font-bold";
    if (data.wr < -80) wrClass = "text-red-400 font-bold";

    let confClass = "text-slate-500";
    if (data.conf > 0.65) confClass = "text-green-400 font-bold";
    else if (data.conf > 0.5) confClass = "text-yellow-400";

    return (
        <tr className="hover:bg-slate-700/30 transition-colors group">
            <td className="py-3 px-4 font-bold text-slate-200 group-hover:text-white transition-colors">{data.coin}</td>
            <td className="py-3 px-4 text-right font-mono text-slate-300">${data.price?.toLocaleString()}</td>
            <td className={`py-3 px-4 text-right font-mono ${wrClass}`}>{data.wr?.toFixed(1)}</td>
            <td className={`py-3 px-4 text-right font-mono ${confClass}`}>{(data.conf * 100).toFixed(1)}%</td>
            <td className="py-3 px-4 text-center">
                {isSignal ? (
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-bold shadow-sm ${isLong ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'} animate-pulse`}>
                        {isLong ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                        {data.signal}
                    </span>
                ) : (
                    <span className="text-slate-600 text-xs font-medium">WAIT</span>
                )}
            </td>
        </tr>
    )
}

function PositionCard({ coin, pos, onClose }) {
    const isLong = pos.type === 'LONG';

    return (
        <div className="bg-slate-700/30 p-4 rounded-xl border border-slate-600 hover:bg-slate-700/50 transition-colors relative group">
            <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                    <span className="font-bold text-lg">{coin}</span>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${isLong ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                        {pos.type}
                    </span>
                </div>
                <button onClick={onClose} className="p-1 hover:bg-red-500/20 rounded text-slate-400 hover:text-red-400 transition-colors" title="Close Position">
                    <XCircle size={18} />
                </button>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-slate-400">
                <div>
                    <div className="mb-0.5">Entry Price</div>
                    <div className="text-slate-200 font-mono">${pos.entry?.toLocaleString()}</div>
                </div>
                <div className="text-right">
                    <div className="mb-0.5">Size</div>
                    <div className="text-slate-200 font-mono">{pos.size?.toFixed(3)} {coin}</div>
                </div>
                <div>
                    <div className="mb-0.5">TP</div>
                    <div className="text-green-400/80 font-mono">${pos.tp?.toLocaleString()}</div>
                </div>
                <div className="text-right">
                    <div className="mb-0.5">SL</div>
                    <div className="text-red-400/80 font-mono">${pos.sl?.toLocaleString()}</div>
                </div>
            </div>
        </div>
    )
}

function StatusBadge({ status }) {
    const isOnline = status === 'online';
    return (
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider shadow-sm border ${isOnline ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
            <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
            {isOnline ? 'System Online' : 'System Offline'}
        </div>
    )
}
