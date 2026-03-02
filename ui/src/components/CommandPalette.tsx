import { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDevMode } from '../context/DevModeContext';
import { useToast } from '../context/ToastContext';
import type { MouseEvent, KeyboardEvent } from 'react';

export function CommandPalette() {
  const { active, isPaletteOpen, closePalette, addMedia, addDocuments, addBrokers, clear, media, documents, brokers } = useDevMode();
  const toast = useToast();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isPaletteOpen) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [isPaletteOpen]);

  if (!isPaletteOpen) return null;

  const handleOverlayClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) closePalette();
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') closePalette();
    if (e.key !== 'Enter') return;

    const cmd = inputRef.current?.value.trim().toLowerCase() || '';
    closePalette();
    runCommand(cmd);
  };

  const runCommand = (cmd: string) => {
    const mediaMatch = cmd.match(/^create\s+(?:images?|media)\s+(\d+)$/);
    if (mediaMatch) {
      const n = Math.min(parseInt(mediaMatch[1]), 200);
      addMedia(n);
      toast(`Created ${n} dev media item${n !== 1 ? 's' : ''} (total: ${media.length + n})`, 'success');
      navigate('/media');
      return;
    }

    const docMatch = cmd.match(/^create\s+documents?\s+(\d+)$/);
    if (docMatch) {
      const n = Math.min(parseInt(docMatch[1]), 200);
      addDocuments(n);
      toast(`Created ${n} dev document${n !== 1 ? 's' : ''} (total: ${documents.length + n})`, 'success');
      navigate('/documents');
      return;
    }

    const brokerMatch = cmd.match(/^create\s+brokers?\s+(\d+)$/);
    if (brokerMatch) {
      const n = Math.min(parseInt(brokerMatch[1]), 200);
      addBrokers(n);
      toast(`Created ${n} dev broker${n !== 1 ? 's' : ''} (total: ${brokers.length + n})`, 'success');
      navigate('/brokers');
      return;
    }

    if (cmd === 'clear') {
      clear();
      toast('Dev data cleared — back to live mode', 'success');
      return;
    }

    toast(`Unknown command: "${cmd}"`, 'error');
  };

  return (
    <div className="cmd-palette-overlay" onClick={handleOverlayClick}>
      <div className="cmd-palette">
        <div className="cmd-palette-header">
          <span className="cmd-palette-title">Command Palette</span>
          {active && <span className="dev-badge">DEV ACTIVE</span>}
        </div>
        <input
          ref={inputRef}
          className="cmd-palette-input"
          placeholder='Try: "create broker 20" or "create media 30" or "clear"'
          onKeyDown={handleKeyDown}
        />
        <div className="cmd-palette-hint">
          <code>create broker &lt;n&gt;</code> — generate n mock brokers
          <br />
          <code>create media &lt;n&gt;</code> — generate n mock media items
          <br />
          <code>create document &lt;n&gt;</code> — generate n mock documents
          <br />
          <code>clear</code> — remove all dev data &amp; exit dev mode
          <br />
          Press <kbd>Enter</kbd> to run &nbsp;·&nbsp; <kbd>Esc</kbd> to close
        </div>
      </div>
    </div>
  );
}
