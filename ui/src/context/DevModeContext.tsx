import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import type { BrokerListItem, Document, Media } from '../types';

interface DevModeContextValue {
  active: boolean;
  media: Media[];
  documents: Document[];
  brokers: BrokerListItem[];
  promptContent: string;
  isPaletteOpen: boolean;
  addMedia: (n: number) => void;
  addDocuments: (n: number) => void;
  addBrokers: (n: number) => void;
  clear: () => void;
  setPromptContent: (content: string) => void;
  openPalette: () => void;
  closePalette: () => void;
  deleteDocument: (id: string) => void;
  deleteMedia: (id: string) => void;
}

const DevModeContext = createContext<DevModeContextValue>(undefined as unknown as DevModeContextValue);

export function DevModeProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [media, setMedia] = useState<Media[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [brokers, setBrokers] = useState<BrokerListItem[]>([]);
  const [promptContent, setPromptContent] = useState('');
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);

  const addMedia = useCallback((n: number) => {
    setActive(true);
    setMedia((prev) => {
      const base = prev.length;
      const newItems: Media[] = [];
      for (let i = 0; i < n; i++) {
        const idx = base + i;
        const isPdf = idx % 4 === 3;
        newItems.push({
          id: `dev-media-${Date.now()}-${idx}`,
          filename: isPdf
            ? `document_${String(idx + 1).padStart(2, '0')}.pdf`
            : `photo_${String(idx + 1).padStart(2, '0')}.jpg`,
          content_type: isPdf ? 'application/pdf' : 'image/jpeg',
          file_size_bytes: isPdf ? 2048000 + idx * 51337 : 512000 + idx * 31337,
          description: isPdf
            ? `Dev PDF #${idx + 1} — sample document for layout testing`
            : `Dev image #${idx + 1} — sample photograph for layout testing`,
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

  const addBrokers = useCallback((n: number) => {
    const NAMES = [
      'Ana Lima', 'Carlos Souza', 'Beatriz Nunes', 'Diego Ferreira', 'Fernanda Costa',
      'Gustavo Alves', 'Helena Martins', 'Igor Pereira', 'Juliana Rocha', 'Lucas Carvalho',
      'Mariana Dias', 'Olivia Santos', 'Paulo Ribeiro', 'Renata Gomes',
    ];
    setActive(true);
    setBrokers((prev) => {
      const base = prev.length;
      const now = Date.now();
      const newItems: BrokerListItem[] = [];
      for (let i = 0; i < n; i++) {
        const idx = base + i;
        const name = NAMES[idx % NAMES.length] + (idx >= NAMES.length ? ` ${Math.floor(idx / NAMES.length) + 1}` : '');
        const joined = new Date(now - Math.floor(Math.random() * 90 * 24 * 3600 * 1000));
        const lastMsg = new Date(joined.getTime() + Math.floor(Math.random() * 30 * 24 * 3600 * 1000));
        newItems.push({
          phone_number: `dev-${Date.now()}-${idx}`,
          name,
          interactions: Math.floor(Math.random() * 200) + 1,
          date_joined: joined.toISOString(),
          last_message_at: lastMsg.toISOString(),
          sold_delpro_product: Math.random() > 0.7,
        });
      }
      return [...prev, ...newItems];
    });
  }, []);

  const clear = useCallback(() => {
    setActive(false);
    setMedia([]);
    setDocuments([]);
    setBrokers([]);
    setPromptContent('');
  }, []);

  const deleteDocument = useCallback((id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  }, []);

  const deleteMedia = useCallback((id: string) => {
    setMedia((prev) => prev.filter((i) => i.id !== id));
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
        media,
        documents,
        brokers,
        promptContent,
        isPaletteOpen,
        addMedia,
        addDocuments,
        addBrokers,
        clear,
        setPromptContent,
        openPalette,
        closePalette,
        deleteDocument,
        deleteMedia,
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
