import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { Document, Image } from '../types';

interface DevModeContextValue {
  active: boolean;
  images: Image[];
  documents: Document[];
  promptContent: string;
  isPaletteOpen: boolean;
  addImages: (n: number) => void;
  addDocuments: (n: number) => void;
  clear: () => void;
  setPromptContent: (content: string) => void;
  openPalette: () => void;
  closePalette: () => void;
  deleteDocument: (id: string) => void;
  deleteImage: (id: string) => void;
}

const DevModeContext = createContext<DevModeContextValue>(undefined as unknown as DevModeContextValue);

export function DevModeProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [images, setImages] = useState<Image[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [promptContent, setPromptContent] = useState('');
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);

  const addImages = useCallback((n: number) => {
    setActive(true);
    setImages((prev) => {
      const base = prev.length;
      const newItems: Image[] = [];
      for (let i = 0; i < n; i++) {
        const idx = base + i;
        newItems.push({
          id: `dev-img-${Date.now()}-${idx}`,
          filename: `photo_${String(idx + 1).padStart(2, '0')}.jpg`,
          content_type: 'image/jpeg',
          file_size_bytes: 512000 + idx * 31337,
          description: `Dev image #${idx + 1} — sample photograph for layout testing`,
          created_at: new Date(Date.now() - idx * 3600 * 1000).toISOString(),
        });
      }
      return [...prev, ...newItems];
    });
  }, []);

  const addDocuments = useCallback((n: number) => {
    setActive(true);
    setDocuments((prev) => {
      const base = prev.length;
      const newItems: Document[] = [];
      for (let i = 0; i < n; i++) {
        const idx = base + i;
        const isPdf = idx % 3 !== 0;
        newItems.push({
          id: `dev-doc-${Date.now()}-${idx}`,
          filename: isPdf
            ? `document_${String(idx + 1).padStart(2, '0')}.pdf`
            : `notes_${String(idx + 1).padStart(2, '0')}.txt`,
          content_type: isPdf ? 'application/pdf' : 'text/plain',
          file_size_bytes: 204800 + idx * 12345,
          chunk_count: 4 + (idx % 7),
          upload_date: new Date(Date.now() - idx * 7200 * 1000).toISOString(),
        });
      }
      return [...prev, ...newItems];
    });
  }, []);

  const clear = useCallback(() => {
    setActive(false);
    setImages([]);
    setDocuments([]);
    setPromptContent('');
  }, []);

  const deleteDocument = useCallback((id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const deleteImage = useCallback((id: string) => {
    setImages((prev) => prev.filter((i) => i.id !== id));
  }, []);

  const openPalette = useCallback(() => setIsPaletteOpen(true), []);
  const closePalette = useCallback(() => setIsPaletteOpen(false), []);

  // Keystroke listener for /dev sequence
  const seqRef = useRef('');
  const seqTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.matches('input, textarea, select, [contenteditable]')) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key.length !== 1) {
        seqRef.current = '';
        return;
      }
      seqRef.current += e.key;
      clearTimeout(seqTimerRef.current);
      seqTimerRef.current = setTimeout(() => {
        seqRef.current = '';
      }, 1000);
      if (seqRef.current.endsWith('/dev')) {
        seqRef.current = '';
        clearTimeout(seqTimerRef.current);
        setIsPaletteOpen(true);
      }
    };

    document.addEventListener('keydown', handler);
    return () => {
      document.removeEventListener('keydown', handler);
      clearTimeout(seqTimerRef.current);
    };
  }, []);

  return (
    <DevModeContext.Provider
      value={{
        active,
        images,
        documents,
        promptContent,
        isPaletteOpen,
        addImages,
        addDocuments,
        clear,
        setPromptContent,
        openPalette,
        closePalette,
        deleteDocument,
        deleteImage,
      }}
    >
      {children}
    </DevModeContext.Provider>
  );
}

export function useDevMode() {
  const ctx = useContext(DevModeContext);
  if (!ctx) throw new Error('useDevMode must be used within DevModeProvider');
  return ctx;
}
