import { useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDevMode } from '../context/DevModeContext';
import { useToast } from '../context/ToastContext';
import type { MouseEvent, KeyboardEvent } from 'react';

export function CommandPalette() {
  const { active, isPaletteOpen, closePalette, addImages, addDocuments, clear, images, documents } = useDevMode();
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
    const imgMatch = cmd.match(/^create\s+images?\s+(\d+)$/);
    if (imgMatch) {
      const n = Math.min(parseInt(imgMatch[1]), 200);
      addImages(n);
      toast(`Created ${n} dev image${n !== 1 ? 's' : ''} (total: ${images.length + n})`, 'success');
      navigate('/images');
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
          placeholder='Try: "create image 30" or "create document 15" or "clear"'
          onKeyDown={handleKeyDown}
        />
        <div className="cmd-palette-hint">
          <code>create image &lt;n&gt;</code> — generate n mock images
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
