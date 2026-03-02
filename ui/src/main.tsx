import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import { DevModeProvider } from './context/DevModeContext';
import { ToastProvider } from './context/ToastContext';
import { App } from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <DevModeProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </DevModeProvider>
    </HashRouter>
  </StrictMode>,
);
