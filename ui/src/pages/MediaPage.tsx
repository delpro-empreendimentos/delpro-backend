import { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { useToast } from '../context/ToastContext';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Pagination } from '../components/Pagination';
import { MediaCard } from '../components/MediaCard';
import { Modal } from '../components/Modal';
import { UploadZone } from '../components/UploadZone';
import { TabPanel } from '../components/TabPanel';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { Lightbox } from '../components/Lightbox';
import { formatBytes, formatDate } from '../utils';
import type { Media } from '../types';

const PAGE_SIZE = 20;
const ACCEPT_TYPES = 'image/jpeg,image/png,application/pdf,.jpg,.jpeg,.png,.pdf';

export function MediaPage() {
  const api = useApi();
  const toast = useToast();
  const [media, setMedia] = useState<Media[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [detailMedia, setDetailMedia] = useState<Media | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; filename: string } | null>(null);

  const loadList = async (p = page) => {
    try {
      const result = await api.listMedia((p - 1) * PAGE_SIZE, PAGE_SIZE);
      setMedia(result.items);
      setTotal(result.total);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load media');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setLoading(true);
    loadList(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handleCardClick = async (id: string) => {
    try {
      const item = await api.getMedia(id);
      setDetailMedia(item);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Failed to load media', 'error');
    }
  };

  return (
    <>
      <div className="toolbar">
        <h2>Media</h2>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
          ➕ Upload Media
        </button>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading media..." />
      ) : error ? (
        <p style={{ color: 'var(--danger)' }}>Error loading media: {error}</p>
      ) : media.length === 0 ? (
        <div className="empty-state">
          <div className="icon">🖼️</div>
          <p>No media yet. Upload your first image or PDF!</p>
        </div>
      ) : (
        <>
          <div className="file-grid">
            {media.map((item) => (
              <MediaCard
                key={item.id}
                media={item}
                mediaUrl={api.mediaContentUrl(item.id)}
                onClick={() => handleCardClick(item.id)}
              />
            ))}
          </div>
          <Pagination page={page} total={total} pageSize={PAGE_SIZE} onChange={setPage} />
        </>
      )}

      {showUpload && (
        <MediaUploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            toast('Media uploaded successfully!', 'success');
            setPage(1);
            loadList(1);
          }}
        />
      )}

      {detailMedia && (
        <MediaDetailModal
          media={detailMedia}
          onClose={() => setDetailMedia(null)}
          onSaved={() => {
            setDetailMedia(null);
            toast('Media updated!', 'success');
            loadList(page);
          }}
          onDelete={() => {
            const item = detailMedia;
            setDetailMedia(null);
            setDeleteTarget({ id: item.id, filename: item.filename });
          }}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Delete Media"
          message={
            <>
              Are you sure you want to delete <strong>{deleteTarget.filename}</strong>?
            </>
          }
          onConfirm={async () => {
            try {
              await api.deleteMedia(deleteTarget.id);
              setDeleteTarget(null);
              toast('Media deleted', 'success');
              setPage(1);
              loadList(1);
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

function MediaUploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const api = useApi();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);

  const isPdf = file?.type === 'application/pdf';

  const handleFile = (files: File[]) => {
    if (files[0]) {
      setFile(files[0]);
      if (files[0].type !== 'application/pdf') {
        setPreviewUrl(URL.createObjectURL(files[0]));
      } else {
        setPreviewUrl(null);
      }
    }
  };

  const removeFile = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(null);
    setPreviewUrl(null);
  };

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    try {
      await api.uploadMedia(file, description.trim());
      onUploaded();
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Upload failed', 'error');
      setUploading(false);
    }
  };

  const canUpload = file !== null && description.trim().length > 0 && !uploading;

  return (
    <Modal
      onClose={onClose}
      title="Upload Media"
      footer={
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" disabled={!canUpload} onClick={handleUpload}>
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      }
    >
      {!file ? (
        <UploadZone
          icon="🖼️"
          message="Drag & drop an image or PDF, or click to browse"
          hint="Max 5 MB for images, 20 MB for PDFs"
          accept={ACCEPT_TYPES}
          onFiles={handleFile}
        />
      ) : (
        <div className="staged-image-preview">
          {isPdf ? (
            <div className="pdf-preview-placeholder">
              <span className="pdf-icon-large">PDF</span>
            </div>
          ) : (
            <img src={previewUrl!} alt="" />
          )}
          <button className="staged-remove-btn" onClick={removeFile} title="Remove">
            &times;
          </button>
          <p className="staged-filename">
            {file.name} ({formatBytes(file.size)})
          </p>
        </div>
      )}
      <div className="form-group" style={{ marginTop: '16px' }}>
        <label>Description *</label>
        <textarea
          placeholder="Describe this media file..."
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
    </Modal>
  );
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function MediaDetailModal({
  media,
  onClose,
  onSaved,
  onDelete,
}: {
  media: Media;
  onClose: () => void;
  onSaved: () => void;
  onDelete: () => void;
}) {
  const api = useApi();
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [filename, setFilename] = useState(media.filename);
  const [description, setDescription] = useState(media.description || '');
  const [newFile, setNewFile] = useState<File | null>(null);
  const [previewSrc, setPreviewSrc] = useState(api.mediaContentUrl(media.id));
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  const isPdf = newFile?.type === 'application/pdf' || (!newFile && media.content_type === 'application/pdf');

  const handleReplace = () => replaceInputRef.current?.click();

  const handleReplaceChange = () => {
    const f = replaceInputRef.current?.files?.[0];
    if (f) {
      setNewFile(f);
      if (f.type !== 'application/pdf') {
        const url = URL.createObjectURL(f);
        setPreviewSrc(url);
      } else {
        setPreviewSrc('');
      }
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      let hasChanges = false;

      if (newFile) {
        await api.replaceMediaContent(media.id, newFile);
        hasChanges = true;
      }

      const updates: Record<string, string> = {};
      const newName = filename.trim();
      const newDesc = description.trim();
      if (newName && newName !== media.filename) updates.filename = newName;
      if (newDesc && newDesc !== media.description) updates.description = newDesc;

      if (Object.keys(updates).length > 0) {
        await api.updateMedia(media.id, updates);
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
      <div className="image-preview-box">
        {isPdf ? (
          <div className="pdf-preview-placeholder">
            <span className="pdf-icon-large">PDF</span>
            <a href={api.mediaContentUrl(media.id)} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ marginTop: '8px' }}>
              Open PDF
            </a>
          </div>
        ) : (
          <>
            <img src={previewSrc} alt={media.filename} />
            <button className="image-fullscreen-btn" title="View fullscreen" onClick={() => setLightboxSrc(previewSrc)}>
              ⛶
            </button>
          </>
        )}
        <button className="image-replace-btn" onClick={handleReplace}>
          Replace File
        </button>
      </div>
      <input
        ref={replaceInputRef}
        type="file"
        accept={ACCEPT_TYPES}
        style={{ display: 'none' }}
        onChange={handleReplaceChange}
      />
    </>
  );

  const infoTab = (
    <>
      <div className="form-group">
        <label>Filename</label>
        <input type="text" value={filename} onChange={(e) => setFilename(e.target.value)} />
      </div>
      <div className="form-group">
        <label>Description</label>
        <textarea rows={3} value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>
      <div className="detail-row">
        <span className="label">Created</span>
        <span className="value">{formatDate(media.created_at)}</span>
      </div>
      <div className="detail-row">
        <span className="label">Size</span>
        <span className="value">{formatBytes(media.file_size_bytes)}</span>
      </div>
    </>
  );

  return (
    <>
      <Modal
        onClose={onClose}
        title="Media Details"
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
      {lightboxSrc && <Lightbox src={lightboxSrc} alt={media.filename} onClose={() => setLightboxSrc(null)} />}
    </>
  );
}
