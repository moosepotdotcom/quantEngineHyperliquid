import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

const ConfirmationModal = ({ isOpen, onClose, onConfirm, title, message, isDanger = false }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm bg-black/40 animate-in fade-in duration-200">
            <div
                className="bg-slate-900/90 border border-slate-700 rounded-2xl shadow-2xl max-w-md w-full p-6 relative transform transition-all scale-100 ring-1 ring-white/10"
                onClick={(e) => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-slate-400 hover:text-white transition-colors"
                >
                    <X size={20} />
                </button>

                <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-full ${isDanger ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'}`}>
                        <AlertTriangle size={24} />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
                        <p className="text-slate-400 text-sm leading-relaxed mb-6">
                            {message}
                        </p>
                    </div>
                </div>

                <div className="flex items-center justify-end gap-3 mt-2">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg text-slate-300 font-medium hover:bg-slate-800 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={() => { onConfirm(); onClose(); }}
                        className={`px-6 py-2 rounded-lg font-bold text-white shadow-lg transition-all transform hover:scale-105 ${isDanger
                                ? 'bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500'
                                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500'
                            }`}
                    >
                        Confirm
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;
