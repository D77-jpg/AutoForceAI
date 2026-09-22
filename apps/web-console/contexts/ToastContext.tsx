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
              flex items-center gap-3 px-4 py-3.5 rounded-2xl shadow-popover text-white min-w-[300px] max-w-md
              backdrop-blur-2xl border border-separator
              transition-all duration-300 ease-out transform
              animate-slide-in-right
              ${toast.type === 'success' ? 'bg-surface/95 text-success' : toast.type === 'warning' ? 'bg-surface/95 text-warning' : toast.type === 'info' ? 'bg-surface/95 text-accent' : 'bg-surface/95 text-danger'}
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
            <span className="flex-1 text-sm font-medium text-text">{toast.message}</span>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-text-secondary hover:text-white hover:bg-text/10 rounded-full p-1 transition-colors"
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
