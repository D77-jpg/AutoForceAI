"use client";
import React, { createContext, useContext, useState, useCallback } from 'react';
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextType {
  showToast: (message: string, type: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = useCallback((message: string, type: ToastType) => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    
    // 3秒后自动消失
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const removeToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-3 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`
              pointer-events-auto
              flex items-center gap-3 px-4 py-3.5 rounded-2xl shadow-apple-lg text-white min-w-[300px] max-w-md
              backdrop-blur-2xl border border-white/10
              transition-all duration-300 ease-out transform
              animate-slide-in-right
              ${toast.type === 'success' ? 'bg-[#1c1c1e]/95 text-[#30d158]' : toast.type === 'warning' ? 'bg-[#1c1c1e]/95 text-[#ffd60a]' : toast.type === 'info' ? 'bg-[#1c1c1e]/95 text-[#0a84ff]' : 'bg-[#1c1c1e]/95 text-[#ff453a]'}
            `}
            role="alert"
          >
            {toast.type === 'success' ? (
              <CheckCircle size={20} />
            ) : toast.type === 'warning' ? (
              <AlertTriangle size={20} />
            ) : toast.type === 'info' ? (
              <Info size={20} />
            ) : (
              <AlertCircle size={20} />
            )}
            <span className="flex-1 text-sm font-medium text-[#f5f5f7]">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-[#86868b] hover:text-white hover:bg-white/10 rounded-full p-1 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
