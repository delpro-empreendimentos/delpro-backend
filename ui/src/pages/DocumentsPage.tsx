import { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { useToast } from '../context/ToastContext';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { FileCard } from '../components/FileCard';
import { Modal } from '../components/Modal';
import { UploadZone } from '../components/UploadZone';
import { TabPanel } from '../components/TabPanel';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { formatBytes, formatDate, getFileIcon } from '../utils';
import type { Document } from '../types';

export function DocumentsPage() {
  const api = useApi();
  const toast = useToast();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [detailDoc, setDetailDoc] = useState<Document | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; filename: string } | null>(null);

  const loadList = async () => {
    try {
      const docs = await api.listDocuments();
      setDocuments(docs);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCardClick = async (id: string) => {
    try {
      const doc = await api.getDocument(id);
      setDetailDoc(doc);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Failed to load document', 'error');
    }
  };

  return (
    <>
      <div className="toolbar">
        <h2>Documents</h2>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
          ➕ Upload Documents
        </button>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading documents..." />
      ) : error ? (
        <p style={{ color: 'var(--danger)' }}>Error loading documents: {error}</p>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <div className="icon">📂</div>
          <p>No documents yet. Upload your first document!</p>
        </div>
      ) : (
        <div className="file-grid">
          {documents.map((doc) => (
            <FileCard key={doc.id} doc={doc} onClick={() => handleCardClick(doc.id)} />
          ))}
        </div>
      )}

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            toast('Documents uploaded successfully!', 'success');
            loadList();
          }}
        />
      )}

      {detailDoc && (
        <DetailModal
          doc={detailDoc}
          onClose={() => setDetailDoc(null)}
          onSaved={() => {
            setDetailDoc(null);
            toast('Document saved!', 'success');
            loadList();
          }}
          onDelete={() => {
            const d = detailDoc;
            setDetailDoc(null);
            setDeleteTarget({ id: d.id, filename: d.filename });
          }}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Delete Document"
          message={
            <>
              Are you sure you want to delete <strong>{deleteTarget.filename}</strong>?
            </>
          }
          warning="This will also remove all associated chunks and embeddings."
          onConfirm={async () => {
            try {
              await api.deleteDocument(deleteTarget.id);
              setDeleteTarget(null);
              toast('Document deleted', 'success');
              loadList();
            } catch (err: unknown) {
              toast(err instanceof Error ? err.message : 'Delete failed', 'error');
            }
          }}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
    </>
  );
}

// ─── Upload Modal ─────────────────────────────────────────────────────────────

function UploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const api = useApi();
  const toast = useToast();
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);

  const addFiles = (newFiles: File[]) => {
    setFiles((prev) => {
      const combined = [...prev];
      for (const f of newFiles) {
        if (combined.length >= 5) break;
        combined.push(f);
      }
      return combined;
    });
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    setUploading(true);
    try {
      await api.uploadDocuments(files);
      onUploaded();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Upload failed', 'error');
      setUploading(false);
    }
  };

  return (
    <Modal
      onClose={onClose}
      title="Upload Documents"
      footer={
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={files.length === 0 || uploading} onClick={handleUpload}>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      }
    >
      <UploadZone
        icon="⬆️"
        message="Drag & drop PDF or TXT files here, or click to browse"
        hint="Up to 5 files at once"
        accept=".pdf,.txt,application/pdf,text/plain"
        multiple
        onFiles={addFiles}
      />
      {files.length > 0 && (
        <div>
          {files.map((f, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '6px 0',
                borderBottom: '1px solid #f0f0f0',
              }}
            >
              <span style={{ fontSize: '14px' }}>
                {f.name} ({formatBytes(f.size)})
              </span>
              <button className="btn btn-sm btn-danger" onClick={() => removeFile(i)}>
                &times;
              </button>
            </div>
          ))}
        </div>
      )}
    </Modal>
  );
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function DetailModal({
  doc,
  onClose,
  onSaved,
  onDelete,
}: {
  doc: Document;
  onClose: () => void;
  onSaved: () => void;
  onDelete: () => void;
}) {
  const api = useApi();
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [filename, setFilename] = useState(doc.filename);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const originalTextRef = useRef<string>('');

  const isPdf = doc.content_type === 'application/pdf';
  const isTxt = doc.content_type === 'text/plain';
  const icon = getFileIcon(doc.content_type);

  useEffect(() => {
    let cancelled = false;

    const loadContent = async () => {
      try {
        const res = await api.getDocumentContent(doc.id);
        if (cancelled) return;

        if (isPdf) {
          const blob = await res.blob();
          if (cancelled) return;
          const url = URL.createObjectURL(blob);
          setBlobUrl(url);
        } else if (isTxt) {
          const text = await res.text();
          if (cancelled) return;
          setTextContent(text);
          originalTextRef.current = text;
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setPreviewError(err instanceof Error ? err.message : 'Failed to load preview');
        }
      }
    };

    loadContent();
    return () => {
      cancelled = true;
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc.id]);

  const handleSave = async () => {
    setSaving(true);
    try {
      let hasChanges = false;

      const newName = filename.trim();
      if (newName && newName !== doc.filename) {
        await api.updateDocument(doc.id, { filename: newName });
        hasChanges = true;
      }

      if (isTxt && textContent !== null) {
        await api.updateDocumentContent(doc.id, textContent);
        hasChanges = true;
      }

      if (!hasChanges) {
        toast('No changes to save', 'error');
        setSaving(false);
        return;
      }

      onSaved();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Save failed', 'error');
      setSaving(false);
    }
  };

  const previewTab = (
    <>
      {previewError ? (
        <p style={{ color: 'var(--danger)' }}>Failed to load preview: {previewError}</p>
      ) : isPdf ? (
        blobUrl ? (
          <object data={blobUrl} type="application/pdf" className="preview-pdf">
            <p>
              Unable to display PDF.{' '}
              <a href={blobUrl} target="_blank" rel="noreferrer">
                Download
              </a>
            </p>
          </object>
        ) : (
          <LoadingSpinner message="Loading preview..." />
        )
      ) : isTxt ? (
        textContent !== null ? (
          <textarea
            className="notepad-textarea"
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
          />
        ) : (
          <LoadingSpinner message="Loading content..." />
        )
      ) : null}
    </>
  );

  const infoTab = (
    <>
      <div className="form-group">
        <label>Filename</label>
        <input type="text" value={filename} onChange={(e) => setFilename(e.target.value)} />
      </div>
      <div className="detail-row">
        <span className="label">Type</span>
        <span className="value">{doc.content_type}</span>
      </div>
      <div className="detail-row">
        <span className="label">Size</span>
        <span className="value">{formatBytes(doc.file_size_bytes)}</span>
      </div>
      <div className="detail-row">
        <span className="label">Uploaded</span>
        <span className="value">{formatDate(doc.upload_date)}</span>
      </div>
    </>
  );

  return (
    <Modal
      onClose={onClose}
      title={`${icon.symbol} ${doc.filename}`}
      footer={
        <div className="modal-footer-actions">
          <button className="btn btn-primary" disabled={saving} onClick={handleSave}>
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button className="btn btn-danger" onClick={onDelete}>
            Delete
          </button>
          <button className="btn btn-gray footer-cancel" onClick={onClose}>
            Cancel
          </button>
        </div>
      }
    >
      <TabPanel
        tabs={[
          { id: 'preview', label: 'Preview', content: previewTab },
          { id: 'information', label: 'Information', content: infoTab },
        ]}
      />
    </Modal>
  );
}
