import { useState, useEffect, useRef } from 'react';
import { useApi } from '../hooks/useApi';
import { useToast } from '../context/ToastContext';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { ImageCard } from '../components/ImageCard';
import { Modal } from '../components/Modal';
import { UploadZone } from '../components/UploadZone';
import { TabPanel } from '../components/TabPanel';
import { ConfirmDialog } from '../components/ConfirmDialog';
import { Lightbox } from '../components/Lightbox';
import { formatBytes, formatDate } from '../utils';
import type { Image } from '../types';

export function ImagesPage() {
  const api = useApi();
  const toast = useToast();
  const [images, setImages] = useState<Image[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [detailImage, setDetailImage] = useState<Image | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; filename: string } | null>(null);

  const loadList = async () => {
    try {
      const imgs = await api.listImages();
      setImages(imgs);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load images');
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
      const img = await api.getImage(id);
      setDetailImage(img);
    } catch (err: unknown) {
      toast(err instanceof Error ? err.message : 'Failed to load image', 'error');
    }
  };

  return (
    <>
      <div className="toolbar">
        <h2>Images</h2>
        <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
          ➕ Upload Image
        </button>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading images..." />
      ) : error ? (
        <p style={{ color: 'var(--danger)' }}>Error loading images: {error}</p>
      ) : images.length === 0 ? (
        <div className="empty-state">
          <div className="icon">🖼️</div>
          <p>No images yet. Upload your first image!</p>
        </div>
      ) : (
        <div className="file-grid">
          {images.map((img) => (
            <ImageCard
              key={img.id}
              image={img}
              imageUrl={api.imageContentUrl(img.id)}
              onClick={() => handleCardClick(img.id)}
            />
          ))}
        </div>
      )}

      {showUpload && (
        <ImageUploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            toast('Image uploaded successfully!', 'success');
            loadList();
          }}
        />
      )}

      {detailImage && (
        <ImageDetailModal
          image={detailImage}
          onClose={() => setDetailImage(null)}
          onSaved={() => {
            setDetailImage(null);
            toast('Image updated!', 'success');
            loadList();
          }}
          onDelete={() => {
            const img = detailImage;
            setDetailImage(null);
            setDeleteTarget({ id: img.id, filename: img.filename });
          }}
        />
      )}

      {deleteTarget && (
        <ConfirmDialog
          title="Delete Image"
          message={
            <>
              Are you sure you want to delete <strong>{deleteTarget.filename}</strong>?
            </>
          }
          onConfirm={async () => {
            try {
              await api.deleteImage(deleteTarget.id);
              setDeleteTarget(null);
              toast('Image deleted', 'success');
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

function ImageUploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: () => void }) {
  const api = useApi();
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [uploading, setUploading] = useState(false);

  const handleFile = (files: File[]) => {
    if (files[0]) {
      setFile(files[0]);
      setPreviewUrl(URL.createObjectURL(files[0]));
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
      await api.uploadImage(file, description.trim());
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
      title="Upload Image"
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
          message="Drag & drop a JPEG or PNG image, or click to browse"
          hint="Max 5 MB"
          accept="image/jpeg,image/png,.jpg,.jpeg,.png"
          onFiles={handleFile}
        />
      ) : (
        <div className="staged-image-preview">
          <img src={previewUrl!} alt="" />
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
          placeholder="Describe this image..."
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
    </Modal>
  );
}

// ─── Detail Modal ─────────────────────────────────────────────────────────────

function ImageDetailModal({
  image,
  onClose,
  onSaved,
  onDelete,
}: {
  image: Image;
  onClose: () => void;
  onSaved: () => void;
  onDelete: () => void;
}) {
  const api = useApi();
  const toast = useToast();
  const [saving, setSaving] = useState(false);
  const [filename, setFilename] = useState(image.filename);
  const [description, setDescription] = useState(image.description || '');
  const [newFile, setNewFile] = useState<File | null>(null);
  const [previewSrc, setPreviewSrc] = useState(api.imageContentUrl(image.id));
  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  const handleReplace = () => replaceInputRef.current?.click();

  const handleReplaceChange = () => {
    const f = replaceInputRef.current?.files?.[0];
    if (f) {
      setNewFile(f);
      const url = URL.createObjectURL(f);
      setPreviewSrc(url);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      let hasChanges = false;

      if (newFile) {
        await api.replaceImageContent(image.id, newFile);
        hasChanges = true;
      }

      const updates: Record<string, string> = {};
      const newName = filename.trim();
      const newDesc = description.trim();
      if (newName && newName !== image.filename) updates.filename = newName;
      if (newDesc && newDesc !== image.description) updates.description = newDesc;

      if (Object.keys(updates).length > 0) {
        await api.updateImage(image.id, updates);
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
        <img src={previewSrc} alt={image.filename} />
        <button className="image-fullscreen-btn" title="View fullscreen" onClick={() => setLightboxSrc(previewSrc)}>
          ⛶
        </button>
        <button className="image-replace-btn" onClick={handleReplace}>
          📷 Replace Image
        </button>
      </div>
      <input
        ref={replaceInputRef}
        type="file"
        accept="image/jpeg,image/png,.jpg,.jpeg,.png"
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
        <span className="value">{formatDate(image.created_at)}</span>
      </div>
      <div className="detail-row">
        <span className="label">Size</span>
        <span className="value">{formatBytes(image.file_size_bytes)}</span>
      </div>
    </>
  );

  return (
    <>
      <Modal
        onClose={onClose}
        title="Image Details"
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
      {lightboxSrc && <Lightbox src={lightboxSrc} alt={image.filename} onClose={() => setLightboxSrc(null)} />}
    </>
  );
}
