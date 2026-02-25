import { Modal } from './Modal';
import type { ReactNode } from 'react';

interface ConfirmDialogProps {
  title: string;
  message: ReactNode;
  warning?: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({ title, message, warning, confirmLabel = 'Delete', onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <Modal onClose={onCancel} title={title} maxWidth="400px">
      <p>{message}</p>
      {warning && (
        <p style={{ color: 'var(--danger)', fontSize: '13px', marginTop: '8px' }}>{warning}</p>
      )}
      <div className="confirm-actions">
        <button className="btn btn-secondary" onClick={onCancel}>
          Cancel
        </button>
        <button className="btn btn-danger" onClick={onConfirm}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
