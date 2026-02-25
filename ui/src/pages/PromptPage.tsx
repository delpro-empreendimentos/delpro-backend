import { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { useToast } from '../context/ToastContext';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { formatDate } from '../utils';

export function PromptPage() {
  const api = useApi();
  const toast = useToast();
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meta, setMeta] = useState('');
  const originalRef = useRef('');

  const isDirty = content !== originalRef.current;

  useEffect(() => {
    const load = async () => {
      try {
        const data = await api.getPrompt();
        setContent(data.content);
        originalRef.current = data.content;
        setMeta(data.updated_at ? `Last saved: ${formatDate(data.updated_at)}` : 'Not yet saved to database');
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load prompt');
      } finally {
        setLoading(false);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const result = await api.updatePrompt(content.trim());
      toast('Prompt saved!', 'success');
      originalRef.current = result.content;
      setContent(result.content);
      setMeta(result.updated_at ? `Last saved: ${formatDate(result.updated_at)}` : 'Saved');
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Save failed', 'error');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading prompt..." />;
  if (error) return <p style={{ color: 'var(--danger)' }}>Error loading prompt: {error}</p>;

  return (
    <>
      <div className="toolbar">
        <h2>Agent Prompt</h2>
        <button className="btn btn-primary" disabled={!isDirty || saving} onClick={handleSave}>
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
      <div className="prompt-editor-wrap">
        <textarea
          className="prompt-textarea"
          spellCheck={false}
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
        <p className="prompt-meta">{meta}</p>
      </div>
    </>
  );
}
