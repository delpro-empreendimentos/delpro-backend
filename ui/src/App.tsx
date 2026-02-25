import { Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { CommandPalette } from './components/CommandPalette';
import { DocumentsPage } from './pages/DocumentsPage';
import { ImagesPage } from './pages/ImagesPage';
import { PromptPage } from './pages/PromptPage';
import './App.css';

export function App() {
  return (
    <>
      <Header />
      <main className="main">
        <Routes>
          <Route path="/" element={<Navigate to="/documents" replace />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="/images" element={<ImagesPage />} />
          <Route path="/prompt" element={<PromptPage />} />
        </Routes>
      </main>
      <CommandPalette />
    </>
  );
}
