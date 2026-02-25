import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { ToastType } from '../types';

interface ToastState {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue>(undefined as unknown as ToastContextValue);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [current, setCurrent] = useState<ToastState | null>(null);
  const counterRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    clearTimeout(timerRef.current);
    const id = ++counterRef.current;
    setCurrent({ id, message, type });
    timerRef.current = setTimeout(() => setCurrent(null), 3000);
  }, []);

  useEffect(() => {
    return () => clearTimeout(timerRef.current);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {current && (
        <div key={current.id} className={`toast ${current.type}`}>
          {current.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx.toast;
}
